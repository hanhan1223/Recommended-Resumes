# -*- coding: utf-8 -*-
"""
岗位画像抽取模块

功能：
1. 从岗位描述文本中提取结构化信息
2. 提取学历要求、工作年限、核心技能、行业经验、管理职责等关键字段
3. 形成标准化的岗位画像 JSON 数据

输出格式：
{
    "job_title": str,              # 岗位名称
    "industry": str,               # 所属行业
    "education_required": str,     # 学历要求
    "education_preference": str,   # 学历偏好
    "min_work_years": int,         # 最低工作年限
    "preferred_work_years": str,   # 偏好工作年限范围
    "core_skills": List[str],      # 核心技能列表
    "soft_skills": List[str],      # 软技能列表
    "industry_experience": str,    # 行业经验要求
    "management_responsibility": { # 管理职责
        "has_team_management": bool,
        "team_size": str,
        "management_level": str
    },
    "key_responsibilities": List[str],  # 关键职责
    "preferred_qualifications": List[str],  # 优先条件
    "salary_range": {              # 薪资范围（可选）
        "min": int,
        "max": int,
        "unit": str
    }
}
"""

import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class JobProfileExtractor:
    """岗位画像抽取器"""

    # 学历层次映射（从高到低）
    EDUCATION_LEVELS = {
        '博士': 5,
        '博士后': 5,
        '硕士': 4,
        '研究生': 4,
        'MBA': 4,
        'EMBA': 4,
        '本科': 3,
        '学士': 3,
        '大专': 2,
        '专科': 2,
        '高职': 2,
        '高中': 1,
        '中专': 1,
        '职高': 1,
        '初中': 0
    }

    # 学历关键词映射
    EDUCATION_KEYWORDS = {
        '博士': ['博士', 'PhD', 'Doctor'],
        '硕士': ['硕士', '研究生', 'Master', 'MBA', 'EMBA'],
        '本科': ['本科', '学士', '大学本科', 'Bachelor'],
        '大专': ['大专', '专科', '高职', '大学专科'],
        '高中': ['高中', '中专', '职高', '高中及以下']
    }

    # 行业关键词映射
    INDUSTRY_KEYWORDS = {
        '电商': ['电商', '电子商务', '淘宝', '天猫', '京东', '拼多多', '抖音电商', '跨境电商', '运营'],
        '品牌': ['品牌', '市场', '推广', '广告', '公关', '媒体', '策划', '营销'],
        '销售': ['销售', '业务', '渠道', '客户', '商务', '招商', '外贸', '代理商'],
        '研发': ['研发', '技术', '开发', '工程师', '科学家', '研究', '实验', '算法'],
        '生产': ['生产', '制造', '工厂', '质量', '工艺', '车间', '精益生产', '厂长'],
        '人力资源': ['人力', 'HR', '招聘', '培训', '薪酬', '绩效', '员工关系', '人事']
    }

    # 管理层级关键词
    MANAGEMENT_LEVELS = {
        '高层': ['总监', '总经理', '副总裁', '总裁', 'CEO', 'COO', 'CFO', 'CTO', '合伙人', '创始人'],
        '中层': ['经理', '主管', '主任', '部长', 'Team Leader', '组长', '主管'],
        '基层': ['专员', '助理', '秘书', '代表', '文员']
    }

    # 团队规模关键词
    TEAM_SIZE_KEYWORDS = {
        '1-5 人': ['小团队', '带领团队', '管理团队'],
        '5-10 人': ['5-10 人', '中型团队'],
        '10-20 人': ['10-20 人', '较大团队'],
        '20-50 人': ['20-50 人', '大型团队'],
        '50 人以上': ['50 人以上', '超大型团队', '百人团队']
    }

    # 软技能词库
    SOFT_SKILLS_LIBRARY = [
        '沟通能力', '团队协作', '领导力', '执行力', '学习能力', '创新能力',
        '逻辑思维', '问题分析', '决策能力', '抗压能力', '时间管理', '目标导向',
        '责任心', '主动性', '适应能力', '谈判能力', '组织能力', '协调能力',
        '人际交往', '表达能力', '策划能力', '统筹能力', '洞察力', '判断力'
    ]

    def __init__(self, verbose: bool = True):
        """
        初始化抽取器

        Args:
            verbose: 是否打印详细输出
        """
        self.verbose = verbose
        self._init_patterns()

    def _init_patterns(self):
        """初始化正则表达式模式"""
        # 时间模式（用于提取工作年限）
        self.year_pattern = r'(\d+[\.．]?\d*)\s*(?:年|年以上|年经验|年及以上|年以上工作经验)'
        self.year_range_pattern = r'(\d+)\s*[-至～]\s*(\d+)\s*(?:年|年经验)'

        # 学历模式
        self.education_pattern = r'(博士 | 硕士|研究生|MBA|本科|学士|大专|专科|高职|高中|中专)'
        self.education_require_pattern = r'(?:要求 | 需|最低学历 | 学历)[:：\s]*(博士 | 硕士|研究生|MBA|本科|学士|大专|专科|高职|高中|中专)'

        # 薪资模式
        self.salary_pattern = r'(\d+(?:\.\d+)?)\s*(k|K|千|万)\s*[-至～]\s*(\d+(?:\.\d+)?)\s*(k|K|千|万)?\s*(?:元 | 元/月 | 元/年 | 月薪 | 年薪)?'

        # 团队规模模式
        self.team_size_pattern = r'(\d+)\s*[-至～]\s*(\d+)\s*人'
        self.team_manage_pattern = r'(?:管理 | 带领 | 负责)\s*(\d+(?:[-至～]\d+)?\s*人)'

    def extract_job_title(self, text: str) -> str:
        """
        提取岗位名称

        Args:
            text: 岗位描述文本

        Returns:
            岗位名称
        """
        # 常见岗位名称模式
        patterns = [
            r'招聘岗位[：:\s]+([\u4e00-\u9fa5A-Z0-9]+(?:总监|经理|工程师|主管|专员|助理|代表|分析师|设计师|研究员|科学家|总裁|总经理|副总裁|合伙人|负责人|组长|主任|部长))',
            r'招聘职位[：:\s]*([\u4e00-\u9fa5A-Z0-9]+(?:总监|经理|工程师|主管|专员|助理|代表|分析师|设计师|研究员|科学家|总裁|总经理|副总裁|合伙人|负责人|组长|主任|部长))',
            r'岗位名称[：:\s]*([\u4e00-\u9fa5A-Z0-9]+(?:总监|经理|工程师|主管|专员|助理|代表|分析师|设计师|研究员|科学家|总裁|总经理|副总裁|合伙人|负责人|组长|主任|部长))',
            r'职位名称[：:\s]*([\u4e00-\u9fa5A-Z0-9]+(?:总监|经理|工程师|主管|专员|助理|代表|分析师|设计师|研究员|科学家|总裁|总经理|副总裁|合伙人|负责人|组长|主任|部长))',
            r'^([\u4e00-\u9fa5A-Z0-9]+(?:总监|经理|工程师|主管|专员|助理|代表|分析师|设计师|研究员|科学家|总裁|总经理|副总裁|合伙人|负责人|组长|主任|部长))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()

        return "未知岗位"

    def extract_education(self, text: str) -> Tuple[str, str]:
        """
        提取学历要求

        Args:
            text: 岗位描述文本

        Returns:
            (学历要求，学历偏好)
        """
        education_required = "不限"
        education_preference = ""

        # 优先查找明确要求
        match = re.search(self.education_require_pattern, text)
        if match:
            education_required = match.group(1)
        else:
            # 查找一般要求
            matches = re.findall(self.education_pattern, text)
            if matches:
                # 取最高学历要求
                max_level = -1
                for edu in matches:
                    level = self.EDUCATION_LEVELS.get(edu, 0)
                    if level > max_level:
                        max_level = level
                        education_required = edu

        # 查找优先条件
        if '985' in text or '211' in text or '双一流' in text:
            education_preference = "985/211/双一流高校优先"
        elif '硕士优先' in text or '研究生优先' in text:
            education_preference = "硕士及以上优先"
        elif '本科优先' in text:
            education_preference = "本科及以上优先"

        return education_required, education_preference

    def extract_work_years(self, text: str) -> Tuple[int, str]:
        """
        提取工作年限要求

        Args:
            text: 岗位描述文本

        Returns:
            (最低工作年限，偏好工作年限范围)
        """
        min_years = 0
        preferred_range = "不限"

        # 查找年限范围
        range_match = re.search(self.year_range_pattern, text)
        if range_match:
            min_years = int(range_match.group(1))
            preferred_range = f"{range_match.group(1)}-{range_match.group(2)}年"
        else:
            # 查找最低年限
            match = re.search(self.year_pattern, text)
            if match:
                min_years = int(float(match.group(1)))
                preferred_range = f"{min_years}年以上"

        # 特殊处理
        if '应届' in text or '应届生' in text or '应届毕业生' in text:
            min_years = 0
            preferred_range = "应届生或 1 年以内"
        elif '不限' in text or '无要求' in text:
            min_years = 0
            preferred_range = "不限"

        return min_years, preferred_range

    def extract_industry(self, text: str) -> str:
        """
        提取行业经验要求

        Args:
            text: 岗位描述文本

        Returns:
            行业名称
        """
        # 统计各行业关键词出现次数
        industry_scores = {}
        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                industry_scores[industry] = score

        if not industry_scores:
            return "不限"

        # 返回得分最高的行业
        best_industry = max(industry_scores, key=industry_scores.get)
        return best_industry

    def extract_skills(self, text: str) -> Tuple[List[str], List[str]]:
        """
        提取技能要求

        Args:
            text: 岗位描述文本

        Returns:
            (核心技能列表，软技能列表)
        """
        core_skills = []
        soft_skills = []

        # 提取硬技能（从技能关键词段落）
        skill_sections = re.split(r'任职要求|岗位要求|职位要求|技能要求|任职资格', text)
        if len(skill_sections) > 1:
            requirement_text = skill_sections[1]
        else:
            requirement_text = text

        # 常见硬技能模式
        skill_patterns = [
            r'熟悉\s*([\u4e00-\u9fa5A-Z0-9,，、\s]+?)(?:[,.。；;]|$)',
            r'精通\s*([\u4e00-\u9fa5A-Z0-9,，、\s]+?)(?:[,.。；;]|$)',
            r'掌握\s*([\u4e00-\u9fa5A-Z0-9,，、\s]+?)(?:[,.。；;]|$)',
            r'擅长\s*([\u4e00-\u9fa5A-Z0-9,，、\s]+?)(?:[,.。；;]|$)',
            r'具备\s*([\u4e00-\u9fa5A-Z0-9,，、\s]+?)(?:经验 | 能力 | 技能)(?:[,.。；;]|$)',
        ]

        for pattern in skill_patterns:
            matches = re.findall(pattern, requirement_text)
            for match in matches:
                # 分割多个技能
                skills = re.split(r'[,，、\s]', match)
                for skill in skills:
                    skill = skill.strip()
                    if skill and len(skill) >= 2 and len(skill) <= 30:
                        # 排除软技能
                        if skill not in self.SOFT_SKILLS_LIBRARY and not any(s in skill for s in ['能力', '技巧']):
                            core_skills.append(skill)

        # 提取软技能
        for soft_skill in self.SOFT_SKILLS_LIBRARY:
            if soft_skill in text:
                soft_skills.append(soft_skill)

        # 去重
        core_skills = list(dict.fromkeys(core_skills))
        soft_skills = list(dict.fromkeys(soft_skills))

        return core_skills[:15], soft_skills[:10]

    def extract_management_responsibility(self, text: str) -> Dict:
        """
        提取管理职责信息

        Args:
            text: 岗位描述文本

        Returns:
            管理职责字典
        """
        result = {
            'has_team_management': False,
            'team_size': None,
            'management_level': None
        }

        # 判断是否有管理职责
        management_keywords = ['管理', '带领', '负责团队', '团队建设', '下属', '汇报']
        if any(keyword in text for keyword in management_keywords):
            result['has_team_management'] = True

        # 提取管理层级
        for level, keywords in self.MANAGEMENT_LEVELS.items():
            if any(keyword in text for keyword in keywords):
                result['management_level'] = level
                break

        # 提取团队规模
        team_match = re.search(self.team_size_pattern, text)
        if team_match:
            result['team_size'] = f"{team_match.group(1)}-{team_match.group(2)}人"
        else:
            team_match = re.search(self.team_manage_pattern, text)
            if team_match:
                result['team_size'] = team_match.group(1).strip()

        return result

    def extract_responsibilities(self, text: str) -> List[str]:
        """
        提取关键职责

        Args:
            text: 岗位描述文本

        Returns:
            职责列表
        """
        responsibilities = []

        # 查找职责部分
        resp_patterns = [
            r'岗位职责?[:：](.*?)(?:任职要求 | 岗位要求 | 职位要求|$)',
            r'工作职责?[:：](.*?)(?:任职要求 | 岗位要求 | 职位要求|$)',
            r'主要职责[:：](.*?)(?:任职要求 | 岗位要求 | 职位要求|$)',
        ]

        for pattern in resp_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                resp_text = match.group(1)
                # 按行分割
                lines = resp_text.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # 清理行首的编号或符号
                    line = re.sub(r'^[\d\.．\-\*•●]\s*', '', line)
                    if line and len(line) > 5:
                        responsibilities.append(line)
                break

        # 如果没有找到，尝试从整个文本提取
        if not responsibilities:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if any(keyword in line for keyword in ['负责', '承担', '主导', '参与', '完成']):
                    line = re.sub(r'^[\d\.．\-\*•●]\s*', '', line)
                    if len(line) > 10 and len(line) < 200:
                        responsibilities.append(line)

        return responsibilities[:10]

    def extract_preferred_qualifications(self, text: str) -> List[str]:
        """
        提取优先条件

        Args:
            text: 岗位描述文本

        Returns:
            优先条件列表
        """
        preferred = []

        # 查找优先条件
        patterns = [
            r'优先[:：\s]*([\u4e00-\u9fa5A-Z，、\s]+?)(?:[,.。；;]|$)',
            r'有 [.．\s]*(?:经验 | 背景|经历)\s*者优先',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match and len(match.strip()) > 1:
                    preferred.append(match.strip())

        # 特殊处理常见优先条件
        if '985' in text or '211' in text:
            preferred.append("985/211 高校毕业优先")
        if '世界 500 强' in text:
            preferred.append("世界 500 强企业经验优先")
        if '同行业' in text:
            preferred.append("同行业经验优先")
        if '海外' in text or '留学' in text:
            preferred.append("海外留学经历优先")

        return list(dict.fromkeys(preferred))[:5]

    def extract_salary(self, text: str) -> Optional[Dict]:
        """
        提取薪资范围

        Args:
            text: 岗位描述文本

        Returns:
            薪资范围字典，如无则返回 None
        """
        match = re.search(self.salary_pattern, text)
        if match:
            min_val = float(match.group(1))
            min_unit = match.group(2).lower()
            max_val = float(match.group(3))
            max_unit = match.group(4).lower() if match.group(4) else min_unit

            # 统一转换为元/月
            unit_mapping = {'k': 1000, '千': 1000, '万': 10000}
            min_salary = int(min_val * unit_mapping.get(min_unit, 1))
            max_salary = int(max_val * unit_mapping.get(max_unit, 1))

            return {
                'min': min_salary,
                'max': max_salary,
                'unit': '元/月'
            }

        return None

    def extract(self, job_description: str, requirements: str = "") -> Dict:
        """
        提取完整的岗位画像

        Args:
            job_description: 岗位描述文本
            requirements: 任职要求文本（可选）

        Returns:
            结构化岗位画像字典
        """
        # 合并文本
        full_text = job_description + "\n" + (requirements or "")

        if self.verbose:
            print("="*60)
            print("开始抽取岗位画像...")
            print("="*60)

        # 提取各字段
        job_title = self.extract_job_title(full_text)
        education_required, education_preference = self.extract_education(full_text)
        min_work_years, preferred_work_years = self.extract_work_years(full_text)
        industry = self.extract_industry(full_text)
        core_skills, soft_skills = self.extract_skills(full_text)
        management_resp = self.extract_management_responsibility(full_text)
        responsibilities = self.extract_responsibilities(full_text)
        preferred_qualifications = self.extract_preferred_qualifications(full_text)
        salary_range = self.extract_salary(full_text)

        profile = {
            'job_title': job_title,
            'industry': industry,
            'education_required': education_required,
            'education_preference': education_preference,
            'min_work_years': min_work_years,
            'preferred_work_years': preferred_work_years,
            'core_skills': core_skills,
            'soft_skills': soft_skills,
            'industry_experience': industry,
            'management_responsibility': management_resp,
            'key_responsibilities': responsibilities,
            'preferred_qualifications': preferred_qualifications,
            'salary_range': salary_range
        }

        if self.verbose:
            print(f"\n岗位名称：{job_title}")
            print(f"所属行业：{industry}")
            print(f"学历要求：{education_required}")
            print(f"工作年限：{min_work_years}年")
            print(f"核心技能：{len(core_skills)}个")
            print(f"软技能：{len(soft_skills)}个")
            print(f"管理职责：{'有' if management_resp['has_team_management'] else '无'}")
            print("\n[OK] 岗位画像抽取完成！")
            print("="*60)

        return profile

    def extract_from_file(self, file_path: str) -> Dict:
        """
        从文件读取岗位描述并抽取画像

        Args:
            file_path: 文件路径（支持.txt 格式）

        Returns:
            结构化岗位画像字典
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在：{file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return self.extract(content)

    def save_profile(self, profile: Dict, output_path: str) -> None:
        """
        保存岗位画像到 JSON 文件

        Args:
            profile: 岗位画像字典
            output_path: 输出文件路径
        """
        import json
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

        if self.verbose:
            print(f"[OK] 岗位画像已保存到：{output_path}")


if __name__ == '__main__':
    # 测试示例
    test_jd = """
    招聘岗位：电商运营总监

    岗位职责：
    1. 负责公司电商平台的整体运营规划和管理
    2. 制定运营策略，提升 GMV 和 ROI
    3. 管理运营团队，带领 10-20 人团队完成业绩目标
    4. 负责淘宝、天猫店铺的日常运营管理
    5. 策划营销活动，提升转化率和客单价

    任职要求：
    1. 本科及以上学历，985/211 高校优先
    2. 5-8 年电商运营经验，3 年以上团队管理经验
    3. 熟悉淘宝、天猫、京东等电商平台运营规则
    4. 精通数据分析优化及营销活动的策划
    5. 具备优秀的沟通能力、团队协作能力和领导力
    6. 有世界 500 强企业经验者优先

    薪资范围：30K-50K/月
    """

    extractor = JobProfileExtractor(verbose=True)
    profile = extractor.extract(test_jd)
    
    import json
    print("\n提取结果:")
    print(json.dumps(profile, ensure_ascii=False, indent=2))
