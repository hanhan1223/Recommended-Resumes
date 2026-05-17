# -*- coding: utf-8 -*-
"""
潜力评估模块

功能：
1. 评估候选人的成长潜力和发展空间
2. 从职业发展连续性、职责提升、项目复杂度、学习能力等维度分析
3. 区分人才类型：高潜力人才、成长型人才、即战力人才、待观察

评估维度：
- 职业发展连续性 (career_continuity)
- 职责提升轨迹 (responsibility_growth)
- 项目复杂度 (project_complexity)
- 学习能力 (learning_ability)
- 公司平台跃迁 (company_platform_growth)

输出格式：
{
    "talent_type": str,              # 人才类型（高潜力/成长型/即战力/待观察）
    "potential_score": float,        # 潜力得分（0-10）
    "potential_comment": str,        # 潜力评语
    "dimension_scores": Dict,        # 各维度得分
    "details": Dict                  # 详细分析
}
"""

import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime


class PotentialEvaluator:
    """潜力评估器"""

    # 人才类型常量
    TALENT_HIGH_POTENTIAL = "高潜力人才"      # 高潜力 + 高成长
    TALENT_GROWTH = "成长型人才"             # 稳定成长
    TALENT_IMMEDIATE = "即战力人才"          # 当前能力强但成长放缓
    TALENT_OBSERVE = "待观察"               # 各项指标较低

    # 职位层级映射（从低到高）
    POSITION_LEVELS = {
        '专员/助理': 1,
        '初级': 1,
        '中级': 2,
        '高级': 3,
        '资深': 4,
        '专家': 5,
        '主管': 6,
        '经理': 7,
        '高级经理': 8,
        '总监': 9,
        '副总裁': 10,
        '总裁': 11,
        'CEO/总经理': 12,
        '合伙人': 13,
        '创始人': 14
    }

    # 职位层级关键词
    POSITION_LEVEL_KEYWORDS = {
        '专员/助理': ['专员', '助理', '秘书', '文员', '代表'],
        '初级': ['初级', '应届', '实习'],
        '中级': ['中级'],
        '高级': ['高级', 'Senior'],
        '资深': ['资深', 'Staff'],
        '专家': ['专家', 'Expert'],
        '主管': ['主管', '组长', 'Team Leader'],
        '经理': ['经理', 'Manager', '部门负责人'],
        '高级经理': ['高级经理', 'Senior Manager'],
        '总监': ['总监', 'Director', 'Head'],
        '副总裁': ['副总裁', 'VP', '副总经理'],
        '总裁': ['总裁', '总经理', 'CEO', 'COO'],
        '合伙人': ['合伙人', 'Partner'],
        '创始人': ['创始人', 'Co-founder', '董事长']
    }

    # 证书库（小型，按行业分类）
    CERTIFICATE_LIBRARY = {
        '电商': [
            {'name': '阿里巴巴电商运营师', 'level': 3},
            {'name': 'Google Analytics 认证', 'level': 3},
            {'name': 'Facebook Blueprint 认证', 'level': 3},
            {'name': '数据分析师', 'level': 4},
        ],
        '品牌': [
            {'name': '品牌管理师', 'level': 4},
            {'name': '数字营销师', 'level': 3},
            {'name': '广告师', 'level': 3},
            {'name': 'CMO 认证', 'level': 5},
        ],
        '销售': [
            {'name': '销售管理师', 'level': 3},
            {'name': '谈判师', 'level': 3},
            {'name': '客户关系管理师', 'level': 3},
        ],
        '研发': [
            {'name': 'PMP 项目管理', 'level': 5},
            {'name': '系统架构师', 'level': 5},
            {'name': '云计算认证', 'level': 4},
            {'name': 'AI 工程师', 'level': 4},
            {'name': '专利代理人', 'level': 5},
        ],
        '生产': [
            {'name': '精益生产师', 'level': 4},
            {'name': '六西格玛黑带', 'level': 5},
            {'name': '质量管理师', 'level': 4},
            {'name': '安全工程师', 'level': 3},
        ],
        '人力资源': [
            {'name': '人力资源管理师', 'level': 4},
            {'name': '心理咨询师', 'level': 3},
            {'name': '薪酬管理师', 'level': 3},
            {'name': 'SHRM 认证', 'level': 5},
        ],
        '通用': [
            {'name': 'MBA', 'level': 5},
            {'name': 'EMBA', 'level': 6},
            {'name': '注册会计师 CPA', 'level': 5},
            {'name': '特许金融分析师 CFA', 'level': 5},
            {'name': '法律职业资格', 'level': 5},
        ]
    }

    # 公司评级映射（简化版）
    COMPANY_LEVELS = {
        '世界 500 强': 5,
        '上市公司': 4,
        '大型企业': 4,
        '中型企业': 3,
        '小型企业': 2,
        '初创公司': 1
    }

    def __init__(self, verbose: bool = True):
        """
        初始化潜力评估器

        Args:
            verbose: 是否打印详细输出
        """
        self.verbose = verbose

    def evaluate_career_continuity(self, resume: Dict) -> Tuple[float, Dict]:
        """
        评估职业发展连续性

        Args:
            resume: 简历字典

        Returns:
            (得分 0-10, 详情字典)
        """
        work_experiences = resume.get('work_experiences', [])

        if not work_experiences:
            return 5.0, {
                'n_positions': 0,
                'has_promotion': False,
                'career_stability': '未知',
                'score': 5.0
            }

        # 分析职位变化
        positions = [exp.get('position', '') for exp in work_experiences]
        companies = [exp.get('company', '') for exp in work_experiences]

        # 判断是否有晋升
        has_promotion = False
        promotion_count = 0

        for i in range(1, len(positions)):
            prev_pos = positions[i-1]
            curr_pos = positions[i]

            # 提取职位层级
            prev_level = self._get_position_level(prev_pos)
            curr_level = self._get_position_level(curr_pos)

            if curr_level > prev_level:
                has_promotion = True
                promotion_count += 1

        # 计算职业稳定性（同一家公司的工作时长）
        company_changes = sum(1 for i in range(1, len(companies)) if companies[i] != companies[i-1])
        avg_tenure = len(work_experiences) / max(company_changes + 1, 1)

        # 评分逻辑
        score = 5.0  # 基础分

        # 有晋升加分
        if has_promotion:
            score += min(promotion_count * 1.5, 3.0)

        # 稳定性适中加分（2-4 年最佳）
        if 2 <= avg_tenure <= 4:
            score += 1.0
        elif avg_tenure > 4:
            score += 0.5

        # 频繁跳槽扣分
        if company_changes >= 4:
            score -= 2.0
        elif company_changes >= 2:
            score -= 1.0

        score = max(0, min(score, 10))

        details = {
            'n_positions': len(positions),
            'has_promotion': has_promotion,
            'promotion_count': promotion_count,
            'company_changes': company_changes,
            'avg_tenure_years': round(avg_tenure, 1),
            'career_stability': '稳定' if avg_tenure >= 2 else '一般',
            'score': round(score, 2)
        }

        return score, details

    def _get_position_level(self, position: str) -> int:
        """获取职位层级"""
        position_lower = position.lower()

        for level_name, keywords in self.POSITION_LEVEL_KEYWORDS.items():
            if any(keyword.lower() in position_lower for keyword in keywords):
                return self.POSITION_LEVELS.get(level_name, 1)

        return 1  # 默认为初级

    def evaluate_responsibility_growth(self, resume: Dict) -> Tuple[float, Dict]:
        """
        评估职责提升轨迹

        Args:
            resume: 简历字典

        Returns:
            (得分 0-10, 详情字典)
        """
        work_experiences = resume.get('work_experiences', [])

        if not work_experiences:
            return 5.0, {
                'has_management_exp': False,
                'team_size_growth': False,
                'scope_expansion': False,
                'score': 5.0
            }

        # 分析管理职责
        has_management_exp = False
        team_sizes = []
        responsibility_keywords = ['负责', '主导', '带领', '管理', '统筹', '规划', '决策']

        for exp in work_experiences:
            responsibilities = exp.get('responsibilities', [])
            if isinstance(responsibilities, list):
                resp_text = ' '.join(str(r) for r in responsibilities)
            else:
                resp_text = str(responsibilities)

            # 检查管理关键词
            if any(keyword in resp_text for keyword in responsibility_keywords):
                has_management_exp = True

            # 提取团队规模
            team_match = re.search(r'(\d+)\s*[-至～]\s*(\d+)\s*人', resp_text)
            if team_match:
                team_sizes.append(int(team_match.group(2)))
            else:
                team_match = re.search(r'(\d+)\s*人', resp_text)
                if team_match:
                    team_sizes.append(int(team_match.group(1)))

        # 判断团队规模增长
        team_size_growth = len(team_sizes) >= 2 and team_sizes[-1] > team_sizes[0]

        # 判断职责范围扩大（简化：基于是否有战略级关键词）
        strategic_keywords = ['战略', '规划', '体系', '制度', '流程', '组织']
        scope_expansion = False
        for exp in work_experiences:
            responsibilities = exp.get('responsibilities', [])
            resp_text = ' '.join(str(r) for r in responsibilities)
            if any(keyword in resp_text for keyword in strategic_keywords):
                scope_expansion = True
                break

        # 评分
        score = 5.0  # 基础分

        if has_management_exp:
            score += 2.0
        if team_size_growth:
            score += 2.0
        if scope_expansion:
            score += 1.0

        # 最近职位有管理职责额外加分
        if work_experiences:
            last_resp = work_experiences[-1].get('responsibilities', [])
            last_text = ' '.join(str(r) for r in last_resp)
            if any(keyword in last_text for keyword in ['管理', '带领', '负责团队']):
                score += 1.0

        score = max(0, min(score, 10))

        details = {
            'has_management_exp': has_management_exp,
            'max_team_size': max(team_sizes) if team_sizes else 0,
            'team_size_growth': team_size_growth,
            'scope_expansion': scope_expansion,
            'score': round(score, 2)
        }

        return score, details

    def evaluate_project_complexity(self, resume: Dict) -> Tuple[float, Dict]:
        """
        评估项目复杂度

        Args:
            resume: 简历字典

        Returns:
            (得分 0-10, 详情字典)
        """
        project_experiences = resume.get('project_experiences', [])

        if not project_experiences:
            return 5.0, {
                'n_projects': 0,
                'has_large_project': False,
                'technical_depth': '未知',
                'score': 5.0
            }

        # 分析项目复杂度
        complexity_indicators = {
            'budget': 0,      # 预算规模
            'team': 0,        # 团队规模
            'tech_stack': 0,  # 技术栈复杂度
            'impact': 0       # 影响力
        }

        budget_keywords = ['万', '亿', '百万', '千万', '预算', '投资']
        team_keywords = ['人团队', '人组成', '带领', '管理']
        tech_keywords = ['架构', '平台', '系统', '框架', '微服务', '分布式', '云']
        impact_keywords = ['核心', '关键', '战略', '重点', '创新', '突破', '行业']

        for project in project_experiences:
            name = project.get('name', '')
            description = project.get('description', [])
            if isinstance(description, list):
                desc_text = ' '.join(str(d) for d in description)
            else:
                desc_text = str(description)

            full_text = name + ' ' + desc_text

            # 预算规模
            if any(keyword in full_text for keyword in budget_keywords):
                complexity_indicators['budget'] += 1

            # 团队规模
            if any(keyword in full_text for keyword in team_keywords):
                complexity_indicators['team'] += 1

            # 技术栈
            if any(keyword in full_text for keyword in tech_keywords):
                complexity_indicators['tech_stack'] += 1

            # 影响力
            if any(keyword in full_text for keyword in impact_keywords):
                complexity_indicators['impact'] += 1

        # 判断是否有大型项目
        has_large_project = any(v >= 2 for v in complexity_indicators.values())

        # 技术深度判断
        technical_depth = '一般'
        if complexity_indicators['tech_stack'] >= 3:
            technical_depth = '深'
        elif complexity_indicators['tech_stack'] >= 1:
            technical_depth = '中等'

        # 评分
        avg_complexity = sum(complexity_indicators.values()) / len(project_experiences)

        score = 5.0  # 基础分
        score += min(avg_complexity * 0.5, 3.0)  # 复杂度加分
        if has_large_project:
            score += 2.0

        score = max(0, min(score, 10))

        details = {
            'n_projects': len(project_experiences),
            'has_large_project': has_large_project,
            'complexity_indicators': complexity_indicators,
            'technical_depth': technical_depth,
            'score': round(score, 2)
        }

        return score, details

    def evaluate_learning_ability(self, resume: Dict) -> Tuple[float, Dict]:
        """
        评估学习能力

        Args:
            resume: 简历字典

        Returns:
            (得分 0-10, 详情字典)
        """
        # 从多个维度评估学习能力
        education_experiences = resume.get('education_experiences', [])
        certifications = resume.get('entities', {}).get('certifications', [])
        skills = resume.get('entities', {}).get('skills', [])
        achievements = resume.get('achievements', [])

        # 1. 学历提升
        degree_improvement = False
        if len(education_experiences) >= 2:
            degrees = [edu.get('degree', '') for edu in education_experiences]
            degree_levels = [self._get_degree_level(d) for d in degrees]
            if len(set(degree_levels)) > 1 and degree_levels[-1] > degree_levels[0]:
                degree_improvement = True

        # 2. 证书获取
        n_certificates = len(certifications)
        high_level_certs = 0
        for cert in certifications:
            cert_name = cert if isinstance(cert, str) else cert.get('name', '')
            for industry, certs in self.CERTIFICATE_LIBRARY.items():
                for cert_info in certs:
                    if cert_info['name'] in cert_name:
                        if cert_info['level'] >= 4:
                            high_level_certs += 1
                        break

        # 3. 技能多样性
        n_skills = len(skills)
        skill_diversity = '丰富' if n_skills >= 10 else '中等' if n_skills >= 5 else '一般'

        # 4. 成就中的学习相关关键词
        learning_keywords = ['学习', '掌握', '熟悉', '研究', '探索', '创新', '优化', '改进']
        learning_achievements = sum(1 for a in achievements
                                   if any(k in a.get('original_text', '') for k in learning_keywords))

        # 评分
        score = 5.0  # 基础分

        if degree_improvement:
            score += 2.0
        score += min(n_certificates * 0.5, 2.0)
        score += min(high_level_certs * 1.0, 2.0)
        if n_skills >= 8:
            score += 1.0
        if learning_achievements >= 2:
            score += 1.0

        score = max(0, min(score, 10))

        details = {
            'degree_improvement': degree_improvement,
            'n_certificates': n_certificates,
            'high_level_certs': high_level_certs,
            'n_skills': n_skills,
            'skill_diversity': skill_diversity,
            'learning_achievements': learning_achievements,
            'score': round(score, 2)
        }

        return score, details

    def _get_degree_level(self, degree: str) -> int:
        """获取学历层级"""
        degree_map = {
            '博士': 5, '博士后': 5,
            '硕士': 4, '研究生': 4,
            '本科': 3, '学士': 3,
            '大专': 2, '专科': 2,
            '高中': 1, '中专': 1, '职高': 1
        }
        return degree_map.get(degree, 1)

    def evaluate_company_platform_growth(self, resume: Dict) -> Tuple[float, Dict]:
        """
        评估公司平台跃迁

        Args:
            resume: 简历字典

        Returns:
            (得分 0-10, 详情字典)
        """
        work_experiences = resume.get('work_experiences', [])
        company_ratings = resume.get('company_ratings', [])

        if not work_experiences:
            return 5.0, {
                'has_platform_growth': False,
                'avg_company_level': 0,
                'score': 5.0
            }

        # 分析公司评级变化
        company_levels = []

        # 使用 company_ratings（如果有）
        if company_ratings:
            for rating in company_ratings:
                company_levels.append(rating.get('rating', 3))
        else:
            # 从公司名称推断
            companies = [exp.get('company', '') for exp in work_experiences]
            for company in companies:
                level = 3  # 默认中型企业
                for keyword, lvl in self.COMPANY_LEVELS.items():
                    if keyword in company:
                        level = lvl
                        break
                company_levels.append(level)

        # 判断是否有平台跃迁
        has_platform_growth = False
        if len(company_levels) >= 2:
            # 最近的公司是否比第一家公司好
            if company_levels[-1] > company_levels[0]:
                has_platform_growth = True

        # 平均公司水平
        avg_company_level = sum(company_levels) / len(company_levels) if company_levels else 0

        # 最大公司水平
        max_company_level = max(company_levels) if company_levels else 0

        # 评分
        score = 5.0  # 基础分

        if has_platform_growth:
            score += 2.0
        score += min(avg_company_level * 0.5, 2.0)
        if max_company_level >= 5:  # 有世界 500 强经验
            score += 1.0

        score = max(0, min(score, 10))

        details = {
            'has_platform_growth': has_platform_growth,
            'avg_company_level': round(avg_company_level, 2),
            'max_company_level': max_company_level,
            'company_levels': company_levels,
            'score': round(score, 2)
        }

        return score, details

    def evaluate(self, resume: Dict) -> Dict:
        """
        综合潜力评估（主方法）

        Args:
            resume: 简历字典

        Returns:
            潜力评估结果字典（JSON 格式）
        """
        if self.verbose:
            print("\n" + "="*60)
            print("开始潜力评估...")
            print("="*60)
            candidate_name = resume.get('basic_info', {}).get('name', '未知')
            print(f"\n候选人：{candidate_name}")

        # 各维度评估
        continuity_score, continuity_details = self.evaluate_career_continuity(resume)
        responsibility_score, responsibility_details = self.evaluate_responsibility_growth(resume)
        project_score, project_details = self.evaluate_project_complexity(resume)
        learning_score, learning_details = self.evaluate_learning_ability(resume)
        platform_score, platform_details = self.evaluate_company_platform_growth(resume)

        # 计算综合潜力得分（加权平均）
        weights = {
            'career_continuity': 0.25,
            'responsibility_growth': 0.25,
            'project_complexity': 0.15,
            'learning_ability': 0.20,
            'company_platform': 0.15
        }

        overall_score = (
            weights['career_continuity'] * continuity_score +
            weights['responsibility_growth'] * responsibility_score +
            weights['project_complexity'] * project_score +
            weights['learning_ability'] * learning_score +
            weights['company_platform'] * platform_score
        )

        # 人才类型划分
        # 高潜力：发展连续性>7 + 学习能力>7 + 项目复杂度>6
        # 成长型：发展连续性>6 + 学习能力>6
        # 即战力：当前能力强（有管理经验 + 大平台）但成长放缓
        # 待观察：各项指标<5

        is_high_potential = (continuity_score >= 7 and learning_score >= 7 and project_score >= 6)
        is_growth = (continuity_score >= 6 and learning_score >= 6) and not is_high_potential
        is_immediate = (responsibility_score >= 7 and platform_score >= 7) and learning_score < 6
        is_observe = (continuity_score < 5 and learning_score < 5)

        if is_high_potential:
            talent_type = self.TALENT_HIGH_POTENTIAL
            comment = "具备优秀的职业发展轨迹和学习能力，成长空间大，建议重点培养"
        elif is_growth:
            talent_type = self.TALENT_GROWTH
            comment = "保持稳定的成长态势，具备良好的发展潜力"
        elif is_immediate:
            talent_type = self.TALENT_IMMEDIATE
            comment = "当前能力强，经验丰富，可立即胜任重要岗位"
        else:
            talent_type = self.TALENT_OBSERVE
            comment = "各项指标表现一般，需要进一步观察和培养"

        result = {
            'talent_type': talent_type,
            'potential_score': round(overall_score, 2),
            'potential_comment': comment,
            'dimension_scores': {
                'career_continuity': round(continuity_score, 2),
                'responsibility_growth': round(responsibility_score, 2),
                'project_complexity': round(project_score, 2),
                'learning_ability': round(learning_score, 2),
                'company_platform_growth': round(platform_score, 2)
            },
            'details': {
                'career_continuity_details': continuity_details,
                'responsibility_growth_details': responsibility_details,
                'project_complexity_details': project_details,
                'learning_ability_details': learning_details,
                'company_platform_details': platform_details
            },
            'weights': weights
        }

        if self.verbose:
            print(f"\n各维度潜力得分:")
            print(f"  职业发展连续性：{continuity_score:.2f}")
            print(f"  职责提升轨迹：{responsibility_score:.2f}")
            print(f"  项目复杂度：{project_score:.2f}")
            print(f"  学习能力：{learning_score:.2f}")
            print(f"  公司平台跃迁：{platform_score:.2f}")
            print(f"\n综合潜力得分：{overall_score:.2f}")
            print(f"人才类型：{talent_type}")
            print(f"评语：{comment}")
            print("\n[OK] 潜力评估完成！")
            print("="*60)

        return result

    def batch_evaluate(self, resumes: List[Dict]) -> List[Dict]:
        """
        批量潜力评估

        Args:
            resumes: 简历列表

        Returns:
            潜力评估结果列表（按潜力得分排序）
        """
        results = []
        for resume in resumes:
            result = self.evaluate(resume)
            result['candidate_id'] = resume.get('basic_info', {}).get('name', '未知')
            results.append(result)

        # 按潜力得分降序排序
        results.sort(key=lambda x: x['potential_score'], reverse=True)

        return results


