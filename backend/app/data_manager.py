"""
数据管理模块 - 负责简历数据的持久化和查询
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

class ResumeDataManager:
    """简历数据管理器"""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.data_file = self.project_root / "Resume_Recognition_Model" / "output" / "all_resumes_summary.json"
        self.upload_dir = self.project_root / "backend" / "uploads"
        
        # 确保目录存在
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据文件
        self._init_data_file()
    
    def _init_data_file(self):
        """初始化数据文件（如果不存在）"""
        if not self.data_file.exists():
            self._save_data([])
    
    def _load_data(self) -> List[Dict]:
        """加载所有简历数据"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 处理不同的JSON格式
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'resumes' in data:
                    # 处理 {"resumes": [...], ...} 格式
                    return data.get('resumes', [])
                else:
                    return []
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_data(self, data: List[Dict]):
        """保存数据到文件"""
        # 保存为 {"resumes": [...], ...} 格式
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump({
                'resumes': data,
                'total': len(data),
                'parsed_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def add_resume(self, resume_data: Dict) -> bool:
        """
        添加新简历到数据源
        
        Args:
            resume_data: 解析后的简历数据
        
        Returns:
            bool: 是否添加成功
        """
        try:
            data = self._load_data()
            
            # 生成唯一ID
            candidate_name = resume_data.get('basic_info', {}).get('name', 'Unknown')
            file_name = resume_data.get('file_name', f"resume_{datetime.now().timestamp()}")
            
            # 检查是否已存在
            existing = [r for r in data if r.get('file_name') == file_name]
            if existing:
                # 更新现有记录
                for r in data:
                    if r.get('file_name') == file_name:
                        r.update(resume_data)
                        break
            else:
                # 添加新记录
                resume_data['file_name'] = file_name
                resume_data['upload_time'] = datetime.now().isoformat()
                data.append(resume_data)
            
            self._save_data(data)
            print("[OK] 简历数据已保存: {} ({})".format(candidate_name, file_name))
            return True
            
        except Exception as e:
            print("[ERROR] 保存简历数据失败: {}".format(e))
            return False
    
    def get_resumes_by_industry(self, industry: str) -> List[Dict]:
        """
        按行业获取简历列表
        
        Args:
            industry: 行业代码
        
        Returns:
            List[Dict]: 简历列表
        """
        data = self._load_data()
        return [r for r in data if r.get('industry') == industry]
    
    def get_all_resumes(self) -> List[Dict]:
        """获取所有简历"""
        return self._load_data()
    
    def get_resume_by_name(self, name: str) -> Optional[Dict]:
        """按姓名查找简历"""
        data = self._load_data()
        for r in data:
            if r.get('basic_info', {}).get('name') == name:
                return r
        return None
    
    def update_resume_industry(self, file_name: str, industry: str, confidence: float = 0.0):
        """
        更新简历的行业信息
        
        Args:
            file_name: 文件名
            industry: 行业代码
            confidence: 行业识别置信度
        """
        data = self._load_data()
        for r in data:
            if r.get('file_name') == file_name:
                r['industry'] = industry
                r['industry_confidence'] = confidence
                break
        self._save_data(data)
    
    def get_statistics(self) -> Dict:
        """获取数据统计信息"""
        data = self._load_data()
        industries = {}
        for r in data:
            ind = r.get('industry', '未知')
            industries[ind] = industries.get(ind, 0) + 1
        
        return {
            "total": len(data),
            "by_industry": industries
        }

# 全局数据管理器实例
_data_manager = None

def get_data_manager(project_root: Path = None) -> ResumeDataManager:
    """获取数据管理器单例"""
    global _data_manager
    if _data_manager is None:
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        _data_manager = ResumeDataManager(project_root)
    return _data_manager
