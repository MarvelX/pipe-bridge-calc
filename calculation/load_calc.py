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
    
    # ========== 1. 每米管道自重 (kN/m) ==========
    # G = γs × A × g / 10^6 (A in mm², output kN/m)
    volume_per_m = pipe.cross_section_area_mm2 / 1e6  # m³/m
    base_self_weight = volume_per_m * load.steel_density * 9.81 / 1000  # kN/m
    # 考虑自重放大系数 (考虑附件、保温层等)
    self_weight_per_m = base_self_weight * load.self_weight_amplification
    
    # ========== 2. 每米防腐层重 (kN/m) ==========
    anti_corrosion_per_m = load.anti_corrosion_weight
    
    # ========== 3. 每米附加荷载 (kN/m) ==========
    additional_per_m = load.additional_load
    
    # ========== 4. 每米管内水重 (kN/m) ==========
    inner_area = math.pi * (pipe.inner_diameter_mm ** 2) / 4 / 1e6  # m²
    water_weight_per_m = inner_area * load.water_density * 9.81 / 1000  # kN/m
    
    # ========== 5. 跨总荷载 ==========
    L = pipe.span_m
    self_weight_kN = self_weight_per_m * L
    anti_corrosion_kN = anti_corrosion_per_m * L
    additional_kN = additional_per_m * L
    water_weight_kN = water_weight_per_m * L
    
    # ========== 6. 可变作用标准值 (规范4.3) ==========
    
    # 6.1 内水压力 (规范4.3.2)
    p = max(load.internal_pressure_MPa, 0.9)
    internal_pressure_kN = p * pipe.diameter_mm * L / 1000
    
    # 6.2 风荷载 (规范4.3.1)
    wind_kN = load.wind_load_kN
    
    # 6.3 施工检修荷载 (规范4.3.6)
    construction_kN = load.construction_load_kN
    
    # 6.4 真空压力 (规范4.3.3)
    vacuum_kN = load.vacuum_pressure_MPa * pipe.diameter_mm * L / 1000
    
    # ========== 7. 荷载组合 (规范第5章) ==========
    
    # 永久荷载总重 (考虑分项系数)
    permanent_load = (
        load.gamma_self_weight * self_weight_kN +
        load.gamma_self_weight * anti_corrosion_kN +
        load.gamma_self_weight * additional_kN +
        load.gamma_water * water_weight_kN
    )
    
    # 组合1: 主要组合 1.2G + 1.4Q
    combination1 = (
        permanent_load +
        load.gamma_pressure * internal_pressure_kN +
        load.gamma_wind * load.psi_wind * wind_kN +
        load.gamma_temp * load.psi_temp * 0 +  # 温度作为应力
        load.gamma_construction * 0  # 施工检修不在组合1
    )
    
    # 组合2: 施工检修组合 (无风，有施工检修)
    combination2 = (
        load.gamma_self_weight * self_weight_kN +
        load.gamma_self_weight * anti_corrosion_kN +
        load.gamma_self_weight * additional_kN +
        load.gamma_water * water_weight_kN +
        load.gamma_pressure * internal_pressure_kN +
        load.gamma_construction * construction_kN
    )
    
    # 组合3: 偶然组合 (扩展)
    combination3 = (
        load.gamma_self_weight * self_weight_kN +
        load.gamma_self_weight * anti_corrosion_kN +
        load.gamma_self_weight * additional_kN +
        load.gamma_water * water_weight_kN +
        load.gamma_pressure * 0.9 * internal_pressure_kN
    )
    
    return LoadResult(
        # 每米荷载
        self_weight_per_m=round(self_weight_per_m, 4),
        anti_corrosion_per_m=round(anti_corrosion_per_m, 4),
        additional_per_m=round(additional_per_m, 4),
        water_weight_per_m=round(water_weight_per_m, 4),
        # 跨总荷载
        self_weight_kN=round(self_weight_kN, 2),
        anti_corrosion_kN=round(anti_corrosion_kN, 2),
        additional_kN=round(additional_kN, 2),
        water_weight_kN=round(water_weight_kN, 2),
        # 可变荷载
        internal_pressure_kN=round(internal_pressure_kN, 2),
        wind_kN=round(wind_kN, 2),
        construction_kN=round(construction_kN, 2),
        vacuum_kN=round(vacuum_kN, 2),
        # 组合
        combination1_total_kN=round(combination1, 2),
        combination2_total_kN=round(combination2, 2),
        combination3_total_kN=round(combination3, 2)
    )
