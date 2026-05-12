"""
组合权重计算模块

将 AHP 主观权重和熵权法客观权重进行线性加权组合
W_final = α * W_AHP + (1 - α) * W_EWM
"""

import numpy as np
from typing import Dict, List, Tuple


class WeightCombiner:
    """组合权重计算器"""

    def __init__(self, alpha: float = 0.5):
        """
        初始化组合权重计算器

        Args:
            alpha: 主观权重占比系数 (0-1)
                   alpha=0.5 表示主客观权重各占 50%
                   alpha>0.5 表示更侧重主观经验
                   alpha<0.5 表示更侧重数据特征
        """
        if not 0 <= alpha <= 1:
            raise ValueError("alpha must be between 0 and 1")

        self.alpha = alpha
        self.last_combined_weights = None
        self.last_ahp_weights = None
        self.last_ewm_weights = None

    def calculate_combined_weights(
        self,
        ahp_weights: np.ndarray,
        ewm_weights: np.ndarray,
        alpha: float = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        计算组合权重

        Args:
            ahp_weights: AHP 主观权重向量
            ewm_weights: 熵权法客观权重向量
            alpha: 主观权重占比系数（可选，覆盖初始化时的值）

        Returns:
            combined_weights: 组合权重向量
            metrics: 计算过程指标字典
        """
        if alpha is not None:
            if not 0 <= alpha <= 1:
                raise ValueError("alpha must be between 0 and 1")
            self.alpha = alpha

        if len(ahp_weights) != len(ewm_weights):
            raise ValueError(
                f"Weight vector lengths mismatch: "
                f"AHP ({len(ahp_weights)}) != EWM ({len(ewm_weights)})"
            )

        combined = self.alpha * ahp_weights + (1 - self.alpha) * ewm_weights

        combined = combined / combined.sum()

        self.last_combined_weights = combined
        self.last_ahp_weights = ahp_weights.copy()
        self.last_ewm_weights = ewm_weights.copy()

        metrics = {
            "alpha": self.alpha,
            "ahp_weight_ratio": self.alpha,
            "ewm_weight_ratio": 1 - self.alpha,
            "combined_weights": combined.tolist(),
            "ahp_weights": ahp_weights.tolist(),
            "ewm_weights": ewm_weights.tolist(),
            "weight_difference": np.abs(combined - ahp_weights).tolist(),
        }

        return combined, metrics

    def analyze_weight_contribution(self, indicator_names: List[str] = None) -> Dict:
        """
        分析各指标权重来源贡献

        Args:
            indicator_names: 指标名称列表

        Returns:
            贡献分析字典
        """
        if self.last_combined_weights is None:
            raise ValueError("No combined weights calculated yet")

        n_indicators = len(self.last_combined_weights)

        if indicator_names is None:
            indicator_names = [f"指标{i+1}" for i in range(n_indicators)]

        if len(indicator_names) != n_indicators:
            raise ValueError(f"indicator_names length ({len(indicator_names)}) != n_indicators ({n_indicators})")

        analysis = []
        for i, name in enumerate(indicator_names):
            ahp_contrib = self.alpha * self.last_ahp_weights[i]
            ewm_contrib = (1 - self.alpha) * self.last_ewm_weights[i]
            total = self.last_combined_weights[i]

            analysis.append({
                "indicator": name,
                "ahp_contribution": float(ahp_contrib),
                "ewm_contribution": float(ewm_contrib),
                "combined_weight": float(total),
                "ahp_ratio": float(ahp_contrib / total) if total > 0 else 0,
                "ewm_ratio": float(ewm_contrib / total) if total > 0 else 0,
            })

        return {
            "alpha": self.alpha,
            "indicator_analysis": analysis,
            "total_ahp_contribution": float(sum(self.alpha * self.last_ahp_weights)),
            "total_ewm_contribution": float(sum((1 - self.alpha) * self.last_ewm_weights))
        }

    def sensitivity_analysis(self, ahp_weights: np.ndarray, ewm_weights: np.ndarray,
                           steps: int = 11) -> Dict:
        """
        α 参数敏感性分析

        Args:
            ahp_weights: AHP 主观权重向量
            ewm_weights: 熵权法客观权重向量
            steps: 分析步数（默认 11 步，从 0 到 1）

        Returns:
            敏感性分析结果字典
        """
        alpha_values = np.linspace(0, 1, steps)
        weight_changes = []

        for alpha in alpha_values:
            combined = alpha * ahp_weights + (1 - alpha) * ewm_weights
            combined = combined / combined.sum()
            weight_changes.append(combined)

        weight_changes = np.array(weight_changes)

        return {
            "alpha_values": alpha_values.tolist(),
            "weight_changes": weight_changes.tolist(),
            "weight_ranges": (weight_changes.max(axis=0) - weight_changes.min(axis=0)).tolist(),
            "most_sensitive_indicator": int(np.argmax(weight_changes.max(axis=0) - weight_changes.min(axis=0))),
            "least_sensitive_indicator": int(np.argmin(weight_changes.max(axis=0) - weight_changes.min(axis=0)))
        }
