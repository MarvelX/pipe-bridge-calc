"""
应力计算模块 - 符合CECS 214-2006规范
平管强度计算 (第7.2节)
"""
import math
from models.pipe import PipeModel
from models.load import LoadModel


class StressResult:
    """
    应力计算结果 - 符合CECS 214-2006规范第7.2节
    """
    def __init__(self):
        # ========== 环向应力 σθ ==========
        self.sigma_theta_Fw = 0      # 内水压产生的环向拉应力 (7.2.1)
        self.sigma_theta_M = 0       # 弯曲产生的环向应力
        self.sigma_theta_total = 0   # 总环向应力
        
        # ========== 轴向应力 σx (跨中) ==========
        self.sigma_x_M = 0           # 竖向弯曲应力 (7.2.2-1): σ = M/W
        self.sigma_x_Fw = 0          # 内水压轴向拉应力 (7.2.2-2,3): σ = N_H/A
        self.sigma_x_t = 0           # 温度应力 (7.2.2-4): σ = αEΔT
        self.sigma_x_t_reduced = 0  # 折减后温度应力
        self.sigma_x_friction = 0    # 摩擦应力 (7.2.2-5): σ = μR/A
        self.sigma_x_total = 0      # 总轴向应力 (跨中)
        
        # ========== 支座处局部应力 (7.2.4条 - 环式支承) ==========
        self.sigma_x_local_out = 0   # 支座处管壁外面局部纵向应力
        self.sigma_x_local_in = 0    # 支座处管壁内面局部纵向应力
        self.beta = 0                # 环式支承环相对刚度影响系数
        
        # ========== 剪切应力 τ ==========
        self.tau_avg = 0            # 平均剪应力 (7.2.3-1): τ = V/A
        self.tau_max = 0            # 最大剪应力 (7.2.3-2): τ = VQ/(It)
        
        # ========== 组合应力 ==========
        self.combined_stress = 0    # 折算应力 (第四强度理论) - 跨中
        self.combined_stress_support = 0  # 折算应力 - 支座处
        self.is_safe = False
        self.is_safe_support = False  # 支座处强度验算
        self.safety_factor = 0
        self.safety_factor_support = 0
        
        # ========== 应力公式引用 ==========
        self.formula_refs = {}       # 公式引用字典


