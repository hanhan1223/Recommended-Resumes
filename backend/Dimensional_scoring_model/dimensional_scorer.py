"""
分维度评分主模块

实现赛题要求的四个核心维度评分：
A. 教育背景评分 (Sedu)
B. 工作经历评分 (Sexp) - 权重最高部分
C. 技能与成果评分 (Sskill)
D. 综合素质与修正项 (Sadj)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional

from .major_matcher import MajorMatcher
from .promotion_calculator import PromotionCalculator
from .skill_matcher import SkillMatcher
from .achievement_scorer import AchievementAndSoftSkillScorer


class DimensionalScorer:
    """分维度评分器"""

    def __init__(self):
        self.major_matcher = MajorMatcher()
        self.promotion_calculator = PromotionCalculator()
        self.skill_matcher = SkillMatcher()
        self.achievement_scorer = AchievementAndSoftSkillScorer()

    def calculate_education_score(self, resume: Dict, job_type: str) -> Tuple[float, Dict]:
        """
        A. 教育背景评分 (Sedu)

        公式：Sedu = w1 * 学历分 + w2 * 学校分 + w3 * 专业匹配度

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            (教育背景总分，详情字典)
        """
        education_experiences = resume.get("education_experiences", [])
        entities = resume.get("entities", {})
        schools = entities.get("schools", [])

        if not education_experiences and not schools:
            return 1.0, {
                "degree_score": 1.0,
                "school_score": 1.0,
                "major_match": 0.5,
                "weights": {"w1": 0.4, "w2": 0.3, "w3": 0.3}
            }

        degree_score = self._extract_degree_score(resume)
        school_score = self._extract_school_score(resume)
        major_match = self.major_matcher.get_professional_match_score(resume, job_type)

        w1, w2, w3 = 0.4, 0.3, 0.3
        sedu_score = w1 * degree_score + w2 * school_score + w3 * major_match * 5

        details = {
            "degree_score": degree_score,
            "school_score": school_score,
            "major_match": major_match,
            "weights": {"w1": w1, "w2": w2, "w3": w3}
        }

        return sedu_score, details

    def _extract_degree_score(self, resume: Dict) -> float:
        """提取学历分数"""
        EDUCATION_SCORE_MAP = {
            "博士": 5.0,
            "硕士": 4.0,
            "本科": 3.0,
            "学士": 3.0,
            "大专": 2.0,
            "高职": 2.0,
            "高中": 1.0,
            "中专": 1.0,
            "初中": 1.0,
        }

        education_experiences = resume.get("education_experiences", [])

        if not education_experiences:
            return 3.0

        max_score = 0
        for edu in education_experiences:
            degree = edu.get("degree", "")
            score = EDUCATION_SCORE_MAP.get(degree, 3.0)
            max_score = max(max_score, score)

        return max_score if max_score > 0 else 3.0

    def _extract_school_score(self, resume: Dict) -> float:
        """提取学校分数"""
        university_ratings = resume.get("university_ratings", [])

        if not university_ratings:
            entities = resume.get("entities", {})
            schools = entities.get("schools", [])
            if schools:
                return 3.0
            return 1.0

        ratings = [r.get("rating", 3) for r in university_ratings]
        avg_rating = np.mean(ratings)

        return avg_rating

    def calculate_experience_score(self, resume: Dict, job_type: str) -> Tuple[float, Dict]:
        """
        B. 工作经历评分 (Sexp) - 权重最高部分

        公式：Sexp = w1 * 公司实力 + w2 * 稳定性 + w3 * 升职速度

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            (工作经历总分，详情字典)
        """
        company_power = self._calculate_company_power(resume)
        stability = self._calculate_stability(resume)
        promotion_speed = self.promotion_calculator.calculate_promotion_speed(resume)

        w1, w2, w3 = 0.4, 0.3, 0.3
        sexp_score = w1 * company_power + w2 * stability + w3 * promotion_speed

        details = {
            "company_power": company_power,
            "stability": stability,
            "promotion_speed": promotion_speed,
            "promotion_analysis": self.promotion_calculator.get_promotion_analysis(resume),
            "weights": {"w1": w1, "w2": w2, "w3": w3}
        }

        return sexp_score, details

    def _calculate_company_power(self, resume: Dict) -> float:
        """
        计算公司实力

        基于公司知名度打分，取自 company_ratings 的平均值
        """
        company_ratings = resume.get("company_ratings", [])

        if not company_ratings:
            entities = resume.get("entities", {})
            companies = entities.get("companies", [])
            if companies:
                return 2.0
            return 1.0

        ratings = [r.get("rating", 3) for r in company_ratings]
        avg_rating = np.mean(ratings)

        return avg_rating

    def _calculate_stability(self, resume: Dict) -> float:
        """
        计算稳定性

        计算平均每份工作时长
        - 时长 < 1 年，扣分
        - 时长 > 3 年，加分
        """
        work_experiences = resume.get("work_experiences", [])
        work_duration_months = resume.get("work_duration_months", 0)

        if not work_experiences:
            if work_duration_months > 0:
                n_jobs = max(1, work_duration_months // 24)
                avg_tenure = work_duration_months / n_jobs
            else:
                return 3.0
        else:
            n_jobs = len(work_experiences)
            if n_jobs == 0:
                return 3.0
            avg_tenure = work_duration_months / n_jobs if work_duration_months > 0 else 24

        base_score = 3.0

        if avg_tenure < 12:
            stability_score = base_score - (12 - avg_tenure) / 12
        elif avg_tenure > 36:
            stability_score = base_score + min((avg_tenure - 36) / 12, 1.5)
        else:
            stability_score = base_score + (avg_tenure - 12) / 24

        return max(1.0, min(stability_score, 5.0))

    def calculate_skill_score(self, resume: Dict, job_type: str) -> Tuple[float, Dict]:
        """
        C. 技能与成果评分 (Sskill)

        公式：Sskill = w1 * 技能匹配度 (Jaccard) + w2 * 重大成果分

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            (技能与成果总分，详情字典)
        """
        skill_match = self.skill_matcher.calculate_skill_match_score(resume, job_type)
        achievement_score = self.achievement_scorer.calculate_achievement_score(resume)

        w1, w2 = 0.5, 0.5
        sskill_score = w1 * skill_match + w2 * achievement_score

        details = {
            "skill_match_score": skill_match,
            "achievement_score": achievement_score,
            "skill_analysis": self.skill_matcher.get_skill_analysis(resume, job_type),
            "achievement_analysis": self.achievement_scorer.get_achievement_analysis(resume),
            "weights": {"w1": w1, "w2": w2}
        }

        return sskill_score, details

    def calculate_comprehensive_score(self, resume: Dict, job_type: str) -> Tuple[float, Dict]:
        """
        D. 综合素质与修正项 (Sadj)

        公式：Sadj = 软技能分 - 跳槽惩罚

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            (综合素质总分，详情字典)
        """
        soft_skill_score = self.achievement_scorer.calculate_soft_skill_score(resume)

        job_hopping_penalty = self._calculate_job_hopping_penalty(resume)

        sadj_score = soft_skill_score * job_hopping_penalty

        details = {
            "soft_skill_score": soft_skill_score,
            "soft_skill_analysis": self.achievement_scorer.get_soft_skill_analysis(resume),
            "job_hopping_penalty": job_hopping_penalty,
            "penalty_triggered": job_hopping_penalty < 1.0
        }

        return sadj_score, details

    def _calculate_job_hopping_penalty(self, resume: Dict) -> float:
        """
        计算跳槽频率惩罚

        若 5 年内跳槽 > 3 次，触发惩罚函数，总分 × 0.9
        跳槽次数根据 work_experiences 的数量判断
        """
        work_experiences = resume.get("work_experiences", [])
        work_duration_months = resume.get("work_duration_months", 0)

        if not work_experiences:
            n_jobs = len(work_experiences)
        else:
            n_jobs = len(work_experiences)

        work_years = work_duration_months / 12.0 if work_duration_months > 0 else n_jobs * 2

        if work_years < 5:
            recent_years = work_years
        else:
            recent_years = 5

        if recent_years < 1:
            recent_years = 1

        job_hopping_rate = n_jobs / recent_years

        if job_hopping_rate > 0.6:
            return 0.9

        return 1.0

    def calculate_all_dimensions(self, resume: Dict, job_type: str) -> Dict:
        """
        计算所有四个维度的得分

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            所有维度得分和详情
        """
        sedu_score, sedu_details = self.calculate_education_score(resume, job_type)
        sexp_score, sexp_details = self.calculate_experience_score(resume, job_type)
        sskill_score, sskill_details = self.calculate_skill_score(resume, job_type)
        sadj_score, sadj_details = self.calculate_comprehensive_score(resume, job_type)

        return {
            "dimensional_scores": {
                "education": sedu_score,
                "experience": sexp_score,
                "skill_achievement": sskill_score,
                "comprehensive": sadj_score
            },
            "details": {
                "education_details": sedu_details,
                "experience_details": sexp_details,
                "skill_details": sskill_details,
                "comprehensive_details": sadj_details
            }
        }
