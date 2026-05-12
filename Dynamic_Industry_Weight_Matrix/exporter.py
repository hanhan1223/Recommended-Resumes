"""
行业权重导出模块

支持将行业权重矩阵导出为 JSON 或 CSV 格式
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Union
import numpy as np


class IndustryWeightExporter:
    """行业权重导出器"""
    
    def __init__(self, save_dir: Optional[str] = None):
        """
        初始化导出器
        
        Args:
            save_dir: 保存目录（可选）
        """
        self.save_dir = Path(save_dir) if save_dir else None
        if self.save_dir:
            self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def export_to_json(
        self,
        all_weights: Dict[str, Dict[str, float]],
        output_path: Optional[str] = None,
        include_metadata: bool = True,
        **metadata
    ) -> str:
        """
        导出行业权重为 JSON 格式
        
        Args:
            all_weights: 行业权重大字典 {industry: {dimension: weight}}
            output_path: 输出文件路径（可选，默认保存到 save_dir）
            include_metadata: 是否包含元数据
            **metadata: 额外的元数据信息
            
        Returns:
            保存的文件路径
        """
        export_data = {
            "industry_weights": {}
        }
        
        # 添加行业权重数据
        for industry, weights in all_weights.items():
            export_data["industry_weights"][industry] = {
                "education": weights.get("education", 0.0),
                "experience": weights.get("experience", 0.0),
                "skill_achievement": weights.get("skill_achievement", 0.0),
                "comprehensive": weights.get("comprehensive", 0.0)
            }
        
        # 添加元数据
        if include_metadata:
            export_data["metadata"] = {
                "description": "动态行业权重矩阵 - 分领域评价人才",
                "formula": "TCI = Wedu·Sedu + Wexp·Sexp + Wskill·Sskill + Wadj·Sadj",
                "dimensions": {
                    "education": "教育背景 (Sedu)",
                    "experience": "工作经历 (Sexp)",
                    "skill_achievement": "技能与成果 (Sskill)",
                    "comprehensive": "综合素质 (Sadj)"
                },
                "industries": list(all_weights.keys()),
                **metadata
            }
        
        # 确定保存路径
        if output_path:
            save_path = Path(output_path)
        elif self.save_dir:
            save_path = self.save_dir / "industry_weights.json"
        else:
            save_path = Path("industry_weights.json")
        
        # 确保目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存 JSON
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] JSON 已导出：{save_path}")
        
        return str(save_path)
    
    def export_to_csv(
        self,
        all_weights: Dict[str, Dict[str, float]],
        output_path: Optional[str] = None,
        include_percentage: bool = True
    ) -> str:
        """
        导出行业权重为 CSV 格式
        
        Args:
            all_weights: 行业权重大字典
            output_path: 输出文件路径（可选）
            include_percentage: 是否包含百分比列
            
        Returns:
            保存的文件路径
        """
        # 准备数据
        rows = []
        headers = ["行业", "教育背景 (Sedu)", "工作经历 (Sexp)", 
                   "技能与成果 (Sskill)", "综合素质 (Sadj)"]
        
        if include_percentage:
            headers.extend([
                "教育背景 (%)", "工作经历 (%)", 
                "技能与成果 (%)", "综合素质 (%)"
            ])
        
        for industry, weights in all_weights.items():
            row = {
                "行业": industry,
                "教育背景 (Sedu)": weights.get("education", 0.0),
                "工作经历 (Sexp)": weights.get("experience", 0.0),
                "技能与成果 (Sskill)": weights.get("skill_achievement", 0.0),
                "综合素质 (Sadj)": weights.get("comprehensive", 0.0)
            }
            
            if include_percentage:
                row["教育背景 (%)"] = f"{weights.get('education', 0.0)*100:.2f}%"
                row["工作经历 (%)"] = f"{weights.get('experience', 0.0)*100:.2f}%"
                row["技能与成果 (%)"] = f"{weights.get('skill_achievement', 0.0)*100:.2f}%"
                row["综合素质 (%)"] = f"{weights.get('comprehensive', 0.0)*100:.2f}%"
            
            rows.append(row)
        
        # 确定保存路径
        if output_path:
            save_path = Path(output_path)
        elif self.save_dir:
            save_path = self.save_dir / "industry_weights.csv"
        else:
            save_path = Path("industry_weights.csv")
        
        # 确保目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存 CSV
        with open(save_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"[OK] CSV 已导出：{save_path}")
        
        return str(save_path)
    
    def export_to_excel(
        self,
        all_weights: Dict[str, Dict[str, float]],
        output_path: Optional[str] = None,
        include_sheet_per_industry: bool = False
    ) -> Optional[str]:
        """
        导出行业权重为 Excel 格式（需要 pandas 和 openpyxl）
        
        Args:
            all_weights: 行业权重大字典
            output_path: 输出文件路径（可选）
            include_sheet_per_industry: 是否为每个行业创建单独的工作表
            
        Returns:
            保存的文件路径，如果 pandas 未安装则返回 None
        """
        try:
            import pandas as pd
        except ImportError:
            print("⚠️  需要安装 pandas: pip install pandas openpyxl")
            return None
        
        # 准备数据
        data = []
        for industry, weights in all_weights.items():
            row = {
                "行业": industry,
                "教育背景 Sedu": weights.get("education", 0.0),
                "工作经历 Sexp": weights.get("experience", 0.0),
                "技能与成果 Sskill": weights.get("skill_achievement", 0.0),
                "综合素质 Sadj": weights.get("comprehensive", 0.0),
                "总和": sum(weights.values())
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # 确定保存路径
        if output_path:
            save_path = Path(output_path)
            if not save_path.suffix:
                save_path = save_path.with_suffix('.xlsx')
        elif self.save_dir:
            save_path = self.save_dir / "industry_weights.xlsx"
        else:
            save_path = Path("industry_weights.xlsx")
        
        # 确保目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存 Excel
        if include_sheet_per_industry:
            with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                # 总表
                df.to_excel(writer, sheet_name='总表', index=False)
                
                # 每个行业一个工作表
                for industry, weights in all_weights.items():
                    industry_df = pd.DataFrame([
                        {"维度": "教育背景", "权重": weights.get("education", 0.0)},
                        {"维度": "工作经历", "权重": weights.get("experience", 0.0)},
                        {"维度": "技能与成果", "权重": weights.get("skill_achievement", 0.0)},
                        {"维度": "综合素质", "权重": weights.get("comprehensive", 0.0)}
                    ])
                    industry_df.to_excel(writer, sheet_name=industry, index=False)
        else:
            df.to_excel(writer, sheet_name='行业权重', index=False)
        
        print(f"[OK] Excel 已导出：{save_path}")
        
        return str(save_path)
    
    def export_all(
        self,
        all_weights: Dict[str, Dict[str, float]],
        output_dir: Optional[str] = None,
        formats: List[str] = ["json", "csv"],
        **kwargs
    ) -> Dict[str, str]:
        """
        一次性导出多种格式
        
        Args:
            all_weights: 行业权重大字典
            output_dir: 输出目录（可选）
            formats: 导出格式列表 ["json", "csv", "excel"]
            **kwargs: 传递给各导出方法的额外参数
            
        Returns:
            保存的文件路径字典 {format: path}
        """
        if output_dir:
            self.save_dir = Path(output_dir)
            self.save_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths = {}
        
        if "json" in formats:
            json_path = self.export_to_json(all_weights, **kwargs)
            saved_paths["json"] = json_path
        
        if "csv" in formats:
            csv_path = self.export_to_csv(all_weights, **kwargs)
            saved_paths["csv"] = csv_path
        
        if "excel" in formats:
            excel_path = self.export_to_excel(all_weights, **kwargs)
            if excel_path:
                saved_paths["excel"] = excel_path
        
        return saved_paths
