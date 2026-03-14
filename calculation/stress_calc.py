"""
应力计算模块 - 符合CECS 214-2006规范
平管强度计算 (第7.2节)
"""
import math
from models.pipe import PipeModel, SupportType
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
        
        # ========== 轴向应力 σx ==========
        self.sigma_x_M = 0           # 竖向弯曲应力 (7.2.2-1): σ = M/W
        self.sigma_x_Fw = 0          # 内水压轴向拉应力 (7.2.2-2,3): σ = N_H/A = γF(1-cosθ)/(2πrt)
        self.sigma_x_t = 0           # 温度应力 (7.2.2-4): σ = αEΔT
        self.sigma_x_friction = 0    # 摩擦应力 (7.2.2-5): σ = μR/A
        self.sigma_x_total = 0      # 总轴向应力
        
        # ========== 剪切应力 τ ==========
        self.tau_avg = 0            # 平均剪应力 (7.2.3-1): τ = V/A
        self.tau_max = 0            # 最大剪应力 (7.2.3-2): τ = VQ/(It)
        
        # ========== 组合应力 ==========
        self.combined_stress = 0    # 折算应力 (第四强度理论)
        
        # ========== 应力公式引用 ==========
        self.formula_refs = {}       # 公式引用字典
        
        # ========== 验算结果 ==========
        self.is_safe = False
        self.safety_factor = 0


def calculate_stress(pipe: PipeModel, load: LoadModel, reaction_force_N: float) -> StressResult:
    """
    计算管道应力 - CECS 214-2006 第7.2节
    
    Args:
        pipe: 管道模型
        load: 荷载模型
        reaction_force_N: 支座反力，单位 N
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
    
    p = load.internal_pressure_MPa  # 内水压 MPa = N/mm²
    R = reaction_force_N            # 支座反力 N (已经是N)
    L = pipe.span_m * 1000            # 跨长 mm
    
    # ========== 1. 环向应力计算 (规范7.2.1) ==========
    # σθ = p·r / t
    result.sigma_theta_Fw = p * r / t
    result.formula_refs['sigma_theta'] = {
        'formula': 'σθ = p·r / t',
        'ref': 'CECS 214-2006 第7.2.1条',
        'desc': '内水压力产生的环向拉应力'
    }
    
    # ========== 2. 轴向应力计算 (规范7.2.2) ==========
    
    # 2.1 竖向弯曲应力 (7.2.2-1): σ = M/W
    M = R * L / 8  # 简支梁跨中最大弯矩 N·mm
    result.sigma_x_M = M / W
    result.formula_refs['sigma_x_M'] = {
        'formula': 'σx,M = M / W',
        'ref': 'CECS 214-2006 公式(7.2.2-1)',
        'desc': '竖向作用下管壁纵向弯曲应力'
    }
    
    # 2.2 内水压产生的轴向拉应力 (7.2.2-2,3)
    # 鞍式支承(θ=90°): N_H = γF
    # σ = N_H / A = γF / A = γp·D / 2 (简化)
    result.sigma_x_Fw = p * r / (2 * t)  # 对于鞍式支承
    result.formula_refs['sigma_x_Fw'] = {
        'formula': 'σx,F = γF(1-cosθ)/(2πrt) ≈ p·r/(2t) (鞍式支承)',
        'ref': 'CECS 214-2006 公式(7.2.2-2,3)',
        'desc': '设计内水压力产生的纵向拉应力'
    }
    
    # 2.3 温度应力 (7.2.2-4): σ = αEΔT
    alpha = 12e-6         # 钢材线膨胀系数 1/°C
    E = 206000           # 弹性模量 MPa
    Delta_T = load.temperature_load_C  # 温差 °C
    result.sigma_x_t = alpha * E * abs(Delta_T)
    result.formula_refs['sigma_x_t'] = {
        'formula': 'σx,T = α·E·ΔT = 12×10⁻⁶ × 206000 × ΔT',
        'ref': 'CECS 214-2006 公式(7.2.2-4)',
        'desc': '温度变化产生的温度应力'
    }
    
    # 2.4 摩擦应力 (7.2.2-5): σ = μR/A
    mu = pipe.friction_coefficient  # 摩擦系数
    result.sigma_x_friction = mu * R / A
    result.formula_refs['sigma_x_friction'] = {
        'formula': 'σx,μ = μR / A',
        'ref': 'CECS 214-2006 公式(7.2.2-5)',
        'desc': '支座摩擦产生的纵向应力'
    }
    
    # 2.5 总轴向应力
    result.sigma_x_total = (result.sigma_x_M + 
                           result.sigma_x_Fw + 
                           result.sigma_x_t + 
                           result.sigma_x_friction)
    
    # ========== 3. 剪应力计算 (规范7.2.3) ==========
    
    # 3.1 平均剪应力 (7.2.3-1): τ = V/A
    V = R / 2  # 剪力 N (简支梁支座处)
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
        'desc': '组合折算应力'
    }
    
    # ========== 5. 强度验算 ==========
    # f = 钢材设计强度, γ0 = 重要性系数
    gamma_0 = load.importance_factor
    allowable_stress = 0.9 * f / gamma_0  # 组合荷载效应设计值
    
    result.formula_refs['check'] = {
        'formula': 'σ ≤ 0.9f/γ0',
        'ref': 'CECS 214-2006 公式(5.2.2-1)',
        'desc': '强度验算条件',
        'allowable': f'{allowable_stress:.1f} MPa'
    }
    
    result.is_safe = result.combined_stress <= allowable_stress
    result.safety_factor = allowable_stress / result.combined_stress if result.combined_stress > 0 else 999
    
    return result


def calculate_support_reaction(pipe: PipeModel, total_load_kN: float) -> float:
    """
    计算支座反力
    对于简支梁: R = qL/2 = 总荷载/2
    返回单位: N
    """
    # 总荷载单位是 kN，转为 N
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
