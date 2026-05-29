# -*- coding: utf-8 -*-
"""
消融实验模块 (Ablation Study)

对人才简历综合优选系统的权重策略进行消融实验，比较不同权重方案下的排名差异。

4 种权重策略：
1. 等权法 (Equal Weights)    - Wedu=Wexp=Wskill=Wadj=0.25
2. 仅 AHP (主观权重)         - 仅使用层次分析法权重
3. 仅熵权法 (客观权重)       - 仅使用熵权法权重
4. AHP-熵权融合 (alpha=0.5)  - 主客观权重各占 50%

TCI 公式: TCI = Wedu*Sedu + Wexp*Sexp + Wskill*Sskill + Wadj*Sadj

评估指标：
- Spearman 秩相关系数
- Kendall tau 秩相关系数
- 排名稳定性指标
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 尝试导入 scipy，不可用时使用手动实现
try:
    from scipy.stats import spearmanr, kendalltau
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger.warning("scipy 未安装，将使用手动实现的秩相关计算")

from app.data_manager import ResumeDataManager
from weight_model import WeightDeterminationModel
from Dimensional_scoring_model import DimensionalScoringModel, DimensionMapper


class AblationStudy:
    """
    消融实验类

    通过控制权重策略变量，评估不同权重计算方法对简历排名的影响。
    使用 Spearman / Kendall 秩相关系数衡量排名一致性，用排名波动衡量稳定性。

    使用方法::

        study = AblationStudy()
        report = study.generate_report("电商")
        print(report["conclusion"])
    """

    # 四维度名称常量
    DIMENSIONS = ["education", "experience", "skill_achievement", "comprehensive"]

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化消融实验

        Args:
            project_root: 项目根目录路径。为 None 时自动推断为 backend 的父目录。
        """
        if project_root is not None:
            self._project_root = Path(project_root)
        else:
            # 默认: backend/ 的父目录即项目根目录
            self._project_root = Path(__file__).resolve().parent.parent

        self.data_manager = ResumeDataManager(self._project_root)
        self.weight_model = WeightDeterminationModel(alpha=0.5, verbose=False)
        self.dim_model = DimensionalScoringModel(verbose=False)
        self.dim_mapper = DimensionMapper()

        # 缓存: WeightDeterminationModel 的计算结果，避免重复计算
        self._weight_cache: Optional[Dict] = None
        self._cached_resumes_key: Optional[str] = None

    # ------------------------------------------------------------------
    # 数据获取
    # ------------------------------------------------------------------

    def _load_resumes(self, industry: str) -> List[Dict]:
        """
        获取指定行业的简历列表

        Args:
            industry: 行业名称（中文，如 "电商"、"品牌"）

        Returns:
            该行业下的简历字典列表

        Raises:
            ValueError: 未找到该行业的简历数据
        """
        resumes = self.data_manager.get_resumes_by_industry(industry)

        if not resumes:
            all_resumes = self.data_manager.get_all_resumes()
            if not all_resumes:
                raise ValueError(
                    f"数据源中无任何简历。请先上传简历数据。"
                )
            raise ValueError(
                f"未找到行业 '{industry}' 的简历数据。"
                f"可用行业: {sorted(set(r.get('industry', '未知') for r in all_resumes))}"
            )

        return resumes

    def _get_weight_results(self, resumes: List[Dict]) -> Dict:
        """
        获取权重计算结果（带缓存）

        Args:
            resumes: 简历列表

        Returns:
            WeightDeterminationModel.calculate() 的返回结果
        """
        cache_key = str(id(resumes))
        if self._weight_cache is not None and self._cached_resumes_key == cache_key:
            return self._weight_cache

        results = self.weight_model.calculate(resumes)
        self._weight_cache = results
        self._cached_resumes_key = cache_key
        return results

    # ------------------------------------------------------------------
    # 权重提取
    # ------------------------------------------------------------------

    def _extract_dimension_weights(
        self, weight_results: Dict, job_type: str, source: str
    ) -> Dict[str, float]:
        """
        从权重模型结果中提取四维度权重

        权重模型输出 5 个指标权重（AHP / 熵权法 / 融合），
        通过 DimensionMapper 映射到 4 个维度（教育、经历、技能成果、综合）。

        Args:
            weight_results: WeightDeterminationModel.calculate() 的返回值
            job_type: 岗位类型 ("technical" / "management" / 行业名)
            source: 权重来源，"ahp" / "entropy" / "combined"

        Returns:
            四维度权重字典 {"education": ..., "experience": ..., ...}
        """
        source_key_map = {
            "ahp": "ahp_weights",
            "entropy": "ewm_weights",
            "combined": "combined_weights",
        }
        key = source_key_map.get(source)
        if key is None:
            raise ValueError(f"未知的权重来源: {source}，应为 ahp/entropy/combined")

        src_weights = weight_results.get(key)
        if src_weights is None:
            raise KeyError(f"权重结果中未找到 '{key}' 字段")

        # 构造临时 results 字典供 DimensionMapper 使用
        mapped_input = {
            "indicators": weight_results.get("indicators", []),
            "combined_weights": src_weights,
        }
        return self.dim_mapper.map_weights(mapped_input, job_type)

    # ------------------------------------------------------------------
    # 4 种权重策略
    # ------------------------------------------------------------------

    def run_equal_weights(self, resumes: List[Dict]) -> List[Dict]:
        """
        策略 1: 等权法

        四个维度各分配 0.25 权重。

        Args:
            resumes: 简历列表

        Returns:
            排名列表 [{"id": ..., "name": ..., "score": ..., "rank": ...}, ...]
        """
        equal_dim_weights = {dim: 0.25 for dim in self.DIMENSIONS}
        return self._score_and_rank(resumes, equal_dim_weights)

    def run_ahp_only(self, resumes: List[Dict]) -> List[Dict]:
        """
        策略 2: 仅 AHP 主观权重

        通过 AHP 层次分析法计算 5 指标权重，映射到 4 维度。

        Args:
            resumes: 简历列表

        Returns:
            排名列表
        """
        weight_results = self._get_weight_results(resumes)
        job_type = weight_results.get("job_type", "technical")
        dim_weights = self._extract_dimension_weights(weight_results, job_type, "ahp")
        return self._score_and_rank(resumes, dim_weights)

    def run_entropy_only(self, resumes: List[Dict]) -> List[Dict]:
        """
        策略 3: 仅熵权法客观权重

        通过熵权法计算 5 指标权重，映射到 4 维度。

        Args:
            resumes: 简历列表

        Returns:
            排名列表
        """
        weight_results = self._get_weight_results(resumes)
        job_type = weight_results.get("job_type", "technical")
        dim_weights = self._extract_dimension_weights(weight_results, job_type, "entropy")
        return self._score_and_rank(resumes, dim_weights)

    def run_fusion(self, resumes: List[Dict]) -> List[Dict]:
        """
        策略 4: AHP-熵权融合 (alpha=0.5)

        W_final = 0.5 * W_ahp + 0.5 * W_entropy，再映射到 4 维度。

        Args:
            resumes: 简历列表

        Returns:
            排名列表
        """
        weight_results = self._get_weight_results(resumes)
        job_type = weight_results.get("job_type", "technical")
        dim_weights = self._extract_dimension_weights(weight_results, job_type, "combined")
        return self._score_and_rank(resumes, dim_weights)

    # ------------------------------------------------------------------
    # 评分与排名
    # ------------------------------------------------------------------

    def _score_and_rank(
        self, resumes: List[Dict], dimension_weights: Dict[str, float]
    ) -> List[Dict]:
        """
        使用指定维度权重对简历评分并排名

        Args:
            resumes: 简历列表
            dimension_weights: 四维度权重

        Returns:
            按 TCI 降序排列的排名列表，每项含 id/name/score/rank
        """
        results = self.dim_model.calculate(
            resumes, dimension_weights=dimension_weights
        )

        ranked = []
        for i, candidate in enumerate(results.get("candidates", [])):
            candidate_id = candidate.get("candidate_id", f"candidate_{i}")
            ranked.append({
                "id": candidate_id,
                "name": candidate_id,
                "score": round(float(candidate.get("tci_score", 0)), 4),
                "rank": 0,  # 占位，下面赋值
            })

        # 按 score 降序排列，相同分数按原始顺序（稳定排序）
        ranked.sort(key=lambda x: x["score"], reverse=True)
        for idx, item in enumerate(ranked, 1):
            item["rank"] = idx

        return ranked

    # ------------------------------------------------------------------
    # 排名相关性计算
    # ------------------------------------------------------------------

    def compare_rankings(self, method_rankings: Dict[str, List[Dict]]) -> Dict:
        """
        计算所有方法对之间的排名相关性

        Args:
            method_rankings: {方法名: 排名列表}

        Returns:
            {
                "spearman": {pair_key: coefficient, ...},
                "kendall": {pair_key: coefficient, ...},
                "stability": {方法名: stability_metrics, ...}
            }
        """
        method_names = list(method_rankings.keys())
        n_methods = len(method_names)

        # 为每种方法构建 id -> rank 的映射
        rank_maps: Dict[str, Dict[str, int]] = {}
        for method, rankings in method_rankings.items():
            rank_maps[method] = {item["id"]: item["rank"] for item in rankings}

        # 收集所有候选 id（取第一个方法的顺序作为基准）
        all_ids = [item["id"] for item in method_rankings[method_names[0]]]

        spearman_matrix: Dict[str, float] = {}
        kendall_matrix: Dict[str, float] = {}

        for i in range(n_methods):
            for j in range(i + 1, n_methods):
                m1, m2 = method_names[i], method_names[j]
                pair_key = f"{m1}_vs_{m2}"

                ranks_1 = [rank_maps[m1].get(cid, 0) for cid in all_ids]
                ranks_2 = [rank_maps[m2].get(cid, 0) for cid in all_ids]

                spearman_matrix[pair_key] = self._compute_spearman(ranks_1, ranks_2)
                kendall_matrix[pair_key] = self._compute_kendall(ranks_1, ranks_2)

        # 排名稳定性指标
        stability = {}
        for method, rankings in method_rankings.items():
            scores = [item["score"] for item in rankings]
            arr = np.array(scores)
            stability[method] = {
                "avg_score": round(float(np.mean(arr)), 4),
                "std": round(float(np.std(arr)), 4),
                "score_range": round(float(np.max(arr) - np.min(arr)), 4),
                "top3_gap": round(float(arr[0] - arr[2]), 4) if len(arr) >= 3 else 0.0,
            }

        return {
            "spearman": spearman_matrix,
            "kendall": kendall_matrix,
            "stability": stability,
        }

    # ------------------------------------------------------------------
    # 秩相关系数（scipy / 手动回退）
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_spearman(ranks_a: List[int], ranks_b: List[int]) -> float:
        """
        计算 Spearman 秩相关系数

        优先使用 scipy.stats.spearmanr，不可用时手动计算。

        Args:
            ranks_a: 第一组排名
            ranks_b: 第二组排名

        Returns:
            Spearman rho，保留 4 位小数
        """
        a = np.asarray(ranks_a, dtype=float)
        b = np.asarray(ranks_b, dtype=float)

        if len(a) < 2:
            return 1.0

        if HAS_SCIPY:
            corr, _ = spearmanr(a, b)
            return round(float(corr), 4)

        # 手动实现: rho = 1 - (6 * sum(d_i^2)) / (n * (n^2 - 1))
        # （无结值情况；有结值时使用 Pearson of fractional ranks）
        n = len(a)
        d = a - b
        rho = 1.0 - (6.0 * np.sum(d ** 2)) / (n * (n ** 2 - 1))

        # 验证: 对有结值数据使用 Pearson of ranks 修正
        std_a = np.std(a)
        std_b = np.std(b)
        if std_a > 0 and std_b > 0:
            rho_pearson = float(np.corrcoef(a, b)[0, 1])
            # 取两种计算的平均值作为折中（处理结值情况）
            rho = (rho + rho_pearson) / 2.0

        return round(float(np.clip(rho, -1.0, 1.0)), 4)

    @staticmethod
    def _compute_kendall(ranks_a: List[int], ranks_b: List[int]) -> float:
        """
        计算 Kendall tau 秩相关系数

        优先使用 scipy.stats.kendalltau，不可用时手动实现 tau-b。

        Args:
            ranks_a: 第一组排名
            ranks_b: 第二组排名

        Returns:
            Kendall tau，保留 4 位小数
        """
        a = np.asarray(ranks_a, dtype=float)
        b = np.asarray(ranks_b, dtype=float)

        if len(a) < 2:
            return 1.0

        if HAS_SCIPY:
            corr, _ = kendalltau(a, b)
            return round(float(corr), 4)

        # 手动实现 Kendall tau-b（正确处理结值）
        n = len(a)
        concordant = 0
        discordant = 0
        tie_a = 0
        tie_b = 0
        tie_both = 0

        for i in range(n):
            for j in range(i + 1, n):
                da = a[i] - a[j]
                db = b[i] - b[j]

                if da == 0 and db == 0:
                    tie_both += 1
                elif da == 0:
                    tie_a += 1
                elif db == 0:
                    tie_b += 1
                else:
                    sign_product = da * db
                    if sign_product > 0:
                        concordant += 1
                    else:
                        discordant += 1

        n0 = n * (n - 1) / 2.0
        n1 = tie_a
        n2 = tie_b
        n3 = tie_both

        denominator = np.sqrt((n0 - n1) * (n0 - n2))
        if denominator == 0:
            return 0.0

        tau_b = (concordant - discordant) / denominator
        return round(float(np.clip(tau_b, -1.0, 1.0)), 4)

    # ------------------------------------------------------------------
    # 排名变动分析
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_ranking_changes(method_rankings: Dict[str, List[Dict]]) -> List[Dict]:
        """
        计算每个候选人在不同方法下的排名变动

        Args:
            method_rankings: {方法名: 排名列表}

        Returns:
            排名变动列表，按 max_change 降序排列
        """
        method_names = list(method_rankings.keys())

        # 以第一个方法的候选顺序为基准
        base_rankings = method_rankings[method_names[0]]
        all_ids = [item["id"] for item in base_rankings]

        # 构建 id -> name 映射
        id_to_name = {}
        for method, rankings in method_rankings.items():
            for item in rankings:
                id_to_name[item["id"]] = item["name"]

        changes = []
        for cid in all_ids:
            entry: Dict = {"candidate": id_to_name.get(cid, cid)}
            ranks = []

            for method in method_names:
                rank_map = {
                    item["id"]: item["rank"]
                    for item in method_rankings[method]
                }
                r = rank_map.get(cid, 0)
                entry[f"{method}_rank"] = r
                ranks.append(r)

            entry["max_change"] = max(ranks) - min(ranks) if ranks else 0
            changes.append(entry)

        # 按排名变动幅度降序排列
        changes.sort(key=lambda x: x["max_change"], reverse=True)
        return changes

    # ------------------------------------------------------------------
    # 结论生成
    # ------------------------------------------------------------------

    def _generate_conclusion(
        self,
        correlation: Dict,
        ranking_changes: List[Dict],
        stability: Dict,
    ) -> str:
        """
        基于实验数据生成中文结论

        Args:
            correlation: 相关性矩阵
            ranking_changes: 排名变动列表
            stability: 稳定性指标

        Returns:
            结论文本
        """
        spearman = correlation.get("spearman", {})

        # 找到相关性最高和最低的方法对
        if spearman:
            best_pair = max(spearman, key=spearman.get)
            worst_pair = min(spearman, key=spearman.get)
            best_val = spearman[best_pair]
            worst_val = spearman[worst_pair]
        else:
            best_pair, worst_pair = "N/A", "N/A"
            best_val, worst_val = 0.0, 0.0

        # 计算平均排名变动
        avg_change = 0.0
        max_change = 0
        if ranking_changes:
            avg_change = np.mean([c["max_change"] for c in ranking_changes])
            max_change = max(c["max_change"] for c in ranking_changes)

        # 找最稳定的方法（标准差最小）
        most_stable = "N/A"
        if stability:
            most_stable = min(stability, key=lambda m: stability[m]["std"])

        parts = []

        parts.append(
            f"{best_pair.replace('_vs_', '与')}相关性最高({best_val:.2f})，"
            f"说明两种方法的排名高度一致"
        )

        parts.append(
            f"{worst_pair.replace('_vs_', '与')}相关性最低({worst_val:.2f})，"
            f"差异主要源于主客观权重视角不同"
        )

        if avg_change > 0:
            parts.append(
                f"候选人平均排名变动为{avg_change:.1f}位，最大变动{max_change}位"
            )

        if most_stable != "N/A":
            std_val = stability[most_stable]["std"]
            parts.append(
                f"排名最稳定的方法为'{most_stable}'（标准差{std_val:.2f}）"
            )

        # 整体判断
        if best_val >= 0.9:
            parts.append("整体来看，各方法排名高度一致，系统具有较好的鲁棒性")
        elif best_val >= 0.7:
            parts.append("各方法排名基本一致，但权重策略的选择仍会影响部分候选人的排名")
        else:
            parts.append("不同权重策略产生了较大分歧，建议结合实际业务需求选择合适的权重方案")

        return "；".join(parts) + "。"

    # ------------------------------------------------------------------
    # 主报告生成
    # ------------------------------------------------------------------

    def generate_report(self, industry: str) -> Dict:
        """
        生成完整的消融实验报告

        运行 4 种权重策略，计算排名相关性、变动分析，并生成结论。

        Args:
            industry: 行业名称（中文，如 "电商"、"品牌"、"研发"）

        Returns:
            完整报告字典，结构如下::

                {
                    "industry": "电商",
                    "sample_size": 10,
                    "methods": {
                        "equal": {"rankings": [...], "avg_score": 3.2, "std": 0.8},
                        "ahp":    {...},
                        "entropy": {...},
                        "fusion":  {...}
                    },
                    "correlation_matrix": {
                        "spearman": {"equal_vs_ahp": 0.85, ...},
                        "kendall":  {"equal_vs_ahp": 0.82, ...}
                    },
                    "ranking_changes": [
                        {"candidate": "张三", "equal_rank": 1, ..., "max_change": 1}
                    ],
                    "conclusion": "..."
                }

        Raises:
            ValueError: 无可用简历数据
        """
        # 加载简历
        resumes = self._load_resumes(industry)
        n = len(resumes)

        # 单候选人边界情况
        if n == 1:
            return self._single_candidate_report(industry, resumes[0])

        # 清除缓存
        self._weight_cache = None
        self._cached_resumes_key = None

        # 运行 4 种策略
        method_rankings: Dict[str, List[Dict]] = {}
        method_rankings["equal"] = self.run_equal_weights(resumes)
        method_rankings["ahp"] = self.run_ahp_only(resumes)
        method_rankings["entropy"] = self.run_entropy_only(resumes)
        method_rankings["fusion"] = self.run_fusion(resumes)

        # 统计每种方法
        methods_detail: Dict[str, Dict] = {}
        for method_name, rankings in method_rankings.items():
            scores = np.array([item["score"] for item in rankings])
            methods_detail[method_name] = {
                "rankings": rankings,
                "avg_score": round(float(np.mean(scores)), 4),
                "std": round(float(np.std(scores)), 4),
            }

        # 计算相关性
        correlation = self.compare_rankings(method_rankings)

        # 排名变动
        ranking_changes = self._compute_ranking_changes(method_rankings)

        # 生成结论
        conclusion = self._generate_conclusion(
            correlation, ranking_changes, correlation.get("stability", {})
        )

        return {
            "industry": industry,
            "sample_size": n,
            "methods": methods_detail,
            "correlation_matrix": {
                "spearman": correlation.get("spearman", {}),
                "kendall": correlation.get("kendall", {}),
            },
            "ranking_changes": ranking_changes,
            "stability": correlation.get("stability", {}),
            "conclusion": conclusion,
        }

    # ------------------------------------------------------------------
    # 边界情况
    # ------------------------------------------------------------------

    @staticmethod
    def _single_candidate_report(industry: str, resume: Dict) -> Dict:
        """
        仅有 1 名候选人时的简化报告

        Args:
            industry: 行业名
            resume: 简历字典

        Returns:
            简化报告
        """
        basic_info = resume.get("basic_info", {}) or {}
        name = basic_info.get("name", "候选人1")
        if not name or not str(name).strip():
            name = resume.get("file_name", "候选人1")

        single_ranking = [{"id": name, "name": name, "score": 0.0, "rank": 1}]
        methods = {}
        for m in ["equal", "ahp", "entropy", "fusion"]:
            methods[m] = {"rankings": single_ranking, "avg_score": 0.0, "std": 0.0}

        return {
            "industry": industry,
            "sample_size": 1,
            "methods": methods,
            "correlation_matrix": {
                "spearman": {},
                "kendall": {},
            },
            "ranking_changes": [
                {
                    "candidate": name,
                    "equal_rank": 1,
                    "ahp_rank": 1,
                    "entropy_rank": 1,
                    "fusion_rank": 1,
                    "max_change": 0,
                }
            ],
            "stability": {},
            "conclusion": "仅有1名候选人，无法进行排名对比分析。",
        }


# ======================================================================
# 便捷函数
# ======================================================================

def run_ablation_study(
    industry: str,
    project_root: Optional[str] = None,
) -> Dict:
    """
    便捷函数: 运行指定行业的消融实验并返回报告

    Args:
        industry: 行业名称（中文）
        project_root: 项目根目录（可选）

    Returns:
        消融实验报告字典

    Example::

        report = run_ablation_study("电商")
        print(report["conclusion"])
    """
    study = AblationStudy(project_root=project_root)
    return study.generate_report(industry)
