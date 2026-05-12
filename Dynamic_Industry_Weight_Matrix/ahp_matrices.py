"""
各行业 AHP 判断矩阵配置

基于行业特点设计的主观权重判断矩阵
包含 6 个行业：研发、电商、人力资源、品牌市场、生产、销售

每个行业有两个判断矩阵：
- 技术类岗位 (technical): 学历、专业技能、项目经验、工作成果、工作年限
- 管理类岗位 (management): 学历、工作经历、情商沟通、稳定性、管理成果
"""

import numpy as np
from typing import Dict, List


class IndustryAHPMatrices:
    """行业 AHP 判断矩阵配置类"""
    
    # 技术类岗位指标
    TECHNICAL_INDICATORS = ["学历", "专业技能", "项目经验", "工作成果", "工作年限"]
    
    # 管理类岗位指标
    MANAGEMENT_INDICATORS = ["学历", "工作经历", "情商沟通", "稳定性", "管理成果"]
    
    def __init__(self):
        """初始化各行业的 AHP 判断矩阵"""
        
        # ========== 研发类 ==========
        # 特点：侧重专业技能和项目经验
        self.research_technical_matrix = np.array([
            # 学历，专业，项目，成果，年限
            [1,   1/5, 1/4, 1/3, 1/2],  # 学历
            [5,   1,   2,   3,   2  ],  # 专业技能 (最重要)
            [4,   1/2, 1,   2,   1  ],  # 项目经验
            [3,   1/3, 1/2, 1,   1/2],  # 工作成果
            [2,   1/2, 1,   2,   1  ]   # 工作年限
        ])
        
        self.research_management_matrix = np.array([
            # 学历，经历，情商，稳定，成果
            [1,   1/4, 1/3, 2,   1/5],  # 学历
            [4,   1,   2,   3,   1/2],  # 工作经历
            [3,   1/2, 1,   2,   1/3],  # 情商沟通
            [1/2, 1/3, 1/2, 1,   1/4],  # 稳定性
            [5,   2,   3,   4,   1  ]   # 管理成果 (最重要)
        ])
        
        # ========== 电商类 ==========
        # 特点：侧重工作经历和专业技能
        self.ecommerce_technical_matrix = np.array([
            # 学历，专业，项目，成果，年限
            [1,   1/3, 1/2, 1/2, 1/3],  # 学历
            [3,   1,   2,   2,   1  ],  # 专业技能
            [2,   1/2, 1,   1,   1/2],  # 项目经验
            [2,   1/2, 1,   1,   1/2],  # 工作成果
            [3,   1,   2,   2,   1  ]   # 工作年限 (电商变化快，经验重要)
        ])
        
        self.ecommerce_management_matrix = np.array([
            # 学历，经历，情商，稳定，成果
            [1,   1/3, 1/2, 2,   1/4],  # 学历
            [3,   1,   2,   3,   1  ],  # 工作经历 (电商重实战)
            [2,   1/2, 1,   2,   1/2],  # 情商沟通
            [1/2, 1/3, 1/2, 1,   1/3],  # 稳定性
            [4,   1,   2,   3,   1  ]   # 管理成果
        ])
        
        # ========== 人力资源类 ==========
        # 特点：侧重情商沟通和工作经历
        self.hr_technical_matrix = np.array([
            # 学历，专业，项目，成果，年限
            [1,   1/3, 1/2, 1/3, 1/4],  # 学历
            [3,   1,   2,   1,   1  ],  # 专业技能
            [2,   1/2, 1,   1/2, 1/2],  # 项目经验
            [3,   1,   2,   1,   1  ],  # 工作成果
            [4,   1,   2,   1,   1  ]   # 工作年限 (HR 越老越吃香)
        ])
        
        self.hr_management_matrix = np.array([
            # 学历，经历，情商，稳定，成果
            [1,   1/4, 1/5, 2,   1/4],  # 学历
            [4,   1,   1/2, 3,   1  ],  # 工作经历
            [5,   2,   1,   4,   2  ],  # 情商沟通 (HR 核心能力)
            [1/2, 1/3, 1/4, 1,   1/3],  # 稳定性
            [4,   1,   1/2, 3,   1  ]   # 管理成果
        ])
        
        # ========== 品牌市场类 ==========
        # 特点：侧重管理成果和情商沟通
        self.brand_marketing_technical_matrix = np.array([
            # 学历，专业，项目，成果，年限
            [1,   1/3, 1/2, 1/3, 1/3],  # 学历
            [3,   1,   2,   1,   1  ],  # 专业技能
            [2,   1/2, 1,   1/2, 1/2],  # 项目经验
            [3,   1,   2,   1,   1  ],  # 工作成果
            [3,   1,   2,   1,   1  ]   # 工作年限
        ])
        
        self.brand_marketing_management_matrix = np.array([
            # 学历，经历，情商，稳定，成果
            [1,   1/3, 1/3, 2,   1/5],  # 学历
            [3,   1,   1,   3,   1/2],  # 工作经历
            [3,   1,   1,   3,   1/2],  # 情商沟通 (市场需要沟通能力)
            [1/2, 1/3, 1/3, 1,   1/4],  # 稳定性
            [5,   2,   2,   4,   1  ]   # 管理成果 (品牌市场看成果)
        ])
        
        # ========== 生产类 ==========
        # 特点：侧重工作成果和稳定性
        self.production_technical_matrix = np.array([
            # 学历，专业，项目，成果，年限
            [1,   1/4, 1/3, 1/3, 1/2],  # 学历
            [4,   1,   2,   2,   1  ],  # 专业技能
            [3,   1/2, 1,   1,   1  ],  # 项目经验
            [3,   1/2, 1,   1,   1  ],  # 工作成果 (生产看良率、效率)
            [2,   1,   1,   1,   1  ]   # 工作年限 (生产需要经验积累)
        ])
        
        self.production_management_matrix = np.array([
            # 学历，经历，情商，稳定，成果
            [1,   1/3, 1/2, 1/2, 1/4],  # 学历
            [3,   1,   1,   2,   1/2],  # 工作经历
            [2,   1,   1,   2,   1/3],  # 情商沟通
            [2,   1/2, 1/2, 1,   1/3],  # 稳定性 (生产需要稳定)
            [4,   2,   3,   3,   1  ]   # 工作成果 (生产最看重成果)
        ])
        
        # ========== 销售类 ==========
        # 特点：侧重工作经历 + 情商沟通（您特别强调）
        self.sales_technical_matrix = np.array([
            # 学历，专业，项目，成果，年限
            [1,   1/3, 1/2, 1/3, 1/4],  # 学历
            [3,   1,   2,   1,   1/2],  # 专业技能
            [2,   1/2, 1,   1/2, 1/3],  # 项目经验
            [3,   1,   2,   1,   1/2],  # 工作成果 (销售看业绩)
            [4,   2,   3,   2,   1  ]   # 工作年限 (销售越老越吃香)
        ])
        
        self.sales_management_matrix = np.array([
            # 学历，经历，情商，稳定，成果
            [1,   1/4, 1/3, 2,   1/5],  # 学历
            [4,   1,   1,   3,   1  ],  # 工作经历 (销售重经验)
            [3,   1,   1,   3,   1  ],  # 情商沟通 (销售核心能力)
            [1/2, 1/3, 1/3, 1,   1/4],  # 稳定性
            [5,   1,   1,   4,   1  ]   # 管理成果 (销售看业绩)
        ])
    
    def get_matrix(self, industry: str, job_type: str) -> np.ndarray:
        """
        获取指定行业和岗位类型的 AHP 判断矩阵
        
        Args:
            industry: 行业名称（研发、电商、人力资源、品牌市场、生产、销售）
            job_type: 岗位类型（technical 或 management）
            
        Returns:
            5x5 的 AHP 判断矩阵
        """
        matrix_map = {
            "研发": {
                "technical": self.research_technical_matrix,
                "management": self.research_management_matrix
            },
            "电商": {
                "technical": self.ecommerce_technical_matrix,
                "management": self.ecommerce_management_matrix
            },
            "人力资源": {
                "technical": self.hr_technical_matrix,
                "management": self.hr_management_matrix
            },
            "品牌市场": {
                "technical": self.brand_marketing_technical_matrix,
                "management": self.brand_marketing_management_matrix
            },
            "生产": {
                "technical": self.production_technical_matrix,
                "management": self.production_management_matrix
            },
            "销售": {
                "technical": self.sales_technical_matrix,
                "management": self.sales_management_matrix
            }
        }
        
        if industry not in matrix_map:
            raise ValueError(f"不支持的行业：{industry}。支持的行业：{list(matrix_map.keys())}")
        
        if job_type not in matrix_map[industry]:
            raise ValueError(f"不支持的岗位类型：{job_type}。支持的类型：technical, management")
        
        return matrix_map[industry][job_type]
    
    def get_indicators(self, job_type: str) -> List[str]:
        """
        获取指定岗位类型的指标列表
        
        Args:
            job_type: 岗位类型（technical 或 management）
            
        Returns:
            指标列表
        """
        if job_type == "technical":
            return self.TECHNICAL_INDICATORS.copy()
        elif job_type == "management":
            return self.MANAGEMENT_INDICATORS.copy()
        else:
            raise ValueError(f"不支持的岗位类型：{job_type}")
    
    def get_all_industries(self) -> List[str]:
        """获取所有支持的行业列表"""
        return ["研发", "电商", "人力资源", "品牌市场", "生产", "销售"]
    
    def get_industry_characteristics(self, industry: str) -> str:
        """
        获取行业特点描述
        
        Args:
            industry: 行业名称
            
        Returns:
            行业特点描述字符串
        """
        characteristics = {
            "研发": "侧重专业技能和项目经验，重视技术创新能力",
            "电商": "侧重工作经历和专业技能，重视实战经验和快速学习能力",
            "人力资源": "侧重情商沟通和工作经历，重视人际交往和组织协调能力",
            "品牌市场": "侧重管理成果和情商沟通，重视创意策划和沟通表达能力",
            "生产": "侧重工作成果和稳定性，重视质量控制和效率提升",
            "销售": "侧重工作经历和情商沟通，重视业绩达成和客户关系维护"
        }
        
        return characteristics.get(industry, "未知行业特点")
