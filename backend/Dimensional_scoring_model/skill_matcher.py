"""
JD 技能词库与技能匹配度计算模块

功能：
1. 构建不同岗位类型的 JD 技能词库
2. 计算简历技能与 JD 技能的 Jaccard 相似系数
"""

from typing import Dict, List, Set


class SkillMatcher:
    """技能匹配度计算器"""

    JD_SKILL_LIBRARY = {
        "technical": {
            "programming": [
                "python", "java", "c++", "javascript", "typescript", "go", "rust", "scala",
                "php", "ruby", "swift", "kotlin", "c#", ".net", "html", "css", "sql"
            ],
            "frameworks": [
                "spring", "django", "flask", "react", "vue", "angular", "node.js",
                "tensorflow", "pytorch", "keras", "sklearn", "pandas", "numpy"
            ],
            "tools": [
                "git", "docker", "kubernetes", "jenkins", "maven", "gradle", "linux",
                "aws", "azure", "gcp", "mysql", "postgresql", "mongodb", "redis", "kafka"
            ],
            "soft_skills": [
                "问题分析", "逻辑思维", "团队协作", "沟通能力", "学习能力", "创新能力"
            ]
        },
        "management": {
            "management": [
                "团队管理", "项目管理", "绩效管理", "目标管理", "时间管理", "风险管理",
                "战略规划", "业务规划", "组织建设", "人才培养", "激励机制"
            ],
            "communication": [
                "沟通技巧", "谈判技巧", "演讲能力", "表达能力", "协调能力", "人际关系",
                "跨部门协作", "向上管理", "向下管理", "平级沟通"
            ],
            "leadership": [
                "领导力", "决策能力", "执行力", "影响力", "授权能力", "激励能力",
                "变革管理", "冲突管理", "危机处理"
            ],
            "business": [
                "商业敏感度", "市场洞察", "竞争分析", "商业模式", "盈利模式", "成本控制"
            ]
        },
        "ecommerce": {
            "platform_ops": [
                "淘宝运营", "天猫运营", "京东运营", "拼多多运营", "抖音电商", "快手电商",
                "亚马逊运营", "ebay", "独立站运营", "跨境电商"
            ],
            "marketing": [
                "直通车", "钻展", "超级推荐", "信息流广告", "seo", "sem", "内容营销",
                "社交媒体营销", "kOL 合作", "直播带货"
            ],
            "data_analysis": [
                "数据分析", "生意参谋", "google analytics", "转化率优化", "用户画像",
                "a/b 测试", "roi 分析", "gmv 提升"
            ],
            "customer_service": [
                "客服管理", "售后处理", "客户关系管理", "crm", "用户运营", "会员体系"
            ]
        },
        "sales": {
            "sales_skills": [
                "客户开发", "客户维护", "商务谈判", "合同签订", "回款管理", "渠道管理",
                "代理商管理", "经销商管理", "大客户销售", "解决方案销售"
            ],
            "market_expansion": [
                "市场开拓", "区域管理", "渠道拓展", "招商加盟", "合作伙伴开发"
            ],
            "industry_knowledge": [
                "行业洞察", "竞品分析", "产品知识", "价格策略", "投标流程"
            ]
        },
        "hr": {
            "recruitment": [
                "招聘渠道", "面试技巧", "人才测评", "背景调查", "offer 谈判", "猎头管理",
                "校园招聘", "社会招聘", "内部推荐"
            ],
            "training": [
                "培训体系", "课程设计", "讲师培养", "在线学习", "职业发展", "继任计划"
            ],
            "compensation": [
                "薪酬设计", "绩效考核", "福利管理", "股权激励", "人工成本分析"
            ],
            "employee_relations": [
                "员工关系", "劳动合同", "企业文化", "员工活动", "满意度调查"
            ]
        },
        "production": {
            "production_management": [
                "生产计划", "生产调度", "产能规划", "精益生产", "5s 管理", "现场管理",
                "班组管理", "安全生产"
            ],
            "quality_control": [
                "质量管理", "iso 体系", "六西格玛", "spc", "fmea", "8d 报告", "qc 七大手法"
            ],
            "process_improvement": [
                "工艺改进", "效率提升", "成本降低", "自动化改造", "ie 工程", "价值流分析"
            ],
            "supply_chain": [
                "供应链管理", "采购管理", "库存控制", "物流管理", "供应商管理"
            ]
        }
    }

    def __init__(self):
        self.cache = {}

    def calculate_jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """
        计算 Jaccard 相似系数

        Jaccard = |A ∩ B| / |A ∪ B|

        Args:
            set1: 集合 1
            set2: 集合 2

        Returns:
            Jaccard 相似系数 (0-1 之间)
        """
        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if union == 0:
            return 0.0

        return intersection / union

    def extract_resume_skills(self, resume: Dict) -> Set[str]:
        """
        从简历中提取技能集合

        Args:
            resume: 简历字典

        Returns:
            技能集合
        """
        entities = resume.get("entities", {})
        skills_raw = entities.get("skills", [])

        if not skills_raw:
            return set()

        skills_normalized = set()
        for skill in skills_raw:
            skill_lower = skill.lower().strip()
            skills_normalized.add(skill_lower)

        project_experiences = resume.get("project_experiences", [])
        for project in project_experiences:
            description = " ".join(project.get("description", []))
            desc_lower = description.lower()

            for job_type, skill_categories in self.JD_SKILL_LIBRARY.items():
                for category, skills in skill_categories.items():
                    for skill in skills:
                        if skill.lower() in desc_lower:
                            skills_normalized.add(skill.lower())

        return skills_normalized

    def get_jd_skills(self, job_type: str) -> Set[str]:
        """
        获取指定岗位类型的 JD 技能集合

        Args:
            job_type: 岗位类型

        Returns:
            JD 技能集合
        """
        if job_type in self.cache:
            return self.cache[job_type]

        skill_categories = self.JD_SKILL_LIBRARY.get(job_type, {})

        all_skills = set()
        for category, skills in skill_categories.items():
            all_skills.update([s.lower() for s in skills])

        self.cache[job_type] = all_skills
        return all_skills

    def calculate_skill_match_score(self, resume: Dict, job_type: str) -> float:
        """
        计算简历技能与 JD 的匹配度

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            技能匹配分数 (0-5 之间)
        """
        resume_skills = self.extract_resume_skills(resume)
        jd_skills = self.get_jd_skills(job_type)

        if not resume_skills or not jd_skills:
            return 1.0

        jaccard = self.calculate_jaccard_similarity(resume_skills, jd_skills)

        coverage = len(resume_skills.intersection(jd_skills)) / len(jd_skills) if jd_skills else 0

        score = (jaccard * 0.6 + coverage * 0.4) * 5

        return min(max(score, 0), 5.0)

    def get_skill_analysis(self, resume: Dict, job_type: str) -> Dict:
        """
        获取技能匹配分析详情

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            技能分析字典
        """
        resume_skills = self.extract_resume_skills(resume)
        jd_skills = self.get_jd_skills(job_type)

        matched_skills = resume_skills.intersection(jd_skills)
        missing_skills = jd_skills - resume_skills

        return {
            "resume_skills_count": len(resume_skills),
            "jd_skills_count": len(jd_skills),
            "matched_skills": list(matched_skills),
            "missing_skills": list(missing_skills)[:10],
            "match_rate": len(matched_skills) / len(jd_skills) if jd_skills else 0,
            "jaccard_similarity": self.calculate_jaccard_similarity(resume_skills, jd_skills),
            "score": self.calculate_skill_match_score(resume, job_type)
        }
