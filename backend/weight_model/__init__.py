"""
权重确定模型

整合 AHP、熵权法、组合权重、数据量化和可视化
提供统一的高层 API
"""

from .model import WeightDeterminationModel
from .ahp import AHPWeightCalculator
from .entropy import EntropyWeightCalculator
from .quantifier import ResumeQuantifier
from .combiner import WeightCombiner

__version__ = "1.0.0"

__all__ = [
    "WeightDeterminationModel",
    "AHPWeightCalculator",
    "EntropyWeightCalculator",
    "ResumeQuantifier",
    "WeightCombiner"
]
