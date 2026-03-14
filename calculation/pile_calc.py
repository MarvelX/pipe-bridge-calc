"""
桩基计算模块
"""
from pydantic import BaseModel, Field
from typing import List


class SoilLayer(BaseModel):
    """土层参数"""
    name: str = Field(description="土层名称")
    thickness_m: float = Field(gt=0, description="土层厚度(m)")
    side_resistance_kPa: float = Field(gt=0, description="侧阻力标准值(kPa)")


class PileModel(BaseModel):
    """桩基参数"""
    pile_diameter_mm: int = Field(gt=0, description="桩径(mm)")
    pile_length_m: float = Field(gt=0, description="桩长(m)")
    end_resistance_kPa: float = Field(default=0, description="端阻力标准值(kPa)")
    layers: List[SoilLayer] = Field(default_factory=list, description="土层列表")


class PileResult(BaseModel):
    """桩基计算结果"""
    total_side_resistance_kN: float = Field(description="总侧阻力(kN)")
    end_resistance_kN: float = Field(description="端阻力(kN)")
    allowable_capacity_kN: float = Field(description="单桩容许承载力(kN)")
    safety_factor: float = Field(description="安全系数")
    is_adequate: bool = Field(description="是否满足要求")


def calculate_pile_capacity(pile: PileModel, working_load_kN: float) -> PileResult:
    """
    计算桩基承载力
    """
    # 桩身周长 u = π * D
    u = 3.14159 * pile.pile_diameter_mm / 1000  # m
    
    # 总侧阻力 Qs = u * Σ(qsi * li)
    total_side = 0
    for layer in pile.layers:
        total_side += u * layer.side_resistance_kPa * layer.thickness_m
    
    # 端阻力 Qp = Ap * qp
    Ap = 3.14159 * (pile.pile_diameter_mm / 1000) ** 2 / 4  # m²
    end_resistance = Ap * pile.end_resistance_kPa * 1000  # kN
    
    # 单桩容许承载力 [Ra] = (Qs + Qp) / 2 (按规范取一半)
    allowable = (total_side + end_resistance) / 2
    
    # 安全系数
    safety = allowable / working_load_kN if working_load_kN > 0 else 999
    
    return PileResult(
        total_side_resistance_kN=round(total_side, 2),
        end_resistance_kN=round(end_resistance, 2),
        allowable_capacity_kN=round(allowable, 2),
        safety_factor=round(safety, 2),
        is_adequate=safety >= 2.0  # 一般要求安全系数≥2
    )


# 标准土层参数参考
STANDARD_SOIL_PARAMS = {
    "杂填土": {"side_kPa": 20},
    "素填土": {"side_kPa": 25},
    "浜填土": {"side_kPa": 15},
    "粉质粘土": {"side_kPa": 40},
    "粘质粉土": {"side_kPa": 35},
    "淤泥质粘土": {"side_kPa": 25},
    "淤泥质粉质粘土": {"side_kPa": 28},
    "砂质粉土": {"side_kPa": 45},
    "粉砂": {"side_kPa": 55},
    "细砂": {"side_kPa": 60},
}


def create_soil_layer(name: str, thickness: float) -> SoilLayer:
    """根据名称创建标准土层"""
    params = STANDARD_SOIL_PARAMS.get(name, STANDARD_SOIL_PARAMS["粉质粘土"])
    return SoilLayer(
        name=name,
        thickness_m=thickness,
        side_resistance_kPa=params["side_kPa"]
    )