def calculate_stress(pipe: PipeModel, load: LoadModel, 
                   vertical_load_kN: float, horizontal_load_kN: float = 0) -> StressResult:
    """
    计算管道应力 - CECS 214-2006 第7.2节
    
    Args:
        pipe: 管道模型
        load: 荷载模型
        vertical_load_kN: 竖向线荷载 (kN/m)
        horizontal_load_kN: 水平线荷载 (kN/m)
    """
    result = StressResult()
    
    # ========== 管道几何参数 ==========
    D = pipe.diameter_mm          # 外径 mm
    r = pipe.inner_radius_mm     # 内半径 mm
    t = pipe.wall_thickness_mm  # 壁厚 mm
    A = pipe.cross_section_area_mm2  # 截面积 mm²
    W = pipe.section_modulus_mm3    # 截面抵抗矩 mm³
    I = pipe.moment_of_inertia_mm4  # 惯性矩 mm⁴
    f = pipe.design_strength_MPa    # 钢材设计强度 MPa
    f_reduced = pipe.reduced_strength_MPa  # 焊缝折减后设计强度 MPa
    
    p = load.internal_pressure_MPa  # 内水压 MPa = N/mm²
    # 支座反力 R = qL/2 (简支梁)
    # 传入的是线荷载(kN/m)，需要乘以跨长再除以2
    R_y = vertical_load_kN * pipe.span_m / 2 * 1000  # N
    L = pipe.span_m * 1000            # 跨长 mm
    theta = pipe.support_half_angle   # 支承半角 (度)
    zeta = load.temperature_stress_reduction  # 温度应力折减系数
    
    # ========== 1. 环向应力计算 (规范7.2.1) ==========
    # σθ = p·r / t
    result.sigma_theta_Fw = p * r / t
    result.formula_refs['sigma_theta'] = {
        'formula': 'σθ = p·r / t',
        'ref': 'CECS 214-2006 第7.2.1条',
        'desc': '内水压力产生的环向拉应力'
    }
    
    # ========== 2. 轴向应力计算 (规范7.2.2) ==========
    
    # 2.1 竖向弯曲应力 (7.2.2-1): σ = My/W
    # 正确公式: My = qyL²/8 (简支梁跨中最大弯矩)
    # 其中 qy = 竖向线荷载(kN/m), L = 跨长
    # 需要转换为 N/mm
    q_vertical = vertical_load_kN  # kN/m = N/mm (数值相同)
    L_mm = pipe.span_m * 1000  # mm
    My = q_vertical * L_mm**2 / 8  # N·mm (竖向弯矩)
    result.sigma_x_M = My / W
    
    # 2.1b 水平弯曲应力 (风荷载产生的水平弯矩)
    # Mz = qzL²/8 (简支梁跨中最大弯矩)
    if horizontal_load_kN > 0:
        q_horizontal = horizontal_load_kN  # kN/m = N/mm
        Mz = q_horizontal * L_mm**2 / 8  # N·mm (水平弯矩)
        result.sigma_x_M_horizontal = Mz / W
    else:
        result.sigma_x_M_horizontal = 0
    
    # 总弯矩矢量合成 (My² + Mz²)^0.5
    result.sigma_x_M_combined = math.sqrt(result.sigma_x_M**2 + result.sigma_x_M_horizontal**2)
    result.formula_refs['sigma_x_M'] = {
        'formula': 'σx,M = M / W',
        'ref': 'CECS 214-2006 公式(7.2.2-1)',
        'desc': '竖向作用下管壁纵向弯曲应力'
    }
    
    # 2.2 内水压产生的轴向拉应力 (7.2.2-2,3)
    # 根据支承半角计算: σ = γF(1-cosθ)/(2πrt)
    # 简化: 对于鞍式支承(θ=90°~120°): σ = p·r/(2t) × (1-cosθ)/π
    theta_rad = math.radians(theta)
    result.sigma_x_Fw = p * r / (2 * t) * (1 - math.cos(theta_rad)) / math.pi
    result.formula_refs['sigma_x_Fw'] = {
        'formula': 'σx,F = p·r/(2t) × (1-cosθ)/π',
        'ref': 'CECS 214-2006 公式(7.2.2-2,3)',
        'desc': '设计内水压力产生的纵向拉应力'
    }
    
    # 2.3 温度应力 (7.2.2-4): σ = αEΔT
    alpha = 12e-6         # 钢材线膨胀系数 1/°C
    E = 206000           # 弹性模量 MPa
    Delta_T = load.temperature_load_C  # 温差 °C
    result.sigma_x_t = alpha * E * abs(Delta_T)
    # 折减后温度应力
    result.sigma_x_t_reduced = result.sigma_x_t * zeta
    result.formula_refs['sigma_x_t'] = {
        'formula': 'σx,T = ζ·α·E·ΔT',
        'ref': 'CECS 214-2006 公式(7.2.2-4)',
        'desc': f'温度变化产生的温度应力 (折减系数ζ={zeta})'
    }
    
    # 2.4 摩擦应力 (7.2.2-5): σ = μR/A
    mu = pipe.friction_coefficient  # 摩擦系数
    result.sigma_x_friction = mu * R_y / A
    result.formula_refs['sigma_x_friction'] = {
        'formula': 'σx,μ = μR / A',
        'ref': 'CECS 214-2006 公式(7.2.2-5)',
        'desc': '支座摩擦产生的纵向应力'
    }
    
    # 2.5 总轴向应力 (使用合成后的弯曲应力)
    result.sigma_x_total = (result.sigma_x_M_combined + 
                           result.sigma_x_Fw + 
                           result.sigma_x_t_reduced + 
                           result.sigma_x_friction)
    
    # ========== 3. 剪应力计算 (规范7.2.3) ==========
    
    # 3.1 剪力 V = R (简支梁支座处剪力等于支座反力)
    V = R_y  # 剪力 N (简支梁支座处)
    result.tau_avg = V / A
    result.formula_refs['tau_avg'] = {
        'formula': 'τ = V / A',
        'ref': 'CECS 214-2006 公式(7.2.3-1)',
        'desc': '管壁截面平均剪应力'
    }
    
    # 3.2 最大剪应力 (7.2.3-2): τ = VQ/(It)
    # 简化: 对于圆管，最大剪应力约为平均剪应力的1.5倍
    result.tau_max = 1.5 * result.tau_avg
    result.formula_refs['tau_max'] = {
        'formula': 'τmax = V·Q/(I·t) ≈ 1.5τavg (圆管简化)',
        'ref': 'CECS 214-2006 公式(7.2.3-2)',
        'desc': '管壁截面中和轴处最大剪应力'
    }
    
    # ========== 4. 组合折算应力 (第四强度理论) ==========
    # σ = √(σx² + σθ² - σx×σθ + 3τ²)
    sigma_x = result.sigma_x_total
    sigma_theta = result.sigma_theta_Fw
    tau = result.tau_max
    
    result.combined_stress = math.sqrt(
        sigma_x**2 + sigma_theta**2 - sigma_x * sigma_theta + 3 * tau**2
    )
    result.formula_refs['combined'] = {
        'formula': 'σ = √(σx² + σθ² - σx·σθ + 3τ²)',
        'ref': 'CECS 214-2006 第7.1.2条 (第四强度理论)',
        'desc': '跨中组合折算应力'
    }
    
    # ========== 4.1 支座处局部应力计算 (7.2.4条 - 环式支承) ==========
    # 当采用环式支承时，需要计算支座处由内水压力产生的管壁局部纵向应力
    support_type = pipe.support_type.value if hasattr(pipe.support_type, 'value') else pipe.support_type
    if support_type == "环式支承":
        # β为环式支承环相对刚度影响系数，可近似取0.9
        result.beta = 0.9
        # σ'x,out = -1.82βσθ,Fw (外面，受压)
        result.sigma_x_local_out = -1.82 * result.beta * result.sigma_theta_Fw
        # σ'x,in = +1.82βσθ,Fw (内面，受拉)
        result.sigma_x_local_in = 1.82 * result.beta * result.sigma_theta_Fw
        
        result.formula_refs['local_stress'] = {
            'formula': "σ'x = ±1.82βσθ,Fw",
            'ref': 'CECS 214-2006 公式(7.2.4-1,2)',
            'desc': f'环式支承处管壁局部纵向应力 (β={result.beta})'
        }
        
        # 支座处组合折算应力 (考虑局部应力)
        # 支座处轴向应力 = 摩擦应力 + 温度应力 + 局部应力
        sigma_x_support = result.sigma_x_friction + result.sigma_x_t_reduced + result.sigma_x_local_in
        result.combined_stress_support = math.sqrt(
            sigma_x_support**2 + sigma_theta**2 - sigma_x_support * sigma_theta + 3 * tau**2
        )
        result.formula_refs['combined_support'] = {
            'formula': 'σ = √(σx² + σθ² - σx·σθ + 3τ²)',
            'ref': 'CECS 214-2006 第7.1.2条 (支座处)',
            'desc': '支座处组合折算应力'
        }
    else:
        # 鞍式支承不做局部应力计算
        result.combined_stress_support = result.combined_stress
    
    # ========== 5. 强度验算 ==========
    # 使用重构的分离验算函数
    midspan_check = check_midspan_stress(result, pipe, load)
    support_check = check_support_stress(result, pipe, load)
    
    # 跨中强度验算 - 安全系数 = 允许应力 / 计算应力
    sigma_combined_max = max(midspan_check["sigma_combined_top"], midspan_check["sigma_combined_bottom"])
    result.is_safe = midspan_check["is_safe"]
    result.safety_factor = midspan_check["allowable"] / sigma_combined_max if sigma_combined_max > 0 else 999
    
    # 支座处强度验算 (仅环式支承)
    result.is_safe_support = support_check["is_safe"]
    result.safety_factor_support = support_check["allowable"] / support_check["tau_with_local"] if support_check["tau_with_local"] > 0 else 999
    
    # 保存允许应力到formula_refs供UI显示
    result.formula_refs['check'] = {
        'formula': 'σ ≤ 0.9φf/γ0',
        'ref': 'CECS 214-2006 公式(7.1.1)',
        'desc': '强度验算条件',
        'allowable': f'{midspan_check["allowable"]:.1f} MPa',
        'f_reduced': f'{f_reduced:.1f} MPa',
        'phi': f'{pipe.weld_reduction_coefficient}'
    }
    
    return result


