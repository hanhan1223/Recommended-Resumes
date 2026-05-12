"""
简历数据指标量化模块

将简历解析数据转换为可计算的指标值
用于熵权法计算
"""

import numpy as np
from typing import Dict, List, Any
import re


class ResumeQuantifier:
    """简历指标量化器"""

    EDUCATION_SCORE_MAP = {
        "博士": 5,
        "硕士": 4,
        "本科": 3,
        "学士": 3,
        "大专": 2,
        "高职": 2,
        "高中": 1,
        "中专": 1,
        "初中": 1,
    }

    TECHNICAL_SKILL_KEYWORDS = [
        "python", "java", "c++", "javascript", "sql", "linux", "aws", "azure",
        "机器学习", "深度学习", "人工智能", "数据分析", "算法", "架构",
        "python", "java", "开发", "编程", "技术", "系统", "数据库",
        "电商", "运营", "推广", "seo", "sem", "用户增长",
        "生产", "工艺", "制造", "精益", "质量", "ie", "六西格玛",
    ]

    MANAGEMENT_SKILL_KEYWORDS = [
        "沟通", "协调", "领导", "团队", "管理", "战略", "规划",
        "谈判", "人际关系", "组织", "决策", "执行", "推动",
        "情商", "激励", "培养", "指导", "合作", "协作",
    ]

    def __init__(self):
        self.last_quantified_data = None
        self.last_indicator_names = None

    def extract_education_score(self, resume: Dict) -> float:
        """
        提取学历分数

        Args:
            resume: 简历字典

        Returns:
            学历分数 (1-5)
        """
        education_experiences = resume.get("education_experiences", [])

        if not education_experiences:
            entities = resume.get("entities", {})
            schools = entities.get("schools", [])
            if schools:
                return 3.0
            return 1.0

        max_score = 0
        for edu in education_experiences:
            degree = edu.get("degree", "")
            score = self.EDUCATION_SCORE_MAP.get(degree, 1)
            max_score = max(max_score, score)

        return float(max_score) if max_score > 0 else 1.0

    def extract_skill_score(self, resume: Dict, job_type: str) -> float:
        """
        提取技能分数

        Args:
            resume: 简历字典
            job_type: 岗位类型 ("technical" 或 "management")

        Returns:
            技能分数
        """
        entities = resume.get("entities", {})
        skills = entities.get("skills", [])

        if not skills:
            return 1.0

        skill_text = " ".join(skills).lower()

        if job_type == "technical":
            keywords = self.TECHNICAL_SKILL_KEYWORDS
        else:
            keywords = self.MANAGEMENT_SKILL_KEYWORDS

        match_count = 0
        for keyword in keywords:
            if keyword.lower() in skill_text:
                match_count += 1

        score = 1.0 + min(match_count / 5, 4.0)

        return score

    def extract_project_score(self, resume: Dict) -> float:
        """
        提取项目经验分数

        Args:
            resume: 简历字典

        Returns:
            项目经验分数
        """
        project_experiences = resume.get("project_experiences", [])

        if not project_experiences:
            return 1.0

        n_projects = len(project_experiences)
        score = 1.0 + min(n_projects / 2, 4.0)

        return score

    def extract_work_duration_score(self, resume: Dict) -> float:
        """
        提取工作年限分数

        Args:
            resume: 简历字典

        Returns:
            工作年限分数
        """
        work_duration_months = resume.get("work_duration_months", 0)

        if work_duration_months <= 0:
            work_experiences = resume.get("work_experiences", [])
            if work_experiences:
                work_duration_months = 12 * len(work_experiences)
            else:
                return 1.0

        years = work_duration_months / 12
        score = 1.0 + min(years / 5, 4.0)

        return score

    def extract_achievement_score(self, resume: Dict) -> float:
        """
        提取工作成果分数

        Args:
            resume: 简历字典

        Returns:
            工作成果分数
        """
        achievements = resume.get("achievements", [])

        if not achievements:
            return 1.0

        n_achievements = len(achievements)
        total_value = 0

        for achievement in achievements:
            value = achievement.get("value", 0)
            if value:
                total_value += abs(value)

        score = 1.0 + min(n_achievements / 2, 2.0) + min(total_value / 100, 2.0)

        return min(score, 5.0)

    def extract_work_experience_score(self, resume: Dict) -> float:
        """
        提取工作经历分数（管理类专用）

        Args:
            resume: 简历字典

        Returns:
            工作经历分数
        """
        work_experiences = resume.get("work_experiences", [])

        if not work_experiences:
            entities = resume.get("entities", {})
            companies = entities.get("companies", [])
            if companies:
                return 2.0 + min(len(companies) / 2, 2.0)
            return 1.0

        n_companies = len(work_experiences)

        level_score = 0
        for exp in work_experiences:
            position = exp.get("position", "").lower()
            if any(keyword in position for keyword in ["总监", "总经理", "总裁", "vp", "负责人", "head"]):
                level_score = max(level_score, 5)
            elif any(keyword in position for keyword in ["经理", "部长", "主管", "manager"]):
                level_score = max(level_score, 4)
            elif any(keyword in position for keyword in ["主管", "组长", "lead"]):
                level_score = max(level_score, 3)

        score = min(n_companies, 3) + level_score

        return min(score, 5.0)

    def extract_stability_score(self, resume: Dict) -> float:
        """
        提取稳定性分数（管理类专用）

        Args:
            resume: 简历字典

        Returns:
            稳定性分数
        """
        work_experiences = resume.get("work_experiences", [])
        gap_periods = resume.get("gap_periods", [])

        if not work_experiences:
            return 3.0

        total_months = sum(exp.get("duration_months", 12) for exp in work_experiences)
        avg_tenure = total_months / len(work_experiences) if work_experiences else 12

        tenure_score = min(avg_tenure / 24, 3.0)

        n_gaps = len(gap_periods) if gap_periods else 0
        gap_penalty = min(n_gaps * 0.5, 2.0)

        score = 3.0 + tenure_score - gap_penalty

        return max(1.0, min(score, 5.0))

    def extract_eq_communication_score(self, resume: Dict) -> float:
        """
        提取情商/沟通能力分数（管理类专用）

        Args:
            resume: 简历字典

        Returns:
            情商/沟通能力分数
        """
        entities = resume.get("entities", {})
        skills = entities.get("skills", [])

        if not skills:
            return 2.0

        skill_text = " ".join(skills).lower()

        match_count = 0
        for keyword in self.MANAGEMENT_SKILL_KEYWORDS:
            if keyword.lower() in skill_text:
                match_count += 1

        score = 2.0 + min(match_count / 3, 3.0)

        return min(score, 5.0)

    def extract_management_achievement_score(self, resume: Dict) -> float:
        """
        提取管理成果分数（管理类专用）

        Args:
            resume: 简历字典

        Returns:
            管理成果分数
        """
        achievements = resume.get("achievements", [])

        if not achievements:
            return 2.0

        management_keywords = ["团队", "管理", "带领", "负责", "业绩", "增长", "提升", "优化"]

        management_score = 0
        for achievement in achievements:
            text = achievement.get("original_text", "").lower()
            if any(keyword in text for keyword in management_keywords):
                management_score += 1

            value = achievement.get("value", 0)
            if value:
                management_score += min(abs(value) / 50, 1.0)

        score = 2.0 + min(management_score / 2, 3.0)

        return min(score, 5.0)

    def quantify_resume(self, resume: Dict, job_type: str) -> Dict[str, float]:
        """
        量化单个简历的所有指标

        Args:
            resume: 简历字典
            job_type: 岗位类型 ("technical" 或 "management")

        Returns:
            指标分数字典
        """
        if job_type == "technical":
            indicators = {
                "学历": self.extract_education_score(resume),
                "专业技能": self.extract_skill_score(resume, "technical"),
                "项目经验": self.extract_project_score(resume),
                "工作成果": self.extract_achievement_score(resume),
                "工作年限": self.extract_work_duration_score(resume),
            }
        else:
            indicators = {
                "学历": self.extract_education_score(resume),
                "工作经历": self.extract_work_experience_score(resume),
                "情商沟通": self.extract_eq_communication_score(resume),
                "稳定性": self.extract_stability_score(resume),
                "管理成果": self.extract_management_achievement_score(resume),
            }

        return indicators

    def quantify_resumes(self, resumes: List[Dict], job_type: str) -> tuple:
        """
        批量量化简历数据

        Args:
            resumes: 简历列表
            job_type: 岗位类型

        Returns:
            data_matrix: 数据矩阵 (n_samples, n_indicators)
            indicator_names: 指标名称列表
        """
        if not resumes:
            raise ValueError("Resumes list is empty")

        all_indicators = []
        for resume in resumes:
            indicators = self.quantify_resume(resume, job_type)
            all_indicators.append(indicators)

        indicator_names = list(all_indicators[0].keys())

        data_matrix = np.array([
            [indicators[name] for name in indicator_names]
            for indicators in all_indicators
        ])

        self.last_quantified_data = data_matrix
        self.last_indicator_names = indicator_names

        return data_matrix, indicator_names

    def get_quantified_data(self) -> tuple:
        """获取最后量化的数据"""
        if self.last_quantified_data is None:
            raise ValueError("No data quantified yet")
        return self.last_quantified_data.copy(), self.last_indicator_names.copy()
