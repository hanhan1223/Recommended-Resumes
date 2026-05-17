@echo off
cd /d "d:\desktop\统计课论文\code3\Recommended-Resumes"
echo ============================================================
echo 人岗匹配模块 - Git 提交
echo ============================================================

echo.
echo 当前目录:
cd

echo.
echo 检查 Git 安装...
if exist "C:\Program Files\Git\bin\git.exe" (
    echo Git found at C:\Program Files\Git\bin\git.exe
    set GIT_CMD="C:\Program Files\Git\bin\git.exe"
) else if exist "C:\Program Files (x86)\Git\bin\git.exe" (
    echo Git found at C:\Program Files (x86)\Git\bin\git.exe
    set GIT_CMD="C:\Program Files (x86)\Git\bin\git.exe"
) else (
    echo Git not found. Please install Git or add it to PATH.
    pause
    exit /b 1
)

echo.
echo 当前分支:
%GIT_CMD% branch --show-current

echo.
echo 创建新分支：feature-person-job-fit
%GIT_CMD% checkout -b feature-person-job-fit

echo.
echo 添加文件...
%GIT_CMD% add backend/Person_job_fit_model/
%GIT_CMD% add backend/app/main.py
%GIT_CMD% add backend/test_api_integration.py

echo.
echo Git 状态:
%GIT_CMD% status --short

echo.
echo 提交更改...
%GIT_CMD% commit -m "feat: 集人岗匹配模块

- 新增岗位画像抽取模块 (JobProfileExtractor)
- 新增人岗匹配评分模块 (JobMatchingScorer) - 支持权重动态调整
- 新增风险识别模块 (RiskIdentifier) - 6 大风险维度
- 新增潜力评估模块 (PotentialEvaluator) - 4 种人才类型
- 新增可视化模块 (FitVisualizer) - 雷达图/仪表盘/柱状图
- 新增主模型类 (PersonJobFitModel) - 统一 API 接口
- 集成到现有评分流程，新增 7 个 API 端点
- 添加示例岗位描述数据集 (18 个岗位)
- 添加证书知识库 (37 个证书)
- 添加完整的测试文件
"

echo.
echo 提交日志:
%GIT_CMD% log -1 --stat

echo.
echo ============================================================
echo ✓ Git 提交完成！
echo ============================================================
echo.
echo 下一步操作:
echo 1. 推送到远程仓库：%GIT_CMD% push origin feature-person-job-fit
echo 2. 在 GitHub 上创建 Pull Request
echo.
pause
