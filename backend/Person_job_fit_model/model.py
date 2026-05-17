# -*- coding: utf-8 -*-
"""
人岗匹配模型主类

整合以下模块：
- 岗位画像抽取 (JobProfileExtractor)
- 人岗匹配评分 (JobMatchingScorer)
- 风险识别 (RiskIdentifier)
- 潜力评估 (PotentialEvaluator)
- 可视化 (FitVisualizer)

提供统一的高层 API，支持：
- 岗位画像抽取
- 单个人岗匹配计算
- 批量人岗匹配计算
- 风险识别
- 潜力评估
- 可视化图表生成
- 结果导出（JSON 格式）
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from .job_profile_extractor import JobProfileExtractor
from .job_matching_scorer import JobMatchingScorer
from .risk_identifier import RiskIdentifier
from .potential_evaluator import PotentialEvaluator
from .fit_visualizer import FitVisualizer


class PersonJobFitModel:
    """
    人岗匹配模型主类
    
    使用示例：
    ```python
    # 初始化模型
    model = PersonJobFitModel()
    
    # 加载简历数据
    resumes = model.load_resumes("path/to/resumes.json")
    
    # 抽取岗位画像
    job_profile = model.extract_job_profile(jd_text)
    
    # 计算人岗匹配
    matching_results = model.batch_matching(resumes, job_profile)
    
    # 识别风险
    risk_results = model.batch_risk_assessment(resumes, job_profile)
    
    # 评估潜力
    potential_results = model.batch_potential_evaluation(resumes)
    
    # 生成可视化图表
    model.generate_visualizations(matching_results[0], save_dir="output/")
    
    # 导出结果
    model.export_results(matching_results, "output/matching_results.json")
    ```
    """

    def __init__(self, 
                 matching_weights: Optional[Dict[str, float]] = None,
                 verbose: bool = True,
                 use_chinese_font: bool = True):
        """
        初始化人岗匹配模型

        Args:
            matching_weights: 人岗匹配权重配置（可选）
            verbose: 是否打印详细输出
            use_chinese_font: 可视化是否使用中文字体
        """
        self.verbose = verbose
        self.use_chinese_font = use_chinese_font
        
        # 初始化各子模块
        if self.verbose:
            print("="*60)
            print("初始化人岗匹配模型...")
            print("="*60)
        
        self.job_profile_extractor = JobProfileExtractor(verbose=verbose)
        self.job_matching_scorer = JobMatchingScorer(weights=matching_weights, verbose=verbose)
        self.risk_identifier = RiskIdentifier(verbose=verbose)
        self.potential_evaluator = PotentialEvaluator(verbose=verbose)
        self.visualizer = FitVisualizer(use_chinese=use_chinese_font)
        
        # 数据存储
        self.resumes = []
        self.job_profiles = {}
        self.matching_results = []
        self.risk_results = []
        self.potential_results = []
        
        if self.verbose:
            print("\n[OK] 模型初始化完成！")
            print("="*60)

    def load_resumes(self, data_source: Union[str, List[Dict]]) -> List[Dict]:
        """
        加载简历数据

        Args:
            data_source: 数据源，可以是：
                        - JSON 文件路径（字符串）
                        - 简历字典列表

        Returns:
            简历列表
        """
        if isinstance(data_source, str):
            file_path = Path(data_source)
            if not file_path.exists():
                raise FileNotFoundError(f"简历文件不存在：{file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                resumes = json.load(f)
            
            if self.verbose:
                print(f"\n[OK] 已加载 {len(resumes)} 份简历 from {file_path.name}")
            
            self.resumes = resumes
            return resumes
        
        elif isinstance(data_source, list):
            if self.verbose:
                print(f"\n[OK] 已加载 {len(data_source)} 份简历")
            self.resumes = data_source
            return data_source
        
        else:
            raise TypeError("data_source 必须是文件路径 (str) 或简历字典列表")

    def extract_job_profile(self, 
                           job_description: str, 
                           requirements: str = "",
                           save_path: Optional[str] = None) -> Dict:
        """
        抽取岗位画像

        Args:
            job_description: 岗位描述文本
            requirements: 任职要求文本（可选）
            save_path: 保存路径（可选）

        Returns:
            结构化岗位画像字典
        """
        profile = self.job_profile_extractor.extract(job_description, requirements)
        
        # 保存岗位画像
        if save_path:
            self.job_profile_extractor.save_profile(profile, save_path)
        
        # 存储到内存
        job_title = profile.get('job_title', '未知岗位')
        self.job_profiles[job_title] = profile
        
        return profile

    def load_job_profile(self, job_profile: Union[str, Dict]) -> Dict:
        """
        加载岗位画像（从文件或字典）

        Args:
            job_profile: 岗位画像文件路径或字典

        Returns:
            岗位画像字典
        """
        if isinstance(job_profile, str):
            file_path = Path(job_profile)
            if not file_path.exists():
                raise FileNotFoundError(f"岗位画像文件不存在：{file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
        elif isinstance(job_profile, dict):
            profile = job_profile
        else:
            raise TypeError("job_profile 必须是文件路径 (str) 或字典")
        
        # 存储到内存
        job_title = profile.get('job_title', '未知岗位')
        self.job_profiles[job_title] = profile
        
        return profile

    def single_matching(self, 
                       resume: Dict, 
                       job_profile: Dict,
                       include_details: bool = True) -> Dict:
        """
        单个人岗匹配计算

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典
            include_details: 是否包含详细信息

        Returns:
            匹配结果字典
        """
        result = self.job_matching_scorer.calculate_overall_match(resume, job_profile)
        
        # 添加候选人 ID
        result['candidate_id'] = resume.get('basic_info', {}).get('name', '未知')
        
        if not include_details:
            result.pop('details', None)
        
        return result

    def batch_matching(self, 
                      resumes: Optional[List[Dict]] = None,
                      job_profile: Optional[Dict] = None,
                      include_details: bool = True) -> List[Dict]:
        """
        批量人岗匹配计算

        Args:
            resumes: 简历列表（如 None 则使用已加载的简历）
            job_profile: 岗位画像字典（如 None 则使用已加载的岗位）
            include_details: 是否包含详细信息

        Returns:
            匹配结果列表（已排序）
        """
        # 使用已加载的数据
        if resumes is None:
            resumes = self.resumes
        if job_profile is None:
            if not self.job_profiles:
                raise ValueError("请先加载或创建岗位画像")
            # 使用第一个岗位画像
            job_profile = list(self.job_profiles.values())[0]
        
        if not resumes:
            raise ValueError("没有简历数据")
        if not job_profile:
            raise ValueError("没有岗位画像数据")
        
        # 批量计算
        results = self.job_matching_scorer.batch_calculate(resumes, job_profile)
        
        if not include_details:
            for result in results:
                result.pop('details', None)
        
        self.matching_results = results
        return results

    def single_risk_assessment(self, 
                              resume: Dict, 
                              job_profile: Optional[Dict] = None) -> Dict:
        """
        单个风险识别

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典（可选，用于技能缺口分析）

        Returns:
            风险识别结果字典
        """
        result = self.risk_identifier.identify(resume, job_profile)
        
        # 添加候选人 ID
        result['candidate_id'] = resume.get('basic_info', {}).get('name', '未知')
        
        return result

    def batch_risk_assessment(self, 
                             resumes: Optional[List[Dict]] = None,
                             job_profile: Optional[Dict] = None) -> List[Dict]:
        """
        批量风险识别

        Args:
            resumes: 简历列表（如 None 则使用已加载的简历）
            job_profile: 岗位画像字典（可选）

        Returns:
            风险识别结果列表（按风险得分降序）
        """
        if resumes is None:
            resumes = self.resumes
        
        if not resumes:
            raise ValueError("没有简历数据")
        
        results = self.risk_identifier.batch_identify(resumes, job_profile)
        self.risk_results = results
        return results

    def single_potential_evaluation(self, resume: Dict) -> Dict:
        """
        单个潜力评估

        Args:
            resume: 简历字典

        Returns:
            潜力评估结果字典
        """
        result = self.potential_evaluator.evaluate(resume)
        
        # 添加候选人 ID
        result['candidate_id'] = resume.get('basic_info', {}).get('name', '未知')
        
        return result

    def batch_potential_evaluation(self, 
                                   resumes: Optional[List[Dict]] = None) -> List[Dict]:
        """
        批量潜力评估

        Args:
            resumes: 简历列表（如 None 则使用已加载的简历）

        Returns:
            潜力评估结果列表（按潜力得分降序）
        """
        if resumes is None:
            resumes = self.resumes
        
        if not resumes:
            raise ValueError("没有简历数据")
        
        results = self.potential_evaluator.batch_evaluate(resumes)
        self.potential_results = results
        return results

    def generate_visualizations(self,
                               matching_result: Optional[Dict] = None,
                               risk_result: Optional[Dict] = None,
                               potential_result: Optional[Dict] = None,
                               save_dir: str = "output/visualizations",
                               show: bool = False) -> Dict[str, str]:
        """
        生成可视化图表

        Args:
            matching_result: 人岗匹配结果（可选）
            risk_result: 风险识别结果（可选）
            potential_result: 潜力评估结果（可选）
            save_dir: 保存目录
            show: 是否显示图表

        Returns:
            图表文件路径字典
        """
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        chart_paths = {}
        
        # 生成人岗匹配雷达图
        if matching_result:
            radar_path = save_path / "matching_radar.png"
            self.visualizer.plot_matching_radar(matching_result, save_path=str(radar_path), show=show)
            chart_paths['matching_radar'] = str(radar_path)
        
        # 生成风险仪表盘
        if risk_result:
            risk_path = save_path / "risk_dashboard.png"
            self.visualizer.plot_risk_dashboard(risk_result, save_path=str(risk_path), show=show)
            chart_paths['risk_dashboard'] = str(risk_path)
        
        # 生成潜力评估柱状图
        if potential_result:
            potential_path = save_path / "potential_bar.png"
            self.visualizer.plot_potential_bar(potential_result, save_path=str(potential_path), show=show)
            chart_paths['potential_bar'] = str(potential_path)
        
        # 生成综合仪表盘
        if matching_result and risk_result and potential_result:
            dashboard_path = save_path / "comprehensive_dashboard.png"
            self.visualizer.create_dashboard(
                matching_result=matching_result,
                risk_result=risk_result,
                potential_result=potential_result,
                save_path=str(dashboard_path),
                show=show
            )
            chart_paths['comprehensive_dashboard'] = str(dashboard_path)
        
        if self.verbose and chart_paths:
            print(f"\n[OK] 已生成 {len(chart_paths)} 个图表，保存到：{save_path}")
        
        return chart_paths

    def export_results(self, 
                      results: Union[List[Dict], Dict],
                      output_path: str,
                      format: str = "json") -> None:
        """
        导出结果

        Args:
            results: 结果数据（列表或字典）
            output_path: 输出文件路径
            format: 输出格式 ("json" 或 "csv")
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            # 添加元数据
            export_data = {
                "metadata": {
                    "export_time": datetime.now().isoformat(),
                    "n_results": len(results) if isinstance(results, list) else 1
                },
                "data": results
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            if self.verbose:
                print(f"\n[OK] 结果已导出到：{output_path}")
        
        elif format == "csv":
            try:
                import pandas as pd
                
                if isinstance(results, list):
                    # 展平字典
                    rows = []
                    for result in results:
                        row = self._flatten_dict(result)
                        rows.append(row)
                    df = pd.DataFrame(rows)
                else:
                    row = self._flatten_dict(results)
                    df = pd.DataFrame([row])
                
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                
                if self.verbose:
                    print(f"\n[OK] 结果已导出到：{output_path}")
            
            except ImportError:
                raise ImportError("导出 CSV 需要安装 pandas: pip install pandas")
        
        else:
            raise ValueError(f"不支持的格式：{format}，请使用 'json' 或 'csv'")

    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """
        展平嵌套字典（用于 CSV 导出）

        Args:
            d: 字典
            parent_key: 父键
            sep: 分隔符

        Returns:
            展平后的字典
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)

    def get_comprehensive_report(self, 
                                resume: Dict,
                                job_profile: Dict,
                                include_charts: bool = False,
                                chart_save_dir: str = "output/charts") -> Dict:
        """
        生成综合评估报告（包含人岗匹配 + 风险识别 + 潜力评估）

        Args:
            resume: 简历字典
            job_profile: 岗位画像字典
            include_charts: 是否包含可视化图表
            chart_save_dir: 图表保存目录

        Returns:
            综合报告字典
        """
        if self.verbose:
            print("\n" + "="*60)
            print("生成综合评估报告...")
            print("="*60)
        
        # 计算各项评估
        matching_result = self.single_matching(resume, job_profile)
        risk_result = self.single_risk_assessment(resume, job_profile)
        potential_result = self.single_potential_evaluation(resume)
        
        # 生成综合报告
        report = {
            "candidate_id": resume.get('basic_info', {}).get('name', '未知'),
            "job_title": job_profile.get('job_title', '未知岗位'),
            "generated_at": datetime.now().isoformat(),
            "matching": {
                "overall_score": matching_result.get('overall_score'),
                "match_level": matching_result.get('match_level'),
                "match_comment": matching_result.get('match_comment'),
                "dimension_scores": matching_result.get('dimension_scores')
            },
            "risk": {
                "overall_risk_level": risk_result.get('overall_risk_level'),
                "overall_risk_score": risk_result.get('overall_risk_score'),
                "risk_comment": risk_result.get('risk_comment'),
                "risk_tags": risk_result.get('risk_tags'),
                "n_high_risks": risk_result.get('n_high_risks'),
                "n_medium_risks": risk_result.get('n_medium_risks')
            },
            "potential": {
                "talent_type": potential_result.get('talent_type'),
                "potential_score": potential_result.get('potential_score'),
                "potential_comment": potential_result.get('potential_comment'),
                "dimension_scores": potential_result.get('dimension_scores')
            },
            "summary": self._generate_summary(matching_result, risk_result, potential_result)
        }
        
        # 生成可视化图表
        if include_charts:
            chart_paths = self.generate_visualizations(
                matching_result=matching_result,
                risk_result=risk_result,
                potential_result=potential_result,
                save_dir=chart_save_dir
            )
            report['charts'] = chart_paths
        
        if self.verbose:
            print(f"\n[OK] 综合评估报告生成完成！")
            print("="*60)
        
        return report

    def _generate_summary(self, 
                         matching_result: Dict, 
                         risk_result: Dict, 
                         potential_result: Dict) -> str:
        """
        生成综合评语

        Args:
            matching_result: 人岗匹配结果
            risk_result: 风险识别结果
            potential_result: 潜力评估结果

        Returns:
            综合评语文本
        """
        matching_score = matching_result.get('overall_score', 0)
        risk_level = risk_result.get('overall_risk_level', '未知')
        talent_type = potential_result.get('talent_type', '未知')
        
        summary_parts = []
        
        # 匹配度评价
        if matching_score >= 4.5:
            summary_parts.append("该候选人与岗位非常匹配")
        elif matching_score >= 4.0:
            summary_parts.append("该候选人与岗位很匹配")
        elif matching_score >= 3.5:
            summary_parts.append("该候选人与岗位比较匹配")
        else:
            summary_parts.append("该候选人与岗位匹配度一般")
        
        # 风险评价
        if risk_level == "低":
            summary_parts.append("风险因素较少，工作稳定性好")
        elif risk_level == "中":
            summary_parts.append("存在一定风险因素，需关注")
        else:
            summary_parts.append("存在较高风险，建议谨慎评估")
        
        # 潜力评价
        if talent_type == "高潜力人才":
            summary_parts.append("具备高成长潜力，建议重点培养")
        elif talent_type == "成长型人才":
            summary_parts.append("保持稳定成长态势")
        elif talent_type == "即战力人才":
            summary_parts.append("经验丰富，可立即胜任重要岗位")
        else:
            summary_parts.append("需要进一步观察和培养")
        
        return "。".join(summary_parts) + "。"

    def update_matching_weights(self, weights: Dict[str, float]) -> None:
        """
        动态更新人岗匹配权重

        Args:
            weights: 新的权重大字典
        """
        self.job_matching_scorer.update_weights(weights)
        if self.verbose:
            print("[OK] 人岗匹配权重已更新")

    def get_model_info(self) -> Dict:
        """
        获取模型信息

        Returns:
            模型信息字典
        """
        return {
            "version": "1.0.0",
            "modules": {
                "job_profile_extractor": "岗位画像抽取模块",
                "job_matching_scorer": "人岗匹配评分模块",
                "risk_identifier": "风险识别模块",
                "potential_evaluator": "潜力评估模块",
                "fit_visualizer": "可视化模块"
            },
            "matching_weights": self.job_matching_scorer.weights,
            "risk_thresholds": self.risk_identifier.thresholds,
            "n_resumes_loaded": len(self.resumes),
            "n_job_profiles_loaded": len(self.job_profiles)
        }


if __name__ == '__main__':
    # 测试示例
    print("="*60)
    print("人岗匹配模型 - 集成测试")
    print("="*60)
    
    # 初始化模型
    model = PersonJobFitModel(verbose=True)
    
    # 测试简历数据
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
    
    # 2. 计算人岗匹配
    print("\n【2】计算人岗匹配...")
    matching_result = model.single_matching(test_resume, job_profile)
    print(f"匹配得分：{matching_result['overall_score']}")
    print(f"匹配等级：{matching_result['match_level']}")
    
    # 3. 识别风险
    print("\n【3】识别风险...")
    risk_result = model.single_risk_assessment(test_resume, job_profile)
    print(f"风险等级：{risk_result['overall_risk_level']}")
    print(f"风险得分：{risk_result['overall_risk_score']}")
    
    # 4. 评估潜力
    print("\n【4】评估潜力...")
    potential_result = model.single_potential_evaluation(test_resume)
    print(f"人才类型：{potential_result['talent_type']}")
    print(f"潜力得分：{potential_result['potential_score']}")
    
    # 5. 生成综合报告
    print("\n【5】生成综合报告...")
    report = model.get_comprehensive_report(test_resume, job_profile, include_charts=False)
    print(f"综合评语：{report['summary']}")
    
    # 6. 导出结果
    print("\n【6】导出结果...")
    model.export_results(matching_result, "output/test_matching.json")
    model.export_results(risk_result, "output/test_risk.json")
    model.export_results(potential_result, "output/test_potential.json")
    model.export_results(report, "output/test_comprehensive_report.json")
    
    print("\n" + "="*60)
    print("[OK] 所有测试完成！")
    print("="*60)
