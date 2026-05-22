# -*- coding: utf-8 -*-
"""
候选人对比分析模块
功能：
1. 多候选人横向对比
2. 维度得分对比
3. 优势劣势分析
4. 推荐排序
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json


class ComparisonDimension(Enum):
    """对比维度"""
    OVERALL = "overall"  # 综合评分
    EDUCATION = "education"  # 教育背景
    EXPERIENCE = "experience"  # 工作经历
    SKILL = "skill"  # 技能成果
    COMPREHENSIVE = "comprehensive"  # 综合素质
    STABILITY = "stability"  # 稳定性
    POTENTIAL = "potential"  # 发展潜力


@dataclass
class CandidateComparisonItem:
    """候选人对比项"""
    candidate_id: str
    name: str
    tci_score: float
    dimensional_scores: Dict[str, float]
    dimension_weights: Dict[str, float]
    risk_factors: List[Dict]
    achievements: List[str]
    work_experiences: List[Dict]
    education_experiences: List[Dict]
    skills: List[str]
    rank: int


@dataclass
class ComparisonResult:
    """对比结果"""
    candidates: List[CandidateComparisonItem]
    dimension_comparison: Dict[str, List[Tuple[str, float]]]  # 各维度排名
    advantage_matrix: Dict[str, Dict[str, List[str]]]  # 优势矩阵
    gap_analysis: Dict[str, Dict[str, float]]  # 差距分析
    recommendation_order: List[str]  # 推荐顺序
    summary: str  # 对比总结


class CandidateComparator:
    """候选人对比分析器"""

    # 维度名称映射
    DIMENSION_NAMES = {
        "education": "教育背景",
        "experience": "工作经历",
        "skill_achievement": "技能成果",
        "comprehensive": "综合素质",
        "stability": "稳定性",
        "potential": "发展潜力"
    }

    def __init__(self):
        self.dimension_weights = {
            "education": 0.15,
            "experience": 0.30,
            "skill_achievement": 0.40,
            "comprehensive": 0.15
        }

    def compare_candidates(
        self,
        candidates: List[Dict],
        job_requirements: Optional[Dict] = None
    ) -> ComparisonResult:
        """
        对比多个候选人

        Args:
            candidates: 候选人数据列表
            job_requirements: 岗位要求（可选）

        Returns:
            对比结果
        """
        # 构建对比项
        comparison_items = self._build_comparison_items(candidates)

        # 各维度对比
        dimension_comparison = self._compare_dimensions(comparison_items)

        # 优势分析
        advantage_matrix = self._analyze_advantages(comparison_items)

        # 差距分析
        gap_analysis = self._analyze_gaps(comparison_items)

        # 生成推荐排序
        recommendation_order = self._generate_recommendation(comparison_items, job_requirements)

        # 生成总结
        summary = self._generate_summary(comparison_items, recommendation_order)

        return ComparisonResult(
            candidates=comparison_items,
            dimension_comparison=dimension_comparison,
            advantage_matrix=advantage_matrix,
            gap_analysis=gap_analysis,
            recommendation_order=recommendation_order,
            summary=summary
        )

    def _build_comparison_items(self, candidates: List[Dict]) -> List[CandidateComparisonItem]:
        """构建候选人对比项列表"""
        items = []
        for i, candidate in enumerate(candidates):
            basic_info = candidate.get("basic_info", {})
            entities = candidate.get("entities", {})
            
            # 处理成就数据，保持原始格式以便后续处理
            raw_achievements = candidate.get("achievements", [])
            processed_achievements = []
            for a in raw_achievements:
                if isinstance(a, dict):
                    processed_achievements.append(a)
                elif isinstance(a, str):
                    processed_achievements.append({"original_text": a})
            
            # 按TCI分数排序，重新计算排名
            sorted_candidates = sorted(candidates, key=lambda x: x.get('tci_score', 0), reverse=True)
            rank = next((idx + 1 for idx, c in enumerate(sorted_candidates) 
                        if c.get('basic_info', {}).get('name') == basic_info.get('name')), i + 1)

            item = CandidateComparisonItem(
                candidate_id=candidate.get("candidate_id", ""),
                name=basic_info.get("name", "未知"),
                tci_score=candidate.get("tci_score", 0),
                dimensional_scores=candidate.get("dimensional_scores", {}),
                dimension_weights=candidate.get("dimension_weights", self.dimension_weights),
                risk_factors=candidate.get("risk_factors", []),
                achievements=processed_achievements,
                work_experiences=candidate.get("work_experiences", []),
                education_experiences=candidate.get("education_experiences", []),
                skills=entities.get("skills", []),
                rank=rank
            )
            items.append(item)
        return items

    def _compare_dimensions(
        self,
        items: List[CandidateComparisonItem]
    ) -> Dict[str, List[Tuple[str, float]]]:
        """对比各维度得分"""
        dimension_comparison = {}

        # 综合评分对比
        dimension_comparison["overall"] = sorted(
            [(item.name, item.tci_score) for item in items],
            key=lambda x: x[1],
            reverse=True
        )

        # 各维度对比
        dimensions = ["education", "experience", "skill_achievement", "comprehensive"]
        for dim in dimensions:
            dimension_comparison[dim] = sorted(
                [(item.name, item.dimensional_scores.get(dim, 0)) for item in items],
                key=lambda x: x[1],
                reverse=True
            )

        return dimension_comparison

    def _analyze_advantages(
        self,
        items: List[CandidateComparisonItem]
    ) -> Dict[str, Dict[str, List[str]]]:
        """分析各候选人的优势"""
        advantage_matrix = {}

        for item in items:
            advantages = {
                "top_dimensions": [],  # 最强维度
                "key_achievements": [],  # 关键成就
                "unique_skills": [],  # 独特技能
                "stability": []  # 稳定性优势
            }

            # 找出得分最高的维度
            scores = item.dimensional_scores
            if scores:
                max_score = max(scores.values())
                for dim, score in scores.items():
                    if score >= max_score - 0.2:  # 与最高分差距在0.2以内
                        advantages["top_dimensions"].append(self.DIMENSION_NAMES.get(dim, dim))

            # 关键成就
            if item.achievements:
                # 处理成就数据，可能是字符串或字典
                achievement_texts = []
                for a in item.achievements:
                    if isinstance(a, dict):
                        # 如果是字典，提取original_text字段
                        text = a.get('original_text', '')
                    elif isinstance(a, str):
                        text = a
                    else:
                        continue
                    
                    if text and any(c.isdigit() for c in text):
                        achievement_texts.append(text)
                
                advantages["key_achievements"] = achievement_texts[:3] if achievement_texts else ["未提取到量化成就"]
            else:
                # 成就数据为空，显示提示信息
                advantages["key_achievements"] = ["简历中未提取到成就数据"]

            # 独特技能（假设其他候选人不具备）
            all_other_skills = set()
            for other in items:
                if other.name != item.name:
                    all_other_skills.update(other.skills)
            unique = set(item.skills) - all_other_skills
            advantages["unique_skills"] = list(unique)[:5]

            # 稳定性
            if not item.risk_factors:
                advantages["stability"].append("无风险因素")
            else:
                low_risk = all(r.get("level") != "高" for r in item.risk_factors)
                if low_risk:
                    advantages["stability"].append("风险可控")

            advantage_matrix[item.name] = advantages

        return advantage_matrix

    def _analyze_gaps(
        self,
        items: List[CandidateComparisonItem]
    ) -> Dict[str, Dict[str, float]]:
        """分析候选人之间的差距"""
        gap_analysis = {}

        if len(items) < 2:
            return gap_analysis

        # 找出最高分候选人作为基准
        top_candidate = max(items, key=lambda x: x.tci_score)

        for item in items:
            if item.name == top_candidate.name:
                gap_analysis[item.name] = {"overall_gap": 0, "is_top": True}
                continue

            gaps = {
                "overall_gap": top_candidate.tci_score - item.tci_score,
                "is_top": False,
                "dimension_gaps": {}
            }

            # 各维度差距
            for dim in ["education", "experience", "skill_achievement", "comprehensive"]:
                top_score = top_candidate.dimensional_scores.get(dim, 0)
                item_score = item.dimensional_scores.get(dim, 0)
                gaps["dimension_gaps"][dim] = round(top_score - item_score, 2)

            gap_analysis[item.name] = gaps

        return gap_analysis

    def _generate_recommendation(
        self,
        items: List[CandidateComparisonItem],
        job_requirements: Optional[Dict] = None
    ) -> List[str]:
        """生成推荐排序"""
        # 基础排序：按TCI得分
        sorted_items = sorted(items, key=lambda x: x.tci_score, reverse=True)

        # 如果有岗位要求，进行匹配度调整
        if job_requirements:
            required_skills = set(job_requirements.get("skills", []))
            min_education = job_requirements.get("min_education", "")

            scored_items = []
            for item in sorted_items:
                score = item.tci_score

                # 技能匹配加分
                if required_skills:
                    matched_skills = set(item.skills) & required_skills
                    match_ratio = len(matched_skills) / len(required_skills)
                    score += match_ratio * 0.5  # 技能匹配最多加0.5分

                # 风险因素减分
                high_risks = sum(1 for r in item.risk_factors if r.get("level") == "高")
                score -= high_risks * 0.3  # 每个高风险减0.3分

                scored_items.append((item, score))

            # 重新排序
            scored_items.sort(key=lambda x: x[1], reverse=True)
            return [item.name for item, _ in scored_items]

        return [item.name for item in sorted_items]

    def _generate_summary(
        self,
        items: List[CandidateComparisonItem],
        recommendation_order: List[str]
    ) -> str:
        """生成对比总结"""
        if not items:
            return "暂无候选人数据"

        top_candidate = next((i for i in items if i.name == recommendation_order[0]), items[0])

        summary_parts = []

        # 总体评价
        summary_parts.append(
            f"本次共对比{len(items)}位候选人，"
            f"推荐优先录用【{top_candidate.name}】"
            f"(TCI得分{top_candidate.tci_score:.2f})。"
        )

        # 优势分析
        if len(items) >= 2:
            second_candidate = next(
                (i for i in items if i.name == recommendation_order[1]),
                items[1] if len(items) > 1 else None
            )
            if second_candidate:
                gap = top_candidate.tci_score - second_candidate.tci_score
                if gap > 0.5:
                    summary_parts.append(f"该候选人领先第二名{gap:.2f}分，优势明显。")
                elif gap > 0.2:
                    summary_parts.append(f"该候选人领先第二名{gap:.2f}分，有一定优势。")
                else:
                    summary_parts.append(f"该候选人仅领先第二名{gap:.2f}分，优势不明显。")

        # 风险提示
        risk_count = sum(len(i.risk_factors) for i in items)
        if risk_count > 0:
            summary_parts.append(f"共发现{risk_count}项风险因素，建议面试时重点关注。")

        return "".join(summary_parts)

    def generate_comparison_report(self, result: ComparisonResult) -> Dict:
        """生成对比报告（JSON格式）"""
        return {
            "summary": result.summary,
            "candidates_count": len(result.candidates),
            "recommendation_order": result.recommendation_order,
            "dimension_comparison": {
                self.DIMENSION_NAMES.get(k, k): v
                for k, v in result.dimension_comparison.items()
            },
            "advantage_matrix": result.advantage_matrix,
            "gap_analysis": result.gap_analysis,
            "candidate_details": [
                {
                    "name": c.name,
                    "tci_score": c.tci_score,
                    "rank": c.rank,
                    "dimensional_scores": c.dimensional_scores,
                    "risk_count": len(c.risk_factors)
                }
                for c in result.candidates
            ]
        }


# 全局对比器实例
_comparator: Optional[CandidateComparator] = None


def get_comparator() -> CandidateComparator:
    """获取对比器实例"""
    global _comparator
    if _comparator is None:
        _comparator = CandidateComparator()
    return _comparator
