"""
管桥计算器 Streamlit UI
符合CECS 214-2006规范
"""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.pipe import PipeModel, STANDARD_PIPES, SupportType, create_pipe
from models.load import LoadModel
from calculation.load_calc import calculate_loads
from calculation.stress_calc import calculate_stress, calculate_support_reaction, calculate_bending_moment, calculate_shear_force
from calculation.deflection_calc import calculate_deflection, get_allowable_deflection
from calculation.stability_calc import calculate_ring_stability, get_stiffener_spacing
from calculation.pile_calc import PileModel, SoilLayer, calculate_pile_capacity
from calculation.book_calc import generate_calculation_book, format_calculation_book


st.set_page_config(
    page_title="管桥计算器",
    page_icon="🌉",
    layout="wide"
)


def main():
    st.title("🌉 管桥结构计算器")
    st.markdown("**符合 CECS 214-2006《自承式给水钢管跨越结构设计规程》**")
    
    # ========== Sidebar 输入参数 ==========
    st.sidebar.header("📝 输入参数")
    
    # 管道参数
    st.sidebar.subheader("📐 管道参数")
    
    # 管道规格 (默认DN1000)选择
    pipe_type = st.sidebar.selectbox(
        "管道规格 (默认DN1000)",
        options=list(STANDARD_PIPES.keys()),
        index=6,
        help="选择标准管道规格 (默认DN1000)"
    )
    
    # 管道壁厚 可调！
    spec = STANDARD_PIPES[pipe_type]
    default_t = spec["wall_thickness_mm"]
    wall_thickness = st.sidebar.number_input(
        "管道壁厚 t (mm)",
        min_value=1.0,
        max_value=30.0,
        value=float(default_t),
        step=0.5,
        help="管道壁厚，可根据需要调整"
    )
    
    # 跨径
    span_m = st.sidebar.number_input("跨径 L (m)", min_value=1.0, max_value=50.0, value=30.0, step=0.5)
    
    # 支承参数
    st.sidebar.subheader("支承参数")
    
    support_type = st.sidebar.selectbox(
        "支承方式",
        options=["鞍式支承", "环式支承"],
        index=1,
        help="CECS 214-2006: 鞍式支承或环式支承"
    )
    
    # 支承半角
    support_half_angle = st.sidebar.slider(
        "支承半角 θ (°)",
        min_value=60.0,
        max_value=180.0,
        value=60.0,
        step=5.0,
        help="CECS 214-2006 公式(7.2.2-2,3): 影响内水压轴向应力"
    )
    
    # 摩擦系数
    friction_coef = st.sidebar.slider(
        "摩擦系数 μ",
        min_value=0.1,
        max_value=0.6,
        value=0.3,
        step=0.05,
        help="CECS 214-2006 公式(7.2.2-5)"
    )
    
    # 焊缝折减系数 新增！
    st.sidebar.subheader("焊缝参数")
    weld_reduction = st.sidebar.slider(
        "焊缝折减系数 φ",
        min_value=0.70,
        max_value=1.0,
        value=0.9,
        step=0.05,
        help="CECS 214-2006 第7.1.1条: 焊缝折减系数"
    )
    
    # 钢材参数
    st.sidebar.subheader("钢材参数")
    steel_grade = st.sidebar.selectbox(
        "钢材牌号",
        options=["Q235", "Q345", "Q390"],
        index=0,
        help="CECS 214-2006 表3.2.1"
    )
    
    # 焊缝参数
    st.sidebar.subheader("焊缝参数")
    weld_type = st.sidebar.selectbox(
        "焊缝类型",
        options=["自动焊", "手工焊", "焊缝质量等级Ⅲ", "焊缝质量等级Ⅱ", "焊缝质量等级Ⅰ"],
        index=0,
        help="CECS 214-2006 第7.1.1条: 不同焊缝类型对应不同折减系数"
    )
    # 焊缝折减系数映射
    weld_reduction_map = {
        "自动焊": 0.9,
        "手工焊": 0.85,
        "焊缝质量等级Ⅲ": 0.85,
        "焊缝质量等级Ⅱ": 0.9,
        "焊缝质量等级Ⅰ": 0.95
    }
    weld_reduction = weld_reduction_map[weld_type]
    
    # ========== 荷载参数 ==========
    st.sidebar.subheader("📊 荷载参数")
    
    # 自重放大系数 新增！
    self_weight_amp = st.sidebar.number_input(
        "管道自重放大系数 K",
        min_value=1.0,
        max_value=2.0,
        value=1.2,
        step=0.1,
        help="CECS 214-2006 第4.2.1条: 考虑附件、保温层等"
    )
    
    # 防腐层重 新增！
    anti_corrosion = st.sidebar.number_input(
        "防腐层重 (kN/m)",
        min_value=0.0,
        max_value=5.0,
        value=0.15,
        step=0.05,
        help="防腐层重量 (kN/m)"
    )
    
    # 附加荷载 新增！
    additional_load = st.sidebar.number_input(
        "附加荷载 (kN/m)",
        min_value=0.0,
        max_value=10.0,
        value=0.5,
        step=0.1,
        help="含保温层、冰雪等 (kN/m)"
    )
    
    # 内水压力
    internal_pressure = st.sidebar.number_input(
        "设计内水压力 p (MPa)", 
        min_value=0.9, 
        max_value=2.0, 
        value=1.0, 
        step=0.1,
        help="CECS 214-2006 4.3.2: 不应小于0.9MPa"
    )
    
    # 风荷载
    wind_load = st.sidebar.number_input(
        "风荷载 (kN)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.70, 
        step=0.1,
        help="CECS 214-2006 4.3.1"
    )
    
    # 温度作用
    temperature_diff = st.sidebar.number_input(
        "闭合温差 ΔT (°C)", 
        min_value=-50.0, 
        max_value=50.0, 
        value=25.0, 
        step=5.0,
        help="CECS 214-2006 4.3.4"
    )
    
    # 温度应力折减系数
    temp_stress_reduction = st.sidebar.slider(
        "温度应力折减系数 ζ",
        min_value=0.5,
        max_value=1.0,
        value=0.70,
        step=0.05,
        help="CECS 214-2006 公式(7.2.2-4)"
    )
    
    # 施工检修荷载
    construction_load = st.sidebar.selectbox(
        "施工检修荷载系数", 
        options=[0.7, 1.0, 2.0],
        index=1,
        help="CECS 214-2006 表4.3.6: 管径≤400取0.5, 400~700取0.75, >700取1.0 (乘以管径系数)"
    )
    
    # 重要性系数
    importance_factor = st.sidebar.number_input(
        "重要性系数 γ₀",
        min_value=0.9,
        max_value=1.1,
        value=1.0,
        step=0.1,
        help="CECS 214-2006"
    )
    
    # ========== Main content ==========
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📐 荷载与内力", 
        "💪 强度计算",
        "📏 挠度验算", 
        "⚙️ 稳定计算",
        "📋 计算书"
    ])
    
    # ========== Tab 1: 荷载与应力 ==========
    with tab1:
        st.header("荷载与应力计算")
        st.markdown("**依据: CECS 214-2006**")
        
        if st.button("🚀 开始计算", type="primary"):
            # 创建模型
            pipe = create_pipe(
                pipe_type, span_m, 
                support_type=support_type, 
                friction_coefficient=friction_coef,
                support_half_angle=support_half_angle,
                weld_reduction_coefficient=weld_reduction
            )
            pipe.steel_grade = steel_grade
            pipe.wall_thickness_mm = wall_thickness
            
            load = LoadModel(
                self_weight_amplification=self_weight_amp,
                anti_corrosion_weight=anti_corrosion,
                additional_load=additional_load,
                internal_pressure_MPa=internal_pressure,
                wind_load_kN=wind_load,
                temperature_load_C=temperature_diff,
                temperature_stress_reduction=temp_stress_reduction,
                construction_load_kN=construction_load,
                importance_factor=importance_factor
            )
            
            # ========== 1. 荷载标准值计算 ==========
            st.subheader("一、荷载标准值计算")
            st.markdown("**依据: CECS 214-2006 第4章**")
            
            load_result = calculate_loads(pipe, load)
            
            # 每米荷载
            st.markdown("#### 1.1 每米荷载 (kN/m)")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("管道自重", f"{load_result.self_weight_per_m:.4f}")
                st.caption("-G=γs×A×g×K/1000\n CECS 214-2006 4.2.1\nK=自重放大系数")
            with col2:
                st.metric("防腐层重", f"{load_result.anti_corrosion_per_m:.4f}")
                st.caption("📐 CECS 214-2006 4.2")
            with col3:
                st.metric("附加荷载", f"{load_result.additional_per_m:.4f}")
                st.caption("📐 CECS 214-2006 4.2")
            with col4:
                st.metric("管内水重", f"{load_result.water_weight_per_m:.4f}")
                st.caption("W=ρw×π×d²/4×g/1000\n📐 CECS 214-2006 4.2.1")
            
            # 跨总荷载
            st.markdown("#### 1.2 跨总荷载 (kN)")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("管道自重 G", f"{load_result.self_weight_kN:.2f}")
                st.caption("G×L\n📐 按跨长换算")
            with col2:
                st.metric("防腐层重", f"{load_result.anti_corrosion_kN:.2f}")
                st.caption("-防腐重×L")
            with col3:
                st.metric("附加荷载", f"{load_result.additional_kN:.2f}")
                st.caption("-附加×L")
            with col4:
                st.metric("管内水重 W", f"{load_result.water_weight_kN:.2f}")
                st.caption("-W×L")
            
            # 荷载组合
            st.markdown("#### 1.3 荷载组合")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("工况1 (基本组合)", f"{load_result.工况1_total_kN:.2f} kN")
                st.caption("1.2×永久 + 1.4×可变 + 1.4×风×ψ\n📐 CECS 214-2006 5.2.1")
            with col2:
                st.metric("工况2 (施工检修)", f"{load_result.工况2_total_kN:.2f} kN")
                st.caption("1.2×永久 + 1.4×(内水+施工)\n📐 CECS 214-2006 5.2.2")
            
            # ========== 2. 内力计算 ==========
            st.subheader("二、内力计算")
            st.markdown("**依据: CECS 214-2006 第6章**")
            
            reaction = calculate_support_reaction(pipe, load_result.工况1_total_kN)
            shear = calculate_shear_force(pipe, load_result.工况1_total_kN)
            moment = calculate_bending_moment(pipe, load_result.工况1_total_kN)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("支座反力 R", f"{reaction/1000:.2f} kN")
                st.caption("R = qL/2\n📐 CECS 214-2006 6.1")
            with col2:
                st.metric("支座剪力 V", f"{shear/1000:.2f} kN")
                st.caption("V = R\n📐 CECS 214-2006 6.1")
            with col3:
                st.metric("跨中弯矩 M", f"{moment/1e6:.2f} kN·m")
                st.caption("M = qL²/8\n📐 CECS 214-2006 6.1")
    
    # ========== Tab 2: 强度计算 ==========
    with tab2:
        st.header("强度计算")
        st.markdown("**依据: CECS 214-2006 第7章**")
        
        if st.button("计算强度", type="primary", key="strength_btn"):
            pipe = create_pipe(
                pipe_type, span_m, 
                support_type=support_type, 
                friction_coefficient=friction_coef,
                support_half_angle=support_half_angle,
                weld_reduction_coefficient=weld_reduction
            )
            pipe.steel_grade = steel_grade
            pipe.wall_thickness_mm = wall_thickness
            
            load = LoadModel(
                self_weight_amplification=self_weight_amp,
                anti_corrosion_weight=anti_corrosion,
                additional_load=additional_load,
                internal_pressure_MPa=internal_pressure,
                wind_load_kN=wind_load,
                temperature_load_C=temperature_diff,
                temperature_stress_reduction=temp_stress_reduction,
                construction_load_kN=construction_load,
                importance_factor=importance_factor
            )
            
            # 计算荷载和内力
            load_result = calculate_loads(pipe, load)
            reaction = calculate_support_reaction(pipe, load_result.工况1_total_kN)
            
            # 计算应力
            stress_result = calculate_stress(pipe, load, reaction)
            
            # 环向应力
            st.markdown("#### 3.1 环向应力 σθ")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("内水压环向应力", f"{stress_result.sigma_theta_Fw:.2f} MPa")
                st.caption("σθ = p·r/t\n📐 CECS 214-2006 第7.2.1条")
            with col2:
                formula = stress_result.formula_refs.get('sigma_theta', {})
                st.caption(f"参数: p={internal_pressure}MPa, r={pipe.inner_radius_mm:.0f}mm, t={wall_thickness}mm")
            
            # 轴向应力
            st.markdown("#### 3.2 轴向应力 σx")
            stress_data = {
                "项目": ["弯曲应力", "内水压轴向", "温度应力", "折减后温度", "摩擦应力", "总轴向"],
                "数值(MPa)": [
                    f"{stress_result.sigma_x_M:.2f}",
                    f"{stress_result.sigma_x_Fw:.2f}",
                    f"{stress_result.sigma_x_t:.2f}",
                    f"{stress_result.sigma_x_t_reduced:.2f}",
                    f"{stress_result.sigma_x_friction:.2f}",
                    f"{stress_result.sigma_x_total:.2f}"
                ],
                "公式": [
                    "σ=M/W (7.2.2-1)",
                    "σ=p·r·(1-cosθ)/(2tπ) (7.2.2-2,3)",
                    "σ=αEΔT (7.2.2-4)",
                    "×ζ折减",
                    "σ=μR/A (7.2.2-5)",
                    "叠加"
                ]
            }
            st.table(stress_data)
            st.caption("注: θ=支承半角, ζ=温度应力折减系数, μ=摩擦系数")
            
            # 剪应力
            st.markdown("#### 3.3 剪切应力 τ")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("平均剪应力", f"{stress_result.tau_avg:.2f} MPa")
                st.caption("τ = V/A\n📐 CECS 214-2006 公式(7.2.3-1)")
            with col2:
                st.metric("最大剪应力", f"{stress_result.tau_max:.2f} MPa")
                st.caption("τmax ≈ 1.5τavg\n📐 CECS 214-2006 公式(7.2.3-2)")
            
            # 组合应力
            st.markdown("#### 3.4 组合折算应力")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("组合折算应力", f"{stress_result.combined_stress:.2f} MPa")
                st.caption("σ=√(σx²+σθ²-σx·σθ+3τ²)\n📐 CECS 214-2006 第7.1.2条")
            with col2:
                formula = stress_result.formula_refs.get('combined', {})
                st.caption(f" {formula.get('ref', '')}")
            with col3:
                allowable = stress_result.formula_refs.get('check', {}).get('allowable', 'N/A')
                st.metric("允许应力", allowable)
                st.caption("σ ≤ 0.9φf/γ₀\n📐 CECS 214-2006 公式(7.1.1)")
            
            # 强度验算结果
            st.markdown("#### 3.5 强度验算结论")
            
            check_info = stress_result.formula_refs.get('check', {})
            st.caption(f"焊缝折减系数 φ = {check_info.get('phi', '')}, 折减后设计强度 f' = {check_info.get('f_reduced', '')}")
            
            if stress_result.is_safe:
                st.success(f"✅ **强度验算通过!** 安全系数: {stress_result.safety_factor:.2f}")
            else:
                st.error(f"❌ **强度验算不通过!** 安全系数: {stress_result.safety_factor:.2f}")
    
    # ========== Tab 3: 挠度验算 ==========
    with tab3:
        st.header("挠度验算")
        st.markdown("**依据: CECS 214-2006 第9章**")
        
        if st.button("计算挠度", type="primary", key="deflection_btn"):
            pipe = create_pipe(pipe_type, span_m, support_type=support_type)
            load = LoadModel(
                internal_pressure_MPa=internal_pressure,
                wind_load_kN=wind_load,
                temperature_load_C=temperature_diff,
                construction_load_kN=construction_load
            )
            load_result = calculate_loads(pipe, load)
            
            deflection_result = calculate_deflection(pipe, load_result)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("跨中挠度 f", f"{deflection_result.deflection_mm:.2f} mm")
            with col2:
                st.metric("允许挠度 [f]", f"{deflection_result.allowable_deflection_mm:.2f} mm")
            with col3:
                st.metric("挠跨比", f"1/{int(1/deflection_result.deflection_ratio):d}")
            
            if deflection_result.is_adequate:
                st.success("✅ 挠度验算通过!")
            else:
                st.error("❌ 挠度验算不通过!")
    
    # ========== Tab 4: 稳定计算 ==========
    with tab4:
        st.header("稳定计算")
        st.markdown("**依据: CECS 214-2006 第8章**")
        
        if st.button("计算稳定", type="primary", key="stability_btn"):
            pipe = create_pipe(pipe_type, span_m)
            
            stability_result = calculate_ring_stability(pipe, internal_pressure)
            stiffener_spacing = get_stiffener_spacing(pipe, internal_pressure)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("实际内水压 p", f"{stability_result.actual_pressure:.2f} MPa")
            with col2:
                st.metric("临界压力 pcr", f"{stability_result.critical_pressure:.2f} MPa")
            with col3:
                st.metric("允许压力 [p]", f"{stability_result.allowable_pressure:.2f} MPa")
            
            st.metric("建议加劲环间距", f"{stiffener_spacing/1000:.1f} m")
            
            if stability_result.is_stable:
                st.success("✅ 稳定验算通过!")
            else:
                st.warning("⚠️ 稳定不足，建议设置加劲环")
    
    # ========== Tab 5: 计算书 ==========
    with tab5:
        st.header("计算书生成")
        st.markdown("**依据: CECS 214-2006《自承式给水钢管跨越结构设计规程》**")
        
        project_name = st.text_input("工程名称", value="自承式钢管跨越结构工程")
        
        if st.button("生成完整计算书", type="primary", key="book_btn"):
            # 创建完整模型
            pipe = create_pipe(
                pipe_type, span_m, 
                support_type=support_type, 
                friction_coefficient=friction_coef,
                support_half_angle=support_half_angle,
                weld_reduction_coefficient=weld_reduction
            )
            pipe.steel_grade = steel_grade
            pipe.wall_thickness_mm = wall_thickness
            pipe.weld_type = weld_type
            
            load = LoadModel(
                self_weight_amplification=self_weight_amp,
                anti_corrosion_weight=anti_corrosion,
                additional_load=additional_load,
                internal_pressure_MPa=internal_pressure,
                wind_load_kN=wind_load,
                temperature_load_C=temperature_diff,
                temperature_stress_reduction=temp_stress_reduction,
                construction_load_kN=construction_load,
                importance_factor=importance_factor
            )
            
            # 计算所有结果
            load_result = calculate_loads(pipe, load)
            reaction = calculate_support_reaction(pipe, load_result.工况1_total_kN)
            stress_result = calculate_stress(pipe, load, reaction)
            deflection_result = calculate_deflection(pipe, load_result)
            stability_result = calculate_ring_stability(pipe, internal_pressure)
            
            # 生成计算书
            book = generate_calculation_book(
                pipe=pipe,
                load=load,
                load_result=load_result,
                stress_result=stress_result,
                deflection_result=deflection_result,
                stability_result=stability_result,
                project_name=project_name
            )
            
            book_text = format_calculation_book(book)
            
            # 显示计算书
            st.markdown(book_text)
            
            # 下载按钮
            st.download_button(
                label="📥 下载计算书 (Markdown)",
                data=book_text,
                file_name=f"计算书_{pipe.name}_{pipe.span_m}m.md",
                mime="text/markdown"
            )


if __name__ == "__main__":
    main()