def calculate_support_reaction(pipe: PipeModel, total_load_kN: float) -> float:
    """
    计算支座反力
    对于简支梁: R = qL/2 = 总荷载/2
    返回单位: N
    """
    return total_load_kN * 1000 / 2  # N


def calculate_shear_force(pipe: PipeModel, total_load_kN: float) -> float:
    """
    计算剪力 V = R (支座处)
    """
    return total_load_kN * 1000 / 2  # N


def calculate_bending_moment(pipe: PipeModel, total_load_kN: float) -> float:
    """
    计算跨中弯矩 M = qL²/8
    对于简支梁跨中最大弯矩
    """
    L_mm = pipe.span_m * 1000  # mm
    q_N_per_mm = total_load_kN * 1000 / L_mm  # N/mm
    M = q_N_per_mm * L_mm**2 / 8  # N·mm
    return M


def check_midspan_stress(stress_result: StressResult, pipe: PipeModel, load: LoadModel) -> dict:
    """
    跨中截面验算
    - 仅检查最大弯曲应力 + 轴向拉/压应力组合
    - 此时剪应力 τ = 0
    - 需要考虑正负号（管顶与管底分别验算）
    """
    result = {
        "location": "跨中截面",
        "sigma_top": 0,  # 管顶应力
        "sigma_bottom": 0,  # 管底应力
        "sigma_combined_top": 0,
        "sigma_combined_bottom": 0,
        "is_safe": True,
        "details": []
    }
    
    # 管顶应力 = -弯曲应力 + 轴向应力 (压为负)
    # 管底应力 = +弯曲应力 + 轴向应力
    sigma_M = stress_result.sigma_x_M_combined  # 弯曲应力
    sigma_Fw = stress_result.sigma_x_Fw  # 内水压轴向
    sigma_t = stress_result.sigma_x_t_reduced  # 温度应力
    sigma_total_no_M = sigma_Fw + sigma_t  # 轴向应力
    
    # 管顶: 弯曲压应力 + 轴向拉应力
    result["sigma_top"] = -sigma_M + sigma_total_no_M
    # 管底: 弯曲拉应力 + 轴向拉应力  
    result["sigma_bottom"] = sigma_M + sigma_total_no_M
    
    # 第四强度理论 (τ=0时简化为)
    result["sigma_combined_top"] = abs(result["sigma_top"])
    result["sigma_combined_bottom"] = abs(result["sigma_bottom"])
    
    # 允许应力
    f = pipe.design_strength_MPa
    phi = pipe.weld_reduction_coefficient
    gamma_0 = load.importance_factor
    allowable = 0.9 * phi * f / gamma_0
    
    result["is_safe"] = (result["sigma_combined_top"] <= allowable and 
                        result["sigma_combined_bottom"] <= allowable)
    result["allowable"] = allowable
    
    return result


