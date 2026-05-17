# -*- coding: utf-8 -*-
"""
人岗匹配模型测试文件

功能：
1. 测试各模块的基本功能
2. 验证数据输入输出格式
3. 演示模型使用方法
"""

import json
from pathlib import Path
import sys

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from Person_job_fit_model import (
    JobProfileExtractor,
    JobMatchingScorer,
    RiskIdentifier,
    PotentialEvaluator,
    FitVisualizer,
    PersonJobFitModel
)


def test_job_profile_extractor():
    """测试岗位画像抽取模块"""
    print("\n" + "="*60)
    print("【测试 1】岗位画像抽取模块")
    print("="*60)
    
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
    
    # 验证关键字段
    assert profile['job_title'] == '电商运营总监', f"岗位名称错误：{profile['job_title']}"
    assert profile['education_required'] == '本科', f"学历要求错误：{profile['education_required']}"
    assert profile['min_work_years'] == 5, f"工作年限错误：{profile['min_work_years']}"
    assert profile['industry'] == '电商', f"行业错误：{profile['industry']}"
    assert len(profile['core_skills']) > 0, "核心技能为空"
    
    print(f"\n✓ 岗位名称：{profile['job_title']}")
    print(f"✓ 学历要求：{profile['education_required']}")
    print(f"✓ 工作年限：{profile['min_work_years']}年")
    print(f"✓ 行业：{profile['industry']}")
    print(f"✓ 核心技能：{len(profile['core_skills'])}个")
    print(f"✓ 软技能：{len(profile['soft_skills'])}个")
    print(f"✓ 管理职责：{'有' if profile['management_responsibility']['has_team_management'] else '无'}")
    print("\n[OK] 岗位画像抽取测试通过！")
    
    return profile


