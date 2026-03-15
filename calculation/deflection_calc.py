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
        self.deflection_mm = 0         # 跨中挠度 mm (竖向)
        self.deflection_vertical_mm = 0  # 竖向挠度 mm
        self.deflection_horizontal_mm = 0  # 水平挠度 mm (风荷载)
        self.deflection_total_mm = 0   # 合成总挠度 mm
        self.allowable_deflection_mm = 0  # 允许挠度 mm
        self.is_adequate = False        # 是否满足要求
        self.deflection_ratio = 0      # 挠跨比
        self.formula_refs = {}          # 公式引用


def calculate_deflection(pipe: PipeModel, load_result: LoadResult) -> DeflectionResult:
    """
    计算挠度 - CECS 214-2006 第9章
    
    根据规范表9.0.1，不同支承形式的挠度计算公式及允许值
    考虑竖向荷载和水平风荷载的组合挠度
    """
    result = DeflectionResult()
    
    # 管道几何参数
    L = pipe.span_m * 1000      # 跨长 mm
    E = 206000                  # 弹性模量 MPa
    I = pipe.moment_of_inertia_mm4  # 惯性矩 mm⁴
    
    # ========== 1. 竖向挠度计算 ==========
    # 挠度计算应使用荷载标准值（不乘分项系数）
    # 注意：内水压不引起竖向挠度！只有重力场荷载才会
    # 重力场荷载 = 自重 + 防腐 + 附加 + 水重
    q_std = (
        load_result.self_weight_kN + 
        load_result.anti_corrosion_kN + 
        load_result.additional_kN + 
        load_result.water_weight_kN
    ) * 1000 / L  # N/mm
    
    # f = 5qL⁴/(384EI) (均布荷载)
    result.deflection_vertical_mm = 5 * q_std * L**4 / (384 * E * I)
    
    result.formula_refs['deflection_vertical'] = {
        'formula': 'f_y = 5qL⁴/(384EI)',
        'ref': 'CECS 214-2006 公式(9.0.1)',
        'desc': '简支梁竖向荷载作用下跨中挠度'
    }
    
    # ========== 2. 水平挠度计算 (风荷载) ==========
    # 风荷载产生的水平侧向挠度
    # 使用荷载标准值（不含分项系数）
    wind_load_kN = load_result.wind_horizontal_kN
    if wind_load_kN > 0:
        q_wind = wind_load_kN * 1000 / L  # N/mm (风荷载线荷载)
        result.deflection_horizontal_mm = 5 * q_wind * L**4 / (384 * E * I)
    else:
        result.deflection_horizontal_mm = 0
    
    result.formula_refs['deflection_horizontal'] = {
        'formula': 'f_z = 5q_wL⁴/(384EI)',
        'ref': 'CECS 214-2006 第9章',
        'desc': '简支梁水平风荷载作用下跨中挠度'
    }
    
    # ========== 3. 总挠度 (矢量合成) ==========
    # 竖向挠度与水平挠度的矢量和
    result.deflection_total_mm = math.sqrt(
        result.deflection_vertical_mm**2 + 
        result.deflection_horizontal_mm**2
    )
    result.deflection_mm = result.deflection_total_mm
    
    result.formula_refs['deflection_total'] = {
        'formula': 'f = √(f_y² + f_z²)',
        'ref': 'CECS 214-2006 第9章',
        'desc': '竖向与水平挠度矢量合成'
    }
    
    # ========== 4. 允许挠度 (规范表9.0.1) ==========
    # 管道: L/500 (根据规范表9.0.1)
    result.allowable_deflection_mm = L / 500
    
    result.formula_refs['allowable'] = {
        'formula': 'f ≤ L/500',
        'ref': 'CECS 214-2006 表9.0.1',
        'desc': '允许挠度值'
    }
    
    # ========== 5. 挠跨比 ==========
    result.deflection_ratio = result.deflection_mm / L
    
    # ========== 6. 验算 ==========
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
