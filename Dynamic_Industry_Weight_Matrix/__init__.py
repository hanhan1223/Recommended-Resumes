"""
动态行业权重矩阵模块

针对赛题要求"分领域评价人才"构建的行业专属权重矩阵模块。
"""

__version__ = "1.0.0"
__author__ = "统计课论文项目"

# 延迟导入，避免matplotlib依赖问题
def __getattr__(name):
    if name == "IndustryAHPMatrices":
        from .ahp_matrices import IndustryAHPMatrices
        return IndustryAHPMatrices
    elif name == "WeightCalculator":
        from .weight_calculator import WeightCalculator
        return WeightCalculator
    elif name == "IndustryWeightMatrix":
        from .industry_matrix import IndustryWeightMatrix
        return IndustryWeightMatrix
    elif name == "IndustryWeightVisualizer":
        from .visualizer import IndustryWeightVisualizer
        return IndustryWeightVisualizer
    elif name == "IndustryWeightExporter":
        from .exporter import IndustryWeightExporter
        return IndustryWeightExporter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "IndustryAHPMatrices",
    "WeightCalculator",
    "IndustryWeightMatrix",
    "IndustryWeightVisualizer",
    "IndustryWeightExporter"
]
