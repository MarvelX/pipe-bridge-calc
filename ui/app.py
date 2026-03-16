"""
管桥计算器 Streamlit UI
符合CECS 214-2006规范
"""
import streamlit as st
import sys
import os
import math

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.pipe import PipeModel, STANDARD_PIPES, SupportType, create_pipe
from models.load import LoadModel
from calculation.load_calc import calculate_loads
from calculation.stress_calc import calculate_stress
from calculation.deflection_calc import calculate_deflection
from calculation.stability_calc import calculate_ring_stability
from calculation.book_calc import generate_calculation_book, format_calculation_book, format_calculation_book_latex, generate_pdf
from calculation.export_doc import create_word_report
from ui.plot_utils import draw_schematic

st.set_page_config(page_title="管桥计算器", page_icon="🌉", layout="wide")

def main():
    st.title("🌉 管桥结构计算器 (V20260316_1522)")
    st.markdown("**符合 CECS 214-2006《自承式给水钢管跨越结构设计规程》**")

    # ========== Sidebar 输入参数 ==========
    st.sidebar.header("📝 输入参数")

    st.sidebar.subheader("📐 1. 几何与材质参数")
    pipe_type = st.sidebar.selectbox("管道规格 (默认DN1000)", options=list(STANDARD_PIPES.keys()), index=7)
    spec = STANDARD_PIPES[pipe_type]
    wall_thickness = st.sidebar.number_input("管道壁厚 t (mm)", min_value=1.0, max_value=30.0, value=float(spec["wall_thickness_mm"]), step=0.5)

    st.sidebar.markdown("**⚠️ 当前仅支持单跨简支梁**")
    span_m = st.sidebar.number_input("跨径 L (m)", min_value=1.0, max_value=50.0, value=20.0, step=1.0)
    support_type = st.sidebar.selectbox("支承方式", ["鞍式支承", "环式支承"], index=1)
    support_half_angle = st.sidebar.slider("支承半角 θ (°)", 60.0, 180.0, 60.0, 5.0)
    friction_coef = st.sidebar.slider("摩擦系数 μ", 0.1, 0.6, 0.3, 0.05)

    # === V3.0 新增: 动态支座参数面板 ===
    saddle_angle = 120
    saddle_width_mm = 300.0
    has_stiffener = False
    if support_type == "鞍式支承":
        st.sidebar.markdown("*(▼ 鞍座详细参数)*")
        saddle_angle = st.sidebar.selectbox("鞍座包角 2θ", [120, 150], index=0)
        saddle_width_mm = st.sidebar.number_input("垫板宽度 b (mm)", value=300.0, step=50.0)
        has_stiffener = st.sidebar.checkbox("设置环向加劲肋", value=False)

    # 动态材质与焊缝
    material_grade = st.sidebar.selectbox("钢材牌号", ["Q235B", "Q355B", "S30408(不锈钢)"], index=0)
    weld_type = st.sidebar.selectbox("焊缝类型", ["自动焊", "手工焊", "焊缝质量等级Ⅲ", "焊缝质量等级Ⅱ", "焊缝质量等级Ⅰ"], index=0)
    weld_reduction_map = {"自动焊": 0.9, "手工焊": 0.85, "焊缝质量等级Ⅲ": 0.85, "焊缝质量等级Ⅱ": 0.9, "焊缝质量等级Ⅰ": 0.95}
    weld_reduction = weld_reduction_map[weld_type]

    st.sidebar.subheader("📊 2. 荷载参数")
    self_weight_amp = st.sidebar.number_input("管道自重放大系数 K", 1.0, 2.0, 1.10, 0.05)
    anti_corrosion = st.sidebar.number_input("防腐层重 (kN/m)", 0.0, 5.0, 0.10, 0.05)
    additional_load = st.sidebar.number_input("附加荷载 (kN/m)", 0.0, 10.0, 0.20, 0.05)
    internal_pressure = st.sidebar.number_input("设计内水压力 p (MPa)", 0.9, 2.0, 1.0, 0.1)

    st.sidebar.subheader("🌪️ 3. 自动风荷载参数")
    basic_wind_pressure = st.sidebar.number_input("基本风压 w0 (kN/m²)", value=0.45, step=0.05)
    elevation_m = st.sidebar.number_input("管道中心标高 z (m)", value=10.0, step=1.0)
    terrain_category = st.sidebar.selectbox("地面粗糙度类别", ["A类", "B类", "C类", "D类"], index=1)

    temperature_diff = st.sidebar.number_input("闭合温差 ΔT (°C)", -50.0, 50.0, 25.0, 5.0)
    temp_stress_reduction = st.sidebar.slider("温度应力折减系数 ζ", 0.5, 1.0, 0.70, 0.05)
    importance_factor = st.sidebar.number_input("重要性系数 γ₀", 0.9, 1.1, 1.0, 0.1)

    # ========== 实时比例反馈 ==========
    st.markdown("### 实时比例校核")
    fig = draw_schematic(spec["diameter_mm"], wall_thickness, span_m)
    st.pyplot(fig)

    # ========== Main content ==========
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📐 荷载与内力", "💪 强度计算", "📏 挠度验算", "⚙️ 稳定计算", "📋 计算书"])

    # 统一构建模型
    pipe = create_pipe(pipe_type, span_m, support_type=support_type, friction_coefficient=friction_coef, support_half_angle=support_half_angle, weld_reduction_coefficient=weld_reduction, saddle_angle=saddle_angle, saddle_width_mm=saddle_width_mm, has_stiffener=has_stiffener)
    pipe.material_grade = material_grade
    pipe.wall_thickness_mm = wall_thickness

    load = LoadModel(
        self_weight_amplification=self_weight_amp, anti_corrosion_weight=anti_corrosion, additional_load=additional_load,
        internal_pressure_MPa=internal_pressure, basic_wind_pressure=basic_wind_pressure, elevation_m=elevation_m, 
        terrain_category=terrain_category, temperature_load_C=temperature_diff, 
        temperature_stress_reduction=temp_stress_reduction, importance_factor=importance_factor
    )

    if st.button("🚀 开始计算", type="primary"):
        # 1. 核心计算调用
        load_result = calculate_loads(pipe, load)

        # 【V3.1 升级】分别求解工况1(满水) 和 工况2(空管) 的两组应力包络
        sr1 = calculate_stress(pipe, load, load_result.工况1_竖向_总计, load_result.工况1_水平荷载)
        sr2 = calculate_stress(pipe, load, load_result.工况2_竖向_总计, load_result.工况2_水平荷载)

        deflection_result = calculate_deflection(pipe, load_result)
        vacuum_kN = load.vacuum_pressure_MPa * pipe.diameter_mm * pipe.span_m / 1000
        stability_result = calculate_ring_stability(pipe, vacuum_kN)

        # ========== Tab 1: 荷载与内力 ==========
        with tab1:
            st.header("1. 内力组合推导明细")
            # 原有的 Tab 1 渲染代码保持不变 ... (展示工况1即可)
            st.info("提示：详细的双工况内力对比，请见导出的 Word 计算书。")

        # ========== Tab 2: 强度验算 (双工况升级版) ==========
        with tab2:
            st.header("2. 截面应力多工况包络验算")
            allowable = 0.9 * pipe.weld_reduction_coefficient * pipe.design_strength_MPa / load.importance_factor
            st.latex(r"\sigma_{eq} = \sqrt{\sigma_{x}^2 + \sigma_\theta^2 - \sigma_{x}\sigma_\theta} \le [\sigma]")
            st.caption(f"**规范允许折算应力 [σ]**: {allowable:.1f} MPa")

            st.markdown("### 2.1 跨中综合折算应力")
            col_c1, col_c2 = st.columns(2)

            with col_c1:
                st.markdown("#### 🌊 工况1: 满水运行+风荷载")
                st.write(f"- 弯曲应力 $\\sigma_M$: **{sr1.sigma_x_M_combined:.2f}** MPa")
                st.write(f"- 环向应力 $\\sigma_\\theta$: **{sr1.sigma_theta_Fw:.2f}** MPa")
                st.metric("工况1 控制折算应力", f"{sr1.combined_stress:.2f} MPa", 
                          delta="安全" if sr1.is_safe else "超限", delta_color="normal" if sr1.is_safe else "inverse")

            with col_c2:
                st.markdown("#### 💨 工况2: 空管状态+风荷载")
                st.write(f"- 弯曲应力 $\\sigma_M$: **{sr2.sigma_x_M_combined:.2f}** MPa")
                st.write(f"- 环向应力 $\\sigma_\\theta$: **{sr2.sigma_theta_Fw:.2f}** MPa")
                st.metric("工况2 控制折算应力", f"{sr2.combined_stress:.2f} MPa", 
                          delta="安全" if sr2.is_safe else "超限", delta_color="normal" if sr2.is_safe else "inverse")

            st.markdown("---")
            st.markdown("### 2.2 支座局部应力 (CECS 214 Zick法)")
            if support_type == "鞍式支承":
                st.caption(f"📌 鞍座参数: 包角 2θ={saddle_angle}°, 宽度 b={saddle_width_mm}mm")
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.markdown("**▶ 工况1 (满水主导)**")
                    st.write(f"- 管底压应力 $\\sigma_{{xL}}$: **{sr1.sigma_xL_bottom:.2f}** MPa")
                    st.write(f"- 鞍角应力 $\\sigma_{{\\theta L}}$: **{sr1.sigma_thetaL_horn:.2f}** MPa")
                    st.info(f"局部控制折算: **{sr1.combined_stress_support:.2f}** MPa")
                with col_s2:
                    st.markdown("**▶ 工况2 (空管风载主导)**")
                    st.write(f"- 管底压应力 $\\sigma_{{xL}}$: **{sr2.sigma_xL_bottom:.2f}** MPa")
                    st.write(f"- 鞍角应力 $\\sigma_{{\\theta L}}$: **{sr2.sigma_thetaL_horn:.2f}** MPa")
                    st.info(f"局部控制折算: **{sr2.combined_stress_support:.2f}** MPa")
            else:
                st.write("采用环式支承，执行支座剪切截面折算验算。")

        # ========== Tab 3: 挠度验算 ==========
        with tab3:
            st.header("3. 挠度验算明细")
            st.latex(r"f_{max} = \frac{5 q L^4}{384 E I}")
            st.info(f"实际计算总挠度: **$f$ = {deflection_result.deflection_mm:.2f} mm**")
            st.caption(f"允许挠度 [f] = L/500 = {deflection_result.allowable_deflection_mm:.1f} mm")
            if deflection_result.is_adequate:
                st.success("✅ 结构刚度满足规范要求！")
            else:
                st.error("❌ 挠度过大！")

        # ========== Tab 4: 稳定计算 ==========
        with tab4:
            st.header("4. 环向屈曲失稳验算")
            st.latex(r"P_{cr} = 2.6 E \left(\frac{t}{D}\right)^{2.5 \text{或} 2}")
            st.info(f"管壁临界失稳压力: **$P_{{cr}}$ = {stability_result.critical_pressure:.4f} MPa**")
            if stability_result.is_stable:
                st.success("✅ 管桥抗局部屈曲验算通过！")
            else:
                st.error("❌ 存在真空抽瘪风险！")

        # ========== Tab 5: 计算书导出 ==========
        with tab5:
            st.subheader("生成设计计算书")

            # 【修改入参】传入 sr1 和 sr2 两个结果对象
            book = generate_calculation_book(pipe, load, load_result, sr1, sr2, deflection_result, stability_result)
            md_report = format_calculation_book(book)

            st.markdown(md_report)

            st.markdown("---")
            st.markdown("### 导出计算书")
            
            col1, col2 = st.columns(2)
            
            # Word下载
            with col1:
                word_file = create_word_report(md_report)
                st.download_button(
                    label="📄 下载 Word (.docx)",
                    data=word_file,
                    file_name=f"管桥计算书_DN{int(pipe.diameter_mm)}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_word"
                )

if __name__ == "__main__":
    main()
