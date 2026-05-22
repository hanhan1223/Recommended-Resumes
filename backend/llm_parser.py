"""
LLM辅助简历解析模块
使用通义千问API进行深度语义理解和结构化信息提取
"""

import json
import re
from typing import Dict, List, Optional
from pathlib import Path

try:
    # 尝试使用阿里云SDK
    import dashscope
    from dashscope import DashScope
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    try:
        # 备选：使用OpenAI兼容接口
        from openai import OpenAI
        OPENAI_COMPATIBLE = True
    except ImportError:
        OPENAI_COMPATIBLE = False
        raise ImportError("请安装阿里云SDK: pip install dashscope 或 openai")

class LLMResumeParser:
    """基于LLM的简历解析器"""

    def __init__(self, api_key: str = None, model: str = "qwen3.5-flash"):
        """
        初始化LLM解析器

        Args:
            api_key: 通义千问API密钥
            model: 模型名称
        """
        if api_key is None:
            config_path = Path(__file__).parent / "config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    api_key = config.get('llm', {}).get('api_key', '')
                    model = config.get('llm', {}).get('model', model)

        if not api_key:
            raise ValueError("未提供API密钥，请检查config.json配置")

        self.api_key = api_key
        self.model = model

        # 根据可用库选择API方式
        if DASHSCOPE_AVAILABLE:
            self.use_dashscope = True
        elif OPENAI_COMPATIBLE:
            self.use_dashscope = False
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
        else:
            raise ImportError("请安装阿里云SDK: pip install dashscope")

    def _call_llm_api(self, messages: List[Dict], temperature: float = 0.1, max_tokens: int = 2000) -> str:
        """调用LLM API"""
        if self.use_dashscope:
            # 使用阿里云SDK
            response = dashscope.Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.api_key
            )

            if response.status_code == 200:
                return response.output['choices'][0]['message']['content']
            else:
                raise Exception(f"API调用失败: {response.message}")

        else:
            # 使用OpenAI兼容接口
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

    def parse_resume(self, resume_text: str, job_type: str = None) -> Dict:
        """
        使用LLM解析简历文本

        Args:
            resume_text: 简历文本内容
            job_type: 目标职位类型（用于上下文理解）

        Returns:
            解析后的结构化数据
        """
        # 构建提示词
        prompt = self._build_parsing_prompt(resume_text, job_type)

        try:
            # 调用LLM API
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            result_text = self._call_llm_api(messages, temperature=0.1, max_tokens=2000)

            # 解析响应
            return self._parse_llm_response(result_text)

        except Exception as e:
            print(f"[LLM Parser Error] {e}")
            return self._get_fallback_structure()

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的简历解析AI助手。你的任务是：
1. 从简历文本中提取关键信息
2. 识别潜在的数据矛盾或不一致
3. 评估信息的完整性和可信度

请严格按照JSON格式返回结果，确保：
- 所有字段名使用英文
- 学历、时间等使用标准格式
- 对不确定的信息使用null而非猜测
- 识别并标注任何数据矛盾"""

    def _build_parsing_prompt(self, resume_text: str, job_type: str = None) -> str:
        """构建解析提示词"""
        job_context = f"\n目标职位类型: {job_type}" if job_type else ""

        prompt = f"""请解析以下简历文本，提取结构化信息并评估数据质量。

{job_context}

简历文本：
---
{resume_text[:4000]}  # 限制长度避免token溢出
---

请返回JSON格式的解析结果，包含以下字段：

1. **基本信息**
   - name: 候选人姓名
   - gender: 性别
   - age: 年龄或出生年份
   - location: 所在地
   - contact: 联系方式

2. **教育经历** (数组)
   - time_period: 时间段
   - school: 学校名称
   - major: 专业
   - degree: 学历 (本科/硕士/博士等)

3. **工作经历** (数组)
   - time_period: 时间段
   - company: 公司名称
   - position: 职位
   - duration_months: 工作月数（数字）
   - key_achievements: 主要成就

