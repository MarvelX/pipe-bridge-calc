import math
from models.pipe import PipeModel
from models.load import LoadModel
from calculation.load_calc import LoadResult
from calculation.stress_calc import StressResult
from calculation.deflection_calc import DeflectionResult
from calculation.stability_calc import StabilityResult
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CalculationBook:
    """计算书数据类"""
    project_name: str
    generated_date: str
    pipe: PipeModel
    load: LoadModel
    load_result: LoadResult
    stress_result_1: StressResult  # 工况1 (满水)
    stress_result_2: StressResult  # 工况2 (空管)
    deflection_result: DeflectionResult = None
    stability_result: StabilityResult = None


def generate_calculation_book(pipe: PipeModel, load: LoadModel, 
                            load_result: LoadResult, 
                            stress_result_1: StressResult,
                            stress_result_2: StressResult,
                            deflection_result: DeflectionResult = None,
                            stability_result: StabilityResult = None,
                            project_name: str = "自承式管线桥结构设计") -> CalculationBook:
    """生成计算书数据对象"""
    return CalculationBook(
        project_name=project_name,
        generated_date=datetime.now().strftime("%Y-%m-%d"),
        pipe=pipe,
        load=load,
        load_result=load_result,
        stress_result_1=stress_result_1,
        stress_result_2=stress_result_2,
        deflection_result=deflection_result,
        stability_result=stability_result
    )


