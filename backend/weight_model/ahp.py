"""
AHP 层次分析法模块

实现赛题要求的 AHP 主观赋权法：
1. 构建判断矩阵（基于 Saaty 1-9 标度）
2. 计算特征向量（权重）
3. 一致性检验（CR < 0.1）
"""

import numpy as np
from typing import Dict, List, Tuple


class AHPWeightCalculator:
    """AHP 权重计算器"""

    # Saaty 1-9 标度定义
    SAATY_SCALE = {
        1: "同等重要",
        3: "稍微重要",
        5: "明显重要",
        7: "强烈重要",
        9: "极端重要",
        2: "介于 1-3 之间",
        4: "介于 3-5 之间",
        6: "介于 5-7 之间",
        8: "介于 7-9 之间"
    }

    # 技术类岗位的判断矩阵（默认）
    TECHNICAL_MATRIX = np.array([
        [1, 1/3, 1/5, 1/3, 1/2],   # 学历
        [3, 1, 1/3, 1/2, 2],       # 专业技能
        [5, 3, 1, 2, 3],           # 项目经验
        [3, 2, 1/2, 1, 2],         # 工作成果
        [2, 1/2, 1/3, 1/2, 1]      # 工作年限
    ])

    # 管理类岗位的判断矩阵
    MANAGEMENT_MATRIX = np.array([
        [1, 1/3, 1/3, 1/2, 1/2],   # 学历
        [3, 1, 1/2, 2, 2],         # 工作经历
        [3, 2, 1, 2, 3],           # 情商沟通
        [2, 1/2, 1/2, 1, 2],       # 稳定性
        [2, 1/2, 1/3, 1/2, 1]      # 管理成果
    ])

    # 行业专属判断矩阵
    INDUSTRY_MATRICES = {
        "电商": np.array([
            [1, 1/2, 1/3, 1/2, 1/3],
            [2, 1, 1/2, 1, 1/2],
            [3, 2, 1, 2, 1],
            [2, 1, 1/2, 1, 1/2],
            [3, 2, 1, 2, 1]
        ]),
        "品牌": np.array([
            [1, 1/3, 1/2, 1/2, 1/3],
            [3, 1, 2, 2, 1],
            [2, 1/2, 1, 1, 1/2],
            [2, 1/2, 1, 1, 1/2],
            [3, 1, 2, 2, 1]
        ]),
        "研发": np.array([
            [1, 1/2, 1/3, 1/3, 1/2],
            [2, 1, 1/2, 1/2, 1],
            [3, 2, 1, 1, 2],
            [3, 2, 1, 1, 2],
            [2, 1, 1/2, 1/2, 1]
        ]),
        "生产": np.array([
            [1, 1/3, 1/3, 1/2, 1/2],
            [3, 1, 1, 2, 2],
            [3, 1, 1, 2, 2],
            [2, 1/2, 1/2, 1, 1],
            [2, 1/2, 1/2, 1, 1]
        ]),
        "人力资源": np.array([
            [1, 1/2, 1/2, 1/3, 1/3],
            [2, 1, 1, 1/2, 1/2],
            [2, 1, 1, 1/2, 1/2],
            [3, 2, 2, 1, 1],
            [3, 2, 2, 1, 1]
        ]),
        "销售": np.array([
            [1, 1/3, 1/2, 1/3, 1/2],
            [3, 1, 2, 1, 2],
            [2, 1/2, 1, 1/2, 1],
            [3, 1, 2, 1, 2],
            [2, 1/2, 1, 1/2, 1]
        ])
    }

    INDICATORS = {
        "technical": ["学历", "专业技能", "项目经验", "工作成果", "工作年限"],
        "management": ["学历", "工作经历", "情商沟通", "稳定性", "管理成果"]
    }

    def __init__(self):
        self.last_weights = None
        self.last_matrix = None
        self.last_metrics = None

    def get_judgment_matrix(self, job_type: str = "technical", industry: str = None) -> np.ndarray:
        """
        获取判断矩阵

        Args:
            job_type: 岗位类型 ("technical" 或 "management")
            industry: 行业名称（可选，用于行业专属矩阵）

        Returns:
            判断矩阵
        """
        if industry and industry in self.INDUSTRY_MATRICES:
            return self.INDUSTRY_MATRICES[industry]

        if job_type == "management":
            return self.MANAGEMENT_MATRIX
        else:
            return self.TECHNICAL_MATRIX

    def get_indicators(self, job_type: str = "technical") -> List[str]:
        """
        获取指标名称列表

        Args:
            job_type: 岗位类型

        Returns:
            指标名称列表
        """
        return self.INDICATORS.get(job_type, self.INDICATORS["technical"])

    def calculate_weights(
        self,
        job_type: str = "technical",
        industry: str = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        计算 AHP 权重（主方法）

        Args:
            job_type: 岗位类型
            industry: 行业名称（可选）

        Returns:
            (权重向量, 计算过程指标字典)
        """
        matrix = self.get_judgment_matrix(job_type, industry)

        # 1. 计算特征值和特征向量
        eigenvalues, eigenvectors = np.linalg.eig(matrix)

        # 2. 找到最大特征值
        max_eigenvalue_idx = np.argmax(eigenvalues.real)
        max_eigenvalue = eigenvalues[max_eigenvalue_idx].real

        # 3. 获取对应的特征向量（权重）
        weights = eigenvectors[:, max_eigenvalue_idx].real

        # 4. 归一化权重
        weights = weights / np.sum(weights)

        # 5. 一致性检验
        n = matrix.shape[0]
        CI = (max_eigenvalue - n) / (n - 1)

        # 随机一致性指标 RI
        RI_TABLE = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}
        RI = RI_TABLE.get(n, 1.49)

        CR = CI / RI if RI > 0 else 0

        # 保存结果
        self.last_weights = weights
        self.last_matrix = matrix
        self.last_metrics = {
            "max_eigenvalue": float(max_eigenvalue),
            "CI": float(CI),
            "CR": float(CR),
            "consistency_check": "通过" if CR < 0.1 else "不通过",
            "judgment_matrix": matrix.tolist()
        }

        return weights, self.last_metrics

    def get_consistency_explanation(self) -> str:
        """获取一致性检验说明"""
        return """
        一致性检验说明：
        - CI (一致性指标) = (λ_max - n) / (n - 1)
        - CR (一致性比率) = CI / RI
        - 当 CR < 0.1 时，认为判断矩阵具有满意的一致性
        - 当 CR >= 0.1 时，需要重新调整判断矩阵
        """

    def print_weights(self, job_type: str = "technical") -> None:
        """打印权重结果"""
        weights, metrics = self.calculate_weights(job_type)
        indicators = self.get_indicators(job_type)

        print("\n" + "="*60)
        print(f"AHP 权重计算结果 ({job_type})")
        print("="*60)

        for name, weight in zip(indicators, weights):
            print(f"  {name:10s}: {weight:.4f} ({weight*100:.2f}%)")

        print(f"\n一致性检验：{metrics['consistency_check']} (CR={metrics['CR']:.4f})")
        print("="*60)
