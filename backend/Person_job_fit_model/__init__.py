"""
人岗匹配模型包
包含以下子模块：
- 岗位画像抽取 (job_profile_extractor)
- 人岗匹配评分 (job_matching_scorer)
- 风险识别 (risk_identifier)
- 潜力评估 (potential_evaluator)
- 可视化 (fit_visualizer)
"""

from .job_profile_extractor import JobProfileExtractor
from .job_matching_scorer import JobMatchingScorer
from .risk_identifier import RiskIdentifier
from .potential_evaluator import PotentialEvaluator
from .fit_visualizer import FitVisualizer
from .model import PersonJobFitModel

__all__ = [
    'JobProfileExtractor',
    'JobMatchingScorer',
    'RiskIdentifier',
    'PotentialEvaluator',
    'FitVisualizer',
    'PersonJobFitModel'
]

__version__ = '1.0.0'
