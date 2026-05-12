"""
权重确定主模型

整合 AHP、熵权法、组合权重、数据量化和可视化
提供统一的高层 API
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .ahp import AHPWeightCalculator
from .entropy import EntropyWeightCalculator
from .quantifier import ResumeQuantifier
from .combiner import WeightCombiner


class WeightDeterminationModel:
    """
    权重确定模型主类

    整合以下模块：
    - AHP 层次分析法（主观权重）
    - 熵权法（客观权重）
    - 线性组合（最终权重）
    - 简历数据量化
    - 可视化分析
    """

    def __init__(
        self,
        alpha: float = 0.5,
        save_dir: Optional[str] = None,
        verbose: bool = True
    ):
        """
        初始化权重确定模型

        Args:
            alpha: 主观权重占比系数 (0-1)，默认 0.5
            save_dir: 可视化结果保存目录（可选）
            verbose: 是否打印详细输出
        """
        self.alpha = alpha
        self.verbose = verbose

        self.ahp = AHPWeightCalculator()
        self.entropy = EntropyWeightCalculator()
        self.quantifier = ResumeQuantifier()
        self.combiner = WeightCombiner(alpha=alpha)
        self.visualizer = None

        self.results = {}

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
                raise FileNotFoundError(f"Resume file not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                resumes = json.load(f)

            if self.verbose:
                print(f"✓ 已加载 {len(resumes)} 份简历 from {file_path.name}")

            return resumes
        elif isinstance(data_source, list):
            if self.verbose:
                print(f"✓ 已加载 {len(data_source)} 份简历")
            return data_source
        else:
            raise TypeError("data_source must be a file path (str) or list of resume dicts")

    def classify_job_type(self, industry: str) -> str:
        """
        根据行业分类判断岗位类型

        Args:
            industry: 行业名称

        Returns:
            "technical" 或 "management"
        """
        technical_industries = ["研发", "电商", "生产", "技术", "it", "互联网"]

        if any(keyword in industry.lower() for keyword in technical_industries):
            return "technical"
        else:
            return "management"

    def calculate(
        self,
        resumes: Union[str, List[Dict]],
        job_type: Optional[str] = None,
        industry: Optional[str] = None,
        filter_by_industry: bool = False
    ) -> Dict:
        """
        计算权重（主方法）

        Args:
            resumes: 简历数据（文件路径或列表）
            job_type: 岗位类型（可选）
                     - "technical": 技术类
                     - "management": 管理类
                     - None: 根据 industry 自动判断
            industry: 行业过滤（可选）
            filter_by_industry: 是否按 industry 过滤简历

        Returns:
            计算结果字典
        """
        if isinstance(resumes, str):
            resumes = self.load_resumes(resumes)

        if filter_by_industry and industry:
            resumes = [r for r in resumes if r.get('industry') == industry]
            if self.verbose:
                print(f"✓ 已过滤到 {len(resumes)} 份 {industry} 行业简历")

        if not resumes:
            raise ValueError("No resumes to process")

        if job_type is None:
            if industry:
                job_type = self.classify_job_type(industry)
            else:
                industries = [r.get('industry', '未知') for r in resumes]
                most_common = max(set(industries), key=industries.count)
                job_type = self.classify_job_type(most_common)

            if self.verbose:
                print(f"✓ 自动识别岗位类型：{'技术类' if job_type == 'technical' else '管理类'}")

        if self.verbose:
            print("\n" + "="*60)
            print(f"开始计算权重 (岗位类型：{'技术类' if job_type == 'technical' else '管理类'})")
            print("="*60)

        indicator_names = self.ahp.get_indicators(job_type)

        if self.verbose:
            print(f"\n【1/4】AHP 层次分析法计算主观权重...")
        ahp_weights, ahp_metrics = self.ahp.calculate_weights(job_type)
        if self.verbose:
            print(f"  ✓ 一致性检验：{ahp_metrics['consistency_check']} (CR={ahp_metrics['CR']:.4f})")
            self._print_weights("AHP 主观权重", indicator_names, ahp_weights)

        if self.verbose:
            print(f"\n【2/4】简历数据量化...")
        data_matrix, _ = self.quantifier.quantify_resumes(resumes, job_type)
        if self.verbose:
            print(f"  ✓ 量化完成：{data_matrix.shape[0]} 份简历 × {data_matrix.shape[1]} 个指标")

        if self.verbose:
            print(f"\n【3/4】熵权法计算客观权重...")
        ewm_weights, ewm_metrics = self.entropy.calculate_weights(data_matrix)
        if self.verbose:
            self._print_weights("熵权法客观权重", indicator_names, ewm_weights)

        if self.verbose:
            print(f"\n【4/4】组合权重计算 (α={self.alpha})...")
        combined_weights, combined_metrics = self.combiner.calculate_combined_weights(
            ahp_weights, ewm_weights, self.alpha
        )
        if self.verbose:
            self._print_weights("最终组合权重", indicator_names, combined_weights)

        self.results = {
            "job_type": job_type,
            "alpha": self.alpha,
            "n_resumes": len(resumes),
            "indicators": indicator_names,
            "ahp_weights": ahp_weights,
            "ahp_metrics": ahp_metrics,
            "ewm_weights": ewm_weights,
            "ewm_metrics": ewm_metrics,
            "combined_weights": combined_weights,
            "combined_metrics": combined_metrics,
            "data_matrix": data_matrix,
        }

        if self.verbose:
            print("\n" + "="*60)
            print("✓ 权重计算完成！")
            print("="*60)

        return self.results

    def export_results(self, output_path: str, format: str = "json") -> None:
        """
        导出计算结果

        Args:
            output_path: 输出文件路径
            format: 输出格式 ("json" 或 "csv")
        """
        if not self.results:
            raise ValueError("请先调用 calculate() 方法计算权重")

        export_data = {
            "job_type": self.results['job_type'],
            "alpha": self.results['alpha'],
            "n_resumes": self.results['n_resumes'],
            "indicators": self.results['indicators'],
            "weights": {
                "ahp": self.results['ahp_weights'].tolist(),
                "ewm": self.results['ewm_weights'].tolist(),
                "combined": self.results['combined_weights'].tolist()
            },
            "metrics": {
                "ahp": {
                    "max_eigenvalue": self.results['ahp_metrics']['max_eigenvalue'],
                    "CI": self.results['ahp_metrics']['CI'],
                    "CR": self.results['ahp_metrics']['CR'],
                    "consistency_check": self.results['ahp_metrics']['consistency_check']
                },
                "ewm": {
                    "entropy_values": self.results['ewm_metrics']['entropy_values'],
                    "information_utility": self.results['ewm_metrics']['information_utility']
                }
            }
        }

        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            if self.verbose:
                print(f"✓ 结果已导出到：{output_path}")
        elif format == "csv":
            try:
                import pandas as pd
                df = pd.DataFrame({
                    "指标": self.results['indicators'],
                    "AHP 权重": self.results['ahp_weights'],
                    "熵权法权重": self.results['ewm_weights'],
                    "组合权重": self.results['combined_weights']
                })
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                if self.verbose:
                    print(f"✓ 结果已导出到：{output_path}")
            except ImportError:
                raise ImportError("需要安装 pandas: pip install pandas")
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _print_weights(self, title: str, indicators: List[str], weights: np.ndarray) -> None:
        """打印权重结果"""
        print(f"\n  {title}:")
        for name, weight in zip(indicators, weights):
            print(f"    {name:10s}: {weight:.4f} ({weight*100:.2f}%)")

    def get_ranking(self) -> List[Dict]:
        """
        获取指标重要性排序

        Returns:
            排序列表
        """
        if not self.results:
            raise ValueError("请先调用 calculate() 方法")

        weights = self.results['combined_weights']
        indicators = self.results['indicators']

        sorted_indices = np.argsort(weights)[::-1]

        ranking = []
        for rank, idx in enumerate(sorted_indices, 1):
            ranking.append({
                "rank": rank,
                "indicator": indicators[idx],
                "weight": float(weights[idx]),
                "percentage": f"{weights[idx]*100:.2f}%"
            })

        return ranking

    def print_summary(self) -> None:
        """打印结果摘要"""
        if not self.results:
            print("请先调用 calculate() 方法计算权重")
            return

        print("\n" + "="*60)
        print("权重计算结果摘要")
        print("="*60)
        print(f"岗位类型：{'技术类' if self.results['job_type'] == 'technical' else '管理类'}")
        print(f"简历数量：{self.results['n_resumes']} 份")
        print(f"α 参数：{self.results['alpha']}")
        print(f"AHP 一致性检验：{self.results['ahp_metrics']['consistency_check']} (CR={self.results['ahp_metrics']['CR']:.4f})")

        print("\n指标重要性排序:")
        ranking = self.get_ranking()
        for item in ranking:
            print(f"  {item['rank']}. {item['indicator']:10s} - {item['percentage']}")

        print("="*60)
