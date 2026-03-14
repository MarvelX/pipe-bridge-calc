"""
荷载模型 - 符合CECS 214-2006规范
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import math


class LoadCombinationType(str, Enum):
    COMBINATION_1 = "组合1"  # 主要组合
    COMBINATION_2 = "组合2"  # 施工检修组合


class LoadModel(BaseModel):
    """荷载参数 - 符合CECS 214-2006规范"""
    
    # ========== 永久作用 ==========
    steel_density: float = Field(default=7850, description="钢材密度(kg/m³)")
    water_density: float = Field(default=1000, description="水密度(kg/m³)")
    
    # ========== 管道自重相关系数 (规范4.2) ==========
    self_weight_amplification: float = Field(
        default=1.2, 
        description="管道自重放大系数 K (考虑附件、保温层等)"
    )
    
    # ========== 可变作用 ==========
    # 内水压力 (规范4.3.2)
    internal_pressure_MPa: float = Field(
        default=0.8, 
        ge=0.5,  # 规范要求不小于0.9MPa
        description="设计内水压力(MPa)"
    )
    
    # 风荷载 (规范4.3.1)
    wind_load_kN: float = Field(default=0, description="风荷载(kN)")
    wind_pressure_kPa: float = Field(default=0.5, description="风压标准值(kPa)")
    
    # 温度作用 (规范4.3.4-4.3.5)
    temperature_load_C: float = Field(default=25, description="闭合温差(°C)")
    temperature_type: str = Field(default="焊接", description="连接方式:焊接/粘接/熔接")
    temperature_stress_reduction: float = Field(
        default=0.7, 
        description="温度应力折减系数 ζ (规范7.2.2-4)"
    )
    
    # 施工检修荷载 (规范4.3.6) - 根据管径自动计算
    # 默认值为0，用户可修改，或根据管径自动计算
    construction_load_auto: bool = Field(
        default=True, 
        description="是否根据管径自动计算施工检修荷载"
    )
    construction_load_kN: float = Field(
        default=0, 
        description="施工检修荷载(kN), 管径≤400mm取0.5, 400~700mm取0.75, >700mm取1.0"
    )
    
    # 真空压力 (规范4.3.3)
    vacuum_pressure_MPa: float = Field(default=0.05, description="真空压力(MPa)")
    
    # 真空压力 (规范4.3.3)
    vacuum_pressure_MPa: float = Field(default=0.05, description="真空压力(MPa)")
    
    # ========== 防腐与附加荷载 (规范4.2) ==========
    anti_corrosion_weight: float = Field(
        default=0.15, 
        description="防腐层重(kN/m)"
    )
    additional_load: float = Field(
        default=0.5, 
        description="附加荷载(kN/m) (含保温层、冰雪等)"
    )
    
    # ========== 分项系数 (根据规范) ==========
    gamma_self_weight: float = Field(default=1.2, description="自重分项系数 γG")
    gamma_water: float = Field(default=1.4, description="水重分项系数 γQ")
    gamma_pressure: float = Field(default=1.4, description="内水压分项系数 γQ")
    gamma_wind: float = Field(default=1.4, description="风荷载分项系数 γQ")
    gamma_temp: float = Field(default=1.4, description="温度作用分项系数 γQ")
    gamma_construction: float = Field(default=1.4, description="施工荷载分项系数 γQ")
    gamma_vacuum: float = Field(default=1.4, description="真空压力分项系数 γQ")
    
    # ========== 组合系数 (规范) ==========
    psi_wind: float = Field(default=0.6, description="风荷载组合系数 ψc")
    psi_temp: float = Field(default=0.8, description="温度作用组合系数 ψc")
    psi_construction: float = Field(default=0.5, description="施工检修组合系数 ψc")
    psi_vacuum: float = Field(default=0.7, description="真空压力准永久系数")
    
    # ========== 结构重要性系数 ==========
    importance_factor: float = Field(default=1.0, description="管道重要性系数 γ0")


class LoadResult(BaseModel):
    """荷载计算结果"""
    # 每米管道自重 (kN/m)
    self_weight_per_m: float = Field(description="每米管道自重(kN/m)")
    
    # 每米防腐层重 (kN/m)
    anti_corrosion_per_m: float = Field(description="每米防腐层重(kN/m)")
    
    # 每米附加荷载 (kN/m)
    additional_per_m: float = Field(description="每米附加荷载(kN/m)")
    
    # 每米管内水重 (kN/m)
    water_weight_per_m: float = Field(description="每米管内水重(kN/m)")
    
    # 永久荷载标准值 (跨总重)
    self_weight_kN: float = Field(description="结构自重标准值(kN)")
    water_weight_kN: float = Field(description="管内水重标准值(kN)")
    anti_corrosion_kN: float = Field(description="防腐层重标准值(kN)")
    additional_kN: float = Field(description="附加荷载标准值(kN)")
    
    # 可变荷载标准值
    internal_pressure_kN: float = Field(description="内水压力标准值(kN)")
    wind_kN: float = Field(default=0, description="风荷载标准值(kN)")
    wind_horizontal_kN: float = Field(default=0, description="水平风荷载(kN)")
    temperature_kN: float = Field(default=0, description="温度作用(kN)")
    construction_kN: float = Field(default=0, description="施工检修荷载标准值(kN)")
    vacuum_kN: float = Field(default=0, description="真空压力(kN)")
    
    # 工况1: 基本组合
    工况1_竖向永久: float = Field(default=0, description="工况1竖向永久作用(kN)")
    工况1_竖向可变: float = Field(default=0, description="工况1竖向可变作用(kN)")
    工况1_水平荷载: float = Field(default=0, description="工况1水平荷载(kN)")
    工况1_total_kN: float = Field(default=0, description="工况1总荷载(kN)")
    
    # 工况2: 施工检修组合
    工况2_竖向永久: float = Field(default=0, description="工况2竖向永久作用(kN)")
    工况2_竖向可变: float = Field(default=0, description="工况2竖向可变作用(kN)")
    工况2_水平荷载: float = Field(default=0, description="工况2水平荷载(kN)")
    工况2_total_kN: float = Field(default=0, description="工况2总荷载(kN)")
    
    # 兼容旧版本
    combination1_total_kN: float = Field(default=0, description="组合1总荷载(kN)")
    combination2_total_kN: float = Field(default=0, description="组合2总荷载(kN)")
    combination3_total_kN: float = Field(default=0, description="组合3总荷载(kN)")
