"""
应力计算模块 - 符合CECS 214-2006规范
(已修复假重构与力学核心错误)
"""
import math
from models.pipe import PipeModel
from models.load import LoadModel

class StressResult:
    def __init__(self):
        self.sigma_theta_Fw = 0     
        self.sigma_theta_M = 0      
        self.sigma_theta_total = 0  
        self.sigma_x_M = 0          
        self.sigma_x_Fw = 0         
        self.sigma_x_t = 0          
        self.sigma_x_t_reduced = 0  
        self.sigma_x_friction = 0   
        self.sigma_x_total = 0      
        self.sigma_x_local_out = 0  
        self.sigma_x_local_in = 0   
        self.beta = 0               
        self.tau_avg = 0            
        self.tau_max = 0            
        self.combined_stress = 0    
        self.combined_stress_support = 0 
        self.is_safe = False
        self.is_safe_support = False  
        self.safety_factor = 0
        self.safety_factor_support = 0
        self.formula_refs = {}      

def calculate_stress(pipe: PipeModel, load: LoadModel, vertical_load_kN: float, horizontal_load_kN: float = 0) -> StressResult:
    result = StressResult()
    
    D = pipe.diameter_mm          
    r = pipe.inner_radius_mm     
    t = pipe.wall_thickness_mm  
    A = pipe.cross_section_area_mm2  
    W = pipe.section_modulus_mm3    
    I = pipe.moment_of_inertia_mm4  
    f = pipe.design_strength_MPa    
    f_reduced = pipe.reduced_strength_MPa  
    
    p = load.internal_pressure_MPa  
    R_y = vertical_load_kN * pipe.span_m / 2 * 1000  # N
    L_mm = pipe.span_m * 1000       
    theta = pipe.support_half_angle   
    zeta = load.temperature_stress_reduction  
    
    # 1. 环向应力
    result.sigma_theta_Fw = p * r / t
    
    # 2. 轴向应力计算
    q_vertical = vertical_load_kN  
    My = q_vertical * L_mm**2 / 8  
    result.sigma_x_M = My / W
    
    if horizontal_load_kN > 0:
        Mz = horizontal_load_kN * L_mm**2 / 8  
        result.sigma_x_M_horizontal = Mz / W
    else:
        result.sigma_x_M_horizontal = 0
    
    result.sigma_x_M_combined = math.sqrt(result.sigma_x_M**2 + result.sigma_x_M_horizontal**2)
    
    theta_rad = math.radians(theta)
    result.sigma_x_Fw = p * r / (2 * t) * (1 - math.cos(theta_rad)) / math.pi
    
    # 【修复 ERR-06】: 温度应力带有正负号，不能盲目取绝对值，正温差(膨胀受阻)产生压应力(-)
    alpha = 12e-6         
    E = 206000           
    Delta_T = load.temperature_load_C  
    result.sigma_x_t = -alpha * E * Delta_T 
    result.sigma_x_t_reduced = result.sigma_x_t * zeta
    
    mu = pipe.friction_coefficient  
    result.sigma_x_friction = mu * R_y / A
    
    # 3. 剪应力计算
    # 【修复 FATAL-05】: 简支梁支座最大剪力 V 应当等于支座反力 R_y
    V = R_y  
    result.tau_avg = V / A
    # 【修复 ERR-07】: 圆管截面最大剪应力系数是 2.0
    result.tau_max = 2.0 * result.tau_avg
    
    # 4. 局部应力
    support_type = pipe.support_type.value if hasattr(pipe.support_type, 'value') else pipe.support_type
    if support_type == "环式支承":
        result.beta = 0.9
        result.sigma_x_local_out = -1.82 * result.beta * result.sigma_theta_Fw
        result.sigma_x_local_in = 1.82 * result.beta * result.sigma_theta_Fw
    
    # 【修复 FATAL-02】: 彻底删除这句散装的缝合怪公式！强制调用分离截面验算
    midspan_check = check_midspan_stress(result, pipe, load)
    support_check = check_support_stress(result, pipe, load)
    
    # 跨中验算结果赋值
    result.combined_stress = max(midspan_check["sigma_combined_top"], midspan_check["sigma_combined_bottom"])
    result.is_safe = midspan_check["is_safe"]
    result.safety_factor = midspan_check["allowable"] / result.combined_stress if result.combined_stress > 0 else 999
    
    # 支座验算结果赋值
    result.combined_stress_support = support_check["tau_with_local"]
    result.is_safe_support = support_check["is_safe"]
    result.safety_factor_support = support_check["allowable"] / result.combined_stress_support if result.combined_stress_support > 0 else 999

    return result

def calculate_support_reaction(pipe: PipeModel, total_load_kN: float) -> float:
    return total_load_kN * 1000 / 2 

def calculate_shear_force(pipe: PipeModel, total_load_kN: float) -> float:
    return total_load_kN * 1000 / 2  

def calculate_bending_moment(pipe: PipeModel, total_load_kN: float) -> float:
    L_mm = pipe.span_m * 1000  
    q_N_per_mm = total_load_kN * 1000 / L_mm  
    return q_N_per_mm * L_mm**2 / 8  

def check_midspan_stress(stress_result: StressResult, pipe: PipeModel, load: LoadModel) -> dict:
    """跨中截面严谨验算：考虑上下边缘受力状态"""
    result = {"is_safe": True}
    
    sigma_M = stress_result.sigma_x_M_combined  # 弯曲应力绝对值
    sigma_Fw = stress_result.sigma_x_Fw  # 内水压轴向拉伸(+)
    sigma_t = stress_result.sigma_x_t_reduced  # 温度应力(+/-)
    sigma_fric = stress_result.sigma_x_friction # 摩擦(暂按最不利叠加)
    
    sigma_axial_max = sigma_Fw + abs(sigma_t) + sigma_fric
    sigma_axial_min = sigma_Fw - abs(sigma_t) - sigma_fric
    
    # 管顶/管底最不利应力
    result["sigma_top"] = -sigma_M + sigma_axial_min  # 最大受压
    result["sigma_bottom"] = sigma_M + sigma_axial_max # 最大受拉
    
    sigma_theta = stress_result.sigma_theta_Fw
    
    def calc_fourth_theory(sigma_x, sigma_theta):
        return math.sqrt(sigma_x**2 + sigma_theta**2 - sigma_x * sigma_theta)
        
    result["sigma_combined_top"] = calc_fourth_theory(result["sigma_top"], sigma_theta)
    result["sigma_combined_bottom"] = calc_fourth_theory(result["sigma_bottom"], sigma_theta)
    
    allowable = 0.9 * pipe.weld_reduction_coefficient * pipe.design_strength_MPa / load.importance_factor
    result["is_safe"] = (result["sigma_combined_top"] <= allowable and result["sigma_combined_bottom"] <= allowable)
    result["allowable"] = allowable
    
    return result

def check_support_stress(stress_result: StressResult, pipe: PipeModel, load: LoadModel) -> dict:
    result = {"is_safe": True}
    tau = stress_result.tau_max
    
    if hasattr(stress_result, 'sigma_x_local_in') and stress_result.sigma_x_local_in != 0:
        sigma_local = stress_result.sigma_x_local_in
        result["tau_with_local"] = math.sqrt(sigma_local**2 + 3 * tau**2)
    else:
        result["tau_with_local"] = math.sqrt(3) * tau
        
    allowable_tau = 0.9 * pipe.weld_reduction_coefficient * pipe.design_strength_MPa / load.importance_factor
    result["is_safe"] = result["tau_with_local"] <= allowable_tau
    result["allowable"] = allowable_tau
    
    return result
