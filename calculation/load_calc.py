"""
荷载计算模块 - CECS 214-2006
符合规范第4章 钢管结构上的作用 (已修复A级力学缺陷)
"""
import math
from models.pipe import PipeModel
from models.load import LoadModel, LoadResult

def get_construction_load_by_diameter(diameter_mm: int) -> float:
    if diameter_mm <= 400: return 0.5
    elif diameter_mm <= 700: return 0.75
    else: return 1.0


def calculate_wind_profile(w0: float, z: float, terrain: str) -> tuple:
    """根据 GB50009 计算风压高度变化系数及标准风压"""
    # 粗糙度截断高度与指数
    alpha_dict = {"A类": 0.12, "B类": 0.15, "C类": 0.22, "D类": 0.30}
    alpha = alpha_dict.get(terrain, 0.15)
    
    # 高度变化系数 mu_z
    mu_z = max(1.0, (z / 10.0) ** (2 * alpha))
    mu_s = 1.2  # 圆管体型系数
    beta_z = 1.5  # 风振系数
    
    Wk = beta_z * mu_s * mu_z * w0
    return Wk, mu_z, mu_s, beta_z


def calculate_loads(pipe: PipeModel, load: LoadModel) -> LoadResult:
    L = pipe.span_m  
    
    # ========== 1. 永久作用标准值 (kN/m) ==========
    volume_per_m = pipe.cross_section_area_mm2 / 1e6 
    base_self_weight = volume_per_m * load.steel_density * 9.81 / 1000
    self_weight_per_m = base_self_weight * load.self_weight_amplification
    anti_corrosion_per_m = load.anti_corrosion_weight
    additional_per_m = load.additional_load
    
    inner_area = math.pi * (pipe.inner_diameter_mm ** 2) / 4 / 1e6
    water_weight_per_m = inner_area * load.water_density * 9.81 / 1000
    
    # ========== 2. 跨总永久作用 (kN) ==========
    self_weight_kN = self_weight_per_m * L
    anti_corrosion_kN = anti_corrosion_per_m * L
    additional_kN = additional_per_m * L
    water_weight_kN = water_weight_per_m * L
    
    # ========== 3. 可变作用标准值 ==========
    p = max(load.internal_pressure_MPa, 0.9)
    # 保留这两个变量仅为了数据流兼容，但它们绝不应该加入竖向重力荷载中！
    internal_pressure_kN = p * pipe.diameter_mm * L / 1000
    vacuum_kN = load.vacuum_pressure_MPa * pipe.diameter_mm * L / 1000
    
    construction_per_m = get_construction_load_by_diameter(pipe.diameter_mm)
    construction_kN = construction_per_m * L
    
    # ========== 风荷载自动计算 ==========
    # 如果手动输入了风荷载则使用手动值，否则自动计算
    if load.wind_load_kN > 0:
        wind_horizontal_kN = load.wind_load_kN
        Wk = load.wind_load_kN / L
        mu_z, mu_s, beta_z = 0, 0, 0
    else:
        # 自动计算风荷载
        Wk, mu_z, mu_s, beta_z = calculate_wind_profile(
            load.basic_wind_pressure, 
            load.elevation_m, 
            load.terrain_category
        )
        wind_horizontal_kN = Wk * (pipe.diameter_mm / 1000.0) * L
    
    # ========== 4. 工况1：基本组合 ==========
    工况1_竖向永久 = (
        load.gamma_self_weight * self_weight_kN +
        load.gamma_self_weight * anti_corrosion_kN +
        load.gamma_self_weight * additional_kN +
        load.gamma_water * water_weight_kN
    )
    
    # 【修复 FATAL-01】: 内水压和真空压是径向膨胀/收缩力，绝对不能作为竖向重力使管桥下弯！
    # 正常基本组合下，没有竖向可变重力荷载（雪荷载这里暂未考虑）
    工况1_竖向可变 = 0
    工况1_竖向_总计 = 工况1_竖向永久 + 工况1_竖向可变
    工况1_水平 = load.gamma_wind * load.psi_wind * wind_horizontal_kN
    工况1_total = 工况1_竖向_总计 
    
    # ========== 5. 工况2：施工检修组合 ==========
    工况2_竖向永久 = 工况1_竖向永久
    # 施工荷载是真正的向下重力，必须计入竖向可变
    工况2_竖向可变 = load.gamma_construction * construction_kN
    工况2_竖向_总计 = 工况2_竖向永久 + 工况2_竖向可变
    工况2_水平 = 0
    工况2_total = 工况2_竖向_总计
    
    # ========== 下部结构提资 ==========
    R_max = 工况1_竖向_总计 / 2  # 满水满载最大垂直下压力
    R_min = (load.gamma_self_weight * self_weight_kN + load.gamma_self_weight * anti_corrosion_kN) / 2  # 空管自重下压力
    V_z_max = 工况1_水平荷载 / 2  # 最大水平风剪力
    
    return LoadResult(
        self_weight_per_m=round(self_weight_per_m, 4),
        anti_corrosion_per_m=round(anti_corrosion_per_m, 4),
        additional_per_m=round(additional_per_m, 4),
        water_weight_per_m=round(water_weight_per_m, 4),
        self_weight_kN=round(self_weight_kN, 2),
        anti_corrosion_kN=round(anti_corrosion_kN, 2),
        additional_kN=round(additional_kN, 2),
        water_weight_kN=round(water_weight_kN, 2),
        wind_horizontal_kN=round(wind_horizontal_kN, 2),
        internal_pressure_kN=round(internal_pressure_kN, 2),
        construction_kN=round(construction_kN, 2),
        vacuum_kN=round(vacuum_kN, 2),
        工况1_竖向永久=round(工况1_竖向永久, 2),
        工况1_竖向可变=round(工况1_竖向可变, 2),
        工况1_竖向_总计=round(工况1_竖向_总计, 2),
        工况1_水平荷载=round(工况1_水平, 2),
        工况1_total_kN=round(工况1_total, 2),
        工况2_竖向永久=round(工况2_竖向永久, 2),
        工况2_竖向可变=round(工况2_竖向可变, 2),
        工况2_竖向_总计=round(工况2_竖向_总计, 2),
        工况2_水平荷载=round(工况2_水平, 2),
        工况2_total_kN=round(工况2_total, 2),
        Wk=round(Wk, 3),
        mu_z=round(mu_z, 3),
        mu_s=mu_s,
        beta_z=beta_z,
        R_max=round(R_max, 2),
        R_min=round(R_min, 2),
        V_z_max=round(V_z_max, 2),
    )
