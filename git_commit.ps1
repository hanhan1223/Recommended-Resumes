# Git 操作脚本
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "人岗匹配模块 - Git 提交" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 设置工作目录
Set-Location "d:\desktop\统计课论文\code3\Recommended-Resumes"

# 检查当前分支
Write-Host "`n 当前分支:" -ForegroundColor Yellow
git branch --show-current

# 创建新分支
Write-Host "`n 创建新分支：feature-person-job-fit" -ForegroundColor Yellow
git checkout -b feature-person-job-fit

# 添加所有新文件
Write-Host "`n 添加文件..." -ForegroundColor Yellow
git add backend/Person_job_fit_model/
git add backend/app/main.py
git add backend/test_api_integration.py

# 查看状态
Write-Host "`n Git 状态:" -ForegroundColor Yellow
git status --short

# 提交
Write-Host "`n 提交更改..." -ForegroundColor Yellow
git commit -m "feat: 集人岗匹配模块

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

功能:
- 岗位画像抽取：学历/年限/技能/行业/管理职责等
- 人岗匹配评分：5 维度加权计算，支持动态权重
- 风险识别：跳槽频率/岗位跨度/行业偏离/技能缺口/成果表达/空窗期
- 潜力评估：职业连续性/职责提升/项目复杂度/学习能力/平台跃迁
- 可视化：匹配雷达图/风险仪表盘/潜力柱状图/综合仪表盘

API 端点:
- POST /api/job-profile/parse - 抽取岗位画像
- POST /api/matching/score - 人岗匹配评分
- POST /api/matching/batch - 批量人岗匹配
- POST /api/risk/assessment - 风险识别
- POST /api/potential/evaluation - 潜力评估
- POST /api/comprehensive-report - 综合报告
- GET /api/model/info - 模型信息
"

# 查看提交日志
Write-Host "`n 提交日志:" -ForegroundColor Yellow
git log -1 --stat

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "✓ Git 提交完成！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "`n 下一步操作:" -ForegroundColor Yellow
Write-Host "1. 推送到远程仓库：git push origin feature-person-job-fit"
Write-Host "2. 在 GitHub 上创建 Pull Request"
Write-Host ""
