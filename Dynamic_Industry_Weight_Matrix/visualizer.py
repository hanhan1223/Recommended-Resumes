"""
行业权重可视化模块

提供以下可视化功能：
1. 行业权重对比热力图
2. 多维度权重对比柱状图
3. 雷达图（展示各行业权重分布）
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager

# 配置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class IndustryWeightVisualizer:
    """行业权重可视化器"""
    
    def __init__(self, save_dir: Optional[str] = None):
        """
        初始化可视化器
        
        Args:
            save_dir: 图表保存目录（可选）
        """
        self.save_dir = Path(save_dir) if save_dir else None
        if self.save_dir:
            self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def plot_heatmap(
        self,
        weight_matrix: np.ndarray,
        industries: List[str],
        dimensions: List[str],
        title: str = "行业权重矩阵热力图",
        show: bool = True,
        save_name: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制行业权重对比热力图
        
        Args:
            weight_matrix: 权重矩阵 (n_industries × n_dimensions)
            industries: 行业列表
            dimensions: 维度列表
            title: 图表标题
            show: 是否显示图表
            save_name: 保存文件名（可选）
            
        Returns:
            Figure 对象
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 绘制热力图
        im = ax.imshow(weight_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=0.5)
        
        # 设置刻度
        ax.set_xticks(np.arange(len(dimensions)))
        ax.set_yticks(np.arange(len(industries)))
        
        # 设置标签
        dimension_labels = {
            "education": "教育背景\n(Sedu)",
            "experience": "工作经历\n(Sexp)",
            "skill_achievement": "技能与成果\n(Sskill)",
            "comprehensive": "综合素质\n(Sadj)"
        }
        
        ax.set_xticklabels([dimension_labels.get(d, d) for d in dimensions])
        ax.set_yticklabels(industries)
        
        # 旋转 x 轴标签
        plt.setp(ax.get_xticklabels(), rotation=0, ha="center", rotation_mode="anchor")
        
        # 创建颜色条
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel('权重值', rotation=-90, va="bottom", labelpad=20)
        
        # 在每个单元格中显示数值
        for i in range(len(industries)):
            for j in range(len(dimensions)):
                text = ax.text(j, i, f'{weight_matrix[i, j]:.3f}',
                              ha="center", va="center", color="black", fontsize=10)
        
        # 设置标题
        ax.set_title(title, fontsize=14, pad=20)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        if save_name and self.save_dir:
            save_path = self.save_dir / f"{save_name}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[OK] 热力图已保存：{save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def plot_bar_comparison(
        self,
        all_weights: Dict[str, Dict[str, float]],
        title: str = "各行业维度权重对比",
        show: bool = True,
        save_name: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制各行业维度权重对比柱状图
        
        Args:
            all_weights: 所有权重大字典 {industry: {dimension: weight}}
            title: 图表标题
            show: 是否显示图表
            save_name: 保存文件名（可选）
            
        Returns:
            Figure 对象
        """
        fig, ax = plt.subplots(figsize=(14, 8))
        
        industries = list(all_weights.keys())
        dimensions = ["education", "experience", "skill_achievement", "comprehensive"]
        
        dimension_labels = {
            "education": "教育背景",
            "experience": "工作经历",
            "skill_achievement": "技能与成果",
            "comprehensive": "综合素质"
        }
        
        x = np.arange(len(industries))
        width = 0.2
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        
        for i, dim in enumerate(dimensions):
            weights = [all_weights[ind][dim] for ind in industries]
            ax.bar(x + i * width, weights, width, label=dimension_labels[dim], color=colors[i])
        
        # 设置标签
        ax.set_xlabel('行业', fontsize=12)
        ax.set_ylabel('权重', fontsize=12)
        ax.set_title(title, fontsize=14, pad=20)
        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels(industries)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 0.5)
        
        # 在柱子上方显示数值
        for i, dim in enumerate(dimensions):
            for j, ind in enumerate(industries):
                weight = all_weights[ind][dim]
                ax.text(x[j] + i * width, weight + 0.01, f'{weight:.2%}',
                       ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        
        # 保存图表
        if save_name and self.save_dir:
            save_path = self.save_dir / f"{save_name}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[OK] 对比图已保存：{save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def plot_radar(
        self,
        all_weights: Dict[str, Dict[str, float]],
        title: str = "各行业权重分布雷达图",
        show: bool = True,
        save_name: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制各行业权重分布雷达图
        
        Args:
            all_weights: 所有权重大字典
            title: 图表标题
            show: 是否显示图表
            save_name: 保存文件名（可选）
            
        Returns:
            Figure 对象
        """
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='polar')
        
        dimensions = ["education", "experience", "skill_achievement", "comprehensive"]
        dimension_labels = ["教育背景", "工作经历", "技能与成果", "综合素质"]
        
        # 设置角度
        angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
        angles += angles[:1]  # 闭合
        
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids(np.degrees(angles[:-1]), dimension_labels)
        
        # 绘制每个行业的雷达图
        colors = plt.cm.Set3(np.linspace(0, 1, len(all_weights)))
        
        for (industry, weights), color in zip(all_weights.items(), colors):
            values = [weights[dim] for dim in dimensions]
            values += values[:1]  # 闭合
            ax.plot(angles, values, 'o-', linewidth=2, label=industry, color=color)
            ax.fill(angles, values, alpha=0.15, color=color)
        
        ax.set_title(title, size=14, pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        ax.set_ylim(0, 0.5)
        ax.grid(True)
        
        # 保存图表
        if save_name and self.save_dir:
            save_path = self.save_dir / f"{save_name}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[OK] 雷达图已保存：{save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def plot_industry_weights(
        self,
        industry_weights: Dict[str, float],
        industry_name: str,
        title: Optional[str] = None,
        show: bool = True,
        save_name: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制单个行业的权重分布图
        
        Args:
            industry_weights: 行业权重大字典
            industry_name: 行业名称
            title: 图表标题（可选）
            show: 是否显示图表
            save_name: 保存文件名（可选）
            
        Returns:
            Figure 对象
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        dimensions = ["education", "experience", "skill_achievement", "comprehensive"]
        dimension_labels = {
            "education": "教育背景\n(Sedu)",
            "experience": "工作经历\n(Sexp)",
            "skill_achievement": "技能与成果\n(Sskill)",
            "comprehensive": "综合素质\n(Sadj)"
        }
        
        weights = [industry_weights[dim] for dim in dimensions]
        x = np.arange(len(dimensions))
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        bars = ax.bar(x, weights, color=colors)
        
        # 设置标签
        ax.set_xlabel('维度', fontsize=12)
        ax.set_ylabel('权重', fontsize=12)
        ax.set_title(title or f'{industry_name} - 维度权重分布', fontsize=14, pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels([dimension_labels[d] for d in dimensions])
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 0.5)
        
        # 在柱子上方显示数值
        for bar, weight in zip(bars, weights):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{weight:.2%}', ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        
        # 保存图表
        if save_name and self.save_dir:
            save_path = self.save_dir / f"{save_name}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[OK] 权重分布图已保存：{save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def plot_all(
        self,
        weight_matrix: np.ndarray,
        industries: List[str],
        dimensions: List[str],
        all_weights: Optional[Dict[str, Dict[str, float]]] = None,
        show: bool = True,
        save_name_prefix: Optional[str] = None
    ) -> List[plt.Figure]:
        """
        绘制所有可视化图表
        
        Args:
            weight_matrix: 权重矩阵
            industries: 行业列表
            dimensions: 维度列表
            all_weights: 所有行业权重（可选）
            show: 是否显示图表
            save_name_prefix: 保存文件名前缀（可选）
            
        Returns:
            Figure 对象列表
        """
        figures = []
        
        # 1. 热力图
        fig1 = self.plot_heatmap(
            weight_matrix, 
            industries, 
            dimensions,
            title="行业权重矩阵热力图",
            show=show,
            save_name=f"{save_name_prefix}_heatmap" if save_name_prefix else "heatmap"
        )
        figures.append(fig1)
        
        # 2. 对比柱状图
        if all_weights:
            fig2 = self.plot_bar_comparison(
                all_weights,
                title="各行业维度权重对比",
                show=show,
                save_name=f"{save_name_prefix}_bar" if save_name_prefix else "bar_comparison"
            )
            figures.append(fig2)
            
            # 3. 雷达图
            fig3 = self.plot_radar(
                all_weights,
                title="各行业权重分布雷达图",
                show=show,
                save_name=f"{save_name_prefix}_radar" if save_name_prefix else "radar"
            )
            figures.append(fig3)
        
        return figures
