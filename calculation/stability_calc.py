"""
稳定计算模块 - CECS 214-2006 第8章
平管环向稳定计算
"""
import math
from models.pipe import PipeModel


class StabilityResult:
    """稳定计算结果"""
    def __init__(self):
        self.is_stable = True           # 是否稳定
        self.critical_pressure = 0     # 临界压力 MPa
        self.allowable_pressure = 0     # 允许压力 MPa
        self.actual_pressure = 0        # 实际压力 MPa
        self.stiffener_spacing_mm = 0    # 加劲环间距 mm
        self.formula_refs = {}           # 公式引用


def calculate_ring_stability(pipe: PipeModel, vacuum_pressure_MPa: float = 0) -> StabilityResult:
    """
    计算平管环向稳定 - CECS 214-2006 第8.1节
    
    钢管管体环向弹性稳定，以钢管管壁厚度作抗力保证。
    当增加管壁厚度不经济时，可沿钢管纵向设置加劲环。
    """
    result = StabilityResult()
    
    D = pipe.diameter_mm          # 外径 mm
    r = pipe.inner_radius_mm     # 内半径 mm
    t = pipe.wall_thickness_mm  # 壁厚 mm
    E = 206000                  # 弹性模量 MPa
    
    # 真空失稳是由管外大气压与管内负压形成的径向压强差(MPa)引起
    # 直接使用真空压力值(MPa)，不需要转换
    result.actual_pressure = vacuum_pressure_MPa
    
    # ========== 1. 临界压力计算 (环向稳定) ==========
    # 对于薄壳结构，环向临界压力公式简化
    # p_cr = 3E(t/D)³ (对于承受外压的圆管)
    # 这里使用规范简化方法
    
    # 方法1: 无加劲环时临界压力
    if t / D < 0.02:
        # 薄壁管临界压力
        result.critical_pressure = 2.6 * E * (t / D)**2.5
    else:
        # 厚壁管临界压力
        result.critical_pressure = 2.6 * E * (t / D)**2
    
    result.formula_refs['critical'] = {
        'formula': 'pcr = 2.6E(t/D)²·⁵',
        'ref': 'CECS 214-2006 第8.1.1条',
        'desc': '钢管管壁环向弹性临界压力'
    }
    
    # ========== 2. 允许压力 ==========
    # 安全系数 K = 2.0
    K = 2.0
    result.allowable_pressure = result.critical_pressure / K
    
    # ========== 3. 稳定验算 ==========
    result.is_stable = result.actual_pressure <= result.allowable_pressure
    
    return result


def get_stiffener_spacing(pipe: PipeModel, internal_pressure_MPa: float) -> float:
    """
    计算所需加劲环间距 - CECS 214-2006 表8.1.1
    
    根据管壁厚度确定不加劲环的最大间距
    """
    t = pipe.wall_thickness_mm
    
    # 根据规范表8.1.1，加劲环间距与壁厚的关系
    # 这里简化处理
    if t >= 18:
        spacing = 18000  # 18mm及以上
    elif t >= 16:
        spacing = 16000
    elif t >= 14:
        spacing = 14000
    elif t >= 12:
        spacing = 12000
    elif t >= 10:
        spacing = 10000
    else:
        spacing = 8000
    
    return spacing


def calculate_stability_with_stiffeners(pipe: PipeModel, spacing_mm: float, 
                                       internal_pressure_MPa: float) -> StabilityResult:
    """
    有加劲环时的稳定计算 - CECS 214-2006 第8.1.1
    """
    result = StabilityResult()
    
    D = pipe.diameter_mm
    t = pipe.wall_thickness_mm
    L = spacing_mm  # 加劲环间距
    E = 206000
    
    # 有加劲环时，临界压力提高
    # p_cr = 2.6E(t/D)²·⁵ * (1 + L/D)⁰·⁵
    if t / D < 0.02:
        base_pressure = 2.6 * E * (t / D)**2.5
    else:
        base_pressure = 2.6 * E * (t / D)**2
    
    result.critical_pressure = base_pressure * math.sqrt(1 + L / D)
    result.allowable_pressure = result.critical_pressure / 2.0
    result.actual_pressure = internal_pressure_MPa
    result.stiffener_spacing_mm = spacing_mm
    
    result.is_stable = result.actual_pressure <= result.allowable_pressure
    
    result.formula_refs['with_stiffener'] = {
        'formula': 'pcr = 2.6E(t/D)²·⁵√(1+L/D)',
        'ref': 'CECS 214-2006 第8.1.1条 (有加劲环)',
        'desc': '有加劲环时管壁环向临界压力'
    }
    
    return result