4. **工作年限**
   - total_work_months: 总工作月数（数字）
   - calculation_basis: 计算依据

5. **数据质量评估**
   - completeness_score: 完整性评分 (0-100)
   - consistency_score: 一致性评分 (0-100)
   - contradictions: 发现的数据矛盾 (数组)
   - missing_fields: 缺失字段 (数组)
   - warnings: 警告信息 (数组)

请确保返回有效的JSON格式，不要包含markdown代码块标记。"""

        return prompt

    def _parse_llm_response(self, response_text: str) -> Dict:
        """解析LLM响应文本"""
        try:
            # 移除可能的markdown代码块标记
            text = response_text.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
                text = text.strip()

            # 尝试解析JSON
            result = json.loads(text)

            # 标准化字段名
            return self._normalize_field_names(result)

        except json.JSONDecodeError as e:
            print(f"[JSON Parse Error] {e}")
            print(f"[Raw Response] {response_text[:200]}")
            return self._get_fallback_structure()

    def _normalize_field_names(self, data: Dict) -> Dict:
        """标准化LLM返回的字段名"""
        normalized = {}

        # 基本信息
        if 'basic_info' in data:
            normalized['basic_info'] = data['basic_info']

        # 教育经历 - 尝试多种可能的字段名
        education_fields = ['education', 'education_experiences', 'education_experience', 'edu']
        for field in education_fields:
            if field in data:
                normalized['education_experiences'] = data[field]
                break

        # 工作经历 - 尝试多种可能的字段名
        work_fields = ['work_experience', 'work_experiences', 'work_experiences', 'work']
        for field in work_fields:
            if field in data:
                normalized['work_experiences'] = data[field]
                break

        # 工作年限
        if 'work_years' in data and isinstance(data['work_years'], dict):
            normalized['total_work_months'] = data['work_years'].get('total_work_months')
            normalized['calculation_basis'] = data['work_years'].get('calculation_basis')
        elif 'total_work_months' in data:
            normalized['total_work_months'] = data['total_work_months']

        # 数据质量评估 - 尝试多种可能的字段名
        quality_fields = ['data_quality_assessment', 'data_quality', 'quality', 'data_quality']
        for field in quality_fields:
            if field in data:
                normalized['data_quality'] = data[field]
                break

        # 保留原始数据
        normalized['_llm_raw'] = data

        return normalized

    def _get_fallback_structure(self) -> Dict:
        """获取备用结构（当解析失败时）"""
        return {
            "basic_info": {},
            "education_experiences": [],
            "work_experiences": [],
            "total_work_months": 0,
            "calculation_basis": "LLM解析失败，使用默认值",
            "data_quality": {
                "completeness_score": 0,
                "consistency_score": 0,
                "contradictions": ["LLM解析失败"],
                "missing_fields": ["所有字段"],
                "warnings": ["数据提取失败，请手动检查"]
            }
        }

    def validate_and_enrich(
        self,
        parsed_data: Dict,
        raw_text: str,
        job_type: str = None
    ) -> Dict:
        """
        验证并丰富解析结果

        Args:
            parsed_data: 已有解析结果
            raw_text: 原始文本
            job_type: 职位类型

        Returns:
            验证后的结构化数据
        """
        # 检查数据质量
        quality = parsed_data.get('data_quality', {})
        print(f"[DEBUG validate_and_enrich] data_quality: {quality}")

        # 如果质量分数较低，使用LLM重新解析
        completeness = quality.get('completeness_score', 0) if isinstance(quality, dict) else 0
        consistency = quality.get('consistency_score', 0) if isinstance(quality, dict) else 0

        print(f"[DEBUG validate_and_enrich] completeness: {completeness}, consistency: {consistency}")

        if completeness < 60 or consistency < 60:
            print(f"[LLM] 数据质量较低 (完整度:{completeness}, 一致性:{consistency})，尝试深度解析...")

            # 深度解析
            deep_result = self._deep_parse(raw_text, job_type)
            print(f"[DEBUG validate_and_enrich] deep_result keys: {list(deep_result.keys())}")
            print(f"[DEBUG validate_and_enrich] deep_result data_quality: {deep_result.get('data_quality')}")

            # 合并结果
            merged_result = self._merge_results(parsed_data, deep_result)
            print(f"[DEBUG validate_and_enrich] merged_result data_quality: {merged_result.get('data_quality')}")

            return merged_result

        return parsed_data

    def _deep_parse(self, raw_text: str, job_type: str = None) -> Dict:
        """深度解析复杂格式"""
        prompt = f"""深度解析以下简历，特别注意处理非标准格式。

