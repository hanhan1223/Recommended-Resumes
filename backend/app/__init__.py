"""
人才简历综合优选系统 - 应用包
包含主要的应用模块和配置
"""

from .main import app
from .llm_service import get_llm_service, init_llm_service
from .data_manager import get_data_manager, ResumeDataManager
from .cache_manager import get_cache_manager, CacheManager
from .data_validator import DataValidator

__version__ = "1.0.0"

__all__ = [
    "app",
    "get_llm_service",
    "init_llm_service",
    "get_data_manager",
    "ResumeDataManager",
    "get_cache_manager",
    "CacheManager",
    "DataValidator"
]
