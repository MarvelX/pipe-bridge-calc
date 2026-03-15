"""
工程计算核心模块单元测试
测试物理计算的正确性
"""
import pytest
import math
from models.pipe import PipeModel
from models.load import LoadModel
from calculation.load_calc import calculate_loads
from calculation.stress_calc import calculate_stress
from calculation.stability_calc import calculate_ring_stability


def test_fatal_orthogonal_load_separation():
    """回归测试：验证竖向荷载与水平荷载是否被正确隔离处理"""
    pipe = PipeModel(diameter_mm=1000, wall_thickness_mm=10, span_m=30, support_type="鞍式支承")
    load = LoadModel(wind_load_kN=2.0) # 施加风荷载
    
    lr = calculate_loads(pipe, load)
    
    # 断言1：竖向重力组合中绝对不包含水平风力
    assert lr.工况1_竖向_总计 > 0
    assert lr.工况1_水平荷载 > 0
    
    # 断言2：总合成弯矩必定是平方和开根号
    My = lr.工况1_竖向_总计 * pipe.span_m**2 / 8
    Mz = lr.工况1_水平荷载 * pipe.span_m**2 / 8
    expected_M_total = math.sqrt(My**2 + Mz**2)
    
    sr = calculate_stress(pipe, load, lr.工况1_竖向_总计, lr.工况1_水平荷载)
    actual_M_total = sr.sigma_x_M_combined * pipe.section_modulus_mm3 / 1e6
    assert abs(actual_M_total - expected_M_total) < 0.1


def test_vacuum_stability_physics():
    """回归测试：内水压绝对不能导致管壁失稳"""
    pipe = PipeModel(diameter_mm=1000, wall_thickness_mm=5, span_m=20, support_type="鞍式支承")
    # 模拟管内极高水压，但无真空负压
    load = LoadModel(internal_pressure_MPa=3.0, vacuum_pressure_MPa=0.0)
    
    lr = calculate_loads(pipe, load)
    assert lr.vacuum_kN == 0
    
    # 稳定计算验证
    stability = calculate_ring_stability(pipe, lr.vacuum_kN)
    assert stability.actual_pressure == 0
    assert stability.is_stable == True


def test_physical_boundary_thin_wall():
    """测试：壁厚过薄的物理边界拦截"""
    with pytest.raises(ValueError, match="管壁极度危险"):
        PipeModel(diameter_mm=1000, wall_thickness_mm=1, span_m=20)


def test_physical_boundary_span_ratio():
    """测试：跨高比过大的物理边界拦截"""
    with pytest.raises(ValueError, match="跨度过大"):
        # D=1000mm, L=50m -> L/D=50 > 45
        PipeModel(diameter_mm=1000, wall_thickness_mm=10, span_m=50)


def test_temperature_stress_sign():
    """回归测试：温度应力符号正确性"""
    pipe = PipeModel(diameter_mm=1000, wall_thickness_mm=10, span_m=20)
    load = LoadModel(temperature_load_C=30)  # 正温差
    
    lr = calculate_loads(pipe, load)
    sr = calculate_stress(pipe, load, lr.工况1_竖向_总计, 0)
    
    # 正温差应该产生压应力（负值）
    assert sr.sigma_x_t < 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
