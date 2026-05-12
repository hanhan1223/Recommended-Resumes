"""
行业权重矩阵主模块

实现动态行业权重矩阵的核心功能：
1. 为不同行业计算专属的维度权重（Wedu, Wexp, Wskill, Wadj）
2. 支持从 Resume_Recognition_Model 的 industry 字段自动识别
3. 提供与 Dimensional_scoring_model 的集成接口
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from .ahp_matrices import IndustryAHPMatrices
from .weight_calculator import WeightCalculator


class IndustryWeightMatrix:
    """
    行业权重矩阵主类
    
    功能：
    1. 根据行业计算 4 个维度的专属权重
    2. 支持 AHP+ 熵权法组合权重计算
    3. 提供行业权重查询接口
    4. 支持与 Dimensional_scoring_model 集成
    
    输入：
    - industry: Resume_Recognition_Model 识别的行业字段值
    - resumes: 简历数据列表
    
    输出：
    - dimension_weights: {education, experience, skill_achievement, comprehensive}
    """
    
    # 行业映射关系（Resume_Recognition_Model → 本模块）
    INDUSTRY_MAPPING = {
        "电商": "电商",
        "品牌": "品牌市场",  # 品牌 → 品牌市场类
        "人力资源": "人力资源",
        "生产": "生产",
        "研发": "研发",
        "销售": "销售"
    }
    
    # 指标到维度的映射
    INDICATOR_TO_DIMENSION = {
        "technical": {
            "学历": "education",
            "专业技能": "skill_achievement",
            "项目经验": "skill_achievement",
            "工作成果": "skill_achievement",
            "工作年限": "experience"
        },
        "management": {
            "学历": "education",
            "工作经历": "experience",
            "情商沟通": "comprehensive",
            "稳定性": "experience",
            "管理成果": "skill_achievement"
        }
    }
    
    def __init__(
        self, 
        alpha: float = 0.5,
        save_dir: Optional[str] = None,
        verbose: bool = True
    ):
        """
        初始化行业权重矩阵
        
        Args:
            alpha: AHP 权重占比系数 (0-1)，默认 0.5
            save_dir: 可视化结果保存目录（可选）
            verbose: 是否打印详细输出
        """
        self.alpha = alpha
        self.save_dir = Path(save_dir) if save_dir else None
        self.verbose = verbose
        
        self.calculator = WeightCalculator(alpha=alpha)
        self.ahp_matrices = IndustryAHPMatrices()

        # 延迟导入，避免matplotlib依赖问题
        from .exporter import IndustryWeightExporter
        self.exporter = IndustryWeightExporter(save_dir=self.save_dir)

        try:
            from .visualizer import IndustryWeightVisualizer
            self.visualizer = IndustryWeightVisualizer(save_dir=self.save_dir)
        except ImportError:
            self.visualizer = None

        self.results = {}
        self.dimension_weights_cache = {}
    
    def _map_industry(self, industry: str) -> str:
        """
        映射行业名称
        
        Args:
            industry: Resume_Recognition_Model 识别的行业值
            
        Returns:
            映射后的行业名称
        """
        mapped = self.INDUSTRY_MAPPING.get(industry, "研发")
        
        if self.verbose:
            if industry != mapped:
                print(f"  [MAP] {industry} -> {mapped}")
            else:
                print(f"  [INDUSTRY] {mapped}")
        
        return mapped
    
    def _map_industry_to_job_type(self, industry: str) -> str:
        """
        根据行业自动判断岗位类型
        
        Args:
            industry: 行业名称
            
        Returns:
            "technical" 或 "management"
        """
        technical_industries = ["研发", "生产", "电商"]
        
        if industry in technical_industries:
            return "technical"
        else:
            return "management"
    
    def _quantify_resume(self, resume: Dict, job_type: str) -> np.ndarray:
        """
        量化单份简历为指标向量
        
        Args:
            resume: 简历字典
            job_type: 岗位类型
            
        Returns:
            指标向量 (5 维)
        """
        indicators = self.ahp_matrices.get_indicators(job_type)
        values = np.zeros(len(indicators))
        
        entities = resume.get("entities", {})
        education_experiences = resume.get("education_experiences", [])
        work_experiences = resume.get("work_experiences", [])
        achievements = resume.get("achievements", [])
        company_ratings = resume.get("company_ratings", [])
        university_ratings = resume.get("university_ratings", [])
        
        if job_type == "technical":
            # 1. 学历
            if education_experiences:
                degree_map = {"博士": 5, "硕士": 4, "本科": 3, "大专": 2, "高中": 1}
                max_degree = max(
                    degree_map.get(edu.get("degree", ""), 3) 
                    for edu in education_experiences
                )
                values[0] = max_degree
            else:
                values[0] = 3
            
            # 2. 专业技能（从技能词数量和质量评估）
            skills = entities.get("skills", [])
            values[1] = min(len(skills) * 0.5 + 1, 5)
            
            # 3. 项目经验
            project_experiences = resume.get("project_experiences", [])
            values[2] = min(len(project_experiences) * 1.0 + 2, 5)
            
            # 4. 工作成果
            values[3] = min(len(achievements) * 0.8 + 2, 5)
            
            # 5. 工作年限
            work_duration_months = resume.get("work_duration_months", 0)
            work_years = work_duration_months / 12.0
            values[4] = min(work_years + 1, 5)
        
        else:  # management
            # 1. 学历
            if education_experiences:
                degree_map = {"博士": 5, "硕士": 4, "本科": 3, "大专": 2, "高中": 1}
                max_degree = max(
                    degree_map.get(edu.get("degree", ""), 3) 
                    for edu in education_experiences
                )
                values[0] = max_degree
            else:
                values[0] = 3
            
            # 2. 工作经历
            n_works = len(work_experiences) if work_experiences else 0
            work_duration_months = resume.get("work_duration_months", 0)
            values[1] = min(n_works * 0.5 + work_duration_months / 24 + 2, 5)
            
            # 3. 情商沟通（从软技能词和跨部门经历评估）
            soft_skill_keywords = ["沟通", "协调", "领导", "团队", "管理", "谈判"]
            soft_skill_count = sum(
                1 for skill in entities.get("skills", [])
                if any(kw in skill for kw in soft_skill_keywords)
            )
            values[2] = min(soft_skill_count * 0.8 + 2, 5)
            
            # 4. 稳定性
            if n_works > 0 and work_duration_months > 0:
                avg_tenure = work_duration_months / n_works / 12  # 年平均
                values[3] = min(avg_tenure + 2, 5)
            else:
                values[3] = 3
            
            # 5. 管理成果
            management_keywords = ["管理", "带领", "负责", "团队", "业绩", "增长"]
            management_achievements = sum(
                1 for ach in achievements
                if any(kw in ach.get("original_text", "") for kw in management_keywords)
            )
            values[4] = min(management_achievements * 1.0 + 2, 5)
        
        return values
    
    def quantify_resumes(
        self, 
        resumes: List[Dict], 
        job_type: str
    ) -> np.ndarray:
        """
        量化多份简历为数据矩阵
        
        Args:
            resumes: 简历列表
            job_type: 岗位类型
            
        Returns:
            数据矩阵 (n_samples × n_indicators)
        """
        n_resumes = len(resumes)
        n_indicators = len(self.ahp_matrices.get_indicators(job_type))
        
        data_matrix = np.zeros((n_resumes, n_indicators))
        
        for i, resume in enumerate(resumes):
            data_matrix[i] = self._quantify_resume(resume, job_type)
        
        return data_matrix
    
    def get_dimension_weights(
        self,
        industry: str,
        resumes: Union[str, List[Dict]],
        job_type: Optional[str] = None
    ) -> Dict[str, float]:
        """
        获取行业专属的维度权重（核心方法）
        
        Args:
            industry: 行业名称（来自 Resume_Recognition_Model 的 industry 字段）
            resumes: 简历数据（文件路径或列表）
            job_type: 岗位类型（可选，默认根据行业自动判断）
            
        Returns:
            维度权重大字典 {education, experience, skill_achievement, comprehensive}
        """
        # 1. 映射行业
        mapped_industry = self._map_industry(industry)
        
        # 2. 自动判断岗位类型
        if job_type is None:
            job_type = self._map_industry_to_job_type(mapped_industry)
        
        # 3. 检查缓存
        cache_key = f"{mapped_industry}_{job_type}_{self.alpha}"
        if cache_key in self.dimension_weights_cache:
            if self.verbose:
                print(f"  [CACHE] Using cached weights: {cache_key}")
            return self.dimension_weights_cache[cache_key]
        
        # 4. 加载简历数据
        if isinstance(resumes, str):
            with open(resumes, 'r', encoding='utf-8') as f:
                resumes = json.load(f)
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"[CALC] Industry Weight Matrix: {mapped_industry} ({job_type})")
            print(f"{'='*60}")
            print(f"[INFO] Resume count: {len(resumes)}")
        
        # 5. 量化简历
        all_data = self.quantify_resumes(resumes, job_type)
        
        # 6. 计算行业专属权重
        result = self.calculator.calculate_industry_weights(
            industry=mapped_industry,
            job_type=job_type,
            all_resumes_data=all_data,
            min_industry_samples=8
        )
        
        # 7. 将指标权重映射到维度权重
        indicator_weights = dict(zip(result["indicators"], result["combined_weights"]))
        dimension_weights = self._map_indicator_weights_to_dimensions(
            indicator_weights, 
            job_type
        )
        
        # 8. 保存结果
        self.results[mapped_industry] = {
            "industry": mapped_industry,
            "original_industry": industry,
            "job_type": job_type,
            "indicator_weights": indicator_weights,
            "dimension_weights": dimension_weights,
            "calculation_result": result
        }
        
        self.dimension_weights_cache[cache_key] = dimension_weights
        
        if self.verbose:
            print(f"\n[OK] Industry weights calculated")
            self._print_dimension_weights(dimension_weights)
            print(f"{'='*60}\n")
        
        return dimension_weights
    
    def _map_indicator_weights_to_dimensions(
        self, 
        indicator_weights: Dict[str, float],
        job_type: str
    ) -> Dict[str, float]:
        """
        将指标权重映射到维度权重
        
        Args:
            indicator_weights: 指标权重大字典
            job_type: 岗位类型
            
        Returns:
            维度权重大字典
        """
        mapping = self.INDICATOR_TO_DIMENSION[job_type]
        
        dimension_weights = {
            "education": 0.0,
            "experience": 0.0,
            "skill_achievement": 0.0,
            "comprehensive": 0.0
        }
        
        for indicator, weight in indicator_weights.items():
            dimension = mapping.get(indicator)
            if dimension:
                dimension_weights[dimension] += weight
        
        # 归一化
        total = sum(dimension_weights.values())
        if total > 0:
            dimension_weights = {k: v / total for k, v in dimension_weights.items()}
        else:
            # 默认权重
            if job_type == "technical":
                dimension_weights = {
                    "education": 0.15,
                    "experience": 0.30,
                    "skill_achievement": 0.35,
                    "comprehensive": 0.20
                }
            else:
                dimension_weights = {
                    "education": 0.15,
                    "experience": 0.35,
                    "skill_achievement": 0.25,
                    "comprehensive": 0.25
                }
        
        return dimension_weights
    
    def get_all_industry_weights(
        self,
        resumes: Union[str, List[Dict]]
    ) -> Dict[str, Dict[str, float]]:
        """
        获取所有行业的维度权重
        
        Args:
            resumes: 简历数据
            
        Returns:
            所有行业的权重大字典 {industry: {dimension: weight}}
        """
        all_weights = {}
        
        for industry in self.ahp_matrices.get_all_industries():
            weights = self.get_dimension_weights(industry, resumes)
            all_weights[industry] = weights
        
        return all_weights
    
    def _print_dimension_weights(self, weights: Dict[str, float]) -> None:
        """打印维度权重"""
        dimension_names = {
            "education": "教育背景 (Sedu)",
            "experience": "工作经历 (Sexp)",
            "skill_achievement": "技能与成果 (Sskill)",
            "comprehensive": "综合素质 (Sadj)"
        }
        
        print("\n  维度权重:")
        for dim, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            dim_name = dimension_names.get(dim, dim)
            print(f"    {dim_name:15s}: {weight:.4f} ({weight*100:.2f}%)")
    
    def get_weight_matrix(self) -> np.ndarray:
        """
        获取完整的行业权重矩阵 W
        
        返回一个 6×4 的矩阵，行表示行业，列表示维度
        
        Returns:
            权重矩阵 (6 行业 × 4 维度)
        """
        industries = self.ahp_matrices.get_all_industries()
        dimensions = ["education", "experience", "skill_achievement", "comprehensive"]
        
        matrix = np.zeros((len(industries), len(dimensions)))
        
        for i, industry in enumerate(industries):
            if industry in self.results:
                weights = self.results[industry]["dimension_weights"]
                for j, dim in enumerate(dimensions):
                    matrix[i, j] = weights.get(dim, 0.25)
            else:
                matrix[i, :] = 0.25  # 默认权重
        
        return matrix
    
    def get_industry_characteristics(self, industry: str) -> str:
        """
        获取行业特点描述
        
        Args:
            industry: 行业名称
            
        Returns:
            行业特点描述
        """
        mapped_industry = self._map_industry(industry)
        return self.ahp_matrices.get_industry_characteristics(mapped_industry)
    
    def print_all_industries_summary(self) -> None:
        """打印所有行业的权重摘要"""
        print("\n" + "="*80)
        print("行业权重矩阵摘要")
        print("="*80)
        
        for industry in self.ahp_matrices.get_all_industries():
            print(f"\n【{industry}】")
            print(f"  特点：{self.get_industry_characteristics(industry)}")
            
            if industry in self.results:
                weights = self.results[industry]["dimension_weights"]
                self._print_dimension_weights(weights)
        
        print("\n" + "="*80)
