"""
后端服务器启动脚本 - 使用 .venv 环境
"""
import sys
from pathlib import Path

# 项目根目录
project_root = Path(__file__).parent.parent

# 添加项目路径
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

# 切换到 backend 目录
import os
os.chdir(Path(__file__).parent)

print("="*60)
print("Starting Backend Server with .venv")
print("="*60)
print(f"Project root: {project_root}")
print(f"Python: {sys.executable}")
print(f"Working dir: {os.getcwd()}")
print("="*60)

try:
    import fastapi
    print(f"[OK] FastAPI version: {fastapi.__version__}")

    import uvicorn
    from app.main import app

    print("[OK] All imports successful")
    print("[INFO] Starting server on http://0.0.0.0:8000")
    print("="*60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
