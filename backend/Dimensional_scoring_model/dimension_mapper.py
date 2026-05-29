"""
维度映射与权重聚合模块

功能：
1. 将 weight_model 的 5 个指标映射到赛题的 6 个维度
2. 从 weight_model 的组合权重聚合得到 Wedu, Wexp, Wskill, Wadj, Wpot, Wmatch
3. 计算 D-TCI 动态人才竞争力指数（含加分/惩罚项）
"""

import numpy as np
from typing import Dict, List, Tuple


class DimensionMapper:
    """维度映射器"""

    DIMENSION_MAPPING = {
        "technical": {
            "education": ["学历"],
            "experience": ["工作年限"],
            "skill_achievement": ["专业技能", "项目经验", "工作成果"],
            "comprehensive": [],
            "growth_potential": [],
            "job_matching": []
        },
        "management": {
            "education": ["学历"],
            "experience": ["工作经历", "稳定性"],
            "skill_achievement": ["管理成果"],
            "comprehensive": ["情商沟通"],
            "growth_potential": [],
            "job_matching": []
        },
        "电商": {
            "education": ["学历"],
            "experience": ["工作年限", "电商运营经验"],
            "skill_achievement": ["GMV 增长", "ROI 优化", "店铺运营成果", "专业技能"],
            "comprehensive": ["团队协作"],
            "growth_potential": [],
            "job_matching": []
        },
        "品牌": {
            "education": ["学历"],
            "experience": ["工作经历", "品牌管理经验"],
            "skill_achievement": ["品牌推广成果", "市场营销成果", "活动策划成果"],
            "comprehensive": ["沟通能力", "创意思维"],
            "growth_potential": [],
            "job_matching": []
        },
        "销售": {
            "education": ["学历"],
            "experience": ["工作年限", "销售业绩", "客户资源"],
            "skill_achievement": ["销售额增长", "回款率", "渠道拓展成果"],
            "comprehensive": ["谈判能力", "抗压能力"],
            "growth_potential": [],
            "job_matching": []
        },
        "研发": {
            "education": ["学历", "毕业院校"],
            "experience": ["工作年限", "研发经验"],
            "skill_achievement": ["专业技能", "专利论文", "技术成果", "项目经验"],
            "comprehensive": ["创新能力"],
            "growth_potential": [],
            "job_matching": []
        },
        "生产": {
            "education": ["学历"],
            "experience": ["工作年限", "生产管理经验"],
            "skill_achievement": ["生产效率提升", "良率改善", "成本控制成果", "精益生产成果"],
            "comprehensive": ["质量管理意识"],
            "growth_potential": [],
            "job_matching": []
        },
        "人力资源": {
            "education": ["学历"],
            "experience": ["工作年限", "人力资源经验"],
            "skill_achievement": ["招聘成果", "培训体系建设", "薪酬绩效优化"],
            "comprehensive": ["沟通能力", "组织协调能力"],
            "growth_potential": [],
            "job_matching": []
        }
    }

    def __init__(self):
        pass

    def map_weights(self, weight_model_results: Dict, job_type: str) -> Dict[str, float]:
        """
        将 weight_model 的 5 个指标权重映射到 6 个维度

        Args:
            weight_model_results: weight_model 的计算结果
            job_type: 岗位类型 ("technical" 或 "management")

        Returns:
            6个维度的权重大字典 {Wedu, Wexp, Wskill, Wadj, Wpot, Wmatch}
        """
        if job_type not in self.DIMENSION_MAPPING:
            job_type = "technical"

        mapping = self.DIMENSION_MAPPING[job_type]

        indicators = weight_model_results.get("indicators", [])
        combined_weights = weight_model_results.get("combined_weights", None)

        if combined_weights is None:
            return self._get_default_weights(job_type)

        if isinstance(combined_weights, np.ndarray):
            combined_weights = combined_weights.tolist()

        indicator_weights = dict(zip(indicators, combined_weights))

        dimension_weights = {}

        for dimension, source_indicators in mapping.items():
            if not source_indicators:
                dimension_weights[dimension] = 0.1
            else:
                weight_sum = sum(
                    indicator_weights.get(ind, 0.0)
                    for ind in source_indicators
                )
                dimension_weights[dimension] = weight_sum

        total = sum(dimension_weights.values())
        if total > 0:
            dimension_weights = {k: v / total for k, v in dimension_weights.items()}
        else:
            dimension_weights = self._get_default_weights(job_type)

        return dimension_weights

    def _get_default_weights(self, job_type: str) -> Dict[str, float]:
        """
        获取默认权重（当 weight_model 结果不可用时）

        Args:
            job_type: 岗位类型

        Returns:
            默认权重大字典
        """
        default_weights = {
            "technical": {
                "education": 0.12,
                "experience": 0.25,
                "skill_achievement": 0.30,
                "comprehensive": 0.15,
                "growth_potential": 0.10,
                "job_matching": 0.08
            },
            "management": {
                "education": 0.12,
                "experience": 0.28,
                "skill_achievement": 0.20,
                "comprehensive": 0.20,
                "growth_potential": 0.10,
                "job_matching": 0.10
            },
            "电商": {
                "education": 0.08,
                "experience": 0.25,
                "skill_achievement": 0.32,
                "comprehensive": 0.15,
                "growth_potential": 0.10,
                "job_matching": 0.10
            },
            "品牌": {
                "education": 0.12,
                "experience": 0.25,
                "skill_achievement": 0.28,
                "comprehensive": 0.15,
                "growth_potential": 0.10,
                "job_matching": 0.10
            },
            "销售": {
                "education": 0.08,
                "experience": 0.28,
                "skill_achievement": 0.32,
                "comprehensive": 0.12,
                "growth_potential": 0.08,
                "job_matching": 0.12
            },
            "研发": {
                "education": 0.15,
                "experience": 0.25,
                "skill_achievement": 0.32,
                "comprehensive": 0.08,
                "growth_potential": 0.12,
                "job_matching": 0.08
            },
            "生产": {
                "education": 0.12,
                "experience": 0.28,
                "skill_achievement": 0.28,
                "comprehensive": 0.12,
                "growth_potential": 0.10,
                "job_matching": 0.10
            },
            "人力资源": {
                "education": 0.12,
                "experience": 0.25,
                "skill_achievement": 0.28,
                "comprehensive": 0.15,
                "growth_potential": 0.10,
                "job_matching": 0.10
            }
        }

        return default_weights.get(job_type, default_weights["technical"])

    def map_scores(self, dimensional_scores: Dict, job_type: str) -> Dict[str, float]:
        """
        对维度得分进行标准化处理（可选）

        Args:
            dimensional_scores: 四个维度的原始得分
            job_type: 岗位类型

        Returns:
            标准化后的维度得分
        """
        normalized = {}

        for dimension, score in dimensional_scores.items():
            normalized[dimension] = min(max(score, 0), 5.0)

        return normalized

    def calculate_tci(
        self,
        dimensional_scores: Dict[str, float],
        dimension_weights: Dict[str, float],
        growth_bonus: float = 0.0,
        risk_penalty: float = 0.0,
        matching_correction: float = 0.0
    ) -> float:
        """
        计算 D-TCI 动态人才竞争力指数

        公式：D-TCI = Σ(Wi×Si) + growth_bonus + risk_penalty + matching_correction

        Args:
            dimensional_scores: 6个维度的得分
            dimension_weights: 6个维度的权重
            growth_bonus: 成长轨迹加分（来自潜力评估）
            risk_penalty: 风险惩罚项（来自风险评估，负值）
            matching_correction: 岗位匹配修正项

        Returns:
            D-TCI 综合得分（钳位到 [0, 5]）
        """
        base_tci = 0.0

        for dimension, score in dimensional_scores.items():
            weight = dimension_weights.get(dimension, 0)
            base_tci += weight * score

        d_tci = base_tci + growth_bonus + risk_penalty + matching_correction

        return max(0.0, min(5.0, d_tci))

    def get_dimension_importance_ranking(
        self,
        dimension_weights: Dict[str, float]
    ) -> List[Dict]:
        """
        获取维度重要性排序

        Args:
            dimension_weights: 维度权重大字典

        Returns:
            排序列表
        """
        dimension_names = {
            "education": "教育背景",
            "experience": "工作经历",
            "skill_achievement": "技能与成果",
            "comprehensive": "综合素质",
            "growth_potential": "成长潜力",
            "job_matching": "岗位匹配"
        }

        sorted_dims = sorted(
            dimension_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )

        ranking = []
        for rank, (dim, weight) in enumerate(sorted_dims, 1):
            ranking.append({
                "rank": rank,
                "dimension": dim,
                "dimension_name": dimension_names.get(dim, dim),
                "weight": weight,
                "percentage": f"{weight * 100:.2f}%"
            })

        return ranking

    def get_mapping_explanation(self, job_type: str) -> str:
        """
        获取维度映射说明

        Args:
            job_type: 岗位类型

        Returns:
            映射说明字符串
        """
        mapping = self.DIMENSION_MAPPING.get(job_type, self.DIMENSION_MAPPING["technical"])

        dimension_names = {
            "education": "教育背景",
            "experience": "工作经历",
            "skill_achievement": "技能与成果",
            "comprehensive": "综合素质",
            "growth_potential": "成长潜力",
            "job_matching": "岗位匹配"
        }

        explanation = f"{job_type} 岗位维度映射关系:\n"

        for dim, indicators in mapping.items():
            dim_name = dimension_names.get(dim, dim)
            if indicators:
                ind_str = " + ".join(indicators)
                explanation += f"  {dim_name} = {ind_str}\n"
            else:
                explanation += f"  {dim_name} = 额外加分项\n"

        return explanation
