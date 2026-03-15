"""
稳定计算模块 - CECS 214-2006 第8章
(已修复真空管壁失稳的算法常识)
"""
import math
from models.pipe import PipeModel

class StabilityResult:
    def __init__(self):
        self.is_stable = True           
        self.critical_pressure = 0     
        self.allowable_pressure = 0     
        self.actual_pressure = 0        
        self.stiffener_spacing_mm = 0    
        self.formula_refs = {}           

def calculate_ring_stability(pipe: PipeModel, vacuum_kN: float = 0) -> StabilityResult:
    result = StabilityResult()
    
    D = pipe.diameter_mm          
    t = pipe.wall_thickness_mm  
    E = 206000                  
    
    # 【修复 FATAL-04】: 之前错把线荷载除以截面积算压强，这是荒谬的！
    # 真实真空压强 p = 总拉力 / (直径 * 长度) 
    if pipe.span_m > 0 and D > 0:
        vacuum_pressure_MPa = vacuum_kN * 1000 / (D * pipe.span_m)
    else:
        vacuum_pressure_MPa = 0
        
    result.actual_pressure = vacuum_pressure_MPa
    
    if t / D < 0.02:
        result.critical_pressure = 2.6 * E * (t / D)**2.5
    else:
        result.critical_pressure = 2.6 * E * (t / D)**2
    
    result.allowable_pressure = result.critical_pressure / 2.0
    result.is_stable = result.actual_pressure <= result.allowable_pressure
    return result


def get_stiffener_spacing(pipe: PipeModel, internal_pressure_MPa: float) -> float:
    """
    计算加劲环间距 - CECS 214-2006 第8.2节
    """
    D = pipe.diameter_mm
    t = pipe.wall_thickness_mm
    E = 206000
    f = pipe.design_strength_MPa
    
    # 加劲环间距计算
    if t / D < 0.02:
        # 薄壁管
        spacing = 2.5 * D * math.sqrt(t / D)
    else:
        # 厚壁管
        spacing = 2.0 * D * math.sqrt(t / D)
    
    # 最大间距限制
    max_spacing = 6 * D
    min_spacing = 0.5 * D
    
    return max(min(spacing, max_spacing), min_spacing)


def calculate_stability_with_stiffeners(pipe: PipeModel, vacuum_kN: float, stiffener_spacing_m: float) -> StabilityResult:
    """
    计算有加劲环的稳定 - CECS 214-2006 第8.2节
    """
    result = StabilityResult()
    
    D = pipe.diameter_mm
    t = pipe.wall_thickness_mm
    E = 206000
    
    # 真空压力
    if pipe.span_m > 0 and D > 0:
        vacuum_pressure_MPa = vacuum_kN * 1000 / (D * pipe.span_m)
    else:
        vacuum_pressure_MPa = 0
    result.actual_pressure = vacuum_pressure_MPa
    
    # 有加劲环时的临界压力
    L = stiffener_spacing_m * 1000  # mm
    if t / D < 0.02:
        result.critical_pressure = 2.6 * E * (t / D)**2.5 * (1 + 0.5 * (D / L)**2)
    else:
        result.critical_pressure = 2.6 * E * (t / D)**2 * (1 + 0.5 * (D / L)**2)
    
    result.allowable_pressure = result.critical_pressure / 2.0
    result.is_stable = result.actual_pressure <= result.allowable_pressure
    result.stiffener_spacing_mm = L
    
    return result
