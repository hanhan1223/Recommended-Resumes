"""
分维度评分主模块

实现赛题要求的六个核心维度评分：
A. 教育背景评分 (Sedu)
B. 工作经历评分 (Sexp) - 权重最高部分
C. 技能与成果评分 (Sskill)
D. 综合素质与修正项 (Sadj)
E. 成长潜力评分 (Spotential) - 来自 Person_job_fit_model
F. 岗位匹配评分 (Smatching) - 来自 Person_job_fit_model
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

        公式：Sexp = w1 * 公司实力 + w2 * 稳定性 + w3 * 升职速度 + w4 * 年龄因子

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            (工作经历总分，详情字典)
        """
        company_power = self._calculate_company_power(resume)
        stability = self._calculate_stability(resume)
        promotion_speed = self.promotion_calculator.calculate_promotion_speed(resume)
        age_factor = self._calculate_age_factor(resume)

        w1, w2, w3, w4 = 0.35, 0.25, 0.25, 0.15
        sexp_score = w1 * company_power + w2 * stability + w3 * promotion_speed + w4 * age_factor

        details = {
            "company_power": company_power,
            "stability": stability,
            "promotion_speed": promotion_speed,
            "age_factor": age_factor,
            "promotion_analysis": self.promotion_calculator.get_promotion_analysis(resume),
            "weights": {"w1": w1, "w2": w2, "w3": w3, "w4": w4}
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

    def _calculate_age_factor(self, resume: Dict) -> float:
        """
        计算年龄因子 - 钟形曲线评分

        使用高斯分布：25-35岁为最佳区间（峰值），两端递减
        - 25-35岁：4.5-5.0（最佳）
        - 20-24岁：3.5-4.5（年轻但有潜力）
        - 36-45岁：3.5-4.5（经验丰富）
        - 46-55岁：2.5-3.5（开始下降）
        - <20 或 >55：1.5-2.5

        Args:
            resume: 简历字典

        Returns:
            年龄因子得分 (1.0-5.0)
        """
        import math

        age = resume.get("age", 0)

        # 如果没有年龄信息，尝试从工作年限推算
        if not age or age <= 0:
            work_duration_months = resume.get("work_duration_months", 0)
            if work_duration_months > 0:
                # 假设22岁开始工作
                age = 22 + work_duration_months / 12
            else:
                return 3.0  # 无信息时给中间分

        # 高斯分布参数
        mu = 30  # 峰值年龄
        sigma = 8  # 标准差，控制曲线宽度

        # 高斯函数: f(x) = exp(-0.5 * ((x - mu) / sigma)^2)
        gaussian = math.exp(-0.5 * ((age - mu) / sigma) ** 2)

        # 映射到 1.0-5.0 范围
        score = 1.0 + 4.0 * gaussian

        return max(1.0, min(score, 5.0))

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

        公式：Sadj = (0.6 * 软技能分 + 0.4 * EQ分) * EQ乘数 * 跳槽惩罚

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            (综合素质总分，详情字典)
        """
        soft_skill_score = self.achievement_scorer.calculate_soft_skill_score(resume)
        eq_score = self.achievement_scorer.calculate_eq_score(resume)

        job_hopping_penalty = self._calculate_job_hopping_penalty(resume)

        # EQ乘数: EQ 4.0以上给1.1加成，3.0以下给0.9惩罚
        if eq_score >= 4.0:
            eq_multiplier = 1.10
        elif eq_score >= 3.0:
            eq_multiplier = 1.0
        else:
            eq_multiplier = 0.90

        base_score = 0.6 * soft_skill_score + 0.4 * eq_score
        sadj_score = base_score * eq_multiplier * job_hopping_penalty

        details = {
            "soft_skill_score": soft_skill_score,
            "eq_score": eq_score,
            "eq_multiplier": eq_multiplier,
            "soft_skill_analysis": self.achievement_scorer.get_soft_skill_analysis(resume),
            "job_hopping_penalty": job_hopping_penalty,
            "penalty_triggered": job_hopping_penalty < 1.0
        }

        return sadj_score, details

    def _calculate_job_hopping_penalty(self, resume: Dict) -> float:
        """
        计算跳槽频率惩罚

        若 5 年内跳槽 > 3 次，触发惩罚函数，总分 × 0.9
        跳槽次数 = 工作段数 - 1（与 risk_identifier 逻辑一致）
        """
        work_experiences = resume.get("work_experiences", [])
        work_duration_months = resume.get("work_duration_months", 0)

        n_jobs = len(work_experiences) if work_experiences else 0
        job_changes = max(0, n_jobs - 1)

        if job_changes <= 3:
            return 1.0

        work_years = work_duration_months / 12.0 if work_duration_months > 0 else n_jobs * 2
        recent_years = min(work_years, 5)
        if recent_years < 1:
            recent_years = 1

        jobs_per_5years = job_changes / recent_years * 5

        if jobs_per_5years > 3:
            return 0.9

        return 1.0

    def calculate_all_dimensions(self, resume: Dict, job_type: str,
                                  potential_score: float = None,
                                  matching_score: float = None) -> Dict:
        """
        计算所有六个维度的得分

        Args:
            resume: 简历字典
            job_type: 岗位类型
            potential_score: 成长潜力得分（0-10，来自Person_job_fit_model），None则默认3.0
            matching_score: 岗位匹配得分（0-5，来自Person_job_fit_model），None则默认3.0

        Returns:
            所有维度得分和详情
        """
        sedu_score, sedu_details = self.calculate_education_score(resume, job_type)
        sexp_score, sexp_details = self.calculate_experience_score(resume, job_type)
        sskill_score, sskill_details = self.calculate_skill_score(resume, job_type)
        sadj_score, sadj_details = self.calculate_comprehensive_score(resume, job_type)

        # 成长潜力：来自 Person_job_fit_model 的 0-10 分归一化到 0-5
        if potential_score is not None:
            growth_potential = min(max(potential_score / 2.0, 0), 5.0)
        else:
            import logging
            logging.getLogger(__name__).warning("Person_job_fit_model 未提供 potential_score，成长潜力使用默认值 3.0")
            growth_potential = 3.0

        # 岗位匹配：来自 Person_job_fit_model 的 0-5 分直接使用
        if matching_score is not None:
            job_matching = min(max(matching_score, 0), 5.0)
        else:
            import logging
            logging.getLogger(__name__).warning("Person_job_fit_model 未提供 matching_score，岗位匹配使用默认值 3.0")
            job_matching = 3.0

        return {
            "dimensional_scores": {
                "education": sedu_score,
                "experience": sexp_score,
                "skill_achievement": sskill_score,
                "comprehensive": sadj_score,
                "growth_potential": growth_potential,
                "job_matching": job_matching
            },
            "details": {
                "education_details": sedu_details,
                "experience_details": sexp_details,
                "skill_details": sskill_details,
                "comprehensive_details": sadj_details,
                "growth_potential_details": {"source": "person_job_fit_model", "raw_score": potential_score},
                "job_matching_details": {"source": "person_job_fit_model", "raw_score": matching_score}
            }
        }