def format_calculation_book(book: CalculationBook) -> str:
    """生成带双工况推导过程的计算书"""

    pipe = book.pipe
    load = book.load
    lr = book.load_result
    sr1 = book.stress_result_1
    sr2 = book.stress_result_2
    dr = book.deflection_result
    stability_result = book.stability_result

    # 提取两组工况的内力
    My1 = lr.工况1_竖向_总计 * pipe.span_m / 8
    Mz1 = lr.工况1_水平荷载 * pipe.span_m / 8
    M_total1 = math.sqrt(My1**2 + Mz1**2)

    My2 = lr.工况2_竖向_总计 * pipe.span_m / 8
    Mz2 = lr.工况2_水平荷载 * pipe.span_m / 8
    M_total2 = math.sqrt(My2**2 + Mz2**2)

    allowable_sigma = 0.9 * pipe.weld_reduction_coefficient * pipe.design_strength_MPa / load.importance_factor

    A_m2 = pipe.cross_section_area_mm2 / 1e6
    W_m3 = pipe.section_modulus_mm3 / 1e9

    # 动态生成支座对比表格
    support_check_md = ""
    R_total1 = math.sqrt((lr.工况1_竖向_总计/2)**2 + (lr.工况1_水平荷载/2)**2)
    R_total2 = math.sqrt((lr.工况2_竖向_总计/2)**2 + (lr.工况2_水平荷载/2)**2)

    support_type_val = pipe.support_type.value if hasattr(pipe.support_type, 'value') else pipe.support_type
    
    if support_type_val == "鞍式支承":
        support_check_md = f"""
### 5.2 鞍式支座局部应力验算 (Zick 分析法)
*依据《CECS 214-2006》第7.2节进行局部折算：*
* **支座参数**: 鞍座包角 $2\\theta$ = {pipe.saddle_angle}°, 垫板宽度 $b$ = {pipe.saddle_width_mm} mm

| 验算位置 / 工况 | 空间总反力 $R$ | 管底压应力 $\\sigma_{{xL}}$ | 鞍角弯曲应力 $\\sigma_{{\\theta L}}$ | 控制点折算应力 $\\sigma_{{eq}}$ | 结论 |
|---|---|---|---|---|---|
| **工况1 (满水+风)** | {R_total1:.2f} kN | {sr1.sigma_xL_bottom:.2f} MPa | {sr1.sigma_thetaL_horn:.2f} MPa | **{sr1.combined_stress_support:.2f}** MPa | {'✅' if sr1.is_safe_support else '❌'} |
| **工况2 (空管+风)** | {R_total2:.2f} kN | {sr2.sigma_xL_bottom:.2f} MPa | {sr2.sigma_thetaL_horn:.2f} MPa | **{sr2.combined_stress_support:.2f}** MPa | {'✅' if sr2.is_safe_support else '❌'} |
"""
    else:
        support_check_md = f"""
### 5.2 环式支承剪切应力验算
| 验算位置 / 工况 | 空间总剪力 $V$ | 平均剪应力 $\\tau$ | 折算应力 $\\sigma_{{eq}}$ | 结论 |
|---|---|---|---|---|
| **工况1 (满水+风)** | {R_total1:.2f} kN | {sr1.tau_avg:.2f} MPa | **{sr1.combined_stress_support:.2f}** MPa | {'✅' if sr1.is_safe_support else '❌'} |
| **工况2 (空管+风)** | {R_total2:.2f} kN | {sr2.tau_avg:.2f} MPa | **{sr2.combined_stress_support:.2f}** MPa | {'✅' if sr2.is_safe_support else '❌'} |
"""

    md = f"""
# 自承式管线桥结构设计计算书

## 第一章 设计基本信息
* **跨度 $L$**: {pipe.span_m} m
* **钢管规格**: D{int(pipe.diameter_mm)} × {int(pipe.wall_thickness_mm)} mm
* **钢材牌号**: {pipe.material_grade} (设计强度 $f$ = {pipe.design_strength_MPa} MPa, $E$ = {pipe.elastic_modulus_MPa} MPa)

## 第二章 截面几何特性计算过程
* **截面积 $A$** = $\\pi(D^2 - d^2)/4$ = **{pipe.cross_section_area_mm2:.2f}** mm²
* **抗弯截面模量 $W$** = $\\pi(D^4 - d^4)/(32D)$ = **{pipe.section_modulus_mm3:.2f}** mm³

## 第三章 荷载计算推导 (全透明展开)
### 3.1 恒载标准值计算
* **管道自重 $G_{{pipe}}$** = **{lr.self_weight_per_m:.2f}** kN/m
* **管内水重 $G_{{water}}$** = **{lr.water_weight_per_m:.2f}** kN/m
* **防腐层及附加活载**: {lr.anti_corrosion_per_m + lr.additional_per_m:.2f} kN/m

### 3.2 自动风荷载计算
* **基本风压 $w_0$**: {load.basic_wind_pressure} kN/m² (标高 {load.elevation_m}m, {load.terrain_category})
* **标准风压 $W_k$** = $\\beta_z \\cdot \\mu_s \\cdot \\mu_z \\cdot w_0$ = **{lr.Wk:.3f}** kN/m²
* **风线荷载 $q_w$** = $W_k \\cdot D$ = **{lr.wind_horizontal_kN / pipe.span_m:.2f}** kN/m

## 第四章 空间内力与应力组合推导 (严格遵循 CECS 214 表 5.2.7)
*注：内水压力与温度作用直接在第五章作为内部管壁截面应力参与叠加，不产生宏观外部组合弯矩。*

### 4.1 组合 I (运行态)：自重 + 水重 + 内压 + 温度 + 活载 (无风载)
* **竖向设计总荷载 $Q_{{y1}}$** = $1.2(G_{{pipe}} + G_{{anti}} + G_{{water}}) + 1.4 Q_{{live}}$ = **{lr.工况1_竖向_总计:.2f}** kN
* **水平设计总荷载 $Q_{{z1}}$** = 0.00 kN (本组合不计风载)
* **跨中最大弯矩 $M_{{total,1}}$** = $Q_{{y1}} \\cdot L / 8$ = **{My1:.2f}** kN·m

### 4.2 组合 II (极端态)：自重 + 水重 + 内压 + 温度 + 风载 (无活载)
* **竖向设计总荷载 $Q_{{y2}}$** = $1.2(G_{{pipe}} + G_{{anti}} + G_{{water}})$ = **{lr.工况2_竖向_总计:.2f}** kN
* **水平设计总荷载 $Q_{{z2}}$** = $1.4 \\cdot W_k \\cdot D \\cdot L$ = **{lr.工况2_水平荷载:.2f}** kN
* **跨中最大弯矩 $M_{{total,2}}$** = $\\sqrt{{M_{{y2}}^2 + M_{{z2}}^2}}$ = **{M_total2:.2f}** kN·m

## 第五章 关键截面应力验证包络
允许应力 $[\\sigma]$ = $0.9 \\cdot \\phi \\cdot f / \\gamma_0$ = **{allowable_sigma:.1f}** MPa

### 5.1 跨中综合折算应力验算
*第四强度理论公式*: $\\sigma_{{eq}} = \\sqrt{{\\sigma_x^2 + \\sigma_\\theta^2 - \\sigma_x \\cdot \\sigma_\\theta}}$

| 工况组合 | 弯曲应力 $\\sigma_M$ | 温度应力 $\\sigma_t$ | 环向应力 $\\sigma_\\theta$ | 综合折算应力 $\\sigma_{{eq}}$ | 结论 |
|---|---|---|---|---|---|
| **工况1 (满水+风)** | {sr1.sigma_x_M_combined:.2f} | {sr1.sigma_x_t:.2f} | {sr1.sigma_theta_Fw:.2f} | **{sr1.combined_stress:.2f}** | {'✅ 满足' if sr1.is_safe else '❌ 超限'} |
| **工况2 (空管+风)** | {sr2.sigma_x_M_combined:.2f} | {sr2.sigma_x_t:.2f} | {sr2.sigma_theta_Fw:.2f} | **{sr2.combined_stress:.2f}** | {'✅ 满足' if sr2.is_safe else '❌ 超限'} |

{support_check_md}

## 第六章 刚度与稳定验算
### 6.1 挠度计算
* **实际最大挠度 $f$** = **{dr.deflection_mm:.2f}** mm
* **规范允许挠度 $[f]$** = $L/500$ = **{dr.allowable_deflection_mm:.1f}** mm ({'✅ 满足' if dr.is_adequate else '❌ 超限'})

### 6.2 环向失稳验算
* **实际真空负压 $p_{{vac}}$** = **{stability_result.actual_pressure:.4f}** MPa
* **临界失稳压力 $P_{{cr}}$** = **{stability_result.critical_pressure:.4f}** MPa
* ({'✅ 稳定' if stability_result.is_stable else '❌ 屈曲风险'})

## 附录：下部土建基础提资表
| 受力状态 | 支座竖向力 $R$ (kN) | 支座水平力 $V_z$ (kN) | 提资用途 |
|---|---|---|---|
| **满载极限压降** | **{lr.R_max:.2f} (↓下压)** | {lr.V_z_max:.2f} | 基础底面积、承台及桩基验算 |
| **空管极轻状态** | **{lr.R_min:.2f} (↓下压)** | {lr.V_z_max:.2f} | 基础抗倾覆、地脚螺栓抗拔 |

---
**计算人**: 管道桥计算程序 V3.1
**审核人**: 
**日期**: 
"""
    return md


def format_calculation_book_latex(book: CalculationBook) -> str:
    """生成LaTeX格式计算书"""
    # 简化版本，暂时返回空字符串
    return ""


def generate_pdf(book: CalculationBook) -> bytes:
    """生成PDF文件"""
    raise Exception("PDF功能需要安装LaTeX，请使用Word导出")
