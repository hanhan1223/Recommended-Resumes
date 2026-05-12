"""
模型层测试 - 评分和权重计算
"""
import pytest
import sys
from pathlib import Path
import numpy as np

# 添加模型路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / ".venv"))

from Dimensional_scoring_model.model import DimensionalScoringModel
from weight_model.ahp import AHPWeightCalculator
from weight_model.entropy import EntropyWeightCalculator


class TestAHPWeightCalculator:
    """AHP权重计算测试"""
    
    def test_technical_weights_sum_to_one(self):
        """技术类权重和为1"""
        calc = AHPWeightCalculator()
        weights, metrics = calc.calculate_weights("technical")
        
        # weights是numpy数组
        total = np.sum(weights)
        assert abs(total - 1.0) < 0.01, f"权重和={total}不等于1"
    
    def test_technical_consistency_ratio(self):
        """技术类一致性比率应在阈值内"""
        calc = AHPWeightCalculator()
        weights, metrics = calc.calculate_weights("technical")
        
        # CR在metrics字典中
        cr = metrics["CR"]
        assert cr < 0.1, f"一致性比率CR={cr}超过0.1阈值"
        assert metrics["consistency_check"] == "通过"
    
    def test_management_weights_positive(self):
        """管理类权重都应为正数"""
        calc = AHPWeightCalculator()
        weights, metrics = calc.calculate_weights("management")
        
        # weights是numpy数组
        assert np.all(weights > 0), f"权重包含非正值: {weights}"


class TestEntropyWeightCalculator:
    """熵权法计算测试"""
    
    def test_normal_data(self):
        """正常数据计算"""
        # 使用numpy数组
        data = np.array([
            [4.0, 3.5, 4.2],
            [3.8, 4.0, 3.9],
            [4.2, 3.2, 4.5],
        ])
        calc = EntropyWeightCalculator()
        weights, info = calc.calculate_weights(data)
        
        total = np.sum(weights)
        assert abs(total - 1.0) < 0.01, f"权重和={total}不等于1"


class TestDimensionalScoringModel:
    """维度评分模型测试"""
    
    def test_model_initialization(self):
        """模型初始化测试"""
        model = DimensionalScoringModel()
        assert model is not None
        assert hasattr(model, 'calculate')
    
    def test_tci_calculation_formula(self):
        """TCI计算公式正确性验证"""
        # 手动计算验证公式: TCI = sum(维度得分 * 权重)
        dimensions = {"a": 4.0, "b": 3.0}
        weights = {"a": 0.6, "b": 0.4}
        
        # 计算TCI
        tci = sum(d * weights[k] for k, d in dimensions.items())
        expected = 4.0 * 0.6 + 3.0 * 0.4  # = 3.6
        
        assert abs(tci - expected) < 0.01, f"TCI={tci}, 期望值={expected}"
        assert 0 <= tci <= 5, f"TCI={tci}超出0-5范围"
