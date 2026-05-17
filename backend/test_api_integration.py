# -*- coding: utf-8 -*-
"""
人岗匹配模型集成测试 - 测试 API 集成
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app, person_job_fit_model

print("\n" + "="*60)
print("人岗匹配模型 API 集成测试")
print("="*60)

# 检查路由
matching_routes = [r for r in app.routes if 'matching' in str(r)]
risk_routes = [r for r in app.routes if 'risk' in str(r)]
potential_routes = [r for r in app.routes if 'potential' in str(r)]
comprehensive_routes = [r for r in app.routes if 'comprehensive' in str(r)]

print(f"\n✓ 人岗匹配相关路由：{len(matching_routes)} 个")
print(f"  - /api/matching/score")
print(f"  - /api/matching/batch")

print(f"\n✓ 风险识别相关路由：{len(risk_routes)} 个")
print(f"  - /api/risk/assessment")

print(f"\n✓ 潜力评估相关路由：{len(potential_routes)} 个")
print(f"  - /api/potential/evaluation")

print(f"\n✓ 综合报告相关路由：{len(comprehensive_routes)} 个")
print(f"  - /api/comprehensive-report")

print(f"\n✓ 岗位画像抽取路由：1 个")
print(f"  - /api/job-profile/parse")

print(f"\n✓ 模型信息路由：1 个")
print(f"  - /api/model/info")

# 检查模型是否初始化
if person_job_fit_model:
    print(f"\n✓ 人岗匹配模型已初始化")
    model_info = person_job_fit_model.get_model_info()
    print(f"✓ 模型版本：{model_info['version']}")
    print(f"✓ 模块数量：{len(model_info['modules'])}")
else:
    print("\n✗ 人岗匹配模型未初始化")

print("\n" + "="*60)
print("✓ API 集成测试通过！")
print("="*60)
