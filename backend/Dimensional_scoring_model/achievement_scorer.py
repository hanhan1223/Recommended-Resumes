"""
重大成果与软技能词库模块

功能：
1. 构建重大成果关键词列表
2. 构建软技能词库（用于情商映射）
3. 计算重大成果得分和软技能得分
"""

from typing import Dict, List, Set


class AchievementAndSoftSkillScorer:
    """重大成果与软技能评分器"""

    MAJOR_ACHIEVEMENT_KEYWORDS = {
        "academic": [
            "专利", "发明专利", "实用新型专利", "外观设计专利", "PCT 专利",
            "论文", "第一作者", "通讯作者", "sci", "ei", "核心期刊", "nature", "science",
            "著作", "专著", "编著", "译著", "教材"
        ],
        "awards": [
            "国家级奖项", "国家科技进步奖", "国家技术发明奖", "自然科学奖",
            "省级奖项", "省部级奖项", "市级奖项",
            "行业奖项", "协会奖项", "学会奖项",
            "优秀员工", "先进个人", "优秀管理者", "金牌销售", "Top sales",
            "创新奖", "突破奖", "贡献奖", "杰出青年", "领军人才"
        ],
        "business": [
            "营收破亿", "业绩破亿", "销售额破亿", "利润破亿",
            "业绩翻倍", "销售翻倍", "增长 100%", "同比增长", "环比增长",
            "从 0 到 1", "从零到一", "白手起家", "创业", "开拓", "奠基",
            "市场突破", "技术突破", "产品突破", "业务突破",
            "扭亏为盈", "扭亏", "扭亏为盈", "扭亏增盈"
        ],
        "leadership": [
            "带领团队", "领导团队", "组建团队", "培养团队", "管理团队",
            "业绩第一", "排名第一", "行业第一", "国内领先", "国际领先",
            "标杆项目", "示范项目", "重点项目", "战略项目"
        ],
        "innovation": [
            "技术创新", "产品创新", "业务创新", "模式创新", "管理创新",
            "自主研发", "自主创新", "核心技术", "关键技术", "卡脖子技术",
            "填补空白", "国内首创", "行业首创", "首创"
        ],
        "scale": [
            "团队规模", "管理人数", "下属人数", "汇报人数",
            "预算规模", "项目金额", "合同金额", "订单金额",
            "用户规模", "客户数量", "门店数量", "渠道数量"
        ]
    }

    SOFT_SKILL_KEYWORDS = {
        "communication": [
            "沟通", "协调", "谈判", "演讲", "表达", "说服", "倾听", "反馈",
            "人际关系", "人际交往", "社交", "公关", "对外联络"
        ],
        "leadership": [
            "领导", "带领", "指导", "培养", "激励", "授权", "决策", "影响力",
            "团队建设", "团队管理", "凝聚力", "向心力"
        ],
        "collaboration": [
            "合作", "协作", "配合", "支持", "协助", "协同", "跨部门", "多方合作",
            "团队合作", "集体荣誉感", "大局意识"
        ],
        "organization": [
            "组织", "策划", "统筹", "安排", "调度", "资源配置", "时间管理",
            "会议组织", "活动组织", "项目组织"
        ],
        "adaptability": [
            "适应", "学习", "快速上手", "抗压", "压力管理", "情绪管理",
            "变化管理", "多任务", "并行处理"
        ],
        "problem_solving": [
            "分析", "解决", "处理", "应对", "排查", "优化", "改进", "创新",
            "问题发现", "问题解决", "危机处理", "应急处理"
        ],
        "emotional_intelligence": [
            "情商", "同理心", "换位思考", "理解他人", "关怀", "包容",
            "自我认知", "自我管理", "自我激励"
        ],
        "experience_indicators": [
            "跨部门项目", "学生会", "社团", "志愿者", "公益",
            "班干部", "党团活动", "组织活动", "外联"
        ]
    }

    def __init__(self):
        self.achievement_cache = {}
        self.soft_skill_cache = {}

    def calculate_achievement_score(self, resume: Dict) -> float:
        """
        计算重大成果得分

        Args:
            resume: 简历字典

        Returns:
            重大成果得分 (0-5 之间)
        """
        achievements = resume.get("achievements", [])

        if not achievements:
            return 1.0

        base_score = 1.0
        keyword_bonus = 0.0
        value_bonus = 0.0

        all_keywords = []
        for category, keywords in self.MAJOR_ACHIEVEMENT_KEYWORDS.items():
            all_keywords.extend(keywords)

        for achievement in achievements:
            text = achievement.get("original_text", "").lower()
            value = achievement.get("value", 0)

            for keyword in all_keywords:
                if keyword.lower() in text:
                    keyword_bonus += 0.3

            if value:
                if achievement.get("unit") == "%":
                    if abs(value) >= 50:
                        value_bonus += 1.0
                    elif abs(value) >= 20:
                        value_bonus += 0.5
                    else:
                        value_bonus += 0.2
                elif achievement.get("unit") in ["亿元", "亿"]:
                    if abs(value) >= 1:
                        value_bonus += 1.5
                    else:
                        value_bonus += 0.5
                elif achievement.get("unit") in ["万元", "万"]:
                    if abs(value) >= 10000:
                        value_bonus += 1.0
                    elif abs(value) >= 1000:
                        value_bonus += 0.5
                else:
                    if abs(value) >= 100:
                        value_bonus += 0.5

        score = base_score + min(keyword_bonus, 3.0) + min(value_bonus, 1.0)
        return min(score, 5.0)

    def calculate_soft_skill_score(self, resume: Dict) -> float:
        """
        计算软技能得分（情商映射）

        Args:
            resume: 简历字典

        Returns:
            软技能得分 (0-5 之间)
        """
        entities = resume.get("entities", {})
        skills_raw = entities.get("skills", [])

        project_experiences = resume.get("project_experiences", [])
        work_experiences = resume.get("work_experiences", [])

        all_text = " ".join(skills_raw).lower() if skills_raw else ""

        for project in project_experiences:
            desc = " ".join(project.get("description", [])).lower()
            all_text += " " + desc

        for work in work_experiences:
            resp = " ".join(work.get("responsibilities", [])).lower()
            all_text += " " + resp

        if not all_text.strip():
            return 2.0

        match_count = 0
        total_keywords = 0

        for category, keywords in self.SOFT_SKILL_KEYWORDS.items():
            total_keywords += len(keywords)
            for keyword in keywords:
                if keyword.lower() in all_text:
                    match_count += 1

        if category == "experience_indicators":
            match_count *= 1.5

        base_score = 2.0
        keyword_score = min(match_count / 10, 2.5)

        n_projects = len(project_experiences)
        project_bonus = min(n_projects * 0.1, 0.5)

        score = base_score + keyword_score + project_bonus
        return min(score, 5.0)

    def get_achievement_analysis(self, resume: Dict) -> Dict:
        """
        获取重大成果分析详情

        Args:
            resume: 简历字典

        Returns:
            成果分析字典
        """
        achievements = resume.get("achievements", [])

        if not achievements:
            return {
                "n_achievements": 0,
                "matched_keywords": [],
                "high_value_achievements": [],
                "score": 1.0
            }

        all_keywords = []
        for category, keywords in self.MAJOR_ACHIEVEMENT_KEYWORDS.items():
            all_keywords.extend([(keyword, category) for keyword in keywords])

        matched_keywords = []
        high_value_achievements = []

        for achievement in achievements:
            text = achievement.get("original_text", "").lower()
            value = achievement.get("value", 0)

            for keyword, category in all_keywords:
                if keyword.lower() in text:
                    matched_keywords.append({
                        "keyword": keyword,
                        "category": category,
                        "text": achievement.get("original_text", "")
                    })

            if value and (
                (achievement.get("unit") == "%" and abs(value) >= 20) or
                (achievement.get("unit") in ["亿元", "亿"] and abs(value) >= 0.5) or
                (achievement.get("unit") in ["万元", "万"] and abs(value) >= 500)
            ):
                high_value_achievements.append(achievement)

        return {
            "n_achievements": len(achievements),
            "matched_keywords": matched_keywords[:20],
            "high_value_achievements": high_value_achievements,
            "score": self.calculate_achievement_score(resume)
        }

    def get_soft_skill_analysis(self, resume: Dict) -> Dict:
        """
        获取软技能分析详情

        Args:
            resume: 简历字典

        Returns:
            软技能分析字典
        """
        entities = resume.get("entities", {})
        skills_raw = entities.get("skills", [])

        all_text = " ".join(skills_raw).lower() if skills_raw else ""

        matched_categories = {}
        for category, keywords in self.SOFT_SKILL_KEYWORDS.items():
            matched = [kw for kw in keywords if kw.lower() in all_text]
            if matched:
                matched_categories[category] = matched

        return {
            "matched_categories": matched_categories,
            "n_matched_keywords": sum(len(v) for v in matched_categories.values()),
            "score": self.calculate_soft_skill_score(resume)
        }