def test_job_matching_scorer():
    """测试人岗匹配评分模块"""
    print("\n" + "="*60)
    print("【测试 2】人岗匹配评分模块")
    print("="*60)
    
    # 岗位画像
    job_profile = {
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
    
    # 测试简历
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
    result = scorer.calculate_overall_match(test_resume, job_profile)
    
    # 验证结果
    assert 'overall_score' in result, "缺少综合得分"
    assert 'match_level' in result, "缺少匹配等级"
    assert 'dimension_scores' in result, "缺少维度得分"
    assert 0 <= result['overall_score'] <= 5, f"得分超出范围：{result['overall_score']}"
    
    print(f"\n✓ 综合得分：{result['overall_score']}")
    print(f"✓ 匹配等级：{result['match_level']}")
    print(f"✓ 匹配评语：{result['match_comment']}")
    print(f"✓ 学历匹配：{result['dimension_scores']['education_match']}")
    print(f"✓ 技能匹配：{result['dimension_scores']['skill_match']}")
    
    # 测试权重动态调整
    print("\n测试权重动态调整...")
    custom_weights = {
        'education': 0.10,
        'work_years': 0.15,
        'skill': 0.45,
        'industry': 0.20,
        'management': 0.10
    }
    scorer.update_weights(custom_weights)
    result2 = scorer.calculate_overall_match(test_resume, job_profile)
    
    print(f"✓ 调整权重后得分：{result2['overall_score']}")
    print("\n[OK] 人岗匹配评分测试通过！")
    
    return result


def test_risk_identifier():
    """测试风险识别模块"""
    print("\n" + "="*60)
    print("【测试 3】风险识别模块")
    print("="*60)
    
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
    
    # 验证结果
    assert 'overall_risk_level' in result, "缺少综合风险等级"
    assert result['overall_risk_level'] in ['高', '中', '低'], f"风险等级错误：{result['overall_risk_level']}"
    assert 'risk_factors' in result, "缺少风险因素"
    assert 'risk_tags' in result, "缺少风险标签"
    
    print(f"\n✓ 综合风险等级：{result['overall_risk_level']}")
    print(f"✓ 风险得分：{result['overall_risk_score']}")
    print(f"✓ 风险评语：{result['risk_comment']}")
    print(f"✓ 风险因素：{len(result['risk_factors'])}个")
    print(f"✓ 风险标签：{len(result['risk_tags'])}个")
    if result['risk_tags']:
        print(f"  标签：{', '.join(result['risk_tags'])}")
    
    print("\n[OK] 风险识别测试通过！")
    
    return result


def test_potential_evaluator():
    """测试潜力评估模块"""
    print("\n" + "="*60)
    print("【测试 4】潜力评估模块")
    print("="*60)
    
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
    
    # 验证结果
    assert 'talent_type' in result, "缺少人才类型"
    assert result['talent_type'] in ['高潜力人才', '成长型人才', '即战力人才', '待观察'], f"人才类型错误：{result['talent_type']}"
    assert 'potential_score' in result, "缺少潜力得分"
    assert 'dimension_scores' in result, "缺少维度得分"
    
    print(f"\n✓ 人才类型：{result['talent_type']}")
    print(f"✓ 潜力得分：{result['potential_score']}")
    print(f"✓ 潜力评语：{result['potential_comment']}")
    print(f"✓ 职业发展连续性：{result['dimension_scores']['career_continuity']}")
    print(f"✓ 学习能力：{result['dimension_scores']['learning_ability']}")
    
    print("\n[OK] 潜力评估测试通过！")
    
    return result


def test_visualizer():
    """测试可视化模块"""
    print("\n" + "="*60)
    print("【测试 5】可视化模块")
    print("="*60)
    
    visualizer = FitVisualizer()
    
    # 测试数据
    matching_result = {
        'overall_score': 4.25,
        'match_level': 'A',
        'dimension_scores': {
            'education_match': 4.5,
            'work_years_match': 4.0,
            'skill_match': 4.5,
            'industry_match': 5.0,
            'management_match': 3.0
        }
    }
    
    risk_result = {
        'overall_risk_level': '中',
        'overall_risk_score': 4.5,
        'details': {
            'job_hopping_details': {'risk_score': 5},
            'career_gap_details': {'risk_score': 3},
            'industry_switch_details': {'risk_score': 4},
            'skill_gap_details': {'risk_score': 6},
            'weak_achievement_details': {'risk_score': 4},
            'employment_gap_details': {'risk_score': 2}
        }
    }
    
    potential_result = {
        'talent_type': '高潜力人才',
        'potential_score': 8.2,
        'dimension_scores': {
            'career_continuity': 8.5,
            'responsibility_growth': 7.5,
            'project_complexity': 8.0,
            'learning_ability': 9.0,
            'company_platform_growth': 7.5
        }
    }
    
    # 创建输出目录
    output_dir = Path(__file__).parent / 'output' / 'test_visualizations'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成图表
    print("\n生成人岗匹配雷达图...")
    visualizer.plot_matching_radar(matching_result, save_path=str(output_dir / 'matching_radar.png'))
    
    print("生成风险仪表盘...")
    visualizer.plot_risk_dashboard(risk_result, save_path=str(output_dir / 'risk_dashboard.png'))
    
    print("生成潜力评估柱状图...")
    visualizer.plot_potential_bar(potential_result, save_path=str(output_dir / 'potential_bar.png'))
    
    print("生成综合仪表盘...")
    visualizer.create_dashboard(
        matching_result=matching_result,
        risk_result=risk_result,
        potential_result=potential_result,
        save_path=str(output_dir / 'comprehensive_dashboard.png')
    )
    
    print(f"\n✓ 图表已保存到：{output_dir}")
    print("\n[OK] 可视化测试通过！")


def test_integrated_model():
    """测试集成模型"""
    print("\n" + "="*60)
    print("【测试 6】集成模型综合测试")
    print("="*60)
    
    # 初始化模型
    model = PersonJobFitModel(verbose=True)
    
    # 测试简历
    test_resume = {
        'basic_info': {'name': '测试候选人'},
        'industry': '电商',
        'work_duration_months': 60,
        'education_experiences': [
            {'degree': '本科', 'school': '某大学'}
        ],
        'entities': {
            'skills': ['电商运营', '数据分析', '团队管理'],
            'positions': ['运营经理'],
            'companies': ['某电商公司']
        },
        'work_experiences': [
            {
                'position': '运营经理',
                'company': '某电商公司',
                'responsibilities': ['带领团队完成 GMV 增长 50%']
            }
        ]
    }
    
    # 测试岗位描述
    test_jd = """
    招聘岗位：电商运营经理
    
    岗位职责：
    1. 负责电商平台的整体运营规划和管理
    2. 制定运营策略，提升 GMV 和 ROI
    3. 管理运营团队，带领 10 人团队完成业绩目标
    
    任职要求：
    1. 本科及以上学历
    2. 5 年以上电商运营经验，3 年以上团队管理经验
    3. 熟悉淘宝、天猫、京东等电商平台运营规则
    4. 精通数据分析优化及营销活动的策划
    5. 具备优秀的沟通能力、团队协作能力和领导力
    
    薪资范围：20K-35K/月
    """
    
    # 1. 抽取岗位画像
    print("\n【1】抽取岗位画像...")
    job_profile = model.extract_job_profile(test_jd)
    print(f"✓ 岗位名称：{job_profile['job_title']}")
    
    # 2. 计算人岗匹配
    print("\n【2】计算人岗匹配...")
    matching_result = model.single_matching(test_resume, job_profile)
    print(f"✓ 匹配得分：{matching_result['overall_score']}")
    print(f"✓ 匹配等级：{matching_result['match_level']}")
    
    # 3. 识别风险
    print("\n【3】识别风险...")
    risk_result = model.single_risk_assessment(test_resume, job_profile)
    print(f"✓ 风险等级：{risk_result['overall_risk_level']}")
    print(f"✓ 风险得分：{risk_result['overall_risk_score']}")
    
    # 4. 评估潜力
    print("\n【4】评估潜力...")
    potential_result = model.single_potential_evaluation(test_resume)
    print(f"✓ 人才类型：{potential_result['talent_type']}")
    print(f"✓ 潜力得分：{potential_result['potential_score']}")
    
    # 5. 生成综合报告
    print("\n【5】生成综合报告...")
    report = model.get_comprehensive_report(test_resume, job_profile, include_charts=False)
    print(f"✓ 综合评语：{report['summary']}")
    
    # 6. 导出结果
    print("\n【6】导出结果...")
    output_dir = Path(__file__).parent / 'output' / 'test_results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    model.export_results(matching_result, str(output_dir / 'matching.json'))
    model.export_results(risk_result, str(output_dir / 'risk.json'))
    model.export_results(potential_result, str(output_dir / 'potential.json'))
    model.export_results(report, str(output_dir / 'comprehensive_report.json'))
    
    print(f"✓ 结果已导出到：{output_dir}")
    
    print("\n" + "="*60)
    print("[OK] 所有集成测试通过！")
    print("="*60)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("人岗匹配模型 - 功能测试")
    print("="*60)
    
    try:
        # 运行所有测试
        test_job_profile_extractor()
        test_job_matching_scorer()
        test_risk_identifier()
        test_potential_evaluator()
        test_visualizer()
        test_integrated_model()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！模型功能正常！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
