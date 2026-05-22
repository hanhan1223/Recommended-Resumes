"""
简历解析与识别模块
支持 PDF、DOCX、TXT 格式简历的解析
"""

from .resume_parser import ResumeParser, batch_parse_resumes

__version__ = "1.0.0"

__all__ = [
    "ResumeParser",
    "batch_parse_resumes"
]