def check_support_stress(stress_result: StressResult, pipe: PipeModel, load: LoadModel) -> dict:
    """
    支座截面验算
    - 仅检查最大剪应力 τ
    - 圆管系数取 2.0 (不是1.5)
    - 考虑局部支座应力
    """
    result = {
        "location": "支座截面",
        "tau_max": 0,
        "tau_with_local": 0,
        "is_safe": True,
        "details": []
    }
    
    # 支座处剪应力系数取2.0
    result["tau_max"] = 2.0 * stress_result.tau_avg
    
    # 考虑局部应力后
    if hasattr(stress_result, 'sigma_x_local_in') and stress_result.sigma_x_local_in != 0:
        # 组合剪应力
        sigma_local = stress_result.sigma_x_local_in
        tau = result["tau_max"]
        result["tau_with_local"] = math.sqrt(sigma_local**2 + 3*tau**2)
    else:
        result["tau_with_local"] = result["tau_max"]
    
    # 允许剪应力 (0.9*0.58f)
    f = pipe.design_strength_MPa
    phi = pipe.weld_reduction_coefficient
    gamma_0 = load.importance_factor
    allowable_tau = 0.9 * 0.58 * phi * f / gamma_0
    
    result["is_safe"] = result["tau_with_local"] <= allowable_tau
    result["allowable"] = allowable_tau
    
    return result
