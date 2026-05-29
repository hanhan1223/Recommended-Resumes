"""
标准行业权重提供器
"""

import json
from pathlib import Path

class StandardWeightProvider:
    """提供行业标准权重配置"""

    _instance = None
    _weights = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_weights()
        return cls._instance

    def _load_weights(self):
        """加载标准权重配置"""
        config_path = Path(__file__).parent / "config" / "industry_standard_weights.json"

        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._weights = data.get('industries', {})
        else:
            # 默认权重（如果配置文件不存在）
            self._weights = {
                "电商": {
                    "education": 0.08,
                    "experience": 0.25,
                    "skill_achievement": 0.32,
                    "comprehensive": 0.15,
                    "growth_potential": 0.10,
                    "job_matching": 0.10
                }
            }

    def get_weights(self, industry: str) -> dict:
        """获取指定行业的权重"""
        # 尝试精确匹配
        if industry in self._weights:
            return self._weights[industry]

        # 尝试模糊匹配
        industry_mapping = {
            "电商": ["电商", "电子商务"],
            "研发": ["研发", "技术", "IT"],
            "销售": ["销售", "营销", "商务"],
            "品牌": ["品牌", "市场", "品牌市场"],
            "生产": ["生产", "制造", "供应链"],
            "人力资源": ["人力资源", "HR", "人事"]
        }

        for standard_name, keywords in industry_mapping.items():
            if any(keyword in industry for keyword in keywords):
                return self._weights.get(standard_name, self._weights["电商"])

        # 默认返回电商权重
        return self._weights.get("电商", {
            "education": 0.08,
            "experience": 0.25,
            "skill_achievement": 0.32,
            "comprehensive": 0.15,
            "growth_potential": 0.10,
            "job_matching": 0.10
        })

# 全局实例
_standard_weights = StandardWeightProvider()

def get_standard_weights(industry: str) -> dict:
    """获取指定行业的标准权重"""
    return _standard_weights.get_weights(industry)
