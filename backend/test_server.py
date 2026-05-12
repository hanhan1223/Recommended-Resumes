"""
测试服务器启动脚本
"""
import sys
from pathlib import Path
import uvicorn

# 添加路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".venv"))

print("[INFO] Starting test server...")

try:
    from app.main import app
    print("[OK] FastAPI app imported successfully")

    print("[INFO] Starting Uvicorn server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
