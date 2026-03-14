"""
挠度验算模块 - CECS 214-2006 第9章
平管、折管挠度计算
"""
import math
from models.pipe import PipeModel
from models.load import LoadModel, LoadResult


class DeflectionResult:
    """挠度计算结果"""
    def __init__(self):
        self.deflection_mm = 0         # 跨中挠度 mm
        self.allowable_deflection_mm = 0  # 允许挠度 mm
        self.is_adequate = False        # 是否满足要求
        self.deflection_ratio = 0      # 挠跨比
        self.formula_refs = {}          # 公式引用


def calculate_deflection(pipe: PipeModel, load_result: LoadResult) -> DeflectionResult:
    """
    计算挠度 - CECS 214-2006 第9章
    
    根据规范表9.0.1，不同支承形式的挠度计算公式及允许值
    """
    result = DeflectionResult()
    
    # 管道几何参数
    L = pipe.span_m * 1000      # 跨长 mm
    E = 206000                  # 弹性模量 MPa
    I = pipe.moment_of_inertia_mm4  # 惯性矩 mm⁴
    
    # 挠度计算应使用荷载标准值（不乘分项系数）
    # 标准值 = 永久荷载 + 可变荷载（不乘γ）
    # 永久荷载: 自重 + 防腐 + 附加 + 水重
    # 可变荷载: 内水压 + 施工检修
    q_std = (
        load_result.self_weight_kN + 
        load_result.anti_corrosion_kN + 
        load_result.additional_kN + 
        load_result.water_weight_kN +
        load_result.internal_pressure_kN +
        load_result.construction_kN
    ) * 1000 / L  # N/mm
    
    # ========== 1. 挠度计算 (简支梁) ==========
    # f = 5qL⁴/(384EI) (均布荷载)
    result.deflection_mm = 5 * q_std * L**4 / (384 * E * I)
    
    result.formula_refs['deflection'] = {
        'formula': 'f = 5qL⁴/(384EI)',
        'ref': 'CECS 214-2006 公式(9.0.1)',
        'desc': '简支梁竖向荷载作用下跨中挠度'
    }
    
    # ========== 2. 允许挠度 (规范表9.0.1) ==========
    # 管道: L/500 (根据规范表9.0.1)
    result.allowable_deflection_mm = L / 500
    
    result.formula_refs['allowable'] = {
        'formula': 'f ≤ L/500',
        'ref': 'CECS 214-2006 表9.0.1',
        'desc': '竖向荷载作用下允许挠度值'
    }
    
    # ========== 3. 挠跨比 ==========
    result.deflection_ratio = result.deflection_mm / L
    
    # ========== 4. 验算 ==========
    result.is_adequate = result.deflection_mm <= result.allowable_deflection_mm
    
    return result


def get_allowable_deflection(span_m: float, support_type: str = "两跨连续") -> float:
    """
    获取允许挠度值 - CECS 214-2006 表9.0.1
    
    Args:
        span_m: 跨径 m
        support_type: 支承形式
    
    Returns:
        允许挠度 mm
    """
    L_mm = span_m * 1000
    
    # 根据规范表9.0.1
    allowable_ratios = {
        "两跨连续": 400,    # L/400
        "三跨连续": 500,    # L/500
        "简支": 500,       # L/500
        "悬臂": 250,        # L/250
    }
    
    ratio = allowable_ratios.get(support_type, 500)
    return L_mm / ratio
