"""
Pytest 配置文件
"""
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".venv"))
sys.path.insert(0, str(project_root.parent / ".venv"))

import pytest
from httpx import AsyncClient

@pytest.fixture
def client():
    """同步测试客户端"""
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
async def async_client():
    """异步测试客户端"""
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def sample_resume():
    """示例简历数据"""
    return {
        "basic_info": {
            "name": "测试候选人",
            "gender": "男",
            "birth_year": 1990,
            "phone": "13800138000",
            "email": "test@example.com"
        },
        "education_experiences": [
            {
                "school": "清华大学",
                "major": "计算机科学与技术",
                "degree": "本科",
                "start_date": "2010-09",
                "end_date": "2014-07"
            }
        ],
        "work_experiences": [
            {
                "company": "阿里巴巴",
                "position": "软件工程师",
                "start_date": "2014-07",
                "end_date": "2018-07"
            },
            {
                "company": "腾讯",
                "position": "高级工程师",
                "start_date": "2018-08",
                "end_date": "至今"
            }
        ],
        "skills": ["Python", "Java", "Vue.js", "MySQL"],
        "industry": "电商"
    }

@pytest.fixture
def sample_dimension_weights():
    """示例维度权重"""
    return {
        "education": 0.15,
        "experience": 0.30,
        "skill_achievement": 0.40,
        "comprehensive": 0.15
    }
