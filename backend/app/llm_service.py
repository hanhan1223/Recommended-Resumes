# -*- coding: utf-8 -*-
"""
LLM服务模块 - 通义千问(Qwen)
"""
import os
import json
import httpx
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

def load_config():
    """从配置文件加载LLM配置"""
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("llm", {})
    return {}

class LLMService:
    """通义千问LLM服务"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        config = load_config()
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "") or config.get("api_key", "")
        self.model = model or config.get("model", "qwen3.5-flash")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.enabled = bool(self.api_key) and self.api_key != "your-api-key-here"

    def is_enabled(self) -> bool:
        """检查LLM是否可用"""
        return self.enabled

    async def chat(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """
        发送对话请求到通义千问

        Args:
            messages: 对话消息列表，格式如 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制随机性 (0-1)

        Returns:
            LLM回复文本
        """
        if not self.is_enabled():
            raise ValueError("LLM未启用，请配置API Key")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                raise Exception(f"LLM API错误: {response.status_code} - {response.text}")

            result = response.json()
            return result["choices"][0]["message"]["content"]

    def build_candidate_summary_prompt(self, candidate: Dict, industry: str) -> str:
        """构建候选人总结的提示词"""
        basic_info = candidate.get("basic_info", {})
        name = basic_info.get("name", candidate.get("candidate_id", "未知"))

        scores = candidate.get("dimensional_scores", {})
        weights = candidate.get("dimension_weights", {})

        prompt = f"""请为以下候选人生成一份简洁的推荐理由和风险提示：

候选人姓名: {name}
应聘行业: {industry}

综合评分: {candidate.get('tci_score', 'N/A')}
排名: 第{candidate.get('rank', 'N/A')}名

各维度得分:
- 教育背景: {scores.get('education', 'N/A')} (权重: {weights.get('education', 0)*100:.0f}%)
- 工作经历: {scores.get('experience', 'N/A')} (权重: {weights.get('experience', 0)*100:.0f}%)
- 技能成果: {scores.get('skill_achievement', 'N/A')} (权重: {weights.get('skill_achievement', 0)*100:.0f}%)
- 综合素质: {scores.get('comprehensive', 'N/A')} (权重: {weights.get('comprehensive', 0)*100:.0f}%)

跳槽风险: {'有' if candidate.get('penalty_applied') else '无'}

请生成:
1. 简要推荐理由（2-3句话）
2. 主要优势（1-2点）
3. 潜在风险（1-2点，如有）
"""

        return prompt

    def build_analysis_prompt(self, candidate: Dict, industry: str, rank: int, total: int) -> List[Dict]:
        """构建综合分析提示词 - 用于自动生成候选人分析报告"""
        basic_info = candidate.get("basic_info", {})
        name = basic_info.get("name", candidate.get("candidate_id", "未知"))

        scores = candidate.get("dimensional_scores", {})
        weights = candidate.get("dimension_weights", {})
        tci_score = candidate.get('tci_score', 0)
        penalty = candidate.get('penalty_applied', False)

        def fmt(val):
            if val is None or val == 'N/A' or val == '':
                return 'N/A'
            try:
                return f"{float(val):.2f}"
            except (ValueError, TypeError):
                return str(val)

        entities = candidate.get("entities", {})
        companies = entities.get("companies", [])
        schools = entities.get("schools", [])
        positions = entities.get("positions", [])
        skills = entities.get("skills", [])

        achievements = candidate.get("achievements", [])
        work_exp = candidate.get("work_experiences", [])
        project_exp = candidate.get("project_experiences", [])
        edu_exp = candidate.get("education_experiences", [])
        company_ratings = candidate.get("company_ratings", [])
        university_ratings = candidate.get("university_ratings", [])
        work_duration = candidate.get("work_duration_months", 0)

        achievements_text = "\n".join([f"- {a.get('original_text', '')}" for a in achievements[:8] if a.get('original_text')]) or "暂无"

        project_text = ""
        for p in project_exp[:3]:
            proj_name = p.get("name", "项目经验")
            proj_desc = p.get("description", [])
            if isinstance(proj_desc, list):
                proj_desc = " | ".join(str(d) for d in proj_desc[:5])
            project_text += f"\n- {proj_name}: {str(proj_desc)[:500]}"

        work_text = ""
        for w in work_exp[:5]:
            period = w.get("time_period", "")
            company = w.get("company", "")
            position = w.get("position", "")
            responsibilities = w.get("responsibilities", [])
            resp_text = " | ".join(str(r) for r in responsibilities[:3])
            work_text += f"\n- {period} {company} {position}: {resp_text[:300]}"

        edu_text = ""
        for e in edu_exp[:3]:
            edu_text += f"\n- {e.get('time_period', '')} {e.get('school', '')} {e.get('major', '')} {e.get('degree', '')}"

        company_ratings_text = "\n".join([f"- {r['company']}: {r['rating']}星 ({r.get('reason', '')})" for r in company_ratings[:5]]) or "暂无"
        university_ratings_text = "\n".join([f"- {r['university']}: {r['rating']}星 ({r.get('reason', '')})" for r in university_ratings[:3]]) or "暂无"

        context = f"""请对以下候选人进行综合分析评估，输出严格的 JSON 格式。

