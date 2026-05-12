"""
排名页面问题诊断测试
用于排查候选人数据未显示的问题
"""
import pytest
import json
from pathlib import Path


class TestRankingDataFlow:
    """
    排名数据流测试 - 验证从数据到前端展示的完整链路
    """
    
    def test_data_source_exists(self):
        """1. 检查数据源文件是否存在"""
        project_root = Path(__file__).parent.parent.parent
        resume_file = project_root / ".venv" / "Resume_Recognition_Model" / "output" / "all_resumes_summary.json"
        
        assert resume_file.exists(), f"数据源文件不存在: {resume_file}"
        
        # 检查文件内容
        with open(resume_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert len(data) > 0, "数据源文件为空"
        print(f"✅ 数据源文件存在，共 {len(data)} 条简历")
    
    def test_industry_data_available(self):
        """2. 检查各行业是否有数据"""
        project_root = Path(__file__).parent.parent.parent
        resume_file = project_root / ".venv" / "Resume_Recognition_Model" / "output" / "all_resumes_summary.json"
        
        with open(resume_file, 'r', encoding='utf-8') as f:
            all_resumes = json.load(f)
        
        # 统计各行业数量
        industries = {}
        for r in all_resumes:
            ind = r.get('industry', 'unknown')
            industries[ind] = industries.get(ind, 0) + 1
        
        print("📊 各行业简历数量统计:")
        for ind, count in sorted(industries.items()):
            print(f"  - {ind}: {count}人")
        
        # 检查前端定义的6个行业
        expected_industries = ['电商', '品牌', '销售', '研发', '生产', '人力资源']
        for ind in expected_industries:
            assert ind in industries, f"行业'{ind}'没有数据"
    
    def test_api_rank_endpoint(self, client):
        """3. 测试排名API端点"""
        # 测试电商行业
        response = client.get("/api/rank/industry/电商?top_n=10")
        
        print(f"📡 API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 返回数据: {data}")
            
            assert "ranking" in data, "响应缺少ranking字段"
            assert isinstance(data["ranking"], list), "ranking应为列表"
            
            if len(data["ranking"]) == 0:
                print("⚠️ 警告: 排名列表为空")
            else:
                print(f"✅ 排名API返回 {len(data['ranking'])} 条数据")
        else:
            print(f"❌ API请求失败: {response.text}")
            pytest.fail(f"API返回错误状态码: {response.status_code}")
    
    def test_score_batch_api(self, client):
        """4. 测试批量评分API"""
        payload = {
            "resume_ids": [],
            "job_type": "电商",
            "industry": "电商"
        }
        
        response = client.post("/api/score/batch", json=payload)
        
        print(f"📡 批量评分API状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            assert "candidates" in data, "响应缺少candidates字段"
            assert "ranking" in data, "响应缺少ranking字段"
            
            print(f"✅ 批量评分返回 {len(data.get('candidates', []))} 个候选人")
            print(f"✅ 排名数据 {len(data.get('ranking', []))} 条")
        else:
            print(f"❌ 批量评分API失败: {response.text}")


class TestDataIntegrity:
    """数据完整性测试"""
    
    def test_resume_required_fields(self):
        """检查简历数据必需字段"""
        project_root = Path(__file__).parent.parent.parent
        resume_file = project_root / ".venv" / "Resume_Recognition_Model" / "output" / "all_resumes_summary.json"
        
        with open(resume_file, 'r', encoding='utf-8') as f:
            all_resumes = json.load(f)
        
        required_fields = ['basic_info', 'industry']
        incomplete = []
        
        for i, resume in enumerate(all_resumes):
            missing = [f for f in required_fields if f not in resume]
            if missing:
                incomplete.append((i, missing))
        
        if incomplete:
            print(f"⚠️ 发现 {len(incomplete)} 条简历缺少字段:")
            for idx, missing in incomplete[:5]:  # 只显示前5条
                print(f"  - 第{idx}条: 缺少 {missing}")
        
        # 允许部分数据不完整，但不应超过20%
        incomplete_ratio = len(incomplete) / len(all_resumes)
        assert incomplete_ratio < 0.2, f"数据不完整率{incomplete_ratio:.1%}过高"


if __name__ == "__main__":
    # 直接运行测试
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
