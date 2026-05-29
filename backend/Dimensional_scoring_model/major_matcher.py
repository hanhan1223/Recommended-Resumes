"""
专业匹配度计算模块

功能：
1. 构建专业 - 职业对应词库
2. 计算简历专业与目标岗位的余弦相似度
"""

import numpy as np
from typing import Dict, List, Tuple


class MajorMatcher:
    """专业匹配度计算器"""

    MAJOR_JOB_MAPPING = {
        "技术类": {
            "keywords": ["计算机", "软件", "网络", "信息", "电子", "通信", "自动化", "智能", "数据", "人工智能", "互联网"],
            "majors": [
                "计算机科学与技术", "软件工程", "网络工程", "信息安全", "物联网工程",
                "电子信息工程", "通信工程", "信息工程", "光电信息科学与工程",
                "自动化", "机器人工程", "智能科学与技术", "空间信息与数字技术",
                "电子与计算机工程", "计算机应用技术", "计算机软件", "计算机系统结构",
                "模式识别与智能系统", "控制科学与工程", "信息与通信工程",
                "数学与应用数学", "信息与计算科学", "统计学", "数据科学与大数据技术",
                "机械工程", "机械设计制造及其自动化", "车辆工程", "测控技术与仪器"
            ]
        },
        "电商类": {
            "keywords": ["电商", "商务", "营销", "运营", "网络销售", "网店", "淘宝", "京东"],
            "majors": [
                "电子商务", "网络营销", "市场营销", "工商管理", "国际贸易",
                "物流管理", "供应链管理", "商务管理", "网络与新媒体", "数字媒体技术",
                "经济信息管理", "商务经济学", "国际经济与贸易", "零售管理"
            ]
        },
        "人力资源类": {
            "keywords": ["人力", "管理", "行政", "组织", "招聘", "培训", "绩效", "薪酬"],
            "majors": [
                "人力资源管理", "工商管理", "行政管理", "公共事业管理", "劳动与社会保障",
                "劳动关系", "应用心理学", "心理学", "社会学", "社会工作",
                "组织行为学", "企业管理", "管理科学与工程"
            ]
        },
        "品牌市场类": {
            "keywords": ["品牌", "市场", "营销", "广告", "公关", "传播", "媒体", "推广"],
            "majors": [
                "市场营销", "广告学", "公共关系学", "传播学", "新闻学", "网络与新媒体",
                "数字媒体艺术", "品牌管理", "文化产业管理", "会展经济与管理",
                "编辑出版学", "广播电视学", "播音与主持艺术"
            ]
        },
        "生产类": {
            "keywords": ["生产", "制造", "工艺", "质量", "工厂", "车间", "精益", "工业工程"],
            "majors": [
                "工业工程", "机械工程", "机械设计制造及其自动化", "材料成型及控制工程",
                "过程装备与控制工程", "质量管理工程", "标准化工程", "智能制造工程",
                "材料科学与工程", "高分子材料与工程", "化学工程与工艺", "制药工程",
                "纺织工程", "轻化工程", "包装工程", "印刷工程"
            ]
        },
        "研发类": {
            "keywords": ["研发", "研究", "开发", "实验", "技术", "创新", "专利", "论文"],
            "majors": [
                "所有理工科专业", "基础学科", "应用学科", "交叉学科",
                "生物学", "化学", "物理学", "材料科学", "环境科学",
                "药学", "医学", "农学", "林学", "畜牧学", "兽医学"
            ]
        },
        "销售类": {
            "keywords": ["销售", "业务", "客户", "渠道", "代理商", "经销商", "外贸", "国际贸易"],
            "majors": [
                "市场营销", "工商管理", "国际贸易", "商务英语", "外贸", "国际经济与贸易",
                "销售管理", "连锁经营管理", "特许经营管理"
            ]
        },
        "财务类": {
            "keywords": ["财务", "会计", "审计", "税务", "金融", "投资", "资金"],
            "majors": [
                "会计学", "财务管理", "审计学", "税务", "金融学", "金融工程",
                "投资学", "保险学", "财政学", "税收学", "经济学", "国民经济管理"
            ]
        }
    }

    def __init__(self):
        self.vectorizer = None

    # 行业与专业大类的交叉映射权重
    CROSS_DOMAIN_BONUS = {
        ("技术类", "研发类"): 0.85,
        ("研发类", "技术类"): 0.85,
        ("电商类", "品牌市场类"): 0.70,
        ("品牌市场类", "电商类"): 0.70,
        ("电商类", "销售类"): 0.65,
        ("销售类", "电商类"): 0.65,
        ("人力资源类", "品牌市场类"): 0.55,
        ("生产类", "技术类"): 0.60,
        ("技术类", "生产类"): 0.60,
        ("财务类", "人力资源类"): 0.50,
    }

    def calculate_major_similarity(self, major: str, job_type: str) -> float:
        """
        计算专业与岗位类型的连续匹配度

        使用多级匹配策略：
        1. 精确专业名称匹配 → 0.90-0.95
        2. 关键词匹配 → 0.70-0.85
        3. 跨领域交叉匹配 → 0.50-0.65
        4. 无匹配 → 0.10-0.30

        Args:
            major: 专业名称
            job_type: 岗位类型（technical, management, sales 等）

        Returns:
            相似度分数 (0.10-0.95 之间)
        """
        if not major or not job_type:
            return 0.10

        job_category = self._map_job_type_to_category(job_type)

        if job_category not in self.MAJOR_JOB_MAPPING:
            return 0.50

        category_info = self.MAJOR_JOB_MAPPING[job_category]
        major_keywords = category_info["keywords"]
        major_list = category_info["majors"]
        major_lower = major.lower()

        # Level 1: 精确专业名称匹配 (0.90-0.95)
        for known_major in major_list:
            known_lower = known_major.lower()
            if known_lower == major_lower:
                return 0.95  # 完全匹配
            if known_lower in major_lower or major_lower in known_lower:
                return 0.90  # 包含匹配

        # Level 2: 关键词匹配 (0.70-0.85)
        keyword_matches = 0
        for keyword in major_keywords:
            if keyword.lower() in major_lower:
                keyword_matches += 1

        if keyword_matches >= 2:
            return 0.85  # 多关键词匹配
        if keyword_matches == 1:
            return 0.75  # 单关键词匹配

        # Level 3: 跨领域交叉匹配 (0.50-0.65)
        # 检查专业是否属于其他领域，获取交叉分数
        for other_category, other_info in self.MAJOR_JOB_MAPPING.items():
            if other_category == job_category:
                continue
            for known_major in other_info["majors"]:
                if known_major.lower() in major_lower or major_lower in known_major.lower():
                    cross_key = (other_category, job_category)
                    return self.CROSS_DOMAIN_BONUS.get(cross_key, 0.50)

        # Level 4: 无匹配 - 根据是否有专业信息给不同分数
        return 0.10

    def _map_job_type_to_category(self, job_type: str) -> str:
        """将岗位类型映射到专业类别"""
        mapping = {
            "technical": "技术类",
            "management": "品牌市场类",
            "sales": "销售类",
            "hr": "人力资源类",
            "ecommerce": "电商类",
            "production": "生产类",
            "rd": "研发类",
            "finance": "财务类"
        }
        return mapping.get(job_type.lower(), "技术类")

    def get_professional_match_score(self, resume: Dict, job_type: str) -> float:
        """
        从简历中提取专业并计算匹配度

        使用最高匹配策略：多个学历取最高匹配分

        Args:
            resume: 简历字典
            job_type: 岗位类型

        Returns:
            专业匹配度分数 (0.10-0.95 之间)
        """
        education_experiences = resume.get("education_experiences", [])

        if not education_experiences:
            return 0.30

        majors = []
        for edu in education_experiences:
            major = edu.get("major", "")
            if major:
                majors.append(major)

        if not majors:
            return 0.30

        similarities = [self.calculate_major_similarity(major, job_type) for major in majors]
        return max(similarities)
