"""
数据验证模块
确保API返回数据的完整性和正确性
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class DataValidator:
    """数据验证器"""

    @staticmethod
    def validate_candidate(candidate: Dict) -> Dict:
        """
        验证候选人数据完整性
        返回验证结果和缺失字段列表
        """
        required_fields = {
            'candidate_id': str,
            'tci_score': (int, float),
            'dimensional_scores': dict,
            'dimension_weights': dict,
            'penalty_applied': bool
        }

        optional_fields = {
            'rank': (int, str),
            'basic_info': dict,
            'education': list,
            'work_experience': list,
            'skills': list,
            'achievements': list
        }

        issues = []
        warnings = []

        # 检查必填字段
        for field, expected_type in required_fields.items():
            if field not in candidate:
                issues.append(f"缺少必填字段: {field}")
            elif not isinstance(candidate[field], expected_type):
                issues.append(f"字段类型错误: {field} (期望 {expected_type}, 实际 {type(candidate[field]).__name__})")

        # 检查选填字段
        for field, expected_type in optional_fields.items():
            if field not in candidate:
                warnings.append(f"缺少可选字段: {field}")

        # 验证 dimensional_scores 结构
        if 'dimensional_scores' in candidate:
            dim_scores = candidate['dimensional_scores']
            required_dims = ['education', 'experience', 'skill_achievement', 'comprehensive']
            for dim in required_dims:
                if dim not in dim_scores:
                    warnings.append(f"缺少维度得分: {dim}")
                elif not isinstance(dim_scores[dim], (int, float)):
                    warnings.append(f"维度得分类型错误: {dim}")

        # 验证 dimension_weights 结构
        if 'dimension_weights' in candidate:
            dim_weights = candidate['dimension_weights']
            for dim in required_dims:
                if dim not in dim_weights:
                    warnings.append(f"缺少维度权重: {dim}")
                elif not isinstance(dim_weights[dim], (int, float)):
                    warnings.append(f"维度权重类型错误: {dim}")
                elif dim_weights[dim] < 0 or dim_weights[dim] > 1:
                    warnings.append(f"维度权重超出范围 [0,1]: {dim}={dim_weights[dim]}")

        # 验证 TCI 分数范围
        if 'tci_score' in candidate:
            score = candidate['tci_score']
            if not isinstance(score, (int, float)):
                issues.append(f"TCI分数类型错误: {type(score).__name__}")
            elif score < 0 or score > 5:
                warnings.append(f"TCI分数超出范围 [0,5]: {score}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'validated_at': datetime.now().isoformat()
        }

    @staticmethod
    def validate_batch_response(response: Dict) -> Dict:
        """
        验证批量评分API响应
        """
        issues = []
        warnings = []

        # 检查状态
        if response.get('status') != 'success':
            issues.append(f"响应状态错误: {response.get('status')}")

        # 检查必要字段
        required = ['status', 'industry', 'ranking', 'candidates']
        for field in required:
            if field not in response:
                issues.append(f"缺少字段: {field}")

        # 检查 candidates 列表
        if 'candidates' in response:
            candidates = response['candidates']
            if not isinstance(candidates, list):
                issues.append(f"candidates应为列表，实际为 {type(candidates).__name__}")
            else:
                for i, candidate in enumerate(candidates):
                    validation = DataValidator.validate_candidate(candidate)
                    if not validation['valid']:
                        warnings.append(f"候选人 {i} ({candidate.get('candidate_id', 'unknown')}) 数据问题: {validation['issues']}")

        # 检查 ranking 列表
        if 'ranking' in response:
            ranking = response['ranking']
            if not isinstance(ranking, list):
                issues.append(f"ranking应为列表，实际为 {type(ranking).__name__}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'validated_at': datetime.now().isoformat()
        }

    @staticmethod
    def sanitize_candidate(candidate: Dict) -> Dict:
        """
        清理和修复候选人数据
        """
        sanitized = {}

        # 必填字段
        sanitized['candidate_id'] = str(candidate.get('candidate_id', 'unknown'))
        sanitized['tci_score'] = float(candidate.get('tci_score', 0))
        sanitized['penalty_applied'] = bool(candidate.get('penalty_applied', False))

        # 维度得分
        dim_scores = candidate.get('dimensional_scores', {})
        sanitized['dimensional_scores'] = {
            'education': float(dim_scores.get('education', 0)),
            'experience': float(dim_scores.get('experience', 0)),
            'skill_achievement': float(dim_scores.get('skill_achievement', 0)),
            'comprehensive': float(dim_scores.get('comprehensive', 0))
        }

        # 维度权重
        dim_weights = candidate.get('dimension_weights', {})
        sanitized['dimension_weights'] = {
            'education': float(dim_weights.get('education', 0.25)),
            'experience': float(dim_weights.get('experience', 0.25)),
            'skill_achievement': float(dim_weights.get('skill_achievement', 0.25)),
            'comprehensive': float(dim_weights.get('comprehensive', 0.25))
        }

        # 可选字段
        if 'rank' in candidate:
            sanitized['rank'] = candidate['rank']
        if 'basic_info' in candidate:
            sanitized['basic_info'] = candidate['basic_info']
        if 'education' in candidate:
            sanitized['education'] = candidate['education']
        if 'work_experience' in candidate:
            sanitized['work_experience'] = candidate['work_experience']
        if 'skills' in candidate:
            sanitized['skills'] = candidate['skills']
        if 'achievements' in candidate:
            sanitized['achievements'] = candidate['achievements']

        return sanitized


def validate_api_response(func):
    """
    装饰器：验证API响应数据完整性
    """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        # 验证响应
        validation = DataValidator.validate_batch_response(result)

        # 添加验证信息到响应
        result['_validation'] = validation

        # 如果有严重问题，记录日志但不阻断
        if not validation['valid']:
            print(f"[WARN] API响应验证失败: {validation['issues']}")

        return result

    return wrapper
