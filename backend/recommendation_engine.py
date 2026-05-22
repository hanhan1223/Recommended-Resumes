# -*- coding: utf-8 -*-
"""
多方案推荐引擎
功能：
1. 基于不同策略生成多种录用方案
2. 平衡型、激进型、保守型推荐
3. 团队搭配建议
4. 成本效益分析
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json


class RecommendationStrategy(Enum):
    """推荐策略"""
    BALANCED = "balanced"  # 平衡型：综合考虑得分和风险
    AGGRESSIVE = "aggressive"  # 激进型：优先高分，承担一定风险
    CONSERVATIVE = "conservative"  # 保守型：优先稳定性，规避风险
    COST_EFFECTIVE = "cost_effective"  # 性价比型：考虑薪资期望和能力匹配
    TEAM_BALANCED = "team_balanced"  # 团队搭配型：考虑团队技能互补


@dataclass
class HirePlan:
    """录用方案"""
    plan_id: str
    name: str
    strategy: RecommendationStrategy
    description: str
    recommended_candidates: List[Dict]
    backup_candidates: List[Dict]  # 备选候选人
    risk_level: str  # 高/中/低
    expected_performance: float  # 预期表现得分
    team_complementarity: float  # 团队互补性得分
    cost_estimate: Optional[float]  # 预估成本
    pros: List[str]  # 优点
    cons: List[str]  # 缺点
    suitable_scenarios: List[str]  # 适用场景


@dataclass
class TeamConfig:
    """团队配置"""
    required_skills: List[str]
    skill_coverage_target: float  # 技能覆盖目标
    max_team_size: int
    min_senior_ratio: float  # 资深人员最低比例


class MultiSchemeRecommender:
    """多方案推荐引擎"""

    STRATEGY_NAMES = {
        RecommendationStrategy.BALANCED: "平衡型方案",
        RecommendationStrategy.AGGRESSIVE: "激进型方案",
        RecommendationStrategy.CONSERVATIVE: "保守型方案",
        RecommendationStrategy.COST_EFFECTIVE: "性价比型方案",
        RecommendationStrategy.TEAM_BALANCED: "团队搭配型方案"
    }

    def __init__(self):
        self.strategies = [
            RecommendationStrategy.BALANCED,
            RecommendationStrategy.AGGRESSIVE,
            RecommendationStrategy.CONSERVATIVE,
            RecommendationStrategy.COST_EFFECTIVE,
            RecommendationStrategy.TEAM_BALANCED
        ]

    def generate_hire_plans(
        self,
        candidates: List[Dict],
        job_requirements: Dict,
        team_config: Optional[TeamConfig] = None,
        budget_constraint: Optional[float] = None
    ) -> List[HirePlan]:
        """
        生成多种录用方案

        Args:
            candidates: 候选人列表
            job_requirements: 岗位要求
            team_config: 团队配置（可选）
            budget_constraint: 预算约束（可选）

        Returns:
            多种录用方案列表
        """
        plans = []

        for strategy in self.strategies:
            plan = self._generate_single_plan(
                strategy,
                candidates,
                job_requirements,
                team_config,
                budget_constraint
            )
            if plan:
                plans.append(plan)

        # 按预期表现排序
        plans.sort(key=lambda x: x.expected_performance, reverse=True)

        return plans

    def _generate_single_plan(
        self,
        strategy: RecommendationStrategy,
        candidates: List[Dict],
        job_requirements: Dict,
        team_config: Optional[TeamConfig],
        budget_constraint: Optional[float]
    ) -> Optional[HirePlan]:
        """生成单个方案"""

        # 根据策略筛选和排序候选人
        scored_candidates = self._score_candidates_by_strategy(
            candidates, strategy, job_requirements
        )

        if not scored_candidates:
            return None

        # 确定推荐人数
        hire_count = job_requirements.get("hire_count", 1)
        if team_config:
            hire_count = min(hire_count, team_config.max_team_size)

        # 选择推荐候选人（scored_candidates是元组列表，需要解包）
        recommended = [c for c, _ in scored_candidates[:hire_count]]
        backup = [c for c, _ in scored_candidates[hire_count:hire_count + 2]] if len(scored_candidates) > hire_count else []

        # 计算方案属性
        risk_level = self._calculate_plan_risk(recommended)
        expected_performance = self._calculate_expected_performance(recommended)
        team_complementarity = self._calculate_team_complementarity(recommended, team_config, job_requirements)

        # 生成优缺点
        pros, cons = self._generate_pros_cons(strategy, recommended, risk_level)

        # 适用场景
        suitable_scenarios = self._get_suitable_scenarios(strategy, risk_level)

        return HirePlan(
            plan_id=f"plan_{strategy.value}",
            name=self.STRATEGY_NAMES[strategy],
            strategy=strategy,
            description=self._generate_plan_description(strategy, recommended),
            recommended_candidates=[self._candidate_to_dict(c) for c in recommended] if recommended else [],
            backup_candidates=[self._candidate_to_dict(c) for c in backup] if backup else [],
            risk_level=risk_level,
            expected_performance=expected_performance,
            team_complementarity=team_complementarity,
            cost_estimate=budget_constraint,
            pros=pros,
            cons=cons,
            suitable_scenarios=suitable_scenarios
        )

    def _score_candidates_by_strategy(
        self,
        candidates: List[Dict],
        strategy: RecommendationStrategy,
        job_requirements: Dict
    ) -> List[Tuple[Dict, float]]:
        """根据策略给候选人打分"""
        scored = []

        required_skills = set(job_requirements.get("skills", []))

        for candidate in candidates:
            base_score = candidate.get("tci_score", 0)
            risk_factors = candidate.get("risk_factors", [])

            # 基础分调整
            if strategy == RecommendationStrategy.BALANCED:
                # 平衡型：得分 - 风险扣分
                high_risks = sum(1 for r in risk_factors if r.get("level") == "高")
                score = base_score - high_risks * 0.2

            elif strategy == RecommendationStrategy.AGGRESSIVE:
                # 激进型：优先高分，风险扣分较少
                high_risks = sum(1 for r in risk_factors if r.get("level") == "高")
                score = base_score - high_risks * 0.05

            elif strategy == RecommendationStrategy.CONSERVATIVE:
                # 保守型：大幅扣分风险
                any_high_risk = any(r.get("level") == "高" for r in risk_factors)
                if any_high_risk:
                    score = base_score * 0.7  # 高风险候选人打7折
                else:
                    score = base_score

            elif strategy == RecommendationStrategy.COST_EFFECTIVE:
                # 性价比型：考虑技能匹配度
                entities = candidate.get("entities", {})
                candidate_skills = set(entities.get("skills", []))
                if required_skills:
                    match_ratio = len(candidate_skills & required_skills) / len(required_skills)
                    score = base_score * (0.7 + 0.3 * match_ratio)  # 技能匹配度占30%
                else:
                    score = base_score

            elif strategy == RecommendationStrategy.TEAM_BALANCED:
                # 团队搭配型：考虑技能多样性
                score = base_score  # 基础分
                # 这里可以添加团队技能互补性计算

            else:
                score = base_score

            scored.append((candidate, score))

        # 按得分排序
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _calculate_plan_risk(self, candidates: List[Dict]) -> str:
        """计算方案风险等级"""
        total_high_risks = sum(
            sum(1 for r in c.get("risk_factors", []) if r.get("level") == "高")
            for c in candidates
        )

        if total_high_risks >= 3:
            return "高"
        elif total_high_risks >= 1:
            return "中"
        return "低"

    def _calculate_expected_performance(self, candidates: List[Dict]) -> float:
        """计算预期表现 - 使用推荐候选人的平均TCI得分"""
        if not candidates:
            return 0.0
        avg_score = sum(c.get("tci_score", 0) for c in candidates) / len(candidates)
        return round(avg_score, 2)

    def _calculate_team_complementarity(
        self,
        candidates: List[Dict],
        team_config: Optional[TeamConfig],
        job_requirements: Optional[Dict] = None
    ) -> float:
        """计算团队互补性"""
        if not candidates:
            return 0.0

        # 收集所有技能
        all_skills = set()
        for c in candidates:
            entities = c.get('entities', {})
            all_skills.update(entities.get('skills', []))

        # 确定所需技能
        required_skills = []
        if team_config and team_config.required_skills:
            required_skills = team_config.required_skills
        elif job_requirements and job_requirements.get('skills'):
            required_skills = job_requirements.get('skills', [])

        # 计算技能覆盖率
        if required_skills:
            coverage = len(all_skills & set(required_skills)) / len(required_skills)
            return round(min(coverage * 100, 100), 1)

        # 如果没有指定所需技能，基于候选人之间的技能互补性计算
        if len(candidates) > 1:
            # 计算技能多样性：每个候选人独特技能占总技能的比例
            total_unique_skills = set()
            candidate_skill_sets = []
            for c in candidates:
                entities = c.get('entities', {})
                skills = set(entities.get('skills', []))
                candidate_skill_sets.append(skills)
                total_unique_skills.update(skills)

            if total_unique_skills:
                # 计算技能覆盖度：如果每个候选人的技能都有独特性，互补性高
                shared_skills = set.intersection(*candidate_skill_sets) if candidate_skill_sets else set()
                unique_skills = total_unique_skills - shared_skills
                complementarity = len(unique_skills) / len(total_unique_skills)
                return round(min(complementarity * 100, 100), 1)

        return 0.0

    def _generate_pros_cons(
        self,
        strategy: RecommendationStrategy,
        candidates: List[Dict],
        risk_level: str
    ) -> Tuple[List[str], List[str]]:
        """生成优缺点"""
        pros = []
        cons = []

        avg_score = sum(c.get("tci_score", 0) for c in candidates) / len(candidates) if candidates else 0

        if strategy == RecommendationStrategy.BALANCED:
            pros.append("综合考虑得分与风险，决策稳健")
            pros.append(f"平均TCI得分{avg_score:.2f}，能力有保障")
            if risk_level == "低":
                pros.append("整体风险较低，用人放心")
            cons.append("可能错过高分但有一定风险的优秀人才")

        elif strategy == RecommendationStrategy.AGGRESSIVE:
            pros.append("优先选择高分候选人，团队实力强")
            pros.append(f"平均TCI得分{avg_score:.2f}，上限高")
            cons.append("风险等级" + risk_level + "，需要做好风险管控")
            cons.append("可能需要更多管理成本")

        elif strategy == RecommendationStrategy.CONSERVATIVE:
            pros.append("风险等级" + risk_level + "，用人安全")
            pros.append("候选人稳定性好，流失率低")
            cons.append("可能过于保守，错过优秀人才")
            cons.append(f"平均TCI得分{avg_score:.2f}，竞争力一般")

        elif strategy == RecommendationStrategy.COST_EFFECTIVE:
            pros.append("技能匹配度高，上岗即用")
            pros.append("投入产出比最优")
            cons.append("可能忽视高潜力但技能不完全匹配的候选人")

        elif strategy == RecommendationStrategy.TEAM_BALANCED:
            pros.append("团队技能互补，协作效率高")
            pros.append("技能覆盖全面，无短板")
            cons.append("单个候选人得分可能不是最高")

        return pros, cons

    def _get_suitable_scenarios(self, strategy: RecommendationStrategy, risk_level: str) -> List[str]:
        """获取适用场景"""
        scenarios = {
            RecommendationStrategy.BALANCED: [
                "常规招聘场景",
                "团队扩张期",
                "稳中求进的发展阶段"
            ],
            RecommendationStrategy.AGGRESSIVE: [
                "业务快速扩张期",
                "需要快速突破的关键岗位",
                "团队能力需要大幅提升"
            ],
            RecommendationStrategy.CONSERVATIVE: [
                "核心岗位招聘",
                "团队稳定性优先",
                "风险厌恶型组织"
            ],
            RecommendationStrategy.COST_EFFECTIVE: [
                "预算有限",
                "需要快速产出",
                "标准化岗位招聘"
            ],
            RecommendationStrategy.TEAM_BALANCED: [
                "新建团队",
                "团队技能补齐",
                "跨职能协作项目"
            ]
        }
        return scenarios.get(strategy, ["通用场景"])

    def _generate_plan_description(self, strategy: RecommendationStrategy, candidates: List[Dict]) -> str:
        """生成方案描述"""
        if not candidates:
            return "暂无推荐候选人"

        names = [c.get("basic_info", {}).get("name", "未知") for c in candidates]
        avg_score = sum(c.get("tci_score", 0) for c in candidates) / len(candidates)

        strategy_desc = {
            RecommendationStrategy.BALANCED: "平衡考虑能力与风险",
            RecommendationStrategy.AGGRESSIVE: "优先高分人才，追求卓越",
            RecommendationStrategy.CONSERVATIVE: "稳健用人，规避风险",
            RecommendationStrategy.COST_EFFECTIVE: "追求最佳投入产出比",
            RecommendationStrategy.TEAM_BALANCED: "注重团队整体协作能力"
        }

        return f"{strategy_desc.get(strategy, '')}。推荐{len(candidates)}人：{', '.join(names)}，平均得分{avg_score:.2f}。"

    def _candidate_to_dict(self, candidate: Dict) -> Dict:
        """将候选人转换为字典"""
        basic_info = candidate.get("basic_info", {})
        return {
            "candidate_id": candidate.get("candidate_id", ""),
            "name": basic_info.get("name", "未知"),
            "tci_score": candidate.get("tci_score", 0),
            "dimensional_scores": candidate.get("dimensional_scores", {}),
            "risk_count": len(candidate.get("risk_factors", [])),
            "rank": candidate.get("rank", 0),
            "entities": candidate.get("entities", {})
        }

    def generate_recommendation_summary(self, plans: List[HirePlan]) -> Dict:
        """生成推荐方案汇总"""
        return {
            "total_plans": len(plans),
            "strategies": [plan.name for plan in plans],
            "risk_distribution": {
                "high": sum(1 for p in plans if p.risk_level == "高"),
                "medium": sum(1 for p in plans if p.risk_level == "中"),
                "low": sum(1 for p in plans if p.risk_level == "低")
            },
            "top_recommendation": {
                "plan_name": plans[0].name if plans else None,
                "expected_performance": plans[0].expected_performance if plans else 0,
                "risk_level": plans[0].risk_level if plans else None
            },
            "comparison_table": [
                {
                    "方案": plan.name,
                    "策略": plan.strategy.value,
                    "风险等级": plan.risk_level,
                    "预期表现": plan.expected_performance,
                    "推荐人数": len(plan.recommended_candidates),
                    "团队互补性": plan.team_complementarity
                }
                for plan in plans
            ]
        }


# 全局推荐引擎实例
_recommender: Optional[MultiSchemeRecommender] = None


def get_recommender() -> MultiSchemeRecommender:
    """获取推荐引擎实例"""
    global _recommender
    if _recommender is None:
        _recommender = MultiSchemeRecommender()
    return _recommender
