"""
熵权法模块

实现赛题要求的熵权法客观赋权：
1. 简历数据标准化
2. 计算信息熵
3. 计算客观权重
"""

import numpy as np
from typing import Dict, List, Tuple


class EntropyWeightCalculator:
    """熵权法权重计算器"""

    def __init__(self):
        self.last_weights = None
        self.last_entropy = None
        self.last_metrics = None

    def normalize_data(self, data_matrix: np.ndarray) -> np.ndarray:
        """
        数据标准化（Min-Max 标准化）

        Args:
            data_matrix: 原始数据矩阵 (n_samples, n_features)

        Returns:
            标准化后的数据矩阵
        """
        # 避免除以零，添加极小值
        min_vals = data_matrix.min(axis=0)
        max_vals = data_matrix.max(axis=0)
        ranges = max_vals - min_vals

        # 对于常数列，ranges 为 0，需要特殊处理
        ranges[ranges == 0] = 1

        normalized = (data_matrix - min_vals) / ranges

        # 确保所有值都是正数（熵权法要求）
        normalized = normalized + 1e-10

        return normalized

    def calculate_entropy(self, data_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算信息熵

        Args:
            data_matrix: 数据矩阵

        Returns:
            (熵值数组, 信息效用值数组)
        """
        # 标准化
        normalized = self.normalize_data(data_matrix)

        # 计算概率分布
        p = normalized / normalized.sum(axis=0)

        # 计算信息熵
        # H_j = -k * sum(p_ij * ln(p_ij))
        k = 1 / np.log(data_matrix.shape[0])
        entropy = -k * np.sum(p * np.log(p), axis=0)

        # 信息效用值 = 1 - 熵值
        information_utility = 1 - entropy

        return entropy, information_utility

    def calculate_weights(self, data_matrix: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        计算熵权法权重（主方法）

        Args:
            data_matrix: 数据矩阵 (n_samples, n_features)

        Returns:
            (权重向量, 计算过程指标字典)
        """
        if data_matrix.size == 0:
            raise ValueError("数据矩阵不能为空")

        entropy, information_utility = self.calculate_entropy(data_matrix)

        # 计算权重
        weights = information_utility / information_utility.sum()

        # 保存结果
        self.last_weights = weights
        self.last_entropy = entropy
        self.last_metrics = {
            "entropy_values": entropy.tolist(),
            "information_utility": information_utility.tolist(),
            "weights": weights.tolist()
        }

        return weights, self.last_metrics

    def get_entropy_explanation(self) -> str:
        """获取熵权法说明"""
        return """
        熵权法原理：
        1. 信息熵越小，指标的变异程度越大，提供的信息量越多，权重越大
        2. 信息熵越大，指标的变异程度越小，提供的信息量越少，权重越小
        3. 完全相同的指标（熵=1），权重为0
        """
