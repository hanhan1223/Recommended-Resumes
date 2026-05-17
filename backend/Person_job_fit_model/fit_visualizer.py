# -*- coding: utf-8 -*-
"""
可视化模块

功能：
1. 人岗匹配雷达图（候选人 vs 岗位要求）
2. 风险仪表盘（6 大风险维度可视化）
3. 潜力评估柱状图（5 个维度得分）
4. 综合对比图（多人对比）

输出：
- matplotlib 图表对象
- 可保存为 PNG/PDF 格式
- 可返回 base64 编码用于前端展示
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import io
import base64


class FitVisualizer:
    """人岗匹配可视化器"""

    # 中文字体配置
    FONT_CONFIG = {
        'font.sans-serif': ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'DejaVu Sans'],
        'axes.unicode_minus': False
    }

    # 配色方案
    COLORS = {
        'primary': '#2E86AB',      # 主色调 - 蓝
        'success': '#43E97B',      # 成功 - 绿
        'warning': '#F5AF19',      # 警告 - 黄
        'danger': '#F5576C',       # 危险 - 红
        'info': '#4FACFE',         # 信息 - 浅蓝
        'purple': '#667EEA',       # 紫色
        'gradient1': ['#667eea', '#764ba2'],
        'gradient2': ['#f093fb', '#f5576c'],
        'gradient3': ['#4facfe', '#00f2fe'],
        'gradient4': ['#43e97b', '#38f9d7']
    }

    def __init__(self, style: str = 'default', use_chinese: bool = True):
        """
        初始化可视化器

        Args:
            style: 图表风格 ('default', 'dark', 'minimal')
            use_chinese: 是否使用中文字体
        """
        self.style = style
        self.use_chinese = use_chinese
        
        # 配置中文字体
        if use_chinese:
            plt.rcParams.update(self.FONT_CONFIG)

    def plot_matching_radar(self, matching_result: Dict, 
                           save_path: Optional[str] = None,
                           show: bool = False) -> plt.Figure:
        """
        绘制人岗匹配雷达图

        Args:
            matching_result: 人岗匹配结果字典
            save_path: 保存路径（可选）
            show: 是否显示图表

        Returns:
            matplotlib Figure 对象
        """
        # 提取维度得分
        dimension_scores = matching_result.get('dimension_scores', {})
        dimensions = ['学历匹配', '工作年限', '技能匹配', '行业经验', '管理职责']
        scores = [
            dimension_scores.get('education_match', 0),
            dimension_scores.get('work_years_match', 0),
            dimension_scores.get('skill_match', 0),
            dimension_scores.get('industry_match', 0),
            dimension_scores.get('management_match', 0)
        ]

        # 计算角度
        angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
        scores += scores[:1]  # 闭合图形
        angles += angles[:1]

        # 创建图表
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

        # 绘制雷达图
        ax.plot(angles, scores, 'o-', linewidth=2, color=self.COLORS['primary'])
        ax.fill(angles, scores, alpha=0.25, color=self.COLORS['primary'])

        # 设置标签
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids(np.degrees(angles[:-1]), dimensions, fontsize=12)

        # 设置范围
        ax.set_rlim(0, 5)
        ax.set_rticks([1, 2, 3, 4, 5])
        ax.set_rlabel_position(0)

        # 添加标题
        overall_score = matching_result.get('overall_score', 0)
        match_level = matching_result.get('match_level', '')
        plt.suptitle(f'人岗匹配雷达图\n综合得分：{overall_score:.2f} ({match_level})', 
                    fontsize=16, fontweight='bold', y=1.02)

        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.7)

        # 自动调整布局
        plt.tight_layout()

        # 保存图表
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[OK] 雷达图已保存到：{save_path}")

        # 显示图表
        if show:
            plt.show()

        return fig

    def plot_risk_dashboard(self, risk_result: Dict,
                           save_path: Optional[str] = None,
                           show: bool = False) -> plt.Figure:
        """
        绘制风险仪表盘

        Args:
            risk_result: 风险识别结果字典
            save_path: 保存路径（可选）
            show: 是否显示图表

        Returns:
            matplotlib Figure 对象
        """
        # 提取风险数据
        details = risk_result.get('details', {})
        
        risk_types = ['跳槽频率', '岗位跨度', '行业偏离', '技能缺口', '成果表达', '空窗期']
        risk_scores = [
            details.get('job_hopping_details', {}).get('risk_score', 0),
            details.get('career_gap_details', {}).get('risk_score', 0),
            details.get('industry_switch_details', {}).get('risk_score', 0),
            details.get('skill_gap_details', {}).get('risk_score', 0),
            details.get('weak_achievement_details', {}).get('risk_score', 0),
            details.get('employment_gap_details', {}).get('risk_score', 0)
        ]

        # 创建子图 - 使用极坐标
        fig = plt.figure(figsize=(15, 10))
        fig.suptitle(f'风险仪表盘\n综合风险等级：{risk_result.get("overall_risk_level", "未知")} '
                    f'(得分：{risk_result.get("overall_risk_score", 0):.2f})',
                    fontsize=16, fontweight='bold')

        # 绘制每个风险的仪表盘
        risk_colors = {
            '低': self.COLORS['success'],
            '中': self.COLORS['warning'],
            '高': self.COLORS['danger']
        }

        for idx in range(6):
            if idx < len(risk_types):
                score = risk_scores[idx]
                risk_name = risk_types[idx]
                
                # 判断风险等级
                if score >= 7:
                    level = '高'
                elif score >= 5:
                    level = '中'
                else:
                    level = '低'

                # 使用极坐标绘制半圆仪表盘
                ax = fig.add_subplot(2, 3, idx+1, projection='polar')
                
                # 指针位置
                pointer_angle = score / 10 * np.pi
                
                # 绘制刻度线
                ax.plot([0, pointer_angle], [0, 0.8], 'r-', linewidth=3, marker='o', markersize=8)
                
                # 设置极坐标
                ax.set_theta_offset(np.pi / 2)
                ax.set_theta_direction(-1)
                ax.set_ylim(0, 1)
                ax.set_yticks([])
                ax.set_xticks([0, np.pi/3, 2*np.pi/3, np.pi])
                ax.set_xticklabels(['0', '3', '7', '10'])
                
                # 标题
                ax.set_title(f'{risk_name}\n风险等级：{level} (得分：{score})', 
                           fontsize=11, fontweight='bold')

        # 调整布局
        plt.tight_layout()

        # 保存图表
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[OK] 风险仪表盘已保存到：{save_path}")

        # 显示图表
        if show:
            plt.show()

        return fig

    def plot_potential_bar(self, potential_result: Dict,
                          save_path: Optional[str] = None,
                          show: bool = False) -> plt.Figure:
        """
        绘制潜力评估柱状图

        Args:
            potential_result: 潜力评估结果字典
            save_path: 保存路径（可选）
            show: 是否显示图表

        Returns:
            matplotlib Figure 对象
        """
        # 提取维度得分
        dimension_scores = potential_result.get('dimension_scores', {})
        dimensions = ['职业发展\n连续性', '职责提升\n轨迹', '项目\n复杂度', '学习\n能力', '公司平台\n跃迁']
        scores = [
            dimension_scores.get('career_continuity', 0),
            dimension_scores.get('responsibility_growth', 0),
            dimension_scores.get('project_complexity', 0),
            dimension_scores.get('learning_ability', 0),
            dimension_scores.get('company_platform_growth', 0)
        ]

        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))

        # 颜色映射（根据得分）
        colors = []
        for score in scores:
            if score >= 8:
                colors.append(self.COLORS['success'])
            elif score >= 6:
                colors.append(self.COLORS['info'])
            elif score >= 4:
                colors.append(self.COLORS['warning'])
            else:
                colors.append(self.COLORS['danger'])

        # 绘制柱状图
        bars = ax.bar(dimensions, scores, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

        # 添加数值标签
        for bar, score in zip(bars, scores):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                   f'{score:.1f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

        # 设置范围和标签
        ax.set_ylim(0, 11)
        ax.set_ylabel('得分', fontsize=12)
        ax.set_title(f'潜力评估维度分析\n人才类型：{potential_result.get("talent_type", "未知")} '
                    f'(综合得分：{potential_result.get("potential_score", 0):.2f})',
                    fontsize=16, fontweight='bold')

        # 添加参考线
        ax.axhline(y=8, color=self.COLORS['success'], linestyle='--', alpha=0.5, label='高潜力线 (8 分)')
        ax.axhline(y=6, color=self.COLORS['warning'], linestyle='--', alpha=0.5, label='成长线 (6 分)')
        ax.legend(loc='upper right')

        # 网格
        ax.grid(True, alpha=0.3, linestyle='--')

        # 自动调整布局
        plt.tight_layout()

        # 保存图表
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[OK] 潜力评估柱状图已保存到：{save_path}")

        # 显示图表
        if show:
            plt.show()

        return fig

    def plot_comparison_chart(self, results: List[Dict],
                             chart_type: str = 'radar',
                             save_path: Optional[str] = None,
                             show: bool = False) -> plt.Figure:
        """
        绘制多人对比图

        Args:
            results: 多个候选人的结果列表
            chart_type: 图表类型 ('radar', 'bar', 'scatter')
            save_path: 保存路径（可选）
            show: 是否显示图表

        Returns:
            matplotlib Figure 对象
        """
        if not results:
            raise ValueError("结果列表不能为空")

        if chart_type == 'radar':
            return self._plot_multi_radar(results, save_path, show)
        elif chart_type == 'bar':
            return self._plot_multi_bar(results, save_path, show)
        elif chart_type == 'scatter':
            return self._plot_multi_scatter(results, save_path, show)
        else:
            raise ValueError(f"不支持的图表类型：{chart_type}")

    def _plot_multi_radar(self, results: List[Dict],
                         save_path: Optional[str] = None,
                         show: bool = False) -> plt.Figure:
        """绘制多人雷达图对比"""
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

        # 维度配置
        if 'dimension_scores' in results[0] and 'education_match' in results[0]['dimension_scores']:
            # 人岗匹配维度
            dimensions = ['学历', '年限', '技能', '行业', '管理']
            max_score = 5
        else:
            # 潜力评估维度
            dimensions = ['职业连续性', '职责提升', '项目复杂度', '学习能力', '公司平台']
            max_score = 10

        angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
        angles += angles[:1]

        # 绘制每个候选人的雷达图
        colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
        
        for idx, result in enumerate(results[:5]):  # 最多显示 5 人
            if 'dimension_scores' in result:
                scores_data = result['dimension_scores']
                if 'education_match' in scores_data:
                    scores = [
                        scores_data.get('education_match', 0),
                        scores_data.get('work_years_match', 0),
                        scores_data.get('skill_match', 0),
                        scores_data.get('industry_match', 0),
                        scores_data.get('management_match', 0)
                    ]
                else:
                    scores = [
                        scores_data.get('career_continuity', 0),
                        scores_data.get('responsibility_growth', 0),
                        scores_data.get('project_complexity', 0),
                        scores_data.get('learning_ability', 0),
                        scores_data.get('company_platform_growth', 0)
                    ]
                
                scores += scores[:1]
                
                candidate_name = result.get('candidate_id', f'候选人{idx+1}')
                ax.plot(angles, scores, 'o-', linewidth=2, color=colors[idx], 
                       label=f'{candidate_name}', alpha=0.7)
                ax.fill(angles, scores, alpha=0.1, color=colors[idx])

        # 设置标签
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids(np.degrees(angles[:-1]), dimensions, fontsize=12)
        ax.set_rlim(0, max_score)
        ax.set_rticks(np.arange(1, max_score + 1))
        ax.set_rlabel_position(0)

        # 标题和图例
        plt.suptitle('多人对比雷达图', fontsize=16, fontweight='bold', y=1.02)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        ax.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()

        return fig

    def _plot_multi_bar(self, results: List[Dict],
                       save_path: Optional[str] = None,
                       show: bool = False) -> plt.Figure:
        """绘制多人柱状图对比"""
        fig, ax = plt.subplots(figsize=(12, 6))

        # 提取候选人姓名和综合得分
        candidates = []
        overall_scores = []
        matching_scores = []
        potential_scores = []

        for result in results[:10]:  # 最多显示 10 人
            candidates.append(result.get('candidate_id', f'候选人'))
            
            if 'overall_score' in result:
                overall_scores.append(result.get('overall_score', 0))
            if 'potential_score' in result:
                potential_scores.append(result.get('potential_score', 0))
            if 'risk_score' in result:
                matching_scores.append(result.get('risk_score', 0))

        x = np.arange(len(candidates))
        width = 0.35

        # 绘制柱状图
        if overall_scores:
            bars = ax.bar(x, overall_scores, width, label='人岗匹配得分', 
                         color=self.COLORS['primary'], alpha=0.8)
        elif potential_scores:
            bars = ax.bar(x, potential_scores, width, label='潜力得分',
                         color=self.COLORS['success'], alpha=0.8)

        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                   f'{height:.1f}', ha='center', va='bottom', fontsize=9)

        # 设置
        ax.set_ylabel('得分', fontsize=12)
        ax.set_title('候选人对比', fontsize=16, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(candidates, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()

        return fig

    def _plot_multi_scatter(self, results: List[Dict],
                           save_path: Optional[str] = None,
                           show: bool = False) -> plt.Figure:
        """绘制多人散点图对比（匹配度 vs 风险）"""
        fig, ax = plt.subplots(figsize=(10, 8))

        x_data = []  # 匹配度
        y_data = []  # 风险得分
        labels = []

        for result in results:
            if 'overall_score' in result:
                x_data.append(result.get('overall_score', 0))
                y_data.append(10 - result.get('overall_risk_score', 5))  # 风险越低越好
                labels.append(result.get('candidate_id', '候选人'))

        # 绘制散点
        scatter = ax.scatter(x_data, y_data, s=200, alpha=0.6, 
                            c=range(len(x_data)), cmap='tab10', edgecolors='black')

        # 添加标签
        for i, label in enumerate(labels):
            ax.annotate(label, (x_data[i], y_data[i]), 
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=9)

        # 设置
        ax.set_xlabel('人岗匹配度', fontsize=12)
        ax.set_ylabel('稳定性（10-风险得分）', fontsize=12)
        ax.set_title('候选人对比：匹配度 vs 稳定性', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)

        # 添加参考线
        ax.axvline(x=4, color='gray', linestyle='--', alpha=0.5)
        ax.axhline(y=7, color='gray', linestyle='--', alpha=0.5)

        plt.tight_layout()

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()

        return fig

    def result_to_base64(self, fig: plt.Figure, format: str = 'png') -> str:
        """
        将图表转换为 base64 编码（用于前端展示）

        Args:
            fig: matplotlib Figure 对象
            format: 图片格式 ('png', 'jpg', 'pdf')

        Returns:
            base64 编码字符串
        """
        buf = io.BytesIO()
        fig.savefig(buf, format=format, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/{format};base64,{img_base64}"

    def create_dashboard(self, matching_result: Optional[Dict] = None,
                        risk_result: Optional[Dict] = None,
                        potential_result: Optional[Dict] = None,
                        save_path: Optional[str] = None,
                        show: bool = False) -> plt.Figure:
        """
        创建综合仪表盘（组合多个图表）

        Args:
            matching_result: 人岗匹配结果（可选）
            risk_result: 风险识别结果（可选）
            potential_result: 潜力评估结果（可选）
            save_path: 保存路径（可选）
            show: 是否显示图表

        Returns:
            matplotlib Figure 对象
        """
        # 计算需要几个子图
        n_charts = sum([
            matching_result is not None,
            risk_result is not None,
            potential_result is not None
        ])

        if n_charts == 0:
            raise ValueError("至少需要一个结果字典")

        # 创建子图布局
        if n_charts == 1:
            fig, axes = plt.subplots(1, 1, figsize=(10, 8))
            axes = [axes]
        elif n_charts == 2:
            fig, axes = plt.subplots(1, 2, figsize=(18, 8))
        else:
            fig, axes = plt.subplots(1, 3, figsize=(24, 8))

        axes = axes if isinstance(axes, (list, np.ndarray)) else [axes]
        chart_idx = 0

        # 绘制人岗匹配雷达图
        if matching_result and chart_idx < len(axes):
            dimension_scores = matching_result.get('dimension_scores', {})
            dimensions = ['学历', '年限', '技能', '行业', '管理']
            scores = [
                dimension_scores.get('education_match', 0),
                dimension_scores.get('work_years_match', 0),
                dimension_scores.get('skill_match', 0),
                dimension_scores.get('industry_match', 0),
                dimension_scores.get('management_match', 0)
            ]
            
            # 在指定 axes 上绘制
            angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
            scores_closed = scores + scores[:1]
            angles_closed = angles + angles[:1]
            
            ax = plt.subplot(1, n_charts, chart_idx + 1, polar=True)
            ax.plot(angles_closed, scores_closed, 'o-', linewidth=2, color=self.COLORS['primary'])
            ax.fill(angles_closed, scores_closed, alpha=0.25, color=self.COLORS['primary'])
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_xticks(angles)
            ax.set_xticklabels(dimensions, fontsize=11, va='center')
            ax.set_rlim(0, 5)
            ax.set_rticks([1, 2, 3, 4, 5])
            ax.set_title(f'人岗匹配\n得分：{matching_result.get("overall_score", 0):.2f}', 
                        fontsize=14, fontweight='bold', pad=20)
            ax.grid(True, linestyle='--', alpha=0.7)
            
            chart_idx += 1

        # 绘制风险仪表盘（简化版）
        if risk_result and chart_idx < len(axes):
            ax = axes[chart_idx] if hasattr(axes[chart_idx], 'bar') else plt.subplot(1, n_charts, chart_idx + 1)
            
            details = risk_result.get('details', {})
            risk_types = ['跳槽', '跨度', '行业', '技能', '成果', '空窗']
            risk_scores = [
                details.get('job_hopping_details', {}).get('risk_score', 0),
                details.get('career_gap_details', {}).get('risk_score', 0),
                details.get('industry_switch_details', {}).get('risk_score', 0),
                details.get('skill_gap_details', {}).get('risk_score', 0),
                details.get('weak_achievement_details', {}).get('risk_score', 0),
                details.get('employment_gap_details', {}).get('risk_score', 0)
            ]
            
            colors = [self.COLORS['success'] if s < 5 else self.COLORS['warning'] if s < 7 else self.COLORS['danger'] 
                     for s in risk_scores]
            
            ax.bar(risk_types, risk_scores, color=colors, alpha=0.8, edgecolor='black')
            ax.set_ylim(0, 10)
            ax.set_ylabel('风险得分', fontsize=11)
            ax.set_title(f'风险识别\n等级：{risk_result.get("overall_risk_level", "未知")}', 
                        fontsize=14, fontweight='bold', pad=20)
            ax.grid(True, alpha=0.3, axis='y')
            
            chart_idx += 1

        # 绘制潜力评估柱状图
        if potential_result and chart_idx < len(axes):
            ax = axes[chart_idx] if hasattr(axes[chart_idx], 'bar') else plt.subplot(1, n_charts, chart_idx + 1)
            
            dimension_scores = potential_result.get('dimension_scores', {})
            dimensions = ['职业连续', '职责提升', '项目复杂', '学习能力', '公司平台']
            scores = [
                dimension_scores.get('career_continuity', 0),
                dimension_scores.get('responsibility_growth', 0),
                dimension_scores.get('project_complexity', 0),
                dimension_scores.get('learning_ability', 0),
                dimension_scores.get('company_platform_growth', 0)
            ]
            
            colors = [self.COLORS['success'] if s >= 8 else self.COLORS['info'] if s >= 6 else self.COLORS['warning'] 
                     for s in scores]
            
            ax.bar(dimensions, scores, color=colors, alpha=0.8, edgecolor='black')
            ax.set_ylim(0, 10)
            ax.set_ylabel('得分', fontsize=11)
            ax.set_title(f'潜力评估\n类型：{potential_result.get("talent_type", "未知")}', 
                        fontsize=14, fontweight='bold', pad=20)
            ax.grid(True, alpha=0.3, axis='y')
            
            chart_idx += 1

        # 总标题
        fig.suptitle('候选人综合评估仪表盘', fontsize=18, fontweight='bold', y=1.02)
        
        plt.tight_layout()

        # 保存
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[OK] 综合仪表盘已保存到：{save_path}")

        # 显示
        if show:
            plt.show()

        return fig


if __name__ == '__main__':
    # 测试示例
    visualizer = FitVisualizer()

    # 测试人岗匹配雷达图
    test_matching = {
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
    
    fig1 = visualizer.plot_matching_radar(test_matching, save_path='test_matching_radar.png')

    # 测试风险仪表盘
    test_risk = {
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
    
    fig2 = visualizer.plot_risk_dashboard(test_risk, save_path='test_risk_dashboard.png')

    # 测试潜力评估柱状图
    test_potential = {
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
    
    fig3 = visualizer.plot_potential_bar(test_potential, save_path='test_potential_bar.png')

    print("\n[OK] 所有可视化测试完成！")
