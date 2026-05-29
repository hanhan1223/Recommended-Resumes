"""
分维度评分主模型

整合所有模块，提供统一的高层 API：
- 六维评分计算（教育背景、工作经历、技能与成果、综合素质、成长潜力、岗位匹配）
- 权重映射与聚合
- D-TCI 动态人才竞争力指数计算（含加分/惩罚项）
- 结果导出
"""

import json
import re
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union

from .dimensional_scorer import DimensionalScorer
from .dimension_mapper import DimensionMapper


def _extract_name_from_filename(filename: str) -> str:
    """
    从简历文件名中提取候选人姓名

    支持的格式：
    - Java实习生-张泽轩-华南理工大学广州学院-大三.pdf
    - 张泽轩-Java实习生.pdf
    - 20230424-WCG-电子商务总监()-for-电商运营负责人.docx
    - 研发2/20240316-LZ博士-研发总监（）-for研究院院长.docx
    - 20250430-荐首席科学家- ZQQ博士-研发总监（）.docx

    Args:
        filename: 文件名（可能包含路径）

    Returns:
        提取的候选人姓名
    """
    import re

    file_path_obj = Path(filename)
    name = file_path_obj.stem

    exclude_keywords = ['for', 'PDF', 'DOCX', 'DOC', 'TXT']
    chinese_name_pattern = re.compile(r'^[\u4e00-\u9fff]{2,4}$')
    english_pattern = re.compile(r'^[A-Z]{2,5}$')
    mixed_pattern = re.compile(r'^([A-Z]{2,5})([\u4e00-\u9fff]{1,3})$')

    job_keywords = ['总监', '经理', '工程师', '研发', '技术', '运营', '主管', '负责人', '专员', '助理', '实习生',
                    '博士', '硕士', '学士', '候选人', '推荐']

    clean_name = name.replace('（', '-').replace('）', '-').replace('()', '-').replace('（', '').replace('）', '')
    segments = clean_name.split('-')

    mixed_candidates = []
    english_candidates = []
    chinese_candidates = []

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        if seg.isdigit():
            continue
        seg_upper = seg.upper()
        if seg_upper in exclude_keywords:
            continue

        if mixed_pattern.match(seg):
            mixed_candidates.append(seg)
        elif english_pattern.match(seg):
            english_candidates.append(seg)
        elif chinese_name_pattern.match(seg):
            if seg not in job_keywords and seg not in ['有限公司', '大学', '学院', '公司', '集团', '股份', '华南理工']:
                chinese_candidates.append(seg)

    if mixed_candidates:
        return mixed_candidates[0]
    if english_candidates:
        return english_candidates[0]
    if chinese_candidates:
        return chinese_candidates[0]

    for seg in segments:
        seg = seg.strip()
        if seg and not seg.isdigit():
            seg_upper = seg.upper()
            if seg_upper not in exclude_keywords:
                is_job = any(job in seg for job in job_keywords)
                if not is_job:
                    if re.match(r'^[A-Za-z]+$', seg) and len(seg) <= 10:
                        return seg
                    if re.match(r'^[\u4e00-\u9fff]+$', seg) and len(seg) >= 2:
                        return seg

    return segments[0] if segments else name