if __name__ == '__main__':
    # 测试示例
    test_resume = {
        'basic_info': {'name': '王五'},
        'work_duration_months': 84,
        'entities': {
            'skills': ['Python', 'Java', '数据分析', '团队管理', '项目管理'],
            'certifications': ['PMP', '系统架构师'],
            'companies': ['某科技公司', '某世界 500 强企业']
        },
        'education_experiences': [
            {'degree': '本科', 'school': '某大学'},
            {'degree': '硕士', 'school': '某重点大学'}
        ],
        'work_experiences': [
            {
                'position': '软件工程师',
                'company': '某科技公司',
                'responsibilities': ['负责后端开发']
            },
            {
                'position': '高级软件工程师',
                'company': '某科技公司',
                'responsibilities': ['主导系统设计，带领 3 人小组']
            },
            {
                'position': '技术经理',
                'company': '某世界 500 强企业',
                'responsibilities': ['负责技术团队管理，带领 15 人团队，统筹技术规划']
            }
        ],
        'project_experiences': [
            {
                'name': '某核心系统重构项目',
                'description': ['负责千万级用户平台的架构重构，带领 20 人团队，预算 500 万']
            }
        ]
    }

    evaluator = PotentialEvaluator(verbose=True)
    result = evaluator.evaluate(test_resume)

    import json
    print("\n潜力评估结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
