"""
分维度评分模型

针对赛题要求的四个核心维度进行评分：
A. 教育背景评分 (Sedu)
B. 工作经历评分 (Sexp) - 权重最高部分
C. 技能与成果评分 (Sskill)
D. 综合素质与修正项 (Sadj)

支持从 weight_model 映射权重，计算 TCI 综合得分
"""

from .major_matcher import MajorMatcher
from .promotion_calculator import PromotionCalculator
from .skill_matcher import SkillMatcher
from .achievement_scorer import AchievementAndSoftSkillScorer
from .dimensional_scorer import DimensionalScorer
from .dimension_mapper import DimensionMapper
from .model import DimensionalScoringModel

__version__ = "1.0.0"

__all__ = [
    "MajorMatcher",
    "PromotionCalculator",
    "SkillMatcher",
    "AchievementAndSoftSkillScorer",
    "DimensionalScorer",
    "DimensionMapper",
    "DimensionalScoringModel"
]
