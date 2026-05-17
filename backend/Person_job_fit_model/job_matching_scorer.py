# -*- coding: utf-8 -*-
"""
人岗匹配评分模块

功能：
1. 计算候选人简历与岗位画像的匹配度
2. 支持学历、工作年限、技能、行业、管理职责等多维度匹配
3. 权重支持动态调整（默认权重 + 手动调整）
4. 输出标准化 JSON 格式结果

匹配维度：
- 学历匹配度 (education_match)
- 工作年限匹配度 (work_years_match)
- 技能匹配度 (skill_match)
- 行业经验匹配度 (industry_match)
- 管理职责匹配度 (management_match)

计算公式：
MATCH_SCORE = w1*学历匹配 + w2*年限匹配 + w3*技能匹配 + w4*行业匹配 + w5*管理匹配
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class JobMatchingScorer:
    """人岗匹配评分器"""

    # 默认权重（支持动态调整）
    DEFAULT_WEIGHTS = {
        'education': 0.15,      # 学历匹配权重
        'work_years': 0.20,     # 工作年限匹配权重
        'skill': 0.35,          # 技能匹配权重（最高）
        'industry': 0.20,       # 行业经验匹配权重
        'management': 0.10      # 管理职责匹配权重
    }

    # 学历层次映射
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
        '初中': 0,
        '不限': 0
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None, verbose: bool = True):
        """
        初始化评分器

        Args:
            weights: 自定义权重字典（可选），如 None 则使用默认权重
            verbose: 是否打印详细输出
        """
        self.verbose = verbose
        
        # 权重验证与归一化
        if weights:
            self.weights = self._normalize_weights(weights)
        else:
            self.weights = self.DEFAULT_WEIGHTS.copy()

    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        权重归一化（确保总和为 1）

        Args:
            weights: 原始权重大字典

        Returns:
            归一化后的权重大字典
        """
        total = sum(weights.values())
        if total <= 0:
            if self.verbose:
                print("[WARN] 权重总和为 0，使用默认权重")
            return self.DEFAULT_WEIGHTS.copy()
        
        normalized = {k: v / total for k, v in weights.items()}
        
        if self.verbose:
            print(f"\n权重配置:")
            for k, v in normalized.items():
                print(f"  {k}: {v:.2%}")
        
        return normalized

    def update_weights(self, weights: Dict[str, float]) -> None:
        """
        动态更新权重

        Args:
            weights: 新的权重大字典
        """
        self.weights = self._normalize_weights(weights)
        if self.verbose:
            print("[OK] 权重已更新")

    def calculate_education_match(self, resume: Dict, job_profile: Dict) -> Tuple[float, Dict]:
        """
        计算学历匹配度

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典

        Returns:
            (匹配分数 0-5, 详情字典)
        """
        # 获取岗位要求
        education_required = job_profile.get('education_required', '不限')
        required_level = self.EDUCATION_LEVELS.get(education_required, 0)

        # 获取候选人学历
        education_experiences = resume.get('education_experiences', [])
        if not education_experiences:
            candidate_level = 0
            candidate_degree = "未知"
        else:
            # 取最高学历
            max_level = 0
            candidate_degree = ""
            for edu in education_experiences:
                degree = edu.get('degree', '')
                level = self.EDUCATION_LEVELS.get(degree, 0)
                if level > max_level:
                    max_level = level
                    candidate_degree = degree
            candidate_level = max_level

        # 计算匹配度
        if required_level == 0:  # 不限学历
            match_score = 5.0
        elif candidate_level >= required_level:
            match_score = 5.0
        elif candidate_level == required_level - 1:  # 略低一级
            match_score = 3.5
        else:  # 远低于要求
            match_score = 1.5

        details = {
            'required_education': education_required,
            'candidate_education': candidate_degree,
            'required_level': required_level,
            'candidate_level': candidate_level,
            'match_score': match_score
        }

        return match_score, details

    def calculate_work_years_match(self, resume: Dict, job_profile: Dict) -> Tuple[float, Dict]:
        """
        计算工作年限匹配度

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典

        Returns:
            (匹配分数 0-5, 详情字典)
        """
        # 获取岗位要求
        min_years = job_profile.get('min_work_years', 0)

        # 获取候选人工作年限
        work_duration_months = resume.get('work_duration_months', 0)
        candidate_years = work_duration_months / 12.0

        # 计算匹配度
        if min_years == 0:  # 不限年限
            match_score = 5.0
        else:
            ratio = candidate_years / min_years
            if ratio >= 1.0:
                match_score = 5.0
            elif ratio >= 0.8:
                match_score = 4.0
            elif ratio >= 0.6:
                match_score = 3.0
            elif ratio >= 0.4:
                match_score = 2.0
            else:
                match_score = 1.0

        details = {
            'required_years': min_years,
            'candidate_years': round(candidate_years, 1),
            'ratio': round(ratio if min_years > 0 else 1.0, 2),
            'match_score': match_score
        }

        return match_score, details

    def calculate_skill_match(self, resume: Dict, job_profile: Dict, use_weighted: bool = True) -> Tuple[float, Dict]:
        """
        计算技能匹配度（使用加权 Jaccard 相似度）

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典
            use_weighted: 是否使用加权 Jaccard（核心技能权重更高）

        Returns:
            (匹配分数 0-5, 详情字典)
        """
        # 获取岗位技能要求
        job_core_skills = set(job_profile.get('core_skills', []))
        job_soft_skills = set(job_profile.get('soft_skills', []))

        # 获取候选人技能
        entities = resume.get('entities', {})
        candidate_skills = set(entities.get('skills', []))

        # 从项目经验中提取更多技能
        project_experiences = resume.get('project_experiences', [])
        for project in project_experiences:
            description = project.get('description', [])
            if isinstance(description, list):
                desc_text = ' '.join(str(d) for d in description)
            else:
                desc_text = str(description)
            
            # 简单匹配
            for skill in job_core_skills:
                if skill.lower() in desc_text.lower():
                    candidate_skills.add(skill)

        if not job_core_skills:
            return 3.0, {
                'job_skills_count': 0,
                'candidate_skills_count': len(candidate_skills),
                'matched_skills': [],
                'missing_skills': [],
                'match_rate': 1.0,
                'match_score': 3.0
            }

        # 计算匹配
        matched_skills = candidate_skills.intersection(job_core_skills)
        missing_skills = job_core_skills - candidate_skills

        # 基础 Jaccard 相似度
        union = candidate_skills.union(job_core_skills)
        if not union:
            jaccard = 0.0
        else:
            jaccard = len(matched_skills) / len(union)

        # 覆盖率
        coverage = len(matched_skills) / len(job_core_skills) if job_core_skills else 0

        # 加权 Jaccard（核心技能权重更高）
        if use_weighted and job_core_skills:
            # 假设前 5 个技能为核心中的核心
            core_core_skills = list(job_core_skills)[:5]
            weighted_matched = sum(2.0 if s in core_core_skills else 1.0 for s in matched_skills)
            weighted_total = sum(2.0 if s in core_core_skills else 1.0 for s in job_core_skills)
            weighted_jaccard = weighted_matched / weighted_total if weighted_total > 0 else 0
            final_score = (weighted_jaccard * 0.6 + coverage * 0.4) * 5
        else:
            final_score = (jaccard * 0.6 + coverage * 0.4) * 5

        match_score = min(max(final_score, 0), 5.0)

        details = {
            'job_skills_count': len(job_core_skills),
            'candidate_skills_count': len(candidate_skills),
            'matched_skills': list(matched_skills),
            'missing_skills': list(missing_skills)[:10],
            'match_rate': len(matched_skills) / len(job_core_skills) if job_core_skills else 0,
            'jaccard_similarity': jaccard,
            'match_score': round(match_score, 2)
        }

        return match_score, details

    def calculate_industry_match(self, resume: Dict, job_profile: Dict) -> Tuple[float, Dict]:
        """
        计算行业经验匹配度

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典

        Returns:
            (匹配分数 0-5, 详情字典)
        """
        # 获取岗位要求行业
        job_industry = job_profile.get('industry', '不限')
        job_industry_experience = job_profile.get('industry_experience', '不限')

        # 获取候选人行业
        candidate_industry = resume.get('industry', '未知')

        # 行业相关性映射
        industry_relatedness = {
            '电商': ['电商', '品牌', '销售'],
            '品牌': ['品牌', '电商', '销售'],
            '销售': ['销售', '电商', '品牌'],
            '研发': ['研发'],
            '生产': ['生产'],
            '人力资源': ['人力资源']
        }

        # 计算匹配度
        if job_industry == '不限':
            match_score = 5.0
        elif candidate_industry == job_industry:
            match_score = 5.0  # 同行业
        elif candidate_industry in industry_relatedness.get(job_industry, []):
            match_score = 3.5  # 相关行业
        else:
            match_score = 2.0  # 跨行业

        details = {
            'job_industry': job_industry,
            'candidate_industry': candidate_industry,
            'is_same_industry': candidate_industry == job_industry,
            'match_score': match_score
        }

        return match_score, details

    def calculate_management_match(self, resume: Dict, job_profile: Dict) -> Tuple[float, Dict]:
        """
        计算管理职责匹配度

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典

        Returns:
            (匹配分数 0-5, 详情字典)
        """
        # 获取岗位管理要求
        job_mgmt = job_profile.get('management_responsibility', {})
        job_has_management = job_mgmt.get('has_team_management', False)
        job_mgmt_level = job_mgmt.get('management_level', None)
        job_team_size = job_mgmt.get('team_size', None)

        # 判断候选人管理经验
        positions = resume.get('entities', {}).get('positions', [])
        work_experiences = resume.get('work_experiences', [])

        # 检查是否有管理职位
        management_keywords = ['总监', '经理', '主管', '主任', '总裁', '总经理', '副总裁', '组长', '部长', '负责人', 'Manager', 'Director']
        has_management_title = any(any(keyword in pos for keyword in management_keywords) for pos in positions)

        # 检查工作职责中是否有管理内容
        has_management_resp = False
        for exp in work_experiences:
            responsibilities = exp.get('responsibilities', [])
            resp_text = ' '.join(str(r) for r in responsibilities)
            if any(keyword in resp_text for keyword in ['管理', '带领', '负责团队', '下属']):
                has_management_resp = True
                break

        # 计算匹配度
        if not job_has_management:
            match_score = 5.0  # 岗位不要求管理，都给满分
        elif has_management_title or has_management_resp:
            match_score = 4.5  # 有管理经验
        else:
            match_score = 2.0  # 无管理经验

        details = {
            'job_requires_management': job_has_management,
            'job_management_level': job_mgmt_level,
            'job_team_size': job_team_size,
            'candidate_has_management_title': has_management_title,
            'candidate_has_management_resp': has_management_resp,
            'match_score': match_score
        }

        return match_score, details

    def calculate_overall_match(self, resume: Dict, job_profile: Dict) -> Dict:
        """
        计算综合人岗匹配度

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典

        Returns:
            匹配结果字典（JSON 格式）
        """
        if self.verbose:
            print("\n" + "="*60)
            print("开始计算人岗匹配度...")
            print("="*60)
            print(f"\n岗位：{job_profile.get('job_title', '未知')}")
            print(f"候选人：{resume.get('basic_info', {}).get('name', '未知')}")

        # 计算各维度匹配度
        edu_match, edu_details = self.calculate_education_match(resume, job_profile)
        years_match, years_details = self.calculate_work_years_match(resume, job_profile)
        skill_match, skill_details = self.calculate_skill_match(resume, job_profile)
        industry_match, industry_details = self.calculate_industry_match(resume, job_profile)
        mgmt_match, mgmt_details = self.calculate_management_match(resume, job_profile)

        # 加权计算总分
        overall_score = (
            self.weights['education'] * edu_match +
            self.weights['work_years'] * years_match +
            self.weights['skill'] * skill_match +
            self.weights['industry'] * industry_match +
            self.weights['management'] * mgmt_match
        )

        # 匹配等级
        if overall_score >= 4.5:
            match_level = "A+"
            match_comment = "非常匹配"
        elif overall_score >= 4.0:
            match_level = "A"
            match_comment = "很匹配"
        elif overall_score >= 3.5:
            match_level = "B+"
            match_comment = "比较匹配"
        elif overall_score >= 3.0:
            match_level = "B"
            match_comment = "基本匹配"
        elif overall_score >= 2.5:
            match_level = "C"
            match_comment = "勉强匹配"
        else:
            match_level = "D"
            match_comment = "不匹配"

        result = {
            'overall_score': round(overall_score, 2),
            'match_level': match_level,
            'match_comment': match_comment,
            'dimension_scores': {
                'education_match': round(edu_match, 2),
                'work_years_match': round(years_match, 2),
                'skill_match': round(skill_match, 2),
                'industry_match': round(industry_match, 2),
                'management_match': round(mgmt_match, 2)
            },
            'dimension_weights': {
                'education': round(self.weights['education'], 3),
                'work_years': round(self.weights['work_years'], 3),
                'skill': round(self.weights['skill'], 3),
                'industry': round(self.weights['industry'], 3),
                'management': round(self.weights['management'], 3)
            },
            'details': {
                'education_details': edu_details,
                'work_years_details': years_details,
                'skill_details': skill_details,
                'industry_details': industry_details,
                'management_details': mgmt_details
            }
        }

        if self.verbose:
            print(f"\n各维度匹配得分:")
            print(f"  学历匹配：{edu_match:.2f}")
            print(f"  工作年限匹配：{years_match:.2f}")
            print(f"  技能匹配：{skill_match:.2f}")
            print(f"  行业经验匹配：{industry_match:.2f}")
            print(f"  管理职责匹配：{mgmt_match:.2f}")
            print(f"\n综合匹配得分：{overall_score:.2f} ({match_comment})")
            print("\n[OK] 人岗匹配评分完成！")
            print("="*60)

        return result

    def batch_calculate(self, resumes: List[Dict], job_profile: Dict) -> List[Dict]:
        """
        批量计算多份简历的匹配度

        Args:
            resumes: 简历列表
            job_profile: 岗位画像字典

        Returns:
            匹配结果列表（已排序）
        """
        results = []
        for resume in resumes:
            result = self.calculate_overall_match(resume, job_profile)
            result['candidate_id'] = resume.get('basic_info', {}).get('name', '未知')
            results.append(result)

        # 按综合得分排序
        results.sort(key=lambda x: x['overall_score'], reverse=True)

        # 添加排名
        for i, result in enumerate(results, 1):
            result['rank'] = i

        return results


if __name__ == '__main__':
    # 测试示例
    test_job_profile = {
        'job_title': '电商运营总监',
        'industry': '电商',
        'education_required': '本科',
        'min_work_years': 5,
        'core_skills': ['电商运营', '团队管理', '数据分析', 'GMV 提升', '淘宝运营'],
        'soft_skills': ['沟通能力', '领导力'],
        'management_responsibility': {
            'has_team_management': True,
            'team_size': '10-20 人',
            'management_level': '总监级'
        }
    }

    test_resume = {
        'basic_info': {'name': '张三'},
        'industry': '电商',
        'education_experiences': [
            {'degree': '本科', 'school': '某大学'}
        ],
        'work_duration_months': 72,
        'entities': {
            'skills': ['电商运营', '数据分析', '淘宝运营', '团队管理'],
            'positions': ['运营经理']
        },
        'work_experiences': [
            {
                'responsibilities': ['负责电商团队管理，带领 15 人团队']
            }
        ]
    }

    scorer = JobMatchingScorer(verbose=True)
    result = scorer.calculate_overall_match(test_resume, test_job_profile)
    
    import json
    print("\n匹配结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
