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
    stress_result: StressResult
    deflection_result: DeflectionResult = None
    stability_result: StabilityResult = None


def generate_calculation_book(pipe: PipeModel, load: LoadModel, 
                            load_result: LoadResult, stress_result: StressResult,
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
        stress_result=stress_result,
        deflection_result=deflection_result,
        stability_result=stability_result
    )


def format_calculation_book(book: CalculationBook) -> str:
    """生成带公式推导过程的计算书"""

    pipe = book.pipe
    load = book.load
    lr = book.load_result
    sr = book.stress_result
    dr = book.deflection_result
    stability_result = book.stability_result

    # 【修复 FATAL-ERROR】：工况总计已经是跨总荷载 (kN)，根据简支梁力学公式 M = Q*L/8，应去掉多余的平方
    My = lr.工况1_竖向_总计 * pipe.span_m / 8
    Mz = lr.工况1_水平荷载 * pipe.span_m / 8
    M_total = math.sqrt(My**2 + Mz**2)
    allowable_sigma = 0.9 * pipe.weld_reduction_coefficient * pipe.design_strength_MPa / load.importance_factor

    # 管道面积与截面模量
    A_m2 = pipe.cross_section_area_mm2 / 1e6
    W_m3 = pipe.section_modulus_mm3 / 1e9

    # 【修复 LaTeX 渲染】：在 f-string 中，LaTeX 下标如 {pipe} 需使用双大括号 {{pipe}} 进行转义。
    # 统一将 HTML 标签 (如 <sub>) 替换为标准的 Markdown 数学公式语法 ($q_y$, $P_{cr}$ 等)。
    md = f"""
# 自承式管线桥结构设计计算书

## 第一章 设计基本信息
* **跨度 $L$**: {pipe.span_m} m
* **钢管规格**: D{int(pipe.diameter_mm)} × {int(pipe.wall_thickness_mm)} mm
* **钢材牌号**: {pipe.material_grade} (设计强度 $f$ = {pipe.design_strength_MPa} MPa, $E$ = {pipe.elastic_modulus_MPa} MPa)
* **结构重要性系数 $\\gamma_0$**: {load.importance_factor}

## 第二章 截面几何特性计算过程
* **截面积 $A$** = $\\pi(D^2 - d^2)/4$ = **{pipe.cross_section_area_mm2:.2f}** mm²
* **惯性矩 $I$** = $\\pi(D^4 - d^4)/64$ = **{pipe.moment_of_inertia_mm4:.2e}** mm⁴
* **抗弯截面模量 $W$** = $\\pi(D^4 - d^4)/(32D)$ = **{pipe.section_modulus_mm3:.2f}** mm³

## 第三章 荷载计算推导 (全透明展开)
### 3.1 恒载标准值计算
* **管道自重 $G_{{pipe}}$** = $A \\cdot \\rho \\cdot g \\cdot K$ = {A_m2:.4f} m² × 7850 kg/m³ × 9.81 N/kg × {load.self_weight_amplification} / 1000 = **{lr.self_weight_per_m:.2f}** kN/m
* **管内水重 $G_{{water}}$** = $\\pi d^2/4 \\cdot \\rho_w \\cdot g$ = {math.pi*(pipe.inner_diameter_mm/1000)**2/4:.4f} m² × 1000 × 9.81 / 1000 = **{lr.water_weight_per_m:.2f}** kN/m
* **防腐层及附加活载**: {lr.anti_corrosion_per_m + lr.additional_per_m:.2f} kN/m

### 3.2 自动风荷载计算 (基于基本风压)
* **基本风压 $w_0$**: {load.basic_wind_pressure} kN/m² (标高 {load.elevation_m}m, {load.terrain_category})
* **标准风压 $W_k$** = $\\beta_z \\cdot \\mu_s \\cdot \\mu_z \\cdot w_0$ = {lr.beta_z:.2f} × {lr.mu_s:.2f} × {lr.mu_z:.3f} × {load.basic_wind_pressure} = **{lr.Wk:.3f}** kN/m²
* **风线荷载 $q_w$** = $W_k \\cdot D$ = {lr.Wk:.3f} × {pipe.diameter_mm/1000:.3f} = **{lr.wind_horizontal_kN / pipe.span_m:.2f}** kN/m

## 第四章 空间内力组合推导
### 4.1 竖向内力 (重力主导)
* **竖向设计总荷载 $Q_y$** = $1.2 \\cdot G_k + 1.4 \\cdot Q_k$ = **{lr.工况1_竖向_总计:.2f}** kN
* **跨中竖向弯矩 $M_y$** = $Q_y \\cdot L / 8$ = {lr.工况1_竖向_总计:.2f} × {pipe.span_m} / 8 = **{My:.2f}** kN·m

### 4.2 水平内力 (风主导)与空间合成
* **水平设计总荷载 $Q_z$** = $1.4 \\cdot W_k \\cdot D \\cdot L$ = **{lr.工况1_水平荷载:.2f}** kN
* **跨中水平弯矩 $M_z$** = $Q_z \\cdot L / 8$ = {lr.工况1_水平荷载:.2f} × {pipe.span_m} / 8 = **{Mz:.2f}** kN·m
* **总合成最大弯矩 $M_{{total}}$** = $\\sqrt{{M_y^2 + M_z^2}}$ = $\\sqrt{{{My:.2f}^2 + {Mz:.2f}^2}}$ = **{M_total:.2f}** kN·m

## 第五章 关键截面应力验证
* **弯曲应力 $\\sigma_M$** = $M/W$ = {M_total:.2f}×10³ / {W_m3:.6f} m³ / 10⁶ = **{sr.sigma_x_M_combined:.2f}** MPa
* **环向应力 $\\sigma_\\theta$** = $p \\cdot r / t$ = {load.internal_pressure_MPa} × {pipe.inner_radius_mm} / {pipe.wall_thickness_mm} = **{sr.sigma_theta_Fw:.2f}** MPa
* **温度应力 $\\sigma_t$** = $\\alpha \\cdot E \\cdot \\Delta T$ = 1.2×10⁻⁵ × {pipe.elastic_modulus_MPa} × ({load.temperature_load_C}) = **{sr.sigma_x_t:.2f}** MPa

### 综合包络验算结论 (按第四强度理论)
允许应力 $[\\sigma]$ = $0.9 \\cdot \\phi \\cdot f / \\gamma_0$ = 0.9 × {pipe.weld_reduction_coefficient} × {pipe.design_strength_MPa} / {load.importance_factor} = **{allowable_sigma:.1f}** MPa

| 验算位置 | 组合公式推导 | 折算应力 (MPa) | 结论 |
|---|---|---|---|
| **跨中最不利截面** | $\\sqrt{{\\sigma_x^2 + \\sigma_\\theta^2 - \\sigma_x \\cdot \\sigma_\\theta}}$ | **{sr.combined_stress:.2f}** | {'✅ 满足' if sr.is_safe else '❌ 不合格'} |
| **支座剪切截面** | $\\sqrt{{\\sigma_{{local}}^2 + 3\\tau^2}}$ | **{sr.combined_stress_support:.2f}** | {'✅ 满足' if sr.is_safe_support else '❌ 不合格'} |

## 第六章 刚度(挠度)与稳定验算
### 6.1 挠度计算
* **实际最大挠度 $f$** = **{dr.deflection_mm:.2f}** mm
* **规范允许挠度 $[f]$** = $L/500$ = **{dr.allowable_deflection_mm:.1f}** mm (结论: {'✅ 满足' if dr.is_adequate else '❌ 超限'})

### 6.2 环向失稳验算 (负压屈曲)
* **实际真空负压 $p_{{vac}}$** = **{stability_result.actual_pressure:.4f}** MPa
* **临界失稳压力 $P_{{cr}}$** = $2.6E(t/D)^{{2.5}}$ = **{stability_result.critical_pressure:.4f}** MPa
* 结论: 实际负压 {stability_result.actual_pressure:.4f} MPa {'≤' if stability_result.is_stable else '>'} 允许负压 {stability_result.allowable_pressure:.4f} MPa ({'✅ 结构稳定' if stability_result.is_stable else '❌ 屈曲风险'})

## 附录：下部土建基础提资表
*以下单侧支座反力极值用于下部结构独立基础设计及抗倾覆/抗拔验算：*
| 受力状态 | 支座竖向力 $R$ (kN) | 支座水平力 $V_z$ (kN) | 提资用途 |
|---|---|---|---|
| **满载极限压降** | **{lr.R_max:.2f} (↓下压)** | {lr.V_z_max:.2f} | 独立基础底面积、承台及桩基端承力设计 |
| **空管极轻状态** | **{lr.R_min:.2f} (↓下压)** | {lr.V_z_max:.2f} | 基础抗倾覆验算，地脚螺栓抗拔验算 |

---
**计算人**: 管道桥计算程序 V5.1
**审核人**: 
**日期**: 
"""
    return md
