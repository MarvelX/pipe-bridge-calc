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
    """生成带公式推导过程的计算书 (Markdown格式)"""

    pipe = book.pipe
    load = book.load
    lr = book.load_result
    sr = book.stress_result
    dr = book.deflection_result
    stability_result = book.stability_result

    My = lr.工况1_竖向_总计 * pipe.span_m / 8
    Mz = lr.工况1_水平荷载 * pipe.span_m / 8
    M_total = math.sqrt(My**2 + Mz**2)
    allowable_sigma = 0.9 * pipe.weld_reduction_coefficient * pipe.design_strength_MPa / load.importance_factor

    A_m2 = pipe.cross_section_area_mm2 / 1e6
    W_m3 = pipe.section_modulus_mm3 / 1e9

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
* **总合成最大弯矩 $M_{{total}}$** = $\\sqrt{{M_y^2 + M_z^2}}$ = **{M_total:.2f}** kN·m

## 第五章 关键截面应力验证
* **弯曲应力 $\\sigma_M$** = $M/W$ = **{sr.sigma_x_M_combined:.2f}** MPa
* **环向应力 $\\sigma_\\theta$** = $p \\cdot r / t$ = **{sr.sigma_theta_Fw:.2f}** MPa
* **温度应力 $\\sigma_t$** = $\\alpha \\cdot E \\cdot \\Delta T$ = **{sr.sigma_x_t:.2f}** MPa

### 综合包络验算结论 (按第四强度理论)
允许应力 $[\\sigma]$ = **{allowable_sigma:.1f}** MPa

| 验算位置 | 折算应力 (MPa) | 结论 |
|---|---|---|
| **跨中最不利截面** | **{sr.combined_stress:.2f}** | {'✅ 满足' if sr.is_safe else '❌ 不合格'} |
| **支座剪切截面** | **{sr.combined_stress_support:.2f}** | {'✅ 满足' if sr.is_safe_support else '❌ 不合格'} |

## 第六章 刚度(挠度)与稳定验算
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
| **满载极限压降** | **{lr.R_max:.2f}** | {lr.V_z_max:.2f} | 基础设计 |
| **空管极轻状态** | **{lr.R_min:.2f}** | {lr.V_z_max:.2f} | 抗倾覆验算 |

---
**计算人**: 管道桥计算程序 V5.1
**审核人**: 
**日期**: 
"""
    return md


def format_calculation_book_latex(book: CalculationBook) -> str:
    """生成LaTeX格式计算书"""
    
    pipe = book.pipe
    load = book.load
    lr = book.load_result
    sr = book.stress_result
    dr = book.deflection_result
    stability_result = book.stability_result

    My = lr.工况1_竖向_总计 * pipe.span_m / 8
    Mz = lr.工况1_水平荷载 * pipe.span_m / 8
    M_total = math.sqrt(My**2 + Mz**2)
    allowable_sigma = 0.9 * pipe.weld_reduction_coefficient * pipe.design_strength_MPa / load.importance_factor

    A_m2 = pipe.cross_section_area_mm2 / 1e6
    W_m3 = pipe.section_modulus_mm3 / 1e9
    
    # 安全结论
    midspan_conclusion = r"\checkmark{满足}" if sr.is_safe else r"\times{不合格}"
    support_conclusion = r"\checkmark{满足}" if sr.is_safe_support else r"\times{不合格}"
    deflection_conclusion = r"\checkmark{满足}" if dr.is_adequate else r"\times{超限}"
    stability_conclusion = r"\checkmark{稳定}" if stability_result.is_stable else r"\times{屈曲风险}"

    latex = fr"""