## 候选人基本信息
- 姓名: {name}
- 应聘行业: {industry}
- 综合评分(TCI): {fmt(tci_score)} / 5.00
- 行业排名: 第{rank}名 / 共{total}人
- 工作年限: {work_duration / 12:.1f}年
- 跳槽风险: {'有（频繁跳槽）' if penalty else '无'}

## 各维度得分（满分5.00）
| 维度 | 得分 | 权重 |
|------|------|------|
| 教育背景 | {fmt(scores.get('education'))} | {fmt(weights.get('education', 0)*100)}% |
| 工作经历 | {fmt(scores.get('experience'))} | {fmt(weights.get('experience', 0)*100)}% |
| 技能成果 | {fmt(scores.get('skill_achievement'))} | {fmt(weights.get('skill_achievement', 0)*100)}% |
| 综合素质 | {fmt(scores.get('comprehensive'))} | {fmt(weights.get('comprehensive', 0)*100)}% |

## 教育背景
学校评级:
{university_ratings_text}
教育经历:
{edu_text or '暂无详细信息'}

## 工作经历
公司评级:
{company_ratings_text}
工作详情:
{work_text or '暂无详细信息'}

## 技能特长
{', '.join(skills[:15]) if skills else '暂无'}

## 任职岗位
{', '.join(positions[:5]) if positions else '暂无'}

## 工作公司
{', '.join(companies[:5]) if companies else '暂无'}

## 主要成就
{achievements_text}

## 项目经验
{project_text or '暂无'}"""

        messages = [
            {"role": "system", "content": """你是一个专业的人才评估分析师。请根据候选人的完整简历数据和评分结果，进行综合分析。

你必须严格按照以下 JSON 格式输出，不要输出任何其他内容：
{
  "summary": "综合评价（2-3句话，概括候选人整体情况）",
  "strengths": ["优势1", "优势2", "优势3"],
  "weaknesses": ["不足1", "不足2"],
  "risks": ["风险1", "风险2"],
  "recommendation": "录用建议（明确推荐/可以考虑/暂不推荐，附理由）",
  "development_suggestions": ["发展建议1", "发展建议2"]
}

