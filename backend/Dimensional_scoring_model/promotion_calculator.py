"""
职级序列与升职速度量化模块

功能：
1. 构建职级序列（助理→专员→主管→经理→总监→VP→总裁）
2. 从简历 positions 中识别职级变化
3. 计算升职速度 = 职级变化次数 / 总工作年限
"""

from typing import Dict, List, Tuple


class PromotionCalculator:
    """升职速度计算器"""

    CAREER_LEVELS = {
        1: ["助理", "专员", "文员", "技术员", "工程师", "初级"],
        2: ["高级", "资深", "主创", "主办", "中级"],
        3: ["主管", "组长", "团队负责人", "lead", "项目经理"],
        4: ["经理", "部长", "部门负责人", "总监助理"],
        5: ["高级经理", "资深经理", "副总监", "总监", "总经理"],
        6: ["资深总监", "高级总监", "执行总监", "常务总监"],
        7: ["副总裁", "副总", "VP", "副总经理", "总裁助理"],
        8: ["总裁", "总经理", "CEO", "COO", "创始人", "联合创始人", "合伙人", "董事长"]
    }

    LEVEL_NAMES = {
        1: "初级员工",
        2: "高级员工",
        3: "基层管理",
        4: "中层管理",
        5: "高层管理",
        6: "资深高层",
        7: "副总裁级",
        8: "总裁级"
    }

    def __init__(self):
        self.position_level_cache = {}

    def get_position_level(self, position: str) -> int:
        """
        识别职位的职级

        Args:
            position: 职位名称

        Returns:
            职级 (1-8)
        """
        if not position:
            return 1

        position_lower = position.lower()

        if position in self.position_level_cache:
            return self.position_level_cache[position]

        max_level = 1

        for level, keywords in self.CAREER_LEVELS.items():
            for keyword in keywords:
                if keyword.lower() in position_lower:
                    max_level = max(max_level, level)

        self.position_level_cache[position] = max_level
        return max_level

    def calculate_promotion_speed(self, resume: Dict) -> float:
        """
        计算升职速度

        升职速度 = 职级变化次数 / 总工作年限

        Args:
            resume: 简历字典

        Returns:
            升职速度分数 (0-2 之间，2 为满分)
        """
        positions = resume.get("entities", {}).get("positions", [])
        work_duration_months = resume.get("work_duration_months", 0)

        if not positions or work_duration_months <= 0:
            return self._calculate_from_positions_only(positions)

        levels = [self.get_position_level(pos) for pos in positions]

        if len(levels) < 2:
            return 1.0

        promotion_count = 0
        for i in range(1, len(levels)):
            if levels[i] > levels[i-1]:
                promotion_count += 1

        work_years = work_duration_months / 12.0

        if work_years < 1:
            work_years = 1

        promotion_speed = promotion_count / work_years

        score = min(promotion_speed * 2, 2.0)

        return score

    def _calculate_from_positions_only(self, positions: List[str]) -> float:
        """
        当没有工作年限时，仅从职位序列计算升职速度

        Args:
            positions: 职位列表

        Returns:
            升职速度分数
        """
        if not positions or len(positions) < 2:
            return 1.0

        levels = [self.get_position_level(pos) for pos in positions]

        max_level = max(levels)
        min_level = min(levels)

        level_range = max_level - min_level

        if level_range >= 3:
            return 2.0
        elif level_range >= 2:
            return 1.5
        elif level_range >= 1:
            return 1.2
        else:
            return 1.0

    def detect_career_path(self, resume: Dict) -> List[Dict]:
        """
        检测职业发展路径

        Args:
            resume: 简历字典

        Returns:
            职业发展路径列表
        """
        positions = resume.get("entities", {}).get("positions", [])

        if not positions:
            return []

        career_path = []
        prev_level = 0

        for position in positions:
            level = self.get_position_level(position)
            change_type = "unchanged"

            if level > prev_level and prev_level > 0:
                change_type = "promotion"
            elif level < prev_level and prev_level > 0:
                change_type = "demotion"

            career_path.append({
                "position": position,
                "level": level,
                "level_name": self.LEVEL_NAMES.get(level, "未知"),
                "change_type": change_type
            })

            prev_level = level

        return career_path

    def get_promotion_analysis(self, resume: Dict) -> Dict:
        """
        获取升职分析详情

        Args:
            resume: 简历字典

        Returns:
            升职分析字典
        """
        positions = resume.get("entities", {}).get("positions", [])
        work_duration_months = resume.get("work_duration_months", 0)

        levels = [self.get_position_level(pos) for pos in positions]

        if not levels:
            return {
                "n_positions": 0,
                "max_level": 0,
                "current_level": 0,
                "promotion_count": 0,
                "work_years": 0,
                "promotion_speed": 0,
                "score": 0
            }

        promotion_count = sum(1 for i in range(1, len(levels)) if levels[i] > levels[i-1])

        return {
            "n_positions": len(positions),
            "max_level": max(levels),
            "current_level": levels[-1] if levels else 0,
            "promotion_count": promotion_count,
            "work_years": work_duration_months / 12.0,
            "promotion_speed": promotion_count / (work_duration_months / 12.0) if work_duration_months > 0 else 0,
            "score": self.calculate_promotion_speed(resume)
        }
