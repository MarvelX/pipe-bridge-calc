"""
管桥计算程序
管道参数模型 - 扩展DN300-DN1800
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import math


class PipeType(str, Enum):
    DN300 = "DN300"
    DN400 = "DN400"
    DN500 = "DN500"
    DN600 = "DN600"
    DN700 = "DN700"
    DN800 = "DN800"
    DN900 = "DN900"
    DN1000 = "DN1000"
    DN1200 = "DN1200"
    DN1400 = "DN1400"
    DN1600 = "DN1600"
    DN1800 = "DN1800"


class SupportType(str, Enum):
    """支承方式"""
    SADDLE = "鞍式支承"      # 鞍式支承
    RING = "环式支承"        # 环式支承


class PipeModel(BaseModel):
    """管道参数"""
    name: str = Field(default="管道1", description="管道名称")
    diameter_mm: int = Field(ge=300, le=1800, description="管道外径(mm)")
    wall_thickness_mm: float = Field(gt=0, le=30, description="管道壁厚(mm)")
    span_m: float = Field(gt=0, description="跨径(m)")
    span_count: int = Field(default=1, ge=1, description="跨数")
    support_type: SupportType = Field(default=SupportType.SADDLE, description="支承方式")
    friction_coefficient: float = Field(default=0.3, description="摩擦系数 μ")
    
    # 支承参数 (规范7.2.2)
    support_half_angle: float = Field(
        default=120.0, 
        ge=0, 
        le=180, 
        description="支承半角 θ (°)"
    )
    
    # 焊缝参数 (规范7.1.1)
    weld_reduction_coefficient: float = Field(
        default=0.9, 
        ge=0.5, 
        le=1.0, 
        description="焊缝折减系数 φ"
    )
    weld_type: str = Field(
        default="自动焊",
        description="焊缝类型: 自动焊/手工焊/焊缝质量等级"
    )
    
    # 钢材参数
    steel_grade: str = Field(default="Q235", description="钢材牌号")
    
    @property
    def inner_radius_mm(self) -> float:
        return (self.diameter_mm - 2 * self.wall_thickness_mm) / 2
    
    @property
    def inner_diameter_mm(self) -> float:
        return self.diameter_mm - 2 * self.wall_thickness_mm
    
    @property
    def outer_radius_mm(self) -> float:
        return self.diameter_mm / 2
    
    @property
    def cross_section_area_mm2(self) -> float:
        """管道截面积 A = π(D² - d²)/4"""
        return math.pi * (self.outer_radius_mm ** 2 - self.inner_radius_mm ** 2)
    
    @property
    def moment_of_inertia_mm4(self) -> float:
        """截面惯性矩 I = π(D^4 - d^4)/64"""
        D = self.diameter_mm
        d = self.inner_diameter_mm
        return math.pi * (D**4 - d**4) / 64
    
    @property
    def section_modulus_mm3(self):
        """截面抵抗矩 W = I / (D/2)"""
        return self.moment_of_inertia_mm4 / (self.diameter_mm / 2)
    
    @property
    def radius_of_gyration_mm(self):
        """截面回转半径 i = √(I/A)"""
        return math.sqrt(self.moment_of_inertia_mm4 / self.cross_section_area_mm2)
    
    @property
    def design_strength_MPa(self) -> float:
        """钢材设计强度 f (MPa) 根据规范表3.2.1"""
        strength_map = {
            "Q235": 215,   # Q235 f=215MPa
            "Q345": 295,  # Q345 f=295MPa (规范表3.2.1-1)
            "Q390": 350,  # Q390 f=350MPa
        }
        return strength_map.get(self.steel_grade, 215)
    
    @property
    def reduced_strength_MPa(self) -> float:
        """焊缝折减后的设计强度 f' = φf (规范7.1.1)"""
        return self.weld_reduction_coefficient * self.design_strength_MPa
    
    class Config:
        use_enum_values = True


# 标准管道规格 (根据规范附录及常用规格)
STANDARD_PIPES = {
    "DN300": {"diameter_mm": 325, "wall_thickness_mm": 6},
    "DN400": {"diameter_mm": 426, "wall_thickness_mm": 7},
    "DN500": {"diameter_mm": 530, "wall_thickness_mm": 8},
    "DN600": {"diameter_mm": 630, "wall_thickness_mm": 8},
    "DN700": {"diameter_mm": 720, "wall_thickness_mm": 9},
    "DN800": {"diameter_mm": 820, "wall_thickness_mm": 10},
    "DN900": {"diameter_mm": 920, "wall_thickness_mm": 10},
    "DN1000": {"diameter_mm": 1020, "wall_thickness_mm": 10},
    "DN1200": {"diameter_mm": 1220, "wall_thickness_mm": 12},
    "DN1400": {"diameter_mm": 1420, "wall_thickness_mm": 14},
    "DN1600": {"diameter_mm": 1620, "wall_thickness_mm": 16},
    "DN1800": {"diameter_mm": 1820, "wall_thickness_mm": 18},
}


def create_pipe(pipe_type: str, span_m: float, span_count: int = 1, 
               support_type: str = "鞍式支承", friction_coefficient: float = 0.3,
               support_half_angle: float = 120.0, 
               weld_reduction_coefficient: float = 0.9) -> PipeModel:
    """创建标准管道"""
    spec = STANDARD_PIPES.get(pipe_type, STANDARD_PIPES["DN1000"])
    return PipeModel(
        name=pipe_type,
        diameter_mm=spec["diameter_mm"],
        wall_thickness_mm=spec["wall_thickness_mm"],
        span_m=span_m,
        span_count=span_count,
        support_type=SupportType(support_type) if support_type in [s.value for s in SupportType] else SupportType.SADDLE,
        friction_coefficient=friction_coefficient,
        support_half_angle=support_half_angle,
        weld_reduction_coefficient=weld_reduction_coefficient
    )
