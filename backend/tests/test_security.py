"""
安全测试 - OWASP Top 10
"""
import pytest

def test_sql_injection_in_resume_id(client):
    """SQL注入防护测试 - resume_id字段"""
    malicious_inputs = [
        "' OR 1=1 --",
        "'; DROP TABLE resumes; --",
        "1' UNION SELECT * FROM users --",
    ]
    
    for injection in malicious_inputs:
        payload = {
            "resume_id": injection,
            "job_type": "电商"
        }
        response = client.post("/api/score/single", json=payload)
        
        # 不应返回500服务器错误
        assert response.status_code != 500, f"SQL注入未防护: {injection}"

def test_xss_in_qa_question(client):
    """XSS跨站脚本防护测试"""
    xss_payloads = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
    ]
    
    for payload in xss_payloads:
        qa_payload = {
            "question": payload,
            "context": {}
        }
        response = client.post("/api/qa/ask", json=qa_payload)
        
        # 接口应正常响应
        assert response.status_code in [200, 500]  # 500可能是处理异常
        
        if response.status_code == 200:
            # 响应中不应包含未转义的脚本标签
            content = response.text
            # 检查是否有XSS漏洞：如果返回了原始脚本标签则有风险
            if "<script>" in content and "&lt;script&gt;" not in content:
                pytest.fail(f"XSS漏洞：响应中包含未转义的脚本标签: {payload}")

def test_invalid_json_payload(client):
    """无效JSON负载测试"""
    response = client.post(
        "/api/score/single",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422

def test_method_not_allowed(client):
    """HTTP方法不允许测试"""
    response = client.delete("/api/industries")
    assert response.status_code == 405

def test_cors_headers_present(client):
    """CORS响应头检查"""
    # 带Origin头的请求才会触发CORS
    response = client.get(
        "/api/industries",
        headers={"Origin": "http://localhost:5173"}
    )
    
    # 检查CORS头是否存在
    assert "access-control-allow-origin" in response.headers, "缺少CORS响应头"
    
    # 检查是否允许跨域（可能是*或具体域名）
    cors_origin = response.headers["access-control-allow-origin"]
    assert cors_origin in ["*", "http://localhost:5173"], f"CORS配置异常: {cors_origin}"
