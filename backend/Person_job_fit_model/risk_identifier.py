# -*- coding: utf-8 -*-
"""
风险识别模块

功能：
1. 识别候选人简历中的各类风险因素
2. 量化风险等级（高/中/低）
3. 生成风险标签和风险评估报告

风险维度：
- 跳槽频率风险 (RISK_JOB_HOPPING)
- 岗位跨度风险 (RISK_CAREER_GAP)
- 行业偏离风险 (RISK_INDUSTRY_SWITCH)
- 技能缺口风险 (RISK_SKILL_GAP)
- 成果表达不足风险 (RISK_WEAK_ACHIEVEMENT)
- 空窗期风险 (RISK_EMPLOYMENT_GAP)

输出格式：
{
    "risk_level": str,              # 综合风险等级（高/中/低）
    "risk_score": float,            # 风险得分（0-10，越高越危险）
    "risk_factors": List[Dict],     # 风险因素列表
    "risk_tags": List[str],         # 风险标签
    "details": Dict                 # 各维度风险详情
}
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime


class RiskIdentifier:
    """风险识别器"""

    # 风险标签常量
    RISK_JOB_HOPPING = "RISK_JOB_HOPPING"           # 跳槽频繁
    RISK_CAREER_GAP = "RISK_CAREER_GAP"             # 岗位跨度大
    RISK_INDUSTRY_SWITCH = "RISK_INDUSTRY_SWITCH"   # 行业偏离
    RISK_SKILL_GAP = "RISK_SKILL_GAP"               # 技能缺口
    RISK_WEAK_ACHIEVEMENT = "RISK_WEAK_ACHIEVEMENT" # 成果表达不足
    RISK_EMPLOYMENT_GAP = "RISK_EMPLOYMENT_GAP"     # 空窗期长

    # 风险阈值配置（可按需调整）
    RISK_THRESHOLDS = {
        'job_hopping': {
            'high': {'jobs_per_5years': 3, 'avg_tenure_months': 18},      # 高风险：5 年 3 跳 或 平均<18 月
            'medium': {'jobs_per_5years': 2, 'avg_tenure_months': 24}     # 中风险：5 年 2 跳 或 平均<24 月
        },
        'career_gap': {
            'high': {'distinct_functions': 3},    # 高风险：跨 3 个以上职能
            'medium': {'distinct_functions': 2}   # 中风险：跨 2 个职能
        },
        'industry_switch': {
            'high': {'distinct_industries': 3},   # 高风险：跨 3 个以上行业
            'medium': {'distinct_industries': 2}  # 中风险：跨 2 个行业
        },
        'employment_gap': {
            'high': {'max_gap_months': 6},    # 高风险：空窗期>6 月
            'medium': {'max_gap_months': 3}   # 中风险：空窗期>3 月
        }
    }

    # 职能分类映射
    FUNCTION_CATEGORIES = {
        '技术/研发': ['工程师', '开发', '研发', '技术', '架构', '算法', '测试', '运维', '产品'],
        '运营/电商': ['运营', '电商', '淘宝', '天猫', '用户运营', '内容运营'],
        '市场/品牌': ['市场', '品牌', '推广', '营销', '广告', '公关', '媒体'],
        '销售/业务': ['销售', '业务', '渠道', '客户', '商务', '招商', '外贸'],
        '生产/制造': ['生产', '制造', '质量', '工艺', '车间', '厂长', '精益'],
        '人力资源': ['人力', 'HR', '招聘', '培训', '薪酬', '绩效', '员工关系'],
        '财务/金融': ['财务', '会计', '审计', '金融', '投资', '资金'],
        '行政/管理': ['行政', '总务', '秘书', '助理', '管理', '总经理'],
        '供应链/采购': ['采购', '供应链', '物流', '仓储', '物料']
    }

    # 成果量化关键词
    ACHIEVEMENT_METRIC_KEYWORDS = [
        '%', '增长', '提升', '提高', '增加', '扩大',
        '降低', '减少', '下降', '缩减', '节约',
        '万', '亿', 'K', '千', '百万',
        '人', '团队', '规模', '人数',
        '倍', '倍率', '翻倍',
        'ROI', 'GMV', 'DAU', 'MAU', 'ARPU'
    ]

    def __init__(self, thresholds: Optional[Dict] = None, verbose: bool = True):
        """
        初始化风险识别器

        Args:
            thresholds: 自定义风险阈值（可选），如 None 则使用默认阈值
            verbose: 是否打印详细输出
        """
        self.verbose = verbose
        self.thresholds = thresholds if thresholds else self.RISK_THRESHOLDS.copy()

    def identify_job_hopping_risk(self, resume: Dict) -> Tuple[str, int, Dict]:
        """
        识别跳槽频率风险

        Args:
            resume: 简历字典

        Returns:
            (风险等级，风险分数 0-10, 详情字典)
        """
        work_experiences = resume.get('work_experiences', [])
        work_duration_months = resume.get('work_duration_months', 0)

        if not work_experiences:
            return "低", 1, {
                'n_jobs': 0,
                'work_years': 0,
                'jobs_per_5years': 0,
                'avg_tenure_months': 0,
                'risk_level': "低"
            }

        n_jobs = len(work_experiences)
        work_years = work_duration_months / 12.0 if work_duration_months > 0 else n_jobs * 2

        # 计算最近 5 年的跳槽次数
        recent_years = min(work_years, 5)
        jobs_per_5years = n_jobs / max(recent_years, 1) * 5

        # 计算平均任期
        avg_tenure_months = work_duration_months / n_jobs if n_jobs > 0 else 0

        # 风险评估
        risk_level = "低"
        risk_score = 1

        if jobs_per_5years > self.thresholds['job_hopping']['high']['jobs_per_5years'] or \
           avg_tenure_months < self.thresholds['job_hopping']['high']['avg_tenure_months']:
            risk_level = "高"
            risk_score = 8
        elif jobs_per_5years > self.thresholds['job_hopping']['medium']['jobs_per_5years'] or \
             avg_tenure_months < self.thresholds['job_hopping']['medium']['avg_tenure_months']:
            risk_level = "中"
            risk_score = 5
        else:
            risk_score = 2

        details = {
            'n_jobs': n_jobs,
            'work_years': round(work_years, 1),
            'jobs_per_5years': round(jobs_per_5years, 2),
            'avg_tenure_months': round(avg_tenure_months, 1),
            'risk_level': risk_level,
            'risk_score': risk_score
        }

        return risk_level, risk_score, details

    def identify_career_gap_risk(self, resume: Dict) -> Tuple[str, int, Dict]:
        """
        识别岗位跨度风险

        Args:
            resume: 简历字典

        Returns:
            (风险等级，风险分数 0-10, 详情字典)
        """
        positions = resume.get('entities', {}).get('positions', [])
        work_experiences = resume.get('work_experiences', [])

        if not positions and not work_experiences:
            return "低", 1, {
                'distinct_functions': 0,
                'functions': [],
                'risk_level': "低"
            }

        # 提取所有职位，分类到职能
        all_positions = positions.copy()
        for exp in work_experiences:
            pos = exp.get('position', '')
            if pos and pos not in all_positions:
                all_positions.append(pos)

        # 职能分类
        functions_detected = set()
        for position in all_positions:
            for func_name, keywords in self.FUNCTION_CATEGORIES.items():
                if any(keyword in position for keyword in keywords):
                    functions_detected.add(func_name)
                    break

        # 如果没有匹配到任何职能，默认为 1 个
        if not functions_detected:
            functions_detected = {'其他'}

        distinct_functions = len(functions_detected)

        # 风险评估
        risk_level = "低"
        risk_score = 1

        if distinct_functions >= self.thresholds['career_gap']['high']['distinct_functions']:
            risk_level = "高"
            risk_score = 8
        elif distinct_functions >= self.thresholds['career_gap']['medium']['distinct_functions']:
            risk_level = "中"
            risk_score = 5
        else:
            risk_score = 2

        details = {
            'distinct_functions': distinct_functions,
            'functions': list(functions_detected),
            'all_positions': all_positions[:10],
            'risk_level': risk_level,
            'risk_score': risk_score
        }

        return risk_level, risk_score, details

    def identify_industry_switch_risk(self, resume: Dict) -> Tuple[str, int, Dict]:
        """
        识别行业偏离风险

        Args:
            resume: 简历字典

        Returns:
            (风险等级，风险分数 0-10, 详情字典)
        """
        # 获取简历标注的行业
        resume_industry = resume.get('industry', '未知')

        # 从工作经历中提取公司，推断行业变化
        work_experiences = resume.get('work_experiences', [])
        companies = resume.get('entities', {}).get('companies', [])

        # 简单判断：如果只有 1 个行业标注，风险低
        # 如果有多个行业关键词，风险高
        industries_detected = set()
        if resume_industry and resume_industry != '未知':
            industries_detected.add(resume_industry)

        # 从公司名推断行业（简化版）
        industry_keywords = {
            '电商': ['电商', '淘宝', '天猫', '京东', '拼多多', '跨境'],
            '互联网': ['互联网', '网络', '科技', '信息'],
            '金融': ['银行', '证券', '保险', '金融', '投资'],
            '制造': ['制造', '工厂', '实业', '工业'],
            '零售': ['零售', '商贸', '商业', '购物'],
            '教育': ['教育', '培训', '学校', '学院'],
            '医疗': ['医疗', '医院', '医药', '健康'],
        }

        for company in companies:
            for industry, keywords in industry_keywords.items():
                if any(keyword in company for keyword in keywords):
                    industries_detected.add(industry)
                    break

        distinct_industries = len(industries_detected)

        # 风险评估
        risk_level = "低"
        risk_score = 1

        if distinct_industries >= self.thresholds['industry_switch']['high']['distinct_industries']:
            risk_level = "高"
            risk_score = 7
        elif distinct_industries >= self.thresholds['industry_switch']['medium']['distinct_industries']:
            risk_level = "中"
            risk_score = 4
        else:
            risk_score = 2

        details = {
            'distinct_industries': distinct_industries,
            'industries': list(industries_detected),
            'resume_industry': resume_industry,
            'risk_level': risk_level,
            'risk_score': risk_score
        }

        return risk_level, risk_score, details

    def identify_skill_gap_risk(self, resume: Dict, job_profile: Optional[Dict] = None) -> Tuple[str, int, Dict]:
        """
        识别技能缺口风险

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典（可选，如无则基于简历自身判断）

        Returns:
            (风险等级，风险分数 0-10, 详情字典)
        """
        # 获取候选人技能
        candidate_skills = set(resume.get('entities', {}).get('skills', []))

        if job_profile:
            # 有岗位要求，对比岗位技能
            required_skills = set(job_profile.get('core_skills', []))
            if not required_skills:
                return "低", 1, {
                    'required_skills_count': 0,
                    'candidate_skills_count': len(candidate_skills),
                    'missing_skills': [],
                    'gap_ratio': 0,
                    'risk_level': "低"
                }

            missing_skills = required_skills - candidate_skills
            gap_ratio = len(missing_skills) / len(required_skills) if required_skills else 0
        else:
            # 无岗位要求，基于技能数量判断
            required_skills = set()
            missing_skills = set()
            gap_ratio = 0

            # 如果技能太少，认为有风险
            if len(candidate_skills) < 3:
                gap_ratio = 0.5

        # 风险评估
        risk_level = "低"
        risk_score = 1

        if gap_ratio >= 0.6:  # 缺口>60%
            risk_level = "高"
            risk_score = 8
        elif gap_ratio >= 0.4:  # 缺口>40%
            risk_level = "中"
            risk_score = 5
        else:
            risk_score = 2

        details = {
            'required_skills_count': len(required_skills),
            'candidate_skills_count': len(candidate_skills),
            'missing_skills': list(missing_skills)[:10],
            'gap_ratio': round(gap_ratio, 2),
            'risk_level': risk_level,
            'risk_score': risk_score
        }

        return risk_level, risk_score, details

    def identify_weak_achievement_risk(self, resume: Dict) -> Tuple[str, int, Dict]:
        """
        识别成果表达不足风险

        Args:
            resume: 简历字典

        Returns:
            (风险等级，风险分数 0-10, 详情字典)
        """
        achievements = resume.get('achievements', [])
        work_experiences = resume.get('work_experiences', [])

        # 统计量化成果数量
        quantified_achievements = 0
        total_descriptions = 0

        # 检查 achievements
        for achievement in achievements:
            original_text = achievement.get('original_text', '')
            if any(keyword in original_text for keyword in self.ACHIEVEMENT_METRIC_KEYWORDS):
                quantified_achievements += 1

        # 检查工作职责描述
        for exp in work_experiences:
            responsibilities = exp.get('responsibilities', [])
            if isinstance(responsibilities, list):
                resp_texts = responsibilities
            else:
                resp_texts = [str(responsibilities)]

            for resp in resp_texts:
                total_descriptions += 1
                if any(keyword in resp for keyword in self.ACHIEVEMENT_METRIC_KEYWORDS):
                    quantified_achievements += 1

        # 计算量化比例
        total_items = len(achievements) + total_descriptions
        if total_items == 0:
            quantified_ratio = 0
        else:
            quantified_ratio = quantified_achievements / total_items

        # 风险评估
        risk_level = "低"
        risk_score = 1

        if quantified_ratio < 0.3:  # <30% 量化
            risk_level = "高"
            risk_score = 7
        elif quantified_ratio < 0.6:  # 30-60% 量化
            risk_level = "中"
            risk_score = 4
        else:
            risk_score = 2

        details = {
            'total_achievements': len(achievements),
            'quantified_achievements': quantified_achievements,
            'total_descriptions': total_descriptions,
            'quantified_ratio': round(quantified_ratio, 2),
            'risk_level': risk_level,
            'risk_score': risk_score
        }

        return risk_level, risk_score, details

    def identify_employment_gap_risk(self, resume: Dict) -> Tuple[str, int, Dict]:
        """
        识别空窗期风险

        Args:
            resume: 简历字典

        Returns:
            (风险等级，风险分数 0-10, 详情字典)
        """
        work_experiences = resume.get('work_experiences', [])
        gap_periods = resume.get('gap_periods', [])

        if not work_experiences:
            return "低", 1, {
                'max_gap_months': 0,
                'total_gap_months': 0,
                'n_gaps': 0,
                'risk_level': "低"
            }

        # 如果有 gap_periods 直接使用
        if gap_periods:
            max_gap = max(gap.get('duration_months', 0) for gap in gap_periods)
            total_gap = sum(gap.get('duration_months', 0) for gap in gap_periods)
            n_gaps = len(gap_periods)
        else:
            # 简单估算：从工作时间推断
            # 假设简历覆盖了从第一份工作到现在的时间
            work_duration = resume.get('work_duration_months', 0)

            # 计算工作经历的总时长
            total_work_months = 0
            for exp in work_experiences:
                time_period = exp.get('time_period', '')
                # 这里简化处理，实际应该解析时间
                total_work_months += 24  # 假设平均每份工作时间

            # 空窗期 = 总时长 - 工作时长
            if work_duration > 0:
                estimated_gap = max(0, work_duration - total_work_months)
            else:
                estimated_gap = 0

            max_gap = estimated_gap
            total_gap = estimated_gap
            n_gaps = 1 if estimated_gap > 3 else 0

        # 风险评估
        risk_level = "低"
        risk_score = 1

        if max_gap > self.thresholds['employment_gap']['high']['max_gap_months']:
            risk_level = "高"
            risk_score = 8
        elif max_gap > self.thresholds['employment_gap']['medium']['max_gap_months']:
            risk_level = "中"
            risk_score = 5
        else:
            risk_score = 2

        details = {
            'max_gap_months': round(max_gap, 1),
            'total_gap_months': round(total_gap, 1),
            'n_gaps': n_gaps,
            'risk_level': risk_level,
            'risk_score': risk_score
        }

        return risk_level, risk_score, details

    def identify(self, resume: Dict, job_profile: Optional[Dict] = None) -> Dict:
        """
        综合风险识别（主方法）

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典（可选）

        Returns:
            风险识别结果字典（JSON 格式）
        """
        if self.verbose:
            print("\n" + "="*60)
            print("开始风险识别...")
            print("="*60)
            candidate_name = resume.get('basic_info', {}).get('name', '未知')
            print(f"\n候选人：{candidate_name}")

        # 各维度风险识别
        job_hop_level, job_hop_score, job_hop_details = self.identify_job_hopping_risk(resume)
        career_gap_level, career_gap_score, career_gap_details = self.identify_career_gap_risk(resume)
        industry_switch_level, industry_switch_score, industry_switch_details = self.identify_industry_switch_risk(resume)
        skill_gap_level, skill_gap_score, skill_gap_details = self.identify_skill_gap_risk(resume, job_profile)
        weak_achieve_level, weak_achieve_score, weak_achieve_details = self.identify_weak_achievement_risk(resume)
        employ_gap_level, employ_gap_score, employ_gap_details = self.identify_employment_gap_risk(resume)

        # 收集风险因素
        risk_factors = []
        risk_tags = []

        # 跳槽风险
        if job_hop_level in ["高", "中"]:
            risk_factors.append({
                'type': '跳槽频率',
                'level': job_hop_level,
                'score': job_hop_score,
                'tag': self.RISK_JOB_HOPPING,
                'description': f"5 年内跳槽{job_hop_details['jobs_per_5years']:.1f}次，平均任期{job_hop_details['avg_tenure_months']:.1f}个月"
            })
            risk_tags.append(self.RISK_JOB_HOPPING)

        # 岗位跨度风险
        if career_gap_level in ["高", "中"]:
            risk_factors.append({
                'type': '岗位跨度',
                'level': career_gap_level,
                'score': career_gap_score,
                'tag': self.RISK_CAREER_GAP,
                'description': f"跨{career_gap_details['distinct_functions']}个职能领域：{', '.join(career_gap_details['functions'])}"
            })
            risk_tags.append(self.RISK_CAREER_GAP)

        # 行业偏离风险
        if industry_switch_level in ["高", "中"]:
            risk_factors.append({
                'type': '行业偏离',
                'level': industry_switch_level,
                'score': industry_switch_score,
                'tag': self.RISK_INDUSTRY_SWITCH,
                'description': f"跨{industry_switch_details['distinct_industries']}个行业：{', '.join(industry_switch_details['industries'])}"
            })
            risk_tags.append(self.RISK_INDUSTRY_SWITCH)

        # 技能缺口风险
        if skill_gap_level in ["高", "中"]:
            risk_factors.append({
                'type': '技能缺口',
                'level': skill_gap_level,
                'score': skill_gap_score,
                'tag': self.RISK_SKILL_GAP,
                'description': f"缺少{len(skill_gap_details['missing_skills'])}个核心技能，缺口率{skill_gap_details['gap_ratio']:.0%}"
            })
            risk_tags.append(self.RISK_SKILL_GAP)

        # 成果表达不足风险
        if weak_achieve_level in ["高", "中"]:
            risk_factors.append({
                'type': '成果表达不足',
                'level': weak_achieve_level,
                'score': weak_achieve_score,
                'tag': self.RISK_WEAK_ACHIEVEMENT,
                'description': f"量化成果占比{weak_achieve_details['quantified_ratio']:.0%}"
            })
            risk_tags.append(self.RISK_WEAK_ACHIEVEMENT)

        # 空窗期风险
        if employ_gap_level in ["高", "中"]:
            risk_factors.append({
                'type': '空窗期',
                'level': employ_gap_level,
                'score': employ_gap_score,
                'tag': self.RISK_EMPLOYMENT_GAP,
                'description': f"最长空窗期{employ_gap_details['max_gap_months']:.1f}个月，共{employ_gap_details['n_gaps']}段"
            })
            risk_tags.append(self.RISK_EMPLOYMENT_GAP)

        # 综合风险评估
        total_score = (
            job_hop_score + career_gap_score + industry_switch_score +
            skill_gap_score + weak_achieve_score + employ_gap_score
        )
        avg_score = total_score / 6.0

        # 高风险标签数量
        n_high_risks = sum(1 for level in [job_hop_level, career_gap_level, industry_switch_level,
                                            skill_gap_level, weak_achieve_level, employ_gap_level]
                          if level == "高")

        n_medium_risks = sum(1 for level in [job_hop_level, career_gap_level, industry_switch_level,
                                              skill_gap_level, weak_achieve_level, employ_gap_level]
                            if level == "中")

        # 综合风险等级判定
        if n_high_risks >= 2 or avg_score >= 7:
            overall_level = "高"
            overall_comment = "存在多项高风险因素，建议谨慎评估"
        elif n_high_risks >= 1 or n_medium_risks >= 2 or avg_score >= 5:
            overall_level = "中"
            overall_comment = "存在一定风险因素，建议重点关注"
        else:
            overall_level = "低"
            overall_comment = "风险因素较少，整体稳定"

        result = {
            'overall_risk_level': overall_level,
            'overall_risk_score': round(avg_score, 2),
            'risk_comment': overall_comment,
            'risk_factors': risk_factors,
            'risk_tags': risk_tags,
            'n_high_risks': n_high_risks,
            'n_medium_risks': n_medium_risks,
            'details': {
                'job_hopping_details': job_hop_details,
                'career_gap_details': career_gap_details,
                'industry_switch_details': industry_switch_details,
                'skill_gap_details': skill_gap_details,
                'weak_achievement_details': weak_achieve_details,
                'employment_gap_details': employ_gap_details
            }
        }

        if self.verbose:
            print(f"\n各维度风险等级:")
            print(f"  跳槽频率：{job_hop_level} ({job_hop_score}分)")
            print(f"  岗位跨度：{career_gap_level} ({career_gap_score}分)")
            print(f"  行业偏离：{industry_switch_level} ({industry_switch_score}分)")
            print(f"  技能缺口：{skill_gap_level} ({skill_gap_score}分)")
            print(f"  成果表达：{weak_achieve_level} ({weak_achieve_score}分)")
            print(f"  空窗期：{employ_gap_level} ({employ_gap_score}分)")
            print(f"\n综合风险等级：{overall_level} ({avg_score:.2f}分)")
            print(f"风险标签：{len(risk_tags)}个")
            if risk_tags:
                print(f"  {', '.join(risk_tags)}")
            print("\n[OK] 风险识别完成！")
            print("="*60)

        return result

    def batch_identify(self, resumes: List[Dict], job_profile: Optional[Dict] = None) -> List[Dict]:
        """
        批量风险识别

        Args:
            resumes: 简历列表
            job_profile: 岗位画像字典（可选）

        Returns:
            风险识别结果列表
        """
        results = []
        for resume in resumes:
            result = self.identify(resume, job_profile)
            result['candidate_id'] = resume.get('basic_info', {}).get('name', '未知')
            results.append(result)

        # 按风险得分降序排序（风险高的在前）
        results.sort(key=lambda x: x['overall_risk_score'], reverse=True)

        return results


if __name__ == '__main__':
    # 测试示例
    test_resume = {
        'basic_info': {'name': '李四'},
        'industry': '电商',
        'work_duration_months': 60,
        'entities': {
            'skills': ['电商运营', '数据分析'],
            'positions': ['运营专员', '运营经理', '销售主管'],
            'companies': ['某电商公司', '某科技公司']
        },
        'work_experiences': [
            {
                'position': '运营专员',
                'time_period': '2018/01-2019/12',
                'responsibilities': ['负责店铺日常运营']
            },
            {
                'position': '运营经理',
                'time_period': '2020/01-2021/06',
                'responsibilities': ['带领团队完成 GMV 增长 50%']
            },
            {
                'position': '销售主管',
                'time_period': '2021/07-2023/01',
                'responsibilities': ['开拓新客户']
            }
        ],
        'achievements': [
            {'original_text': 'GMV 增长 50%'},
            {'original_text': '负责日常运营工作'}
        ]
    }

    identifier = RiskIdentifier(verbose=True)
    result = identifier.identify(test_resume)

    import json
    print("\n风险识别结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