class DimensionalScoringModel:
    """
    分维度评分模型主类

    整合以下模块：
    - 六维评分计算（教育背景、工作经历、技能与成果、综合素质、成长潜力、岗位匹配）
    - 维度映射与权重聚合（从 weight_model 映射）
    - D-TCI 动态人才竞争力指数计算（含成长加分、风险惩罚、岗位匹配修正）
    - Person_job_fit_model 集成（成长潜力、风险评估、岗位匹配）
    """

    # 行业默认岗位画像（用于岗位匹配评分）
    DEFAULT_JOB_PROFILES = {
        "电商": {"title": "电商运营", "education": "本科", "work_years": 3, "skills": ["电商运营", "数据分析", "推广", "供应链"], "industry": "电商"},
        "品牌": {"title": "品牌经理", "education": "本科", "work_years": 3, "skills": ["品牌策划", "市场营销", "传播", "创意"], "industry": "品牌"},
        "销售": {"title": "销售经理", "education": "本科", "work_years": 3, "skills": ["销售", "客户关系", "谈判", "渠道"], "industry": "销售"},
        "研发": {"title": "研发工程师", "education": "本科", "work_years": 3, "skills": ["编程", "架构设计", "技术方案", "项目管理"], "industry": "研发"},
        "生产": {"title": "生产主管", "education": "本科", "work_years": 5, "skills": ["生产管理", "质量管理", "精益生产", "成本控制"], "industry": "生产"},
        "人力资源": {"title": "HR经理", "education": "本科", "work_years": 3, "skills": ["招聘", "培训", "薪酬绩效", "员工关系"], "industry": "人力资源"},
        "technical": {"title": "技术工程师", "education": "本科", "work_years": 3, "skills": ["专业技能", "项目管理"], "industry": "技术"},
        "management": {"title": "管理岗", "education": "本科", "work_years": 5, "skills": ["团队管理", "组织协调", "战略规划"], "industry": "管理"},
    }

    def __init__(
        self,
        save_dir: Optional[str] = None,
        verbose: bool = True
    ):
        """
        初始化分维度评分模型

        Args:
            save_dir: 可视化结果保存目录（可选）
            verbose: 是否打印详细输出
        """
        self.verbose = verbose

        self.scorer = DimensionalScorer()
        self.mapper = DimensionMapper()

        # 尝试集成 Person_job_fit_model
        self.person_job_fit_model = None
        try:
            import sys
            from pathlib import Path
            backend_dir = str(Path(__file__).parent.parent)
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            from Person_job_fit_model import PersonJobFitModel
            self.person_job_fit_model = PersonJobFitModel(verbose=False)
            if self.verbose:
                print("[OK] Person_job_fit_model 已集成（成长潜力+风险评估+岗位匹配）")
        except Exception as e:
            if self.verbose:
                print(f"[INFO] Person_job_fit_model 未集成，使用4维评分模式: {e}")

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
                print(f"[OK] 已加载 {len(resumes)} 份简历 from {file_path.name}")

            return resumes
        elif isinstance(data_source, list):
            if self.verbose:
                print(f"[OK] 已加载 {len(data_source)} 份简历")
            return data_source
        else:
            raise TypeError("data_source must be a file path (str) or list of resume dicts")

    def calculate(
        self,
        resumes: Union[str, List[Dict]],
        weight_model_results: Optional[Dict] = None,
        job_type: str = "technical",
        dimension_weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        计算维度得分（主方法）

        Args:
            resumes: 简历数据（文件路径或列表）
            weight_model_results: weight_model 的计算结果（可选）
            job_type: 岗位类型 ("technical" 或 "management")
            dimension_weights: 直接传入的维度权重（可选，优先级最高）

        Returns:
            计算结果字典
        """
        if isinstance(resumes, str):
            resumes = self.load_resumes(resumes)

        if not resumes:
            raise ValueError("No resumes to process")

        if self.verbose:
            print("\n" + "="*60)
            print(f"开始计算维度得分 (岗位类型：{'技术类' if job_type == 'technical' else '管理类'})")
            print("="*60)

        if dimension_weights:
            if self.verbose:
                print(f"\n[OK] 使用传入的动态维度权重")
                self._print_weights(dimension_weights)
        elif weight_model_results:
            dimension_weights = self.mapper.map_weights(weight_model_results, job_type)
            if self.verbose:
                print(f"\n[OK] 已从 weight_model 映射维度权重")
                self._print_weights(dimension_weights)
        else:
            # 使用默认权重
            dimension_weights = self.mapper._get_default_weights(job_type)
            if self.verbose:
                print(f"\n[OK] 使用默认维度权重")
                self._print_weights(dimension_weights)

        all_results = []
        default_job_profile = self.DEFAULT_JOB_PROFILES.get(job_type, self.DEFAULT_JOB_PROFILES["technical"])

        for i, resume in enumerate(resumes, 1):
            if self.verbose:
                print(f"\n【{i}/{len(resumes)}】计算第 {i} 份简历...")

            # Person_job_fit_model 评估
            potential_score = None
            risk_score = None
            matching_score = None
            growth_bonus = 0.0
            risk_penalty = 0.0
            matching_correction = 0.0

            if self.person_job_fit_model:
                try:
                    # 成长潜力评估
                    potential_result = self.person_job_fit_model.single_potential_evaluation(resume)
                    if potential_result and "potential_score" in potential_result:
                        potential_score = potential_result["potential_score"]

                    # 风险评估
                    risk_result = self.person_job_fit_model.single_risk_assessment(resume)
                    if risk_result and "overall_risk_score" in risk_result:
                        risk_score = risk_result["overall_risk_score"]

                    # 岗位匹配评估
                    matching_result = self.person_job_fit_model.single_matching(resume, default_job_profile)
                    if matching_result and "overall_score" in matching_result:
                        matching_score = matching_result["overall_score"]
                except Exception as e:
                    if self.verbose:
                        print(f"  [WARN] Person_job_fit_model 评估异常: {e}")

            # 六维评分
            dimensional_scores = self.scorer.calculate_all_dimensions(
                resume, job_type,
                potential_score=potential_score,
                matching_score=matching_score
            )

            normalized_scores = self.mapper.map_scores(dimensional_scores["dimensional_scores"], job_type)

            # 计算加分/惩罚项
            if potential_score is not None:
                growth_bonus = 0.1 * (min(max(potential_score, 0), 10) / 2.0 - 3.0) / 2.0
            if risk_score is not None:
                risk_penalty = -0.15 * (min(max(risk_score, 0), 10) / 10.0)
            if matching_score is not None:
                matching_correction = 0.1 * (min(max(matching_score, 0), 5) - 3.0) / 2.0

            # D-TCI 计算
            tci_score = self.mapper.calculate_tci(
                normalized_scores, dimension_weights,
                growth_bonus=growth_bonus,
                risk_penalty=risk_penalty,
                matching_correction=matching_correction
            )

            penalty_applied = dimensional_scores["details"]["comprehensive_details"].get("penalty_triggered", False)

            # 使用简历中的真实姓名
            basic_info = resume.get('basic_info', {}) or {}
            candidate_name = basic_info.get('name')

            # 如果姓名为空、None或空字符串，尝试使用文件名
            if not candidate_name or (isinstance(candidate_name, str) and not candidate_name.strip()):
                file_name = resume.get('file_name', '')
                if file_name:
                    candidate_name = _extract_name_from_filename(file_name)
                else:
                    candidate_name = f"候选人{i+1}"

            result = {
                "candidate_id": candidate_name,
                "job_type": job_type,
                "dimensional_scores": normalized_scores,
                "tci_score": tci_score,
                "penalty_applied": penalty_applied,
                "dimension_weights": dimension_weights,
                "details": dimensional_scores["details"],
                "d_tci_breakdown": {
                    "base_weighted_sum": tci_score - growth_bonus - risk_penalty - matching_correction,
                    "growth_bonus": round(growth_bonus, 4),
                    "risk_penalty": round(risk_penalty, 4),
                    "matching_correction": round(matching_correction, 4),
                    "final_d_tci": tci_score
                }
            }

            all_results.append(result)

            if self.verbose:
                print(f"  TCI 得分：{tci_score:.2f}")
                if penalty_applied:
                    print(f"  [WARN] 触发跳槽惩罚")

        self.results = {
            "job_type": job_type,
            "n_resumes": len(resumes),
            "dimension_weights": dimension_weights,
            "candidates": all_results,
            "summary": self._generate_summary(all_results)
        }

        if self.verbose:
            print("\n" + "="*60)
            print("[OK] 维度得分计算完成！")
            print("="*60)

        return self.results

    def _generate_summary(self, candidates: List[Dict]) -> Dict:
        """
        生成结果摘要

        Args:
            candidates: 候选人结果列表

        Returns:
            摘要字典
        """
        if not candidates:
            return {}

        tci_scores = [c["tci_score"] for c in candidates]

        ranking = sorted(
            enumerate(candidates, 1),
            key=lambda x: x[1]["tci_score"],
            reverse=True
        )

        return {
            "avg_tci": float(np.mean(tci_scores)),
            "max_tci": float(np.max(tci_scores)),
            "min_tci": float(np.min(tci_scores)),
            "std_tci": float(np.std(tci_scores)),
            "top_3": [
                {
                    "rank": i,
                    "candidate": candidates[idx-1]["candidate_id"],
                    "tci_score": candidates[idx-1]["tci_score"]
                }
                for i, (idx, _) in enumerate(ranking[:3], 1)
            ],
            "penalty_count": sum(1 for c in candidates if c["penalty_applied"])
        }

    def export_results(self, output_path: str, format: str = "json") -> None:
        """
        导出计算结果

        Args:
            output_path: 输出文件路径
            format: 输出格式 ("json"、"csv" 或 "excel")
        """
        if not self.results:
            raise ValueError("请先调用 calculate() 方法计算得分")

        if format == "json":
            export_data = self._prepare_json_export()
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            if self.verbose:
                print(f"[OK] 结果已导出到：{output_path}")

        elif format == "csv":
            try:
                import pandas as pd
                df = self._prepare_csv_export()
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                if self.verbose:
                    print(f"[OK] 结果已导出到：{output_path}")
            except ImportError:
                raise ImportError("需要安装 pandas: pip install pandas")

        elif format == "excel":
            try:
                import pandas as pd
                df = self._prepare_csv_export()
                df.to_excel(output_path, index=False, engine='openpyxl')
                if self.verbose:
                    print(f"[OK] 结果已导出到：{output_path}")
            except ImportError:
                raise ImportError("需要安装 pandas 和 openpyxl: pip install pandas openpyxl")

        else:
            raise ValueError(f"Unsupported format: {format}. 支持: json, csv, excel")

    def _prepare_json_export(self) -> Dict:
        """准备 JSON 导出数据"""
        export_data = {
            "job_type": self.results["job_type"],
            "n_resumes": self.results["n_resumes"],
            "dimension_weights": self.results["dimension_weights"],
            "summary": self.results["summary"],
            "candidates": []
        }

        for candidate in self.results["candidates"]:
            candidate_export = {
                "candidate_id": candidate["candidate_id"],
                "job_type": candidate["job_type"],
                "dimensional_scores": candidate["dimensional_scores"],
                "tci_score": candidate["tci_score"],
                "penalty_applied": candidate["penalty_applied"],
                "dimension_weights": candidate["dimension_weights"]
            }
            export_data["candidates"].append(candidate_export)

        return export_data

    def _prepare_csv_export(self) -> 'pd.DataFrame':
        """准备 CSV 导出数据"""
        import pandas as pd

        rows = []
        for candidate in self.results["candidates"]:
            scores = candidate["dimensional_scores"]
            weights = candidate["dimension_weights"]
            row = {
                "candidate_id": candidate["candidate_id"],
                "job_type": candidate["job_type"],
                "education_score": scores.get("education", 0),
                "experience_score": scores.get("experience", 0),
                "skill_achievement_score": scores.get("skill_achievement", 0),
                "comprehensive_score": scores.get("comprehensive", 0),
                "growth_potential_score": scores.get("growth_potential", 0),
                "job_matching_score": scores.get("job_matching", 0),
                "tci_score": candidate["tci_score"],
                "penalty_applied": candidate["penalty_applied"],
                "wedu_weight": weights.get("education", 0),
                "wexp_weight": weights.get("experience", 0),
                "wskill_weight": weights.get("skill_achievement", 0),
                "wadj_weight": weights.get("comprehensive", 0),
                "wpot_weight": weights.get("growth_potential", 0),
                "wmatch_weight": weights.get("job_matching", 0)
            }
            rows.append(row)

        return pd.DataFrame(rows)

    def get_ranking(self) -> List[Dict]:
        """
        获取候选人排名

        Returns:
            排名列表，包含TCI分数和维度得分
        """
        if not self.results:
            raise ValueError("请先调用 calculate() 方法")

        ranking = sorted(
            self.results["candidates"],
            key=lambda x: x["tci_score"],
            reverse=True
        )

        return [
            {
                "rank": i,
                "candidate_id": c["candidate_id"],
                "tci_score": c["tci_score"],
                "penalty_applied": c["penalty_applied"],
                "dimensional_scores": c.get("dimensional_scores", {
                    "education": 0,
                    "experience": 0,
                    "skill_achievement": 0,
                    "comprehensive": 0,
                    "growth_potential": 0,
                    "job_matching": 0
                })
            }
            for i, c in enumerate(ranking, 1)
        ]

    def print_summary(self) -> None:
        """打印结果摘要"""
        if not self.results:
            print("请先调用 calculate() 方法计算得分")
            return

        print("\n" + "="*60)
        print("分维度评分结果摘要")
        print("="*60)
        job_type_name = self._get_job_type_name(self.results['job_type'])
        print(f"岗位类型：{job_type_name}")
        print(f"简历数量：{self.results['n_resumes']} 份")

        print(f"\n维度权重:")
        self._print_weights(self.results["dimension_weights"])

        print(f"\nTCI 得分统计:")
        summary = self.results["summary"]
        print(f"  平均分：{summary['avg_tci']:.2f}")
        print(f"  最高分：{summary['max_tci']:.2f}")
        print(f"  最低分：{summary['min_tci']:.2f}")
        print(f"  标准差：{summary['std_tci']:.2f}")

        print(f"\nTop 3 候选人:")
        for item in summary["top_3"]:
            print(f"  {item['rank']}. {item['candidate']} - {item['tci_score']:.2f}")

        if summary["penalty_count"] > 0:
            print(f"\n[WARN] 跳槽惩罚触发：{summary['penalty_count']} 人")

        print("="*60)

    def _print_weights(self, weights: Dict[str, float]) -> None:
        """打印权重"""
        dimension_names = {
            "education": "教育背景",
            "experience": "工作经历",
            "skill_achievement": "技能与成果",
            "comprehensive": "综合素质",
            "growth_potential": "成长潜力",
            "job_matching": "岗位匹配"
        }

        for dim, weight in weights.items():
            dim_name = dimension_names.get(dim, dim)
            print(f"  {dim_name:10s}: {weight:.4f} ({weight*100:.2f}%)")

    def _get_job_type_name(self, job_type: str) -> str:
        """获取岗位类型的中文名称"""
        job_type_names = {
            "technical": "技术类",
            "management": "管理类",
            "电商": "电商行业",
            "品牌": "品牌市场",
            "销售": "销售业务",
            "研发": "研发技术",
            "生产": "生产管理",
            "人力资源": "人力资源"
        }
        return job_type_names.get(job_type, job_type)
