import math
from models.pipe import PipeModel
from models.load import LoadModel
from calculation.load_calc import LoadResult
from calculation.stress_calc import StressResult
from calculation.deflection_calc import DeflectionResult
from calculation.stability_calc import StabilityResult


def format_calculation_book(pipe: PipeModel, load: LoadModel, 
                            lr: LoadResult, sr: StressResult, 
                            dr: DeflectionResult = None, stability_result: StabilityResult = None) -> str:
    
    # 提前计算一些用于显示的局部中间变量
    My = lr.工况1_竖向_总计 * pipe.span_m**2 / 8
    Mz = lr.工况1_水平荷载 * pipe.span_m**2 / 8
    M_total = math.sqrt(My**2 + Mz**2)
    allowable_sigma = 0.9 * pipe.weld_reduction_coefficient * pipe.design_strength_MPa / load.importance_factor

    # 使用 f-string 生成带有推导过程的透明化 Markdown
    md = f"""
# 自承式管线桥结构设计计算书

## 第一章 设计基本信息
* **跨度 L**: {pipe.span_m} m
* **支承方式**: {pipe.support_type}
* **钢材牌号**: {pipe.steel_grade} (抗拉设计强度 f = {pipe.design_strength_MPa} MPa)
* **结构重要性系数 γ₀**: {load.importance_factor}

## 第二章 截面几何特性计算过程
根据输入的管径 D={pipe.diameter_mm} mm，壁厚 t={pipe.wall_thickness_mm} mm，内径 d={pipe.inner_diameter_mm} mm：
* **截面积 A** = π(D² - d²)/4 = **{pipe.cross_section_area_mm2:.2f}** mm²
* **惯性矩 I** = π(D⁴ - d⁴)/64 = **{pipe.moment_of_inertia_mm4:.2e}** mm⁴
* **抗弯截面模量 W** = π(D⁴ - d⁴)/(32D) = **{pipe.section_modulus_mm3:.2f}** mm³

## 第三章 荷载标准值计算
* **管道自重**: {lr.self_weight_per_m:.2f} kN/m
* **管内水重**: {lr.water_weight_per_m:.2f} kN/m
* **风荷载标准值**: {lr.wind_horizontal_kN / pipe.span_m:.2f} kN/m

## 第四章 空间内力计算过程 (基于基本组合工况)
### 4.1 竖向作用 (重力主导)
* **竖向组合线荷载 qᵧ** = {lr.工况1_竖向_总计:.2f} kN/m
* **竖向支座反力 Rᵧ** = qᵧ × L / 2 = {lr.工况1_竖向_总计 * pipe.span_m / 2:.2f} kN
* **竖向跨中弯矩 Mᵧ** = qᵧ × L² / 8 = **{My:.2f}** kN·m

### 4.2 水平作用 (风荷载主导)
* **水平组合线荷载 qᵤ** = {lr.工况1_水平荷载:.2f} kN/m
* **水平跨中弯矩 Mᵤ** = qᵤ × L² / 8 = **{Mz:.2f}** kN·m

### 4.3 空间合成内力
* **跨中总合成弯矩 M<sub>total</sub>** = √(Mᵧ² + Mᵤ²) = **{M_total:.2f}** kN·m

## 第五章 关键应力分量求值
* **最大弯曲应力 σₘ** = M<sub>total</sub>/W = **{sr.sigma_x_M_combined:.2f}** MPa
* **内水压环向应力 σ<sub>θ</sub>** = p×r/t = **{sr.sigma_theta_Fw:.2f}** MPa
* **温度应力 σ<sub>t</sub>** = α×E×ΔT = **{sr.sigma_x_t:.2f}** MPa
* **支座最大剪应力 τ<sub>max</sub>** = 2V/A = **{sr.tau_max:.2f}** MPa

## 第六章 综合包络验算结论 (按第四强度理论)
允许应力 [σ] = 0.9×φ×f/γ₀ = **{allowable_sigma:.1f}** MPa

| 验算位置 | 组合公式推导 | 折算应力 (MPa) | 结论 |
|---|---|---|---|
| **跨中包络** (取管顶/管底不利极值) | √(σ<sub>x(极值)</sub>² + σ<sub>θ</sub>² - σ<sub>x</sub>σ<sub>θ</sub>) | **{sr.combined_stress:.2f}** | {'✅ 满足' if sr.is_safe else '❌ 不合格'} |
| **支座截面** (含局部压应力) | √(σ<sub>local</sub>² + 3τ²) | **{sr.combined_stress_support:.2f}** | {'✅ 满足' if sr.is_safe_support else '❌ 不合格'} |

## 第七章 环向失稳验算 (负压屈曲)
* **实际真空负压 p** = **{stability_result.actual_pressure:.4f}** MPa
* **管壁宽厚比 t/D** = {pipe.wall_thickness_mm} / {pipe.diameter_mm} = {pipe.wall_thickness_mm/pipe.diameter_mm:.4f}
* **临界失稳压力 P<sub>cr</sub>** = 2.6E(t/D)<sup>2或2.5</sup> = **{stability_result.critical_pressure:.4f}** MPa
* **结论**: 实际负压 {stability_result.actual_pressure:.4f} MPa {'≤' if stability_result.is_stable else '>'} 允许负压 {stability_result.allowable_pressure:.4f} MPa ({'✅ 结构稳定' if stability_result.is_stable else '❌ 存在屈曲风险'})

---
**计算人**: 管道桥计算程序 V5.0
**审核人**: 
**日期**: 
"""
    return md
