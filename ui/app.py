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


def display_formula_box(title, formula, ref, value=""):
    """显示公式框"""
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;">
        <b>{title}</b><br>
        <code style="background-color: #e0e0e0; padding: 2px 5px; border-radius: 3px;">{formula}</code><br>
        <small style="color: #666;">引用: {ref}</small>
        {f'<br><b>计算结果: {value}</b>' if value else ''}
    </div>
    """, unsafe_allow_html=True)


def main():
    st.title("🌉 管桥结构计算器")
    st.markdown("**符合 CECS 214-2006《自承式给水钢管跨越结构设计规程》**")
    
    # ========== Sidebar - 输入参数 ==========
    st.sidebar.header("📝 输入参数")
    
    # 管道参数 (扩展DN300-DN1800)
    st.sidebar.subheader("📐 管道参数")
    pipe_type = st.sidebar.selectbox(
        "管道规格",
        options=list(STANDARD_PIPES.keys()),
        index=6  # 默认DN800
    )
    span_m = st.sidebar.number_input("跨径(m)", min_value=1.0, max_value=50.0, value=24.0, step=0.5)
    
    # 支承方式 (新增)
    support_type = st.sidebar.selectbox(
        "支承方式",
        options=["鞍式支承", "环式支承"],
        index=0
    )
    
    # 摩擦系数 (新增)
    friction_coef = st.sidebar.slider(
        "摩擦系数 μ",
        min_value=0.1,
        max_value=0.6,
        value=0.3,
        step=0.05,
        help="CECS 214-2006 公式(7.2.2-5)"
    )
    
    # 钢材牌号 (新增)
    steel_grade = st.sidebar.selectbox(
        "钢材牌号",
        options=["Q235", "Q345", "Q390"],
        index=0,
        help="CECS 214-2006 表3.2.1"
    )
    
    # ========== 荷载参数 ==========
    st.sidebar.subheader("📊 荷载参数")
    
    # 内水压力 (规范4.3.2)
    internal_pressure = st.sidebar.number_input(
        "设计内水压力(MPa)", 
        min_value=0.5, 
        max_value=2.0, 
        value=0.8, 
        step=0.1,
        help="CECS 214-2006 4.3.2: 不应小于0.9MPa"
    )
    
    # 风荷载 (规范4.3.1) - 极差改为0.1
    wind_load = st.sidebar.number_input(
        "风荷载(kN)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.0, 
        step=0.1,
        help="CECS 214-2006 4.3.1: 按GB50009采用"
    )
    
    # 温度作用 (规范4.3.4)
    temperature_diff = st.sidebar.number_input(
        "闭合温差(°C)", 
        min_value=-50.0, 
        max_value=50.0, 
        value=25.0, 
        step=5.0,
        help="CECS 214-2006 4.3.4: 一般地区±25°C, 寒冷地区±30°C"
    )
    
    # 施工检修荷载 (规范4.3.6)
    construction_load = st.sidebar.number_input(
        "施工检修荷载(kN)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.0, 
        step=5.0,
        help="CECS 214-2006 表4.3.6"
    )
    
    # 重要性系数 (新增)
    importance_factor = st.sidebar.number_input(
        "重要性系数 γ₀",
        min_value=0.9,
        max_value=1.1,
        value=1.0,
        step=0.1,
        help="CECS 214-2006"
    )
    
    # ========== 桩基参数 ==========
    st.sidebar.subheader("桩基参数")
    pile_diameter = st.sidebar.number_input("桩径(mm)", min_value=400, max_value=2000, value=800, step=100)
    pile_length = st.sidebar.number_input("桩长(m)", min_value=5.0, max_value=50.0, value=25.0, step=1.0)
    pile_end_resistance = st.sidebar.number_input("桩端阻力(kPa)", min_value=0, max_value=5000, value=0, step=100)
    
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
            pipe = create_pipe(pipe_type, span_m, support_type=support_type, 
                            friction_coefficient=friction_coef)
            pipe.steel_grade = steel_grade
            
            load = LoadModel(
                internal_pressure_MPa=internal_pressure,
                wind_load_kN=wind_load,
                temperature_load_C=temperature_diff,
                construction_load_kN=construction_load,
                importance_factor=importance_factor
            )
            
            # ========== 1. 荷载标准值计算 ==========
            st.subheader("一、荷载标准值计算")
            st.markdown("**依据: CECS 214-2006 第4章**")
            
            # 1.1 永久作用
            st.markdown("#### 1.1 永久作用 (规范4.2)")
            
            # 结构自重计算
            volume_per_m = pipe.cross_section_area_mm2 / 1e6  # m³/m
            self_weight_kN_per_m = volume_per_m * load.steel_density * 9.81 / 1000
            self_weight_kN = self_weight_kN_per_m * pipe.span_m
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("结构自重 Gk", f"{self_weight_kN:.2f} kN")
            with col2:
                st.caption("""
                **公式**: G = γs × A × L × g / 1000  
                **引用**: CECS 214-2006 4.2.1  
                **参数**: γs=7850kg/m³, A={:.2f}mm², L={}m
                """.format(pipe.cross_section_area_mm2, pipe.span_m))
            
            # 管内水重
            inner_area = 3.14159 * (pipe.inner_diameter_mm ** 2) / 4 / 1e6  # m²
            water_volume = inner_area * pipe.span_m
            water_weight_kN = water_volume * load.water_density * 9.81 / 1000
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("管内水重 Wk", f"{water_weight_kN:.2f} kN")
            with col2:
                st.caption("""
                **公式**: W = ρw × π×d²/4 × L × g / 1000  
                **引用**: CECS 214-2006 4.2.1  
                **参数**: ρw=1000kg/m³, d={}mm
                """.format(pipe.inner_diameter_mm))
            
            # 1.2 可变作用
            st.markdown("#### 1.2 可变作用 (规范4.3)")
            
            # 内水压力
            internal_pressure_kN = internal_pressure * pipe.diameter_mm * pipe.span_m / 1000
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("内水压力 Fk", f"{internal_pressure_kN:.2f} kN")
            with col2:
                st.caption("""
                **公式**: F = p × D × L / 1000  
                **引用**: CECS 214-2006 4.3.2  
                **参数**: p={}MPa, D={}mm
                """.format(internal_pressure, pipe.diameter_mm))
            
            # 荷载组合
            st.markdown("#### 1.3 荷载组合 (规范第5章)")
            
            # 组合1计算
            combination1 = (
                1.2 * self_weight_kN +
                1.4 * water_weight_kN +
                1.4 * internal_pressure_kN
            )
            
            # 组合2计算
            combination2 = (
                1.2 * self_weight_kN +
                1.4 * water_weight_kN +
                1.4 * internal_pressure_kN +
                1.4 * construction_load
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("组合1 (1.2G+1.4Q)", f"{combination1:.2f} kN")
            with col2:
                st.metric("组合2 (含施工)", f"{combination2:.2f} kN")
            with col3:
                st.caption("""
                **公式**: Σ = γG×Gk + γQ×Qk  
                **引用**: CECS 214-2006 5.2.1
                """)
            
            # ========== 2. 内力计算 ==========
            st.subheader("二、内力计算")
            st.markdown("**依据: CECS 214-2006 第6章**")
            
            # 支座反力
            reaction = calculate_support_reaction(pipe, combination1)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("支座反力 R", f"{reaction/1000:.2f} kN")
            with col2:
                st.caption("""
                **公式**: R = qL/2  
                **引用**: CECS 214-2006 6.1  
                **说明**: 简支梁支座反力
                """)
            
            # 剪力
            shear_force = calculate_shear_force(pipe, combination1)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("支座剪力 V", f"{shear_force/1000:.2f} kN")
            with col2:
                st.caption("""
                **公式**: V = R  
                **引用**: CECS 214-2006 6.1  
                **说明**: 简支梁支座处剪力
                """)
            
            # 弯矩
            bending_moment = calculate_bending_moment(pipe, combination1)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("跨中弯矩 M", f"{bending_moment/1e6:.2f} kN·m")
            with col2:
                st.caption("""
                **公式**: M = qL²/8 = R×L/4  
                **引用**: CECS 214-2006 6.1  
                **说明**: 简支梁跨中最大弯矩
                """)
            
            # ========== 3. 应力计算 ==========
            st.subheader("三、应力计算")
            st.markdown("**依据: CECS 214-2006 第7.2节**")
            
            # 应力计算
            stress_result = calculate_stress(pipe, load, reaction)
            
            # 3.1 环向应力
            st.markdown("#### 3.1 环向应力 σθ (MPa)")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("内水压环向应力 σθ", f"{stress_result.sigma_theta_Fw:.2f} MPa")
            with col2:
                st.caption(f"""
                **公式**: σθ = p·r / t  
                **引用**: CECS 214-2006 公式(7.2.1)  
                **计算**: {internal_pressure}×{pipe.inner_radius_mm:.0f}/{pipe.wall_thickness_mm} = {stress_result.sigma_theta_Fw:.2f} MPa
                """)
            
            # 3.2 轴向应力
            st.markdown("#### 3.2 轴向应力 σx (MPa)")
            
            # 创建应力表格
            stress_data = {
                "项目": [
                    "弯曲应力 σx,M", 
                    "内水压轴向 σx,F", 
                    "温度应力 σx,T", 
                    "摩擦应力 σx,μ",
                    "总轴向应力 Σσx"
                ],
                "数值(MPa)": [
                    f"{stress_result.sigma_x_M:.2f}",
                    f"{stress_result.sigma_x_Fw:.2f}",
                    f"{stress_result.sigma_x_t:.2f}",
                    f"{stress_result.sigma_x_friction:.2f}",
                    f"{stress_result.sigma_x_total:.2f}"
                ],
                "公式": [
                    "σ = M/W  (7.2.2-1)",
                    "σ = p·r/(2t)  (7.2.2-2,3)",
                    "σ = αEΔT  (7.2.2-4)",
                    "σ = μR/A  (7.2.2-5)",
                    "Σ 叠加"
                ]
            }
            st.table(stress_data)
            
            # 3.3 剪应力
            st.markdown("#### 3.3 剪切应力 τ (MPa)")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("平均剪应力 τ", f"{stress_result.tau_avg:.2f} MPa")
                st.caption("""
                **公式**: τ = V/A  
                **引用**: CECS 214-2006 公式(7.2.3-1)
                """)
            with col2:
                st.metric("最大剪应力 τmax", f"{stress_result.tau_max:.2f} MPa")
                st.caption("""
                **公式**: τmax = VQ/(It)  
                **引用**: CECS 214-2006 公式(7.2.3-2)
                """)
            
            # 3.4 组合折算应力
            st.markdown("#### 3.4 组合折算应力 (MPa)")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("组合折算应力 σ", f"{stress_result.combined_stress:.2f} MPa")
            with col2:
                formula = stress_result.formula_refs.get('combined', {})
                st.caption(f"""
                **公式**: {formula.get('formula', '')}  
                **引用**: {formula.get('ref', '')}
                """)
            with col3:
                allowable = stress_result.formula_refs.get('check', {}).get('allowable', 'N/A')
                st.metric("允许应力 [σ]", allowable)
            
            # ========== 4. 强度验算 ==========
            st.subheader("四、强度验算")
            
            if stress_result.is_safe:
                st.success(f"✅ **强度验算通过!** 安全系数: {stress_result.safety_factor:.2f}")
            else:
                st.error(f"❌ **强度验算不通过!** 安全系数: {stress_result.safety_factor:.2f}")
            
            st.caption(f"""
            **验算条件**: σ ≤ 0.9f/γ₀  
            **引用**: CECS 214-2006 公式(5.2.2-1)  
            **实际**: {stress_result.combined_stress:.2f} MPa ≤ {allowable}
            """)
    
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
            
            # 挠度计算
            deflection_result = calculate_deflection(pipe, load_result)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("跨中挠度 f", f"{deflection_result.deflection_mm:.2f} mm")
                st.caption("""
                **公式**: f = 5qL⁴/(384EI)  
                **引用**: CECS 214-2006 公式(9.0.1)
                """)
            with col2:
                st.metric("允许挠度 [f]", f"{deflection_result.allowable_deflection_mm:.2f} mm")
                st.caption("""
                **公式**: f ≤ L/500  
                **引用**: CECS 214-2006 表9.0.1
                """)
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
            
            # 稳定计算
            stability_result = calculate_ring_stability(pipe, internal_pressure)
            
            # 加劲环间距
            stiffener_spacing = get_stiffener_spacing(pipe, internal_pressure)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("实际内水压 p", f"{stability_result.actual_pressure:.2f} MPa")
            with col2:
                st.metric("临界压力 pcr", f"{stability_result.critical_pressure:.2f} MPa")
                st.caption("""
                **公式**: pcr = 2.6E(t/D)²·⁵  
                **引用**: CECS 214-2006 第8.1.1条
                """)
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