\documentclass[12pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage{{amsmath,amssymb}}
\usepackage{{graphicx}}
\usepackage{{ctex}}
\usepackage{{geometry}}
\geometry{{left=25mm,right=25mm,top=30mm,bottom=30mm}}

\title{{自承式管线桥结构设计计算书}}
\author{{管道桥计算程序 V5.1}}
\date{{{datetime.now().strftime("%Y年%m月%d日")}}}

\begin{{document}}

\maketitle

\section*{{设计基本信息}}
\begin{{itemize}}
    \item 跨度 $L$: {pipe.span_m} m
    \item 钢管规格: D{int(pipe.diameter_mm)} $\times$ {int(pipe.wall_thickness_mm)} mm
    \item 钢材牌号: {pipe.material_grade} (设计强度 $f$ = {pipe.design_strength_MPa} MPa, $E$ = {pipe.elastic_modulus_MPa} MPa)
    \item 结构重要性系数 $\gamma_0$: {load.importance_factor}
\end{{itemize}}

\section*{{截面几何特性计算过程}}
\begin{{align}}
A &= \frac{{\pi(D^2 - d^2)}}{{4}} = {pipe.cross_section_area_mm2:.2f}\ mm^2 \\
I &= \frac{{\pi(D^4 - d^4)}}{{64}} = {pipe.moment_of_inertia_mm4:.2e}\ mm^4 \\
W &= \frac{{\pi(D^4 - d^4)}}{{32D}} = {pipe.section_modulus_mm3:.2f}\ mm^3
\end{{align}}

\section*{{荷载计算推导}}
\subsection*{{恒载标准值计算}}
\begin{{align}}
G_{{pipe}} &= A \cdot \rho \cdot g \cdot K = {A_m2:.4f} \times 7850 \times 9.81 \times {load.self_weight_amplification} / 1000 = {lr.self_weight_per_m:.2f}\ kN/m \\
G_{{water}} &= \frac{{\pi d^2}}{{4}} \cdot \rho_w \cdot g = {math.pi*(pipe.inner_diameter_mm/1000)**2/4:.4f} \times 1000 \times 9.81 / 1000 = {lr.water_weight_per_m:.2f}\ kN/m
\end{{align}}

\subsection*{{自动风荷载计算}}
\begin{{align}}
w_0 &= {load.basic_wind_pressure}\ kN/m^2 \\
W_k &= \beta_z \cdot \mu_s \cdot \mu_z \cdot w_0 = {lr.beta_z:.2f} \times {lr.mu_s:.2f} \times {lr.mu_z:.3f} \times {load.basic_wind_pressure} = {lr.Wk:.3f}\ kN/m^2 \\
q_w &= W_k \cdot D = {lr.Wk:.3f} \times {pipe.diameter_mm/1000:.3f} = {lr.wind_horizontal_kN / pipe.span_m:.2f}\ kN/m
\end{{align}}

\section*{{空间内力组合推导}}
\subsection*{{竖向内力}}
\begin{{align}}
Q_y &= 1.2 \cdot G_k + 1.4 \cdot Q_k = {lr.工况1_竖向_总计:.2f}\ kN \\
M_y &= \frac{{Q_y \cdot L}}{{8}} = \frac{{{lr.工况1_竖向_总计:.2f} \times {pipe.span_m}}}{{8}} = {My:.2f}\ kN\cdot m
\end{{align}}

\subsection*{{水平内力与空间合成}}
\begin{{align}}
Q_z &= 1.4 \cdot W_k \cdot D \cdot L = {lr.工况1_水平荷载:.2f}\ kN \\
M_z &= \frac{{Q_z \cdot L}}{{8}} = \frac{{{lr.工况1_水平荷载:.2f} \times {pipe.span_m}}}{{8}} = {Mz:.2f}\ kN\cdot m \\
M_{{total}} &= \sqrt{{M_y^2 + M_z^2}} = {M_total:.2f}\ kN\cdot m
\end{{align}}

\section*{{关键截面应力验证}}
\begin{{align}}
\sigma_M &= \frac{{M}}{{W}} = {sr.sigma_x_M_combined:.2f}\ MPa \\
\sigma_\theta &= \frac{{p \cdot r}}{{t}} = {sr.sigma_theta_Fw:.2f}\ MPa \\
\sigma_t &= \alpha \cdot E \cdot \Delta T = {sr.sigma_x_t:.2f}\ MPa
\end{{align}}

允许应力 $[\sigma] = 0.9 \cdot \phi \cdot f / \gamma_0 = {allowable_sigma:.1f}\ MPa$

\begin{{table}}[h]
\caption{{应力验算结果}}
\begin{{tabular}}{{|c|c|c|}}
\hline
验算位置 & 折算应力 (MPa) & 结论 \\
\hline
跨中最不利截面 & {sr.combined_stress:.2f} & {midspan_conclusion} \\
\hline
支座剪切截面 & {sr.combined_stress_support:.2f} & {support_conclusion} \\
\hline
\end{{tabular}}
\end{{table}}

\section*{{刚度(挠度)与稳定验算}}
\begin{{align}}
f &= {dr.deflection_mm:.2f}\ mm \\
[f] &= L/500 = {dr.allowable_deflection_mm:.1f}\ mm \quad {deflection_conclusion}
\end{{align}}

\begin{{align}}
p_{{vac}} &= {stability_result.actual_pressure:.4f}\ MPa \\
P_{{cr}} &= {stability_result.critical_pressure:.4f}\ MPa \quad {stability_conclusion}
\end{{align}}

\section*{{附录：下部土建基础提资表}}
\begin{{table}}[h]
\caption{{支座反力极值}}
\begin{{tabular}}{{|c|c|c|c|}}
\hline
受力状态 & 支座竖向力 $R$ (kN) & 支座水平力 $V_z$ (kN) & 提资用途 \\
\hline
满载极限压降 & {lr.R_max:.2f} & {lr.V_z_max:.2f} & 基础设计 \\
\hline
空管极轻状态 & {lr.R_min:.2f} & {lr.V_z_max:.2f} & 抗倾覆验算 \\
\hline
\end{{tabular}}
\end{{table}}

\vspace{{2cm}}
\begin{{center}}
计算人: 管道桥计算程序 V5.1 \qquad 审核人: \qquad 日期: \underline{{\\quad\quad\quad\quad}}
\end{{center}}

\end{{document}}
"""
    return latex


def generate_pdf(book: CalculationBook) -> bytes:
    """生成PDF文件"""
    try:
        from pylatex import Document, PageStyle, Head, Foot, MiniPage, Standalone, Section, Subsection, Command, NewPage
        from pylatex.utils import NoEscape, italic
        from pylatex.math import Math, Alignat, Equation
        import io
        
        doc = Document(geometry_options={"left": "25mm", "right": "25mm", "top": "30mm", "bottom": "30mm"})
        
        # 中文支持
        doc.packages.append(NoEscape(r'\usepackage{ctex}'))
        
        # 标题
        doc.append(NoEscape(r'\title{自承式管线桥结构设计计算书}'))
        doc.append(NoEscape(r'\author{管道桥计算程序 V5.1}'))
        doc.append(NoEscape(r'\date{' + datetime.now().strftime("%Y年%m月%d日") + '}'))
        doc.append(Command('maketitle'))
        
        pipe = book.pipe
        load = book.load
        lr = book.load_result
        sr = book.stress_result
        dr = book.deflection_result
        stability_result = book.stability_result
        
        My = lr.工况1_竖向_总计 * pipe.span_m / 8
        Mz = lr.工况1_水平荷载 * pipe.span_m / 8
        M_total = math.sqrt(My**2 + Mz**2)
        allowable_sigma = 0.9 * pipe.weld_reduction_coefficient * pipe.design_strength_MPa / load.importance_factor
        
        # 第一章 设计基本信息
        with doc.create(Section('设计基本信息')):
            doc.append(f'跨度 L: {pipe.span_m} m\n')
            doc.append(f'钢管规格: D{int(pipe.diameter_mm)} × {int(pipe.wall_thickness_mm)} mm\n')
            doc.append(f'钢材牌号: {pipe.material_grade} (f = {pipe.design_strength_MPa} MPa, E = {pipe.elastic_modulus_MPa} MPa)\n')
            doc.append(f'结构重要性系数 γ₀: {load.importance_factor}\n')
        
        # 第二章 截面几何特性
        with doc.create(Section('截面几何特性计算过程')):
            doc.append(f'A = {pipe.cross_section_area_mm2:.2f} mm²\n')
            doc.append(f'I = {pipe.moment_of_inertia_mm4:.2e} mm⁴\n')
            doc.append(f'W = {pipe.section_modulus_mm3:.2f} mm³\n')
        
        # 第三章 荷载计算
        with doc.create(Section('荷载计算推导')):
            with doc.create(Subsection('恒载标准值')):
                doc.append(f'管道自重 G_pipe = {lr.self_weight_per_m:.2f} kN/m\n')
                doc.append(f'管内水重 G_water = {lr.water_weight_per_m:.2f} kN/m\n')
            with doc.create(Subsection('自动风荷载')):
                doc.append(f'基本风压 w₀ = {load.basic_wind_pressure} kN/m²\n')
                doc.append(f'标准风压 Wk = {lr.Wk:.3f} kN/m²\n')
        
        # 第四章 内力组合
        with doc.create(Section('空间内力组合推导')):
            doc.append(f'竖向设计总荷载 Qy = {lr.工况1_竖向_总计:.2f} kN\n')
            doc.append(f'跨中竖向弯矩 My = {My:.2f} kN·m\n')
            doc.append(f'水平设计总荷载 Qz = {lr.工况1_水平荷载:.2f} kN\n')
            doc.append(f'跨中水平弯矩 Mz = {Mz:.2f} kN·m\n')
            doc.append(f'总合成最大弯矩 M_total = {M_total:.2f} kN·m\n')
        
        # 第五章 应力验证
        with doc.create(Section('关键截面应力验证')):
            doc.append(f'弯曲应力 σM = {sr.sigma_x_M_combined:.2f} MPa\n')
            doc.append(f'环向应力 σθ = {sr.sigma_theta_Fw:.2f} MPa\n')
            doc.append(f'温度应力 σt = {sr.sigma_x_t:.2f} MPa\n')
            doc.append(f'允许应力 [σ] = {allowable_sigma:.1f} MPa\n')
            doc.append(f'跨中折算应力 = {sr.combined_stress:.2f} MPa ({["不合格", "满足"][sr.is_safe]})\n')
        
        # 第六章 挠度与稳定
        with doc.create(Section('刚度与稳定验算')):
            doc.append(f'实际挠度 f = {dr.deflection_mm:.2f} mm\n')
            doc.append(f'允许挠度 [f] = {dr.allowable_deflection_mm:.1f} mm\n')
            doc.append(f'真空负压 p_vac = {stability_result.actual_pressure:.4f} MPa\n')
            doc.append(f'临界失稳压力 P_cr = {stability_result.critical_pressure:.4f} MPa\n')
        
        # 附录
        with doc.create(Section('附录：下部土建基础提资表')):
            doc.append(f'满载极限 R_max = {lr.R_max:.2f} kN\n')
            doc.append(f'空管极轻 R_min = {lr.R_min:.2f} kN\n')
            doc.append(f'最大水平剪力 V_z_max = {lr.V_z_max:.2f} kN\n')
        
        # 落款
        doc.append(NoEscape(r'\vspace{2cm}'))
        doc.append(NoEscape(r'\begin{center}'))
        doc.append('计算人: 管道桥计算程序 V5.1 \quad 审核人: \quad 日期: __________\n')
        doc.append(NoEscape(r'\end{center}'))
        
        # 生成PDF
        pdf_bytes = doc.pdf_attached_file
        return pdf_bytes
        
    except Exception as e:
        raise Exception(f"PDF生成失败: {str(e)}。请确保已安装 xelatex: brew install mactex-no-gui 或 apt-get install texlive-latex-base")
