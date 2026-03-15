"""
计算书生成模块 - CECS 214-2006
完整输出工程计算书
"""
from datetime import datetime
from models.pipe import PipeModel
from models.load import LoadModel, LoadResult
from calculation.load_calc import calculate_loads
from calculation.stress_calc import calculate_stress, StressResult, calculate_support_reaction
from calculation.deflection_calc import calculate_deflection, DeflectionResult
from calculation.stability_calc import calculate_ring_stability, StabilityResult


class CalculationBook:
    """
    计算书数据容器
    """
    def __init__(self):
        self.project_name = ""
        self.design_standard = "CECS 214-2006"
        self.pipe = None
        self.load = None
        self.load_result = None
        self.stress_result = None
        self.deflection_result = None
        self.stability_result = None
        self.generated_date = ""


def generate_calculation_book(
    pipe: PipeModel,
    load: LoadModel,
    load_result: LoadResult,
    stress_result: StressResult,
    deflection_result: DeflectionResult = None,
    stability_result: StabilityResult = None,
    project_name: str = "自承式钢管跨越结构"
) -> CalculationBook:
    """
    生成完整计算书
    """
    book = CalculationBook()
    book.project_name = project_name
    book.generated_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    book.pipe = pipe
    book.load = load
    book.load_result = load_result
    book.stress_result = stress_result
    book.deflection_result = deflection_result
    book.stability_result = stability_result
    
    return book