要求：
1. 所有分析必须基于提供的实际数据，禁止编造
2. strengths 侧重于候选人的核心竞争力和亮点
3. weaknesses 指出候选人需要改进或注意的地方
4. risks 分析潜在的用人风险（稳定性、能力匹配等）
5. recommendation 给出明确的录用建议和理由
6. development_suggestions 给出候选人职业发展建议
7. 使用中文回答，语言专业客观"""},
            {"role": "user", "content": context}
        ]

        return messages

    def build_qa_prompt(self, question: str, candidate: Dict, industry: str, all_candidates: List[Dict] = None) -> List[Dict]:
        """构建问答提示词"""
        basic_info = candidate.get("basic_info", {})
        name = basic_info.get("name", candidate.get("candidate_id", "未知"))

        scores = candidate.get("dimensional_scores", {})
        weights = candidate.get("dimension_weights", {})
        tci_score = candidate.get('tci_score', 0)
        rank = candidate.get('rank', 'N/A')

        def fmt(val):
            if val is None or val == 'N/A' or val == '':
                return 'N/A'
            try:
                return f"{float(val):.2f}"
            except (ValueError, TypeError):
                return str(val)

        entities = candidate.get("entities", {})
        companies = entities.get("companies", [])
        schools = entities.get("schools", [])
        positions = entities.get("positions", [])
        skills = entities.get("skills", [])

        achievements = candidate.get("achievements", [])
        work_exp = candidate.get("work_experiences", [])
        project_exp = candidate.get("project_experiences", [])
        edu_exp = candidate.get("education_experiences", [])

        achievements_text = "\n".join([f"- {a.get('original_text', '')}" for a in achievements[:5] if a.get('original_text')]) or "暂无"

        project_exp_text = ""
        if project_exp:
            for p in project_exp[:2]:
                proj_name = p.get("name", "项目经验")
                proj_desc = p.get("description", [])
                if isinstance(proj_desc, list):
                    proj_desc = " | ".join(str(d) for d in proj_desc[:3])
                project_exp_text += f"\n【{proj_name}】{proj_desc[:300]}..."

        context = f"""你是人才简历综合优选系统的智能助手，帮助用户了解候选人的情况和系统功能。

当前用户询问关于候选人 {name} 的问题。

## 候选人基本信息
- 姓名: {name}
- 应聘行业: {industry}
- 综合评分(TCI): {fmt(tci_score)} / 5.00
- 行业排名: 第{rank}名

## 各维度得分（满分5.00）
| 维度 | 得分 | 权重 |
|------|------|------|
| 教育背景 | {fmt(scores.get('education'))} | {fmt(weights.get('education', 0)*100)}% |
| 工作经历 | {fmt(scores.get('experience'))} | {fmt(weights.get('experience', 0)*100)}% |
| 技能成果 | {fmt(scores.get('skill_achievement'))} | {fmt(weights.get('skill_achievement', 0)*100)}% |
| 综合素质 | {fmt(scores.get('comprehensive'))} | {fmt(weights.get('comprehensive', 0)*100)}% |

跳槽风险: {'⚠️ 有' if candidate.get('penalty_applied') else '✅ 无'}"""

        if companies or schools or positions or skills:
            context += "\n\n## 简历摘要"
            if companies:
                context += f"\n- 工作公司: {', '.join(companies[:5])}"
            if positions:
                context += f"\n- 任职岗位: {', '.join(positions[:5])}"
            if schools:
                context += f"\n- 毕业学校: {', '.join(schools[:3])}"
            if skills:
                context += f"\n- 技能特长: {', '.join(skills[:10])}"

        if achievements_text != "暂无":
            context += f"\n\n## 主要成就\n{achievements_text}"

        if project_exp_text:
            context += f"\n\n## 项目经历{project_exp_text}"

        if all_candidates and len(all_candidates) > 1:
            top3 = all_candidates[:3]
            context += "\n\n## 同行业Top 3候选人"
            for i, c in enumerate(top3, 1):
                c_name = c.get('candidate_id', '未知')
                c_score = fmt(c.get('tci_score', 0))
                context += f"\n{i}. {c_name} - TCI: {c_score}"

        context += f"\n\n---\n用户问题: {question}"

        messages = [
            {"role": "system", "content": """你是一个专业的人才招聘助手。请使用Markdown格式，严格按照以下结构回答：

## 【综合评分】
- 评分：[X.XX]/5.00
- 评价：简短一句

## 【优势分析】
- 优势1
- 优势2

## 【风险提示】
- 风险1（如有）

## 【录用建议】
- 建议

---
⚠️ 重要提醒：
1. 所有评分必须使用上方提供的实际数据，格式为XX.XX（如3.50）
2. 如果数据为"N/A"，必须说明"数据暂未获取"
3. 禁止编造或修改任何数据
4. 回答简洁专业，总字数150-200字"""},
            {"role": "user", "content": context}
        ]

        return messages


# 全局LLM服务实例
_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """获取LLM服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

def init_llm_service(api_key: str, model: str = "qwen-turbo") -> LLMService:
    """初始化LLM服务"""
    global _llm_service
    _llm_service = LLMService(api_key=api_key, model=model)
    return _llm_service
