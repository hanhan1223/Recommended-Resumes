# -*- coding: utf-8 -*-
"""
决策摘要生成模块
功能：
1. 生成录用决策建议
2. 风险评估摘要
3. 决策依据整理
4. 后续行动建议
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class DecisionFactor:
    """决策因素"""
    factor_type: str  # 类型：优势/劣势/风险/机会
    description: str  # 描述
    weight: float  # 权重（影响程度）
    evidence: List[str]  # 证据/依据


@dataclass
class DecisionSummary:
    """决策摘要"""
    candidate_name: str
    decision: str  # 建议：强烈推荐/推荐/考虑/不推荐
    confidence: float  # 置信度 0-1
    overall_score: float  # 综合得分
    key_factors: List[DecisionFactor]  # 关键决策因素
    risk_summary: str  # 风险摘要
    opportunity_summary: str  # 机会摘要
    suggested_actions: List[str]  # 建议行动
    interview_focus: List[str]  # 面试重点
    final_recommendation: str  # 最终推荐意见


class DecisionSummaryGenerator:
    """决策摘要生成器"""

    DECISION_LEVELS = {
        "strongly_recommend": {"label": "强烈推荐", "min_score": 4.0, "max_risk": 1},
        "recommend": {"label": "推荐", "min_score": 3.5, "max_risk": 2},
        "consider": {"label": "可以考虑", "min_score": 3.0, "max_risk": 3},
        "not_recommend": {"label": "不推荐", "min_score": 0, "max_risk": 999}
    }

    def __init__(self):
        pass

    def generate_summary(
        self,
        candidate: Dict,
        comparison_result: Optional[Dict] = None,
        job_requirements: Optional[Dict] = None
    ) -> DecisionSummary:
        """
        生成决策摘要

        Args:
            candidate: 候选人数据
            comparison_result: 对比结果（可选）
            job_requirements: 岗位要求（可选）

        Returns:
            决策摘要
        """
        candidate_name = candidate.get("basic_info", {}).get("name", "未知")
        tci_score = candidate.get("tci_score", 0)
        risk_factors = candidate.get("risk_factors", [])

        # 分析决策因素
        key_factors = self._analyze_decision_factors(candidate, job_requirements)

        # 确定决策建议
        decision, confidence = self._determine_decision(tci_score, risk_factors)

        # 生成风险摘要
        risk_summary = self._generate_risk_summary(risk_factors)

        # 生成机会摘要
        opportunity_summary = self._generate_opportunity_summary(candidate)

        # 生成建议行动
        suggested_actions = self._generate_suggested_actions(decision, candidate)

        # 生成面试重点
        interview_focus = self._generate_interview_focus(candidate, risk_factors)

        # 生成最终推荐意见
        final_recommendation = self._generate_final_recommendation(
            candidate_name, decision, tci_score, risk_factors, key_factors
        )

        return DecisionSummary(
            candidate_name=candidate_name,
            decision=self.DECISION_LEVELS[decision]["label"],
            confidence=confidence,
            overall_score=tci_score,
            key_factors=key_factors,
            risk_summary=risk_summary,
            opportunity_summary=opportunity_summary,
            suggested_actions=suggested_actions,
            interview_focus=interview_focus,
            final_recommendation=final_recommendation
        )

    def _analyze_decision_factors(
        self,
        candidate: Dict,
        job_requirements: Optional[Dict]
    ) -> List[DecisionFactor]:
        """分析决策因素"""
        factors = []

        dimensional_scores = candidate.get("dimensional_scores", {})
        achievements = candidate.get("achievements", [])
        risk_factors = candidate.get("risk_factors", [])
        entities = candidate.get("entities", {})

        # 优势因素
        if dimensional_scores:
            max_dim = max(dimensional_scores.items(), key=lambda x: x[1])
            factors.append(DecisionFactor(
                factor_type="优势",
                description=f"{self._get_dimension_name(max_dim[0])}表现突出",
                weight=max_dim[1] / 5.0,
                evidence=[f"得分：{max_dim[1]:.2f}/5.00"]
            ))

        # 量化成就
        quantified_achievements = [
            a for a in achievements
            if isinstance(a, dict) and any(c.isdigit() for c in a.get("original_text", ""))
        ]
        if quantified_achievements:
            factors.append(DecisionFactor(
                factor_type="优势",
                description=f"有{len(quantified_achievements)}项量化成就",
                weight=0.7,
                evidence=[a.get("original_text", "")[:50] + "..." for a in quantified_achievements[:2]]
            ))

        # 技能匹配
        if job_requirements:
            required_skills = set(job_requirements.get("skills", []))
            candidate_skills = set(entities.get("skills", []))
            if required_skills:
                matched = candidate_skills & required_skills
                match_ratio = len(matched) / len(required_skills)
                factors.append(DecisionFactor(
                    factor_type="优势" if match_ratio >= 0.6 else "劣势",
                    description=f"技能匹配度{match_ratio*100:.0f}%",
                    weight=match_ratio,
                    evidence=[f"匹配技能：{', '.join(list(matched)[:5])}"]
                ))

        # 风险因素 - 使用risk_factors中的实际风险
        high_risks = [r for r in risk_factors if r.get("level") == "高"]
        medium_risks = [r for r in risk_factors if r.get("level") == "中"]

        # 添加具体的风险因素（最多2个）
        for risk in high_risks[:2]:
            factors.append(DecisionFactor(
                factor_type="风险",
                description=risk.get("description", "存在风险因素"),
                weight=0.8,
                evidence=[risk.get("type", "")]
            ))

        # 如果没有高风险但有中风险，添加中风险
        if not high_risks and medium_risks:
            for risk in medium_risks[:1]:
                factors.append(DecisionFactor(
                    factor_type="风险",
                    description=risk.get("description", "存在中等风险"),
                    weight=0.5,
                    evidence=[risk.get("type", "")]
                ))

        return factors

    def _determine_decision(
        self,
        tci_score: float,
        risk_factors: List[Dict]
    ) -> tuple:
        """确定决策建议"""
        high_risk_count = sum(1 for r in risk_factors if r.get("level") == "高")
        medium_risk_count = sum(1 for r in risk_factors if r.get("level") == "中")

        # 计算置信度
        base_confidence = 0.7
        if high_risk_count == 0:
            base_confidence += 0.2
        if tci_score >= 4.0:
            base_confidence += 0.1

        confidence = min(base_confidence, 0.95)

        # 确定决策级别
        if tci_score >= 4.0 and high_risk_count <= 1:
            return "strongly_recommend", confidence
        elif tci_score >= 3.5 and high_risk_count <= 2:
            return "recommend", confidence
        elif tci_score >= 3.0:
            return "consider", confidence
        else:
            return "not_recommend", confidence

    def _generate_risk_summary(self, risk_factors: List[Dict]) -> str:
        """生成风险摘要"""
        if not risk_factors:
            return "该候选人无明显风险因素，用人安全。"

        high_risks = [r for r in risk_factors if r.get("level") == "高"]
        medium_risks = [r for r in risk_factors if r.get("level") == "中"]

        parts = []
        if high_risks:
            parts.append(f"存在{len(high_risks)}项高风险：" + "、".join([
                r.get("type", "未知") for r in high_risks[:2]
            ]))
        if medium_risks:
            parts.append(f"{len(medium_risks)}项中风险需关注")

        if parts:
            return "；".join(parts) + "。建议面试时重点核实。"
        return "风险可控，正常录用流程。"

    def _generate_opportunity_summary(self, candidate: Dict) -> str:
        """生成机会摘要"""
        parts = []

        tci_score = candidate.get("tci_score", 0)
        if tci_score >= 4.0:
            parts.append("高分候选人，能为团队带来显著提升")
        elif tci_score >= 3.5:
            parts.append("能力良好，符合岗位要求")

        achievements = candidate.get("achievements", [])
        if len(achievements) >= 3:
            parts.append(f"有{len(achievements)}项成就记录，执行力强")

        work_duration = candidate.get("work_duration_months", 0)
        if work_duration >= 60:  # 5年以上
            parts.append("工作经验丰富，可快速上手")

        if parts:
            return "。".join(parts) + "。"
        return "符合基本录用条件。"

    def _generate_suggested_actions(
        self,
        decision: str,
        candidate: Dict
    ) -> List[str]:
        """生成建议行动"""
        actions = []

        if decision == "strongly_recommend":
            actions.extend([
                "优先安排终面，加快录用流程",
                "准备有竞争力的薪酬方案",
                "可安排与团队核心成员提前交流"
            ])
        elif decision == "recommend":
            actions.extend([
                "按正常流程安排面试",
                "重点关注风险因素核实",
                "准备标准薪酬方案"
            ])
        elif decision == "consider":
            actions.extend([
                "安排多轮面试深入考察",
                "重点验证能力短板",
                "可考虑作为备选候选人"
            ])
        else:
            actions.extend([
                "建议暂不录用",
                "如有特殊考虑，需充分论证",
                "继续寻找更合适的候选人"
            ])

        # 通用建议
        risk_factors = candidate.get("risk_factors", [])
        if any(r.get("type") == "跳槽频率" for r in risk_factors):
            actions.append("面试时重点了解跳槽原因和职业规划")

        if any(r.get("type") == "技能缺口" for r in risk_factors):
            actions.append("评估技能差距是否可通过培训弥补")

        return actions

    def _generate_interview_focus(
        self,
        candidate: Dict,
        risk_factors: List[Dict]
    ) -> List[str]:
        """生成面试重点"""
        focus = []

        # 根据风险因素确定面试重点
        risk_types = {r.get("type", "") for r in risk_factors}

        if "跳槽频率" in risk_types:
            focus.extend([
                "详细了解每次跳槽的真实原因",
                "评估对当前岗位的稳定性预期",
                "了解职业规划和长期目标"
            ])

        if "技能缺口" in risk_types:
            focus.extend([
                "深入了解技能掌握程度",
                "评估学习能力和提升意愿",
                "了解过往学习新技能的经验"
            ])

        if "空窗期" in risk_types:
            focus.extend([
                "了解空窗期的具体情况",
                "评估是否影响工作能力",
                "了解空窗期间的学习或成长"
            ])

        if "行业偏离" in risk_types:
            focus.extend([
                "了解跨行业的原因和动机",
                "评估行业转换的适应能力",
                "了解相关行业经验或知识储备"
            ])

        # 如果没有特定风险，设置通用面试重点
        if not focus:
            focus.extend([
                "深入了解核心技能的实际应用",
                "验证关键成就的真实性和贡献度",
                "评估团队协作和沟通能力",
                "了解职业期望和发展诉求"
            ])

        return focus

    def _generate_final_recommendation(
        self,
        candidate_name: str,
        decision: str,
        tci_score: float,
        risk_factors: List[Dict],
        key_factors: List[DecisionFactor]
    ) -> str:
        """生成最终推荐意见"""
        decision_label = self.DECISION_LEVELS[decision]["label"]

        parts = [
            f"【{decision_label}】{candidate_name}",
            f"综合评分：{tci_score:.2f}/5.00"
        ]

        # 添加关键因素
        advantages = [f for f in key_factors if f.factor_type == "优势"]

        if advantages:
            parts.append(f"核心优势：{advantages[0].description}")

        # 使用risk_factors生成风险描述（与_risk_summary保持一致）
        high_risks = [r for r in risk_factors if r.get("level") == "高"]
        medium_risks = [r for r in risk_factors if r.get("level") == "中"]

        if high_risks:
            # 取第一个高风险因素的描述
            risk_desc = high_risks[0].get("description", "存在高风险因素")
            parts.append(f"主要风险：{risk_desc}")
        elif medium_risks:
            risk_desc = medium_risks[0].get("description", "存在中等风险因素")
            parts.append(f"主要风险：{risk_desc}")

        # 添加录用建议
        if decision in ["strongly_recommend", "recommend"]:
            parts.append("建议：尽快推进录用流程")
        elif decision == "consider":
            parts.append("建议：进一步考察后再决定")
        else:
            parts.append("建议：暂不录用，继续寻找")

        return " | ".join(parts)

    def generate_summary_report(self, summary: DecisionSummary) -> Dict:
        """生成决策摘要报告"""
        return {
            "candidate_name": summary.candidate_name,
            "generated_at": datetime.now().isoformat(),
            "decision": summary.decision,
            "confidence": f"{summary.confidence*100:.0f}%",
            "overall_score": f"{summary.overall_score:.2f}/5.00",
            "executive_summary": {
                "risk_summary": summary.risk_summary,
                "opportunity_summary": summary.opportunity_summary,
                "final_recommendation": summary.final_recommendation
            },
            "key_factors": [
                {
                    "type": f.factor_type,
                    "description": f.description,
                    "weight": f"{f.weight*100:.0f}%",
                    "evidence": f.evidence
                }
                for f in summary.key_factors
            ],
            "action_items": {
                "suggested_actions": summary.suggested_actions,
                "interview_focus": summary.interview_focus
            }
        }

    def _get_dimension_name(self, dim_key: str) -> str:
        """获取维度名称"""
        names = {
            "education": "教育背景",
            "experience": "工作经历",
            "skill_achievement": "技能成果",
            "comprehensive": "综合素质"
        }
        return names.get(dim_key, dim_key)


# 全局生成器实例
_generator: Optional[DecisionSummaryGenerator] = None


def get_generator() -> DecisionSummaryGenerator:
    """获取决策摘要生成器实例"""
    global _generator
    if _generator is None:
        _generator = DecisionSummaryGenerator()
    return _generator
