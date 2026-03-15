"""
荷载计算模块 - CECS 214-2006
符合规范第4章 钢管结构上的作用
"""
import math
from models.pipe import PipeModel
from models.load import LoadModel, LoadResult


def get_construction_load_by_diameter(diameter_mm: int) -> float:
    """
    根据管径获取施工检修荷载 - CECS 214-2006 表4.3.6
    """
    if diameter_mm <= 400:
        return 0.5
    elif diameter_mm <= 700:
        return 0.75
    else:
        return 1.0


def calculate_loads(pipe: PipeModel, load: LoadModel) -> LoadResult:
    """
    计算荷载 - CECS 214-2006 第4章
    分工况1(基本组合)和工况2(施工检修组合)计算
    区分竖向荷载和水平荷载(风荷载)
    """
    
    L = pipe.span_m  # 跨长
    
    # ========== 1. 永久作用标准值 (kN/m) ==========
    # 管道自重 (考虑放大系数K)
    volume_per_m = pipe.cross_section_area_mm2 / 1e6  # m³/m
    base_self_weight = volume_per_m * load.steel_density * 9.81 / 1000
    self_weight_per_m = base_self_weight * load.self_weight_amplification
    
    # 防腐层重 (不乘放大系数)
    anti_corrosion_per_m = load.anti_corrosion_weight
    
    # 附加荷载 (不乘放大系数)
    additional_per_m = load.additional_load
    
    # 管内水重
    inner_area = math.pi * (pipe.inner_diameter_mm ** 2) / 4 / 1e6
    water_weight_per_m = inner_area * load.water_density * 9.81 / 1000
    
    # ========== 2. 跨总永久作用 (kN) ==========
    self_weight_kN = self_weight_per_m * L
    anti_corrosion_kN = anti_corrosion_per_m * L
    additional_kN = additional_per_m * L
    water_weight_kN = water_weight_per_m * L
    
    # ========== 3. 可变作用标准值 ==========
    # 内水压力 (作为竖向荷载)
    p = max(load.internal_pressure_MPa, 0.9)
    internal_pressure_kN = p * pipe.diameter_mm * L / 1000
    
    # 施工检修荷载 (按表4.3.6)
    construction_per_m = get_construction_load_by_diameter(pipe.diameter_mm)
    construction_kN = construction_per_m * L
    
    # 风荷载 (作为水平荷载)
    wind_horizontal_kN = load.wind_load_kN
    
    # 真空压力 (作为竖向荷载)
    vacuum_kN = load.vacuum_pressure_MPa * pipe.diameter_mm * L / 1000
    
    # ========== 4. 工况1：基本组合 ==========
    # 竖向永久作用 (分项系数1.2)
    工况1_竖向永久 = (
        load.gamma_self_weight * self_weight_kN +
        load.gamma_self_weight * anti_corrosion_kN +
        load.gamma_self_weight * additional_kN +
        load.gamma_water * water_weight_kN
    )
    
    # 竖向可变作用 (分项系数1.4)
    # 注意：内水压与真空压力是互斥工况，应取包络(最大值)而非叠加
    internal_pressure_effect = load.gamma_pressure * internal_pressure_kN
    vacuum_effect = load.gamma_vacuum * load.psi_vacuum * vacuum_kN
    工况1_竖向可变 = max(internal_pressure_effect, vacuum_effect)
    
    # 竖向总荷载 (用于计算竖向内力)
    工况1_竖向_总计 = 工况1_竖向永久 + 工况1_竖向可变
    
    # 水平风荷载 (单独计算，用于水平内力)
    工况1_水平 = load.gamma_wind * load.psi_wind * wind_horizontal_kN
    
    # 总荷载(仅用于稳定计算，不用于应力)
    工况1_total = 工况1_竖向_总计  # 应力计算只用竖向荷载
    
    # ========== 5. 工况2：施工检修组合 ==========
    # 竖向永久作用 (相同)
    工况2_竖向永久 = 工况1_竖向永久
    
    # 竖向可变作用 (不含风荷载，含施工检修)
    工况2_竖向可变 = (
        load.gamma_pressure * internal_pressure_kN +
        load.gamma_construction * construction_kN
    )
    
    # 竖向总荷载
    工况2_竖向_总计 = 工况2_竖向永久 + 工况2_竖向可变
    
    # 水平荷载 (施工检修组合不考虑风荷载)
    工况2_水平 = 0
    
    # 总荷载
    工况2_total = 工况2_竖向_总计
    
    return LoadResult(
        # 每米荷载
        self_weight_per_m=round(self_weight_per_m, 4),
        anti_corrosion_per_m=round(anti_corrosion_per_m, 4),
        additional_per_m=round(additional_per_m, 4),
        water_weight_per_m=round(water_weight_per_m, 4),
        # 跨总荷载 - 竖向
        self_weight_kN=round(self_weight_kN, 2),
        anti_corrosion_kN=round(anti_corrosion_kN, 2),
        additional_kN=round(additional_kN, 2),
        water_weight_kN=round(water_weight_kN, 2),
        # 跨总荷载 - 水平
        wind_horizontal_kN=round(wind_horizontal_kN, 2),
        # 可变荷载
        internal_pressure_kN=round(internal_pressure_kN, 2),
        construction_kN=round(construction_kN, 2),
        vacuum_kN=round(vacuum_kN, 2),
        # 工况1
        工况1_竖向永久=round(工况1_竖向永久, 2),
        工况1_竖向可变=round(工况1_竖向可变, 2),
        工况1_竖向_总计=round(工况1_竖向_总计, 2),
        工况1_水平荷载=round(工况1_水平, 2),
        工况1_total_kN=round(工况1_total, 2),
        # 工况2
        工况2_竖向永久=round(工况2_竖向永久, 2),
        工况2_竖向可变=round(工况2_竖向可变, 2),
        工况2_竖向_总计=round(工况2_竖向_总计, 2),
        工况2_水平荷载=round(工况2_水平, 2),
        工况2_total_kN=round(工况2_total, 2),
    )
