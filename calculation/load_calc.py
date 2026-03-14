"""
荷载计算模块 - CECS 214-2006
符合规范第4章 钢管结构上的作用
"""
import math
from models.pipe import PipeModel
from models.load import LoadModel, LoadResult


def calculate_loads(pipe: PipeModel, load: LoadModel) -> LoadResult:
    """
    计算荷载 - CECS 214-2006 第4章
    """
    
    # ========== 1. 永久作用标准值 (规范4.2) ==========
    
    # 1.1 结构自重 (规范4.2.1)
    # 钢管自重 = 截面积 × 长度 × 密度 × g
    volume_per_m = pipe.cross_section_area_mm2 / 1e6  # m³/m
    self_weight_kN_per_m = volume_per_m * load.steel_density * 9.81 / 1000  # kN/m
    self_weight_kN = self_weight_kN_per_m * pipe.span_m
    
    # 1.2 管内水重 (规范4.2.1)
    inner_area = math.pi * (pipe.inner_diameter_mm ** 2) / 4 / 1e6  # m²
    water_volume = inner_area * pipe.span_m  # m³
    water_weight_kN = water_volume * load.water_density * 9.81 / 1000
    
    # ========== 2. 可变作用标准值 (规范4.3) ==========
    
    # 2.1 内水压力 (规范4.3.2)
    # 标准值按设计内水压力计算，不小于0.9MPa
    p = max(load.internal_pressure_MPa, 0.9)
    # 简化: 内水压力产生的轴向力
    internal_pressure_kN = p * pipe.diameter_mm * pipe.span_m / 1000  # 简化
    
    # 2.2 风荷载 (规范4.3.1)
    wind_kN = load.wind_load_kN
    
    # 2.3 温度作用 (规范4.3.4-4.3.5)
    # 温度应力不直接作为荷载，体现在温度应力计算中
    
    # 2.4 施工检修荷载 (规范4.3.6)
    construction_kN = load.construction_load_kN
    
    # 2.5 真空压力 (规范4.3.3)
    vacuum_kN = load.vacuum_pressure_MPa * pipe.diameter_mm * pipe.span_m / 1000
    
    # ========== 3. 荷载组合 (规范第5章) ==========
    
    # 组合1: 主要组合 1.2G + 1.4Q
    combination1 = (
        load.gamma_self_weight * self_weight_kN +
        load.gamma_water * water_weight_kN +
        load.gamma_pressure * internal_pressure_kN +
        load.gamma_wind * load.psi_wind * wind_kN +
        load.gamma_temp * load.psi_temp * 0 +  # 温度作为应力
        load.gamma_construction * 0  # 施工检修不在组合1
    )
    
    # 组合2: 施工检修组合 (无风，有施工检修)
    combination2 = (
        load.gamma_self_weight * self_weight_kN +
        load.gamma_water * water_weight_kN +
        load.gamma_pressure * internal_pressure_kN +
        load.gamma_temp * load.psi_temp * 0 +
        load.gamma_construction * construction_kN
    )
    
    # 组合3: 偶然组合 (扩展)
    combination3 = (
        load.gamma_self_weight * self_weight_kN +
        load.gamma_water * water_weight_kN +
        load.gamma_pressure * 0.9 * internal_pressure_kN  # 偶然组合
    )
    
    return LoadResult(
        self_weight_kN=round(self_weight_kN, 2),
        water_weight_kN=round(water_weight_kN, 2),
        internal_pressure_kN=round(internal_pressure_kN, 2),
        wind_kN=round(wind_kN, 2),
        construction_kN=round(construction_kN, 2),
        vacuum_kN=round(vacuum_kN, 2),
        combination1_total_kN=round(combination1, 2),
        combination2_total_kN=round(combination2, 2),
        combination3_total_kN=round(combination3, 2)
    )