目标职位: {job_type or '未指定'}

简历内容：
---
{raw_text[:3000]}
---

请严格按照以下JSON格式返回，包含所有字段：

{{
    "basic_info": {{
        "name": "姓名",
        "gender": "性别",
        "age": 年龄数字,
        "location": "所在地"
    }},
    "education_experiences": [
        {{
            "time_period": "时间段",
            "school": "学校名称",
            "major": "专业",
            "degree": "学历"
        }}
    ],
    "work_experiences": [
        {{
            "time_period": "时间段",
            "company": "公司名称",
            "position": "职位",
            "duration_months": 工作月数数字,
            "key_achievements": "主要成就"
        }}
    ],
    "total_work_months": 总工作月数数字,
    "calculation_basis": "计算依据说明",
    "data_quality": {{
        "completeness_score": 完整度评分0-100,
        "consistency_score": 一致性评分0-100,
        "contradictions": ["矛盾1", "矛盾2"],
        "missing_fields": ["缺失字段1"],
        "warnings": ["警告1"]
    }}
}}

确保返回有效JSON，不要包含markdown代码块。"""

        try:
            messages = [
                {"role": "system", "content": "你是一个专业的简历数据质量审核员。"},
                {"role": "user", "content": prompt}
            ]

            result_text = self._call_llm_api(messages, temperature=0.05, max_tokens=2500)

            return self._parse_llm_response(result_text)

        except Exception as e:
            print(f"[Deep Parse Error] {e}")
            return self._get_fallback_structure()

    def _merge_results(self, original: Dict, deep: Dict) -> Dict:
        """合并两个解析结果"""
        print(f"[DEBUG _merge_results] original keys: {list(original.keys())}")
        print(f"[DEBUG _merge_results] deep keys: {list(deep.keys())}")

        merged = original.copy()

        # 优先使用deep解析的结果
        for key in ['total_work_months', 'data_quality', 'calculation_basis']:
            if key in deep and deep[key] is not None:
                print(f"[DEBUG _merge_results] Merging key: {key}, value: {deep[key]}")
                merged[key] = deep[key]

        # 合并教育经历（去重）
        if 'education_experiences' in deep and isinstance(deep['education_experiences'], list):
            existing_schools = {e.get('school') for e in merged.get('education_experiences', []) if isinstance(e, dict)}
            for exp in deep['education_experiences']:
                if isinstance(exp, dict) and exp.get('school') not in existing_schools:
                    existing_schools.add(exp.get('school'))
                    merged.setdefault('education_experiences', []).append(exp)

        # 合并工作经历（去重）
        if 'work_experiences' in deep and isinstance(deep['work_experiences'], list):
            existing_companies = {e.get('company') for e in merged.get('work_experiences', []) if isinstance(e, dict)}
            for exp in deep['work_experiences']:
                if isinstance(exp, dict) and exp.get('company') not in existing_companies:
                    existing_companies.add(exp.get('company'))
                    merged.setdefault('work_experiences', []).append(exp)

        print(f"[DEBUG _merge_results] merged keys: {list(merged.keys())}")
        print(f"[DEBUG _merge_results] merged data_quality: {merged.get('data_quality')}")

        return merged


# 辅助函数
def create_llm_parser() -> LLMResumeParser:
    """创建LLM解析器实例"""
    try:
        return LLMResumeParser()
    except Exception as e:
        print(f"[Warning] 无法创建LLM解析器: {e}")
        return None
