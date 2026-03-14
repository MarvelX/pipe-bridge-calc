"""
管桥计算器 - Streamlit UI
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


st.set_page_config(
    page_title="管桥计算器",
    page_icon="🌉",
    layout="wide"
)


def main():
    st.title("🌉 管桥结构计算器")
    st.markdown("**符合 CECS 214-2006《自承式给水钢管跨越结构设计规程》**")
    
    # ========== Sidebar - 输入参数 ==========
    st.sidebar.header("📝 输入参数")
    
    # 管道参数
    st.sidebar.subheader("📐 管道参数")
    
    # 管道规格选择
    pipe_type = st.sidebar.selectbox(
        "管道规格",
        options=list(STANDARD_PIPES.keys()),
        index=6,
        help="选择标准管道规格"
    )
    
    # 管道壁厚 - 可调！
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
        index=0
    )
    
    # 支承半角 - 新增！
    support_half_angle = st.sidebar.slider(
        "支承半角 θ (°)",
        min_value=60.0,
        max_value=180.0,
        value=120.0,
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
    
    # 焊缝折减系数 - 新增！
    st.sidebar.subheader("焊缝参数")
    weld_reduction = st.sidebar.slider(
        "焊缝折减系数 φ",
        min_value=0.7,
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
    
    # ========== 荷载参数 ==========
    st.sidebar.subheader("📊 荷载参数")
    
    # 自重放大系数 - 新增！
    self_weight_amp = st.sidebar.number_input(
        "管道自重放大系数 K",
        min_value=1.0,
        max_value=2.0,
        value=1.2,
        step=0.1,
        help="CECS 214-2006 第4.2.1条: 考虑附件、保温层等"
    )
    
    # 防腐层重 - 新增！
    anti_corrosion = st.sidebar.number_input(
        "防腐层重 (kN/m)",
        min_value=0.0,
        max_value=5.0,
        value=0.15,
        step=0.05,
        help="防腐层重量 (kN/m)"
    )
    
    # 附加荷载 - 新增！
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
        min_value=0.5, 
        max_value=2.0, 
        value=0.8, 
        step=0.1,
        help="CECS 214-2006 4.3.2: 不应小于0.9MPa"
    )
    
    # 风荷载
    wind_load = st.sidebar.number_input(
        "风荷载 (kN)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.0, 
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
    
    # 温度应力折减系数 - 新增！
    temp_stress_reduction = st.sidebar.slider(
        "温度应力折减系数 ζ",
        min_value=0.5,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="CECS 214-2006 公式(7.2.2-4)"
    )
    
    # 施工检修荷载
    construction_load = st.sidebar.number_input(
        "施工检修荷载 (kN)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.0, 
        step=5.0,
        help="CECS 214-2006 表4.3.6"
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
    tab1, tab2, tab3, tab4 = st.tabs([
        "📐 荷载与应力", 
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
                st.caption(f"K={self_weight_amp}")
            with col2:
                st.metric("防腐层重", f"{load_result.anti_corrosion_per_m:.4f}")
            with col3:
                st.metric("附加荷载", f"{load_result.additional_per_m:.4f}")
            with col4:
                st.metric("管内水重", f"{load_result.water_weight_per_m:.4f}")
            
            # 跨总荷载
            st.markdown("#### 1.2 跨总荷载 (kN)")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("管道自重 G", f"{load_result.self_weight_kN:.2f}")
            with col2:
                st.metric("防腐层重", f"{load_result.anti_corrosion_kN:.2f}")
            with col3:
                st.metric("附加荷载", f"{load_result.additional_kN:.2f}")
            with col4:
                st.metric("管内水重 W", f"{load_result.water_weight_kN:.2f}")
            
            # 组合荷载
            st.markdown("#### 1.3 荷载组合")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("组合1 (1.2G+1.4Q)", f"{load_result.combination1_total_kN:.2f} kN")
            with col2:
                st.metric("组合2 (含施工)", f"{load_result.combination2_total_kN:.2f} kN")
            
            # ========== 2. 内力计算 ==========
            st.subheader("二、内力计算")
            st.markdown("**依据: CECS 214-2006 第6章**")
            
            reaction = calculate_support_reaction(pipe, load_result.combination1_total_kN)
            shear = calculate_shear_force(pipe, load_result.combination1_total_kN)
            moment = calculate_bending_moment(pipe, load_result.combination1_total_kN)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("支座反力 R", f"{reaction/1000:.2f} kN")
            with col2:
                st.metric("支座剪力 V", f"{shear/1000:.2f} kN")
            with col3:
                st.metric("跨中弯矩 M", f"{moment/1e6:.2f} kN·m")
            
            # ========== 3. 应力计算 ==========
            st.subheader("三、应力计算")
            st.markdown("**依据: CECS 214-2006 第7.2节**")
            
            stress_result = calculate_stress(pipe, load, reaction)
            
            # 环向应力
            st.markdown("#### 3.1 环向应力 σθ")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("内水压环向应力", f"{stress_result.sigma_theta_Fw:.2f} MPa")
            with col2:
                formula = stress_result.formula_refs.get('sigma_theta', {})
                st.caption(f"公式: {formula.get('formula', '')}\n引用: {formula.get('ref', '')}")
            
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
                "公式": ["(7.2.2-1)", "(7.2.2-2,3)", "(7.2.2-4)", "×ζ", "(7.2.2-5)", "叠加"]
            }
            st.table(stress_data)
            
            # 剪应力
            st.markdown("#### 3.3 剪切应力 τ")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("平均剪应力", f"{stress_result.tau_avg:.2f} MPa")
            with col2:
                st.metric("最大剪应力", f"{stress_result.tau_max:.2f} MPa")
            
            # 组合应力
            st.markdown("#### 3.4 组合折算应力")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("组合折算应力", f"{stress_result.combined_stress:.2f} MPa")
            with col2:
                formula = stress_result.formula_refs.get('combined', {})
                st.caption(f"公式: {formula.get('formula', '')}")
            with col3:
                allowable = stress_result.formula_refs.get('check', {}).get('allowable', 'N/A')
                st.metric("允许应力", allowable)
            
            # ========== 4. 强度验算 ==========
            st.subheader("四、强度验算")
            
            check_info = stress_result.formula_refs.get('check', {})
            st.caption(f"焊缝折减系数 φ = {check_info.get('phi', '')}, 折减后设计强度 f' = {check_info.get('f_reduced', '')}")
            
            if stress_result.is_safe:
                st.success(f"✅ **强度验算通过!** 安全系数: {stress_result.safety_factor:.2f}")
            else:
                st.error(f"❌ **强度验算不通过!** 安全系数: {stress_result.safety_factor:.2f}")
    
    # ========== Tab 2: 挠度验算 ==========
    with tab2:
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
    
    # ========== Tab 3: 稳定计算 ==========
    with tab3:
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
    
    # ========== Tab 4: 计算书 ==========
    with tab4:
        st.header("计算书生成")
        st.info("📝 计算书功能开发中...")


if __name__ == "__main__":
    main()