def format_calculation_book(book: CalculationBook) -> str:
    """
    格式化计算书为Markdown文本
    """
    pipe = book.pipe
    load = book.load
    lr = book.load_result
    sr = book.stress_result
    
    # 获取钢材设计强度
    steel_strength_map = {"Q235": 215, "Q345": 295, "Q390": 350}
    f = steel_strength_map.get(pipe.steel_grade, 215)
    phi = pipe.weld_reduction_coefficient
    f_reduced = phi * f
    
    text = f"""# {book.project_name}结构计算书

**依据标准**: {book.design_standard}《自承式给水钢管跨越结构设计规程》
**编制日期**: {book.generated_date}

---

## 第一章 工程概况

### 1.1 基本参数

| 参数 | 数值 | 单位 |
|------|------|------|
| 管道规格 | {pipe.name} | - |
| 管道外径 D | {pipe.diameter_mm} | mm |
| 管道壁厚 t | {pipe.wall_thickness_mm} | mm |
| 管道内径 d | {pipe.inner_diameter_mm} | mm |
| 跨径 L | {pipe.span_m} | m |
| 支承方式 | {pipe.support_type.value if hasattr(pipe.support_type, 'value') else pipe.support_type} | - |
| 支承半角 θ | {pipe.support_half_angle} | ° |
| 摩擦系数 μ | {pipe.friction_coefficient} | - |
| 钢材牌号 | {pipe.steel_grade} | - |
| 焊缝类型 | {pipe.weld_type if hasattr(pipe, 'weld_type') else '自动焊'} | - |
| 设计内水压力 | {load.internal_pressure_MPa} | MPa |
| 闭合温差 ΔT | {load.temperature_load_C} | °C |

### 1.2 截面特性

| 特性 | 数值 | 单位 |
|------|------|------|
| 截面积 A | {pipe.cross_section_area_mm2:.2f} | mm² |
| 惯性矩 I | {pipe.moment_of_inertia_mm4:.2e} | mm⁴ |
| 截面抵抗矩 W | {pipe.section_modulus_mm3:.2e} | mm³ |
| 回转半径 i | {pipe.radius_of_gyration_mm:.2f} | mm |

---

## 第二章 设计依据

1. 《自承式给水钢管跨越结构设计规程》CECS 214-2006
2. 《钢结构设计规范》GB 50017-2017
3. 《建筑结构荷载规范》GB 50009-2012

### 2.1 材料参数

| 材料 | 设计强度 f (MPa) |
|------|------------------|
| Q235 | 215 |
| Q345 | 295 |
| Q390 | 350 |

**焊缝折减系数 φ = {phi:.2f}**，折减后设计强度 **f' = {f_reduced:.1f} MPa**

---

## 第三章 荷载计算

### 3.1 永久作用标准值

| 荷载类型 | 每米荷载 (kN/m) | 跨总荷载 (kN) |
|----------|-----------------|---------------|
| 管道自重 | {lr.self_weight_per_m:.4f} | {lr.self_weight_kN:.2f} |
| 防腐层重 | {lr.anti_corrosion_per_m:.4f} | {lr.anti_corrosion_kN:.2f} |
| 附加荷载 | {lr.additional_per_m:.4f} | {lr.additional_kN:.2f} |
| 管内水重 | {lr.water_weight_per_m:.4f} | {lr.water_weight_kN:.2f} |

### 3.2 可变作用标准值

| 荷载类型 | 数值 | 单位 |
|----------|------|------|
| 内水压力 | {lr.internal_pressure_kN:.2f} | kN |
| 施工检修荷载 | {lr.construction_kN:.2f} | kN |
| 风荷载 | {lr.wind_horizontal_kN:.2f} | kN |

### 3.3 荷载组合

按《CECS 214-2006》第5.2条进行荷载组合：

#### 工况1：基本组合 (1.2×永久 + 1.4×可变)

| 分项 | 数值 (kN) |
|------|-----------|
| 竖向永久作用 | {lr.工况1_竖向永久:.2f} |
| 竖向可变作用 | {lr.工况1_竖向可变:.2f} |
| 水平荷载(风) | {lr.工况1_水平荷载:.2f} |
| **总计** | **{lr.工况1_total_kN:.2f}** |

#### 工况2：施工检修组合 (1.2×永久 + 1.4×施工)

| 分项 | 数值 (kN) |
|------|-----------|
| 竖向永久作用 | {lr.工况2_竖向永久:.2f} |
| 竖向可变作用 | {lr.工况2_竖向可变:.2f} |
| 水平荷载 | {lr.工况2_水平荷载:.2f} |
| **总计** | **{lr.工况2_total_kN:.2f}** |

---

## 第四章 内力计算

### 4.1 基本公式

简支梁在均布荷载作用下：
- 支座反力: R = qL/2
- 跨中弯矩: M = qL²/8
- 支座剪力: V = R

### 4.2 计算结果 (工况1)

| 内力 | 数值 | 单位 |
|------|------|------|
| 支座反力 R | {lr.工况1_total_kN/2:.2f} | kN |
| 支座剪力 V | {lr.工况1_total_kN/2:.2f} | kN |
| 跨中弯矩 M | {lr.工况1_total_kN * pipe.span_m / 8:.2f} | kN·m |

---

## 第五章 应力计算

### 5.1 环向应力 (《CECS 214-2006》第7.2.1条)

$$\\sigma_\\theta = \\frac{{p \\cdot r}}{{t}}$$

计算结果: **{sr.sigma_theta_Fw:.2f} MPa**

参数: p = {load.internal_pressure_MPa} MPa, r = {pipe.inner_radius_mm:.0f} mm, t = {pipe.wall_thickness_mm} mm

### 5.2 轴向应力 (《CECS 214-2006》第7.2.2条)

| 应力分量 | 公式 | 数值 (MPa) |
|----------|------|------------|
| 弯曲应力 | σ = M/W | {sr.sigma_x_M:.2f} |
| 内水压轴向 | σ = p·r(1-cosθ)/(2πrt) | {sr.sigma_x_Fw:.2f} |
| 温度应力(折减) | σ = ζ·α·E·ΔT | {sr.sigma_x_t_reduced:.2f} |
| 摩擦应力 | σ = μR/A | {sr.sigma_x_friction:.2f} |
| **总轴向应力** | 叠加 | **{sr.sigma_x_total:.2f}** |

### 5.3 剪应力 (《CECS 214-2006》第7.2.3条)

| 应力类型 | 数值 (MPa) |
|----------|------------|
| 平均剪应力 τ | {sr.tau_avg:.2f} |
| 最大剪应力 τmax | {sr.tau_max:.2f} |

### 5.4 支座处局部应力 (《CECS 214-2006》第7.2.4条)

**仅环式支承需要计算**

| 位置 | 局部应力 (MPa) |
|------|----------------|
| 管壁外面 | {sr.sigma_x_local_out:.2f} |
| 管壁内面 | {sr.sigma_x_local_in:.2f} |

公式: σ'x = ±1.82βσθ,Fw (β = {sr.beta})

---

## 第六章 强度验算

### 6.1 组合折算应力 (第四强度理论)

$$\\sigma = \\sqrt{{\\sigma_x^2 + \\sigma_\\theta^2 - \\sigma_x \\cdot \\sigma_\\theta + 3\\tau^2}}$$

| 位置 | 组合应力 (MPa) | 允许应力 (MPa) | 安全系数 | 验算结果 |
|------|----------------|----------------|----------|----------|
| 跨中截面 | {sr.combined_stress:.2f} | {0.9*f_reduced:.1f} | {sr.safety_factor:.2f} | {'✅ 通过' if sr.is_safe else '❌ 不通过'} |
| 支座截面 | {sr.combined_stress_support:.2f} | {0.9*f_reduced:.1f} | {sr.safety_factor_support:.2f} | {'✅ 通过' if sr.is_safe_support else '❌ 不通过'} |

**强度验算条件**: σ ≤ 0.9φf/γ₀ = 0.9 × {phi:.2f} × {f} / {load.importance_factor} = **{0.9*f_reduced/load.importance_factor:.1f} MPa**

---

## 第七章 挠度验算

### 7.1 计算公式 (《CECS 214-2006》第9章)

简支梁挠度公式: f = 5qL⁴/(384EI)

"""

    # 添加挠度计算结果
    if book.deflection_result:
        text += f"""
### 7.2 挠度计算结果

| 项目 | 数值 | 单位 |
|------|------|------|
| 跨中挠度 f | {deflection_result.deflection_mm:.2f} | mm |
| 允许挠度 [f] | {deflection_result.allowable_deflection_mm:.2f} | mm |
| 挠跨比 | 1/{int(1/deflection_result.deflection_ratio) if deflection_result.deflection_ratio > 0 else '∞'} | - |

**验算结果**: {'✅ 挠度满足要求' if deflection_result.is_adequate else '❌ 挠度不满足要求'}

"""
    else:
        text += """
### 7.2 挠度计算结果

未进行挠度验算

"""

    # 添加稳定计算结果
    if book.stability_result:
        text += f"""
---

## 第八章 稳定计算

### 8.1 环向稳定验算 (《CECS 214-2006》第8章)

| 项目 | 数值 | 单位 |
|------|------|------|
| 实际内水压 p | {stability_result.actual_pressure:.2f} | MPa |
| 临界压力 pcr | {stability_result.critical_pressure:.2f} | MPa |
| 允许压力 [p] | {stability_result.allowable_pressure:.2f} | MPa |

**稳定验算**: {'✅ 稳定满足要求' if stability_result.is_stable else '⚠️ 需要设置加劲环'}

"""
    else:
        text += """
---

## 第八章 稳定计算

未进行稳定验算

"""

    # 添加结论
    text += f"""
---

## 第九章 计算结论

### 9.1 强度评价

| 验算项目 | 结果 | 备注 |
|----------|------|------|
| 跨中强度 | {'✅ 通过' if sr.is_safe else '❌ 不通过'} | 安全系数 {sr.safety_factor:.2f} |
| 支座强度 | {'✅ 通过' if sr.is_safe_support else '❌ 不通过'} | 安全系数 {sr.safety_factor_support:.2f} |
"""
    
    if book.deflection_result:
        text += f"| 挠度验算 | {'✅ 通过' if deflection_result.is_adequate else '❌ 不通过'} | |\n"
    
    if book.stability_result:
        text += f"| 稳定验算 | {'✅ 通过' if stability_result.is_stable else '⚠️ 需加劲环'} | |\n"
    
    text += f"""
### 9.2 设计建议

1. 管道采用 {pipe.name} 规格，壁厚 {pipe.wall_thickness_mm}mm
2. 钢材采用 {pipe.steel_grade}，焊缝折减系数 φ = {phi:.2f}
3. 支承方式采用 {'环式支承' if (pipe.support_type.value if hasattr(pipe.support_type, 'value') else pipe.support_type) == '环式支承' else '鞍式支承'}，支承半角 {pipe.support_half_angle}°
4. 设计内水压力 {load.internal_pressure_MPa} MPa，闭合温差 {load.temperature_load_C}°C

---

**计算人**: 管道桥计算程序
**审核人**: 
**日期**: {book.generated_date}

"""

    return text
