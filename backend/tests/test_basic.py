"""
基础功能测试 - 验证测试框架和导入正常
"""
import sys
from pathlib import Path

def test_project_paths():
    """验证项目路径配置正确"""
    project_root = Path(__file__).parent.parent
    
    # 检查关键目录存在
    assert (project_root / "app").exists(), "app目录不存在"
    assert (project_root.parent / ".venv").exists(), ".venv目录不存在"
    
    # 检查关键文件存在
    assert (project_root / "app" / "main.py").exists(), "main.py不存在"

def test_import_main():
    """测试能否正常导入main模块"""
    try:
        from app import main
        assert main.app is not None, "FastAPI app未创建"
        assert main.app.title == "人才简历综合优选系统", "App标题不匹配"
    except ImportError as e:
        pytest.fail(f"导入main模块失败: {e}")

def test_import_models():
    """测试能否正常导入模型模块"""
    try:
        from Dimensional_scoring_model import DimensionalScoringModel
        assert DimensionalScoringModel is not None
    except ImportError as e:
        pytest.fail(f"导入DimensionalScoringModel失败: {e}")
    
    try:
        from Dynamic_Industry_Weight_Matrix import IndustryWeightMatrix
        assert IndustryWeightMatrix is not None
    except ImportError as e:
        pytest.fail(f"导入IndustryWeightMatrix失败: {e}")
