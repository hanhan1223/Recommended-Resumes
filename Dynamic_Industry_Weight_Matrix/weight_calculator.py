"""
权重计算器

实现 AHP+ 熵权法的组合权重计算
采用方案 A：全局熵权 + 行业系数调整
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from .ahp_matrices import IndustryAHPMatrices


class WeightCalculator:
    """
    权重计算器
    
    功能：
    1. AHP 主观权重计算
    2. 熵权法客观权重计算
    3. 组合权重计算
    4. 行业系数调整
    """
    
    # 行业系数配置（用于全局熵权的行业调整）
    # 系数 > 1 表示该指标在该行业中更重要
    INDUSTRY_COEFFICIENTS = {
        "研发": {
            "technical": {"学历": 1.0, "专业技能": 1.3, "项目经验": 1.2, "工作成果": 1.1, "工作年限": 0.9},
            "management": {"学历": 1.0, "工作经历": 1.1, "情商沟通": 1.0, "稳定性": 0.9, "管理成果": 1.3}
        },
        "电商": {
            "technical": {"学历": 0.9, "专业技能": 1.2, "项目经验": 1.0, "工作成果": 1.1, "工作年限": 1.2},
            "management": {"学历": 0.9, "工作经历": 1.3, "情商沟通": 1.1, "稳定性": 0.8, "管理成果": 1.2}
        },
        "人力资源": {
            "technical": {"学历": 1.0, "专业技能": 1.0, "项目经验": 0.9, "工作成果": 1.0, "工作年限": 1.2},
            "management": {"学历": 0.9, "工作经历": 1.2, "情商沟通": 1.4, "稳定性": 1.0, "管理成果": 1.0}
        },
        "品牌市场": {
            "technical": {"学历": 1.0, "专业技能": 1.1, "项目经验": 1.0, "工作成果": 1.2, "工作年限": 1.0},
            "management": {"学历": 0.9, "工作经历": 1.1, "情商沟通": 1.2, "稳定性": 0.9, "管理成果": 1.4}
        },
        "生产": {
            "technical": {"学历": 0.9, "专业技能": 1.2, "项目经验": 1.0, "工作成果": 1.3, "工作年限": 1.1},
            "management": {"学历": 0.9, "工作经历": 1.1, "情商沟通": 1.0, "稳定性": 1.2, "管理成果": 1.3}
        },
        "销售": {
            "technical": {"学历": 0.8, "专业技能": 1.1, "项目经验": 0.9, "工作成果": 1.2, "工作年限": 1.3},
            "management": {"学历": 0.8, "工作经历": 1.3, "情商沟通": 1.3, "稳定性": 1.0, "管理成果": 1.2}
        }
    }
    
    def __init__(self, alpha: float = 0.5):
        """
        初始化权重计算器
        
        Args:
            alpha: AHP 权重占比系数 (0-1)，默认 0.5
                   alpha > 0.5: 更侧重主观经验
                   alpha < 0.5: 更侧重数据特征
        """
        self.alpha = alpha
        self.ahp_matrices = IndustryAHPMatrices()
    
    def calculate_ahp_weights(self, industry: str, job_type: str) -> Tuple[np.ndarray, Dict]:
        """
        计算 AHP 主观权重
        
        Args:
            industry: 行业名称
            job_type: 岗位类型
            
        Returns:
            weights: AHP 权重向量
            metrics: 评估指标字典
        """
        matrix = self.ahp_matrices.get_matrix(industry, job_type)
        indicators = self.ahp_matrices.get_indicators(job_type)
        
        # 计算最大特征值和特征向量
        eigenvalues, eigenvectors = np.linalg.eig(matrix)
        max_idx = np.argmax(eigenvalues.real)
        max_eigenvalue = eigenvalues[max_idx].real
        max_eigenvector = eigenvectors[:, max_idx].real
        
        # 归一化得到权重
        weights = max_eigenvector / np.sum(max_eigenvector)
        
        # 一致性检验
        n = matrix.shape[0]
        CI = (max_eigenvalue - n) / (n - 1)
        RI_table = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}
        RI = RI_table.get(n, 1.45)
        CR = CI / RI if RI > 0 else 0
        
        metrics = {
            "max_eigenvalue": float(max_eigenvalue),
            "CI": float(CI),
            "CR": float(CR),
            "consistency_check": "通过" if CR < 0.1 else "未通过",
            "indicators": indicators,
            "judgment_matrix": matrix.tolist()
        }
        
        return weights, metrics
    
    def calculate_entropy_weights(self, data_matrix: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        计算熵权法客观权重
        
        Args:
            data_matrix: 数据矩阵 (n_samples × n_indicators)
            
        Returns:
            weights: 熵权法权重向量
            metrics: 评估指标字典
        """
        n_samples, n_indicators = data_matrix.shape
        
        # 数据标准化（极差法）
        min_vals = np.min(data_matrix, axis=0)
        max_vals = np.max(data_matrix, axis=0)
        range_vals = max_vals - min_vals
        
        # 避免除零
        range_vals[range_vals == 0] = 1
        
        normalized = (data_matrix - min_vals) / range_vals
        
        # 加一个小常数避免 log(0)
        normalized = normalized + 1e-6
        
        # 计算比重
        proportions = normalized / np.sum(normalized, axis=0)
        
        # 计算熵值
        e = -np.sum(proportions * np.log(proportions), axis=0) / np.log(n_samples)
        
        # 计算信息效用值
        d = 1 - e
        
        # 归一化得到权重
        weights = d / np.sum(d)
        
        metrics = {
            "entropy_values": e.tolist(),
            "information_utility": d.tolist(),
            "n_samples": n_samples,
            "n_indicators": n_indicators
        }
        
        return weights, metrics
    
    def calculate_combined_weights(
        self, 
        ahp_weights: np.ndarray, 
        ewm_weights: np.ndarray,
        alpha: Optional[float] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        计算组合权重（AHP + 熵权法）
        
        公式：W_final = α × W_AHP + (1 - α) × W_EWM
        
        Args:
            ahp_weights: AHP 权重向量
            ewm_weights: 熵权法权重向量
            alpha: AHP 权重占比系数（可选，默认使用初始化时的值）
            
        Returns:
            combined_weights: 组合权重向量
            metrics: 评估指标字典
        """
        if alpha is None:
            alpha = self.alpha
        
        # 线性组合
        combined_weights = alpha * ahp_weights + (1 - alpha) * ewm_weights
        
        # 归一化
        combined_weights = combined_weights / np.sum(combined_weights)
        
        metrics = {
            "alpha": alpha,
            "ahp_contribution": alpha,
            "ewm_contribution": 1 - alpha
        }
        
        return combined_weights, metrics
    
    def apply_industry_coefficients(
        self, 
        global_ewm_weights: np.ndarray,
        industry: str,
        job_type: str,
        indicators: List[str]
    ) -> np.ndarray:
        """
        应用行业系数调整全局熵权
        
        方案 A 的核心实现
        
        Args:
            global_ewm_weights: 全局熵权权重向量（使用全部简历计算）
            industry: 行业名称
            job_type: 岗位类型
            indicators: 指标列表
            
        Returns:
            adjusted_weights: 调整后的权重向量
        """
        if industry not in self.INDUSTRY_COEFFICIENTS:
            return global_ewm_weights
        
        coefficients_dict = self.INDUSTRY_COEFFICIENTS[industry].get(job_type, {})
        
        if not coefficients_dict:
            return global_ewm_weights
        
        # 构建系数向量
        coefficients = np.array([
            coefficients_dict.get(ind, 1.0) 
            for ind in indicators
        ])
        
        # 应用系数调整
        adjusted_weights = global_ewm_weights * coefficients
        
        # 归一化
        adjusted_weights = adjusted_weights / np.sum(adjusted_weights)
        
        return adjusted_weights
    
    def calculate_industry_weights(
        self,
        industry: str,
        job_type: str,
        all_resumes_data: np.ndarray,
        industry_resumes_data: Optional[np.ndarray] = None,
        min_industry_samples: int = 8
    ) -> Dict:
        """
        计算行业专属权重（混合策略）
        
        Args:
            industry: 行业名称
            job_type: 岗位类型
            all_resumes_data: 全部简历数据矩阵
            industry_resumes_data: 该行业简历数据矩阵（可选）
            min_industry_samples: 行业专属熵权的最小样本数阈值
            
        Returns:
            权重计算结果字典
        """
        indicators = self.ahp_matrices.get_indicators(job_type)
        
        # 1. 计算 AHP 权重
        ahp_weights, ahp_metrics = self.calculate_ahp_weights(industry, job_type)
        
        # 2. 计算全局熵权
        global_ewm_weights, global_ewm_metrics = self.calculate_entropy_weights(all_resumes_data)
        
        # 3. 混合策略计算最终熵权
        if industry_resumes_data is not None and len(industry_resumes_data) >= min_industry_samples:
            # 行业数据充足：计算行业专属熵权并与全局熵权融合
            industry_ewm_weights, industry_ewm_metrics = self.calculate_entropy_weights(industry_resumes_data)
            
            # 融合权重：行业熵权占比 = min(行业简历数/总简历数，0.7)
            fusion_weight = min(len(industry_resumes_data) / len(all_resumes_data), 0.7)
            ewm_weights = (1 - fusion_weight) * global_ewm_weights + fusion_weight * industry_ewm_weights
            
            strategy = "industry_entropy_fusion"
        else:
            # 行业数据不足：使用全局熵权 + 行业系数调整
            ewm_weights = self.apply_industry_coefficients(
                global_ewm_weights, 
                industry, 
                job_type, 
                indicators
            )
            strategy = "global_entropy_with_coefficients"
        
        # 4. 计算组合权重
        combined_weights, combined_metrics = self.calculate_combined_weights(
            ahp_weights, 
            ewm_weights,
            self.alpha
        )
        
        return {
            "industry": industry,
            "job_type": job_type,
            "indicators": indicators,
            "ahp_weights": ahp_weights.tolist(),
            "ahp_metrics": ahp_metrics,
            "ewm_weights": ewm_weights.tolist(),
            "combined_weights": combined_weights.tolist(),
            "combined_metrics": combined_metrics,
            "strategy": strategy,
            "alpha": self.alpha
        }
    
    def get_ranking(self, weights: np.ndarray, indicators: List[str]) -> List[Dict]:
        """
        获取指标重要性排序
        
        Args:
            weights: 权重向量
            indicators: 指标列表
            
        Returns:
            排序列表
        """
        sorted_indices = np.argsort(weights)[::-1]
        
        ranking = []
        for rank, idx in enumerate(sorted_indices, 1):
            ranking.append({
                "rank": rank,
                "indicator": indicators[idx],
                "weight": float(weights[idx]),
                "percentage": f"{weights[idx]*100:.2f}%"
            })
        
        return ranking
