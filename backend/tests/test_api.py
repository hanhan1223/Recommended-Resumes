"""
API接口测试
"""
import pytest

def test_root_endpoint(client):
    """测试根路径接口"""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "docs" in data

def test_industries_endpoint(client):
    """测试行业列表接口"""
    response = client.get("/api/industries")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "industries" in data
    
    industries = data["industries"]
    assert len(industries) == 6  # 现在只有6个行业
    
    # 验证不包含技术类和管理类
    codes = [i["code"] for i in industries]
    assert "technical" not in codes
    assert "management" not in codes
    
    # 验证每个行业有必需字段
    for ind in industries:
        assert "code" in ind
        assert "name" in ind
        assert "description" in ind

def test_score_single_missing_resume_id(client):
    """测试单份评分接口 - 缺少resume_id"""
    payload = {
        "job_type": "电商",
        "industry": "电商"
    }
    response = client.post("/api/score/single", json=payload)
    assert response.status_code == 422  # 验证错误

def test_qa_ask_endpoint(client):
    """测试智能问答接口"""
    test_cases = [
        ("排名第几？", 200),
        ("得分如何？", 200),
        ("有什么优势？", 200),
        ("有风险吗？", 200),
        ("是否推荐？", 200),
    ]
    
    for question, expected_status in test_cases:
        payload = {
            "question": question,
            "context": {}
        }
        response = client.post("/api/qa/ask", json=payload)
        assert response.status_code == expected_status
        
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

def test_report_generate_invalid_format(client):
    """测试报告生成接口 - 无效格式"""
    response = client.get("/api/report/generate/电商?format=xml")
    assert response.status_code == 400

def test_cors_headers(client):
    """测试CORS配置 - 预检请求"""
    # 带Origin头的GET请求才会触发CORS
    response = client.get(
        "/api/industries",
        headers={"Origin": "http://localhost:5173"}
    )
    
    # GET请求应该包含CORS头
    assert "access-control-allow-origin" in response.headers, "缺少CORS响应头"
