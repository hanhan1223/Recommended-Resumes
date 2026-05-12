"""
人才简历综合优选系统 - FastAPI后端主入口
基于已有模型构建，提供API服务
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import html

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn

# 添加模型路径
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
project_root = backend_dir.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "Resume_Recognition_Model"))

from Dimensional_scoring_model import DimensionalScoringModel
from Dynamic_Industry_Weight_Matrix import IndustryWeightMatrix
from app.data_manager import get_data_manager, ResumeDataManager
from app.llm_service import get_llm_service, init_llm_service
from app.data_validator import DataValidator
from app.cache_manager import get_cache_manager

app = FastAPI(
    title="人才简历综合优选系统",
    description="基于AHP+熵权法的多维度简历评分系统",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局模型实例
weight_matrix_calculator = None
scoring_model = None

# ============== 数据模型定义 ==============

class JobDescription(BaseModel):
    """岗位描述"""
    title: str
    description: str
    requirements: Optional[str] = None
    industry: Optional[str] = None

class ResumeScoreRequest(BaseModel):
    """简历评分请求"""
    resume_id: str
    job_type: str = "technical"  # technical/management/电商/品牌/销售/研发/生产/人力资源
    industry: Optional[str] = None

class BatchScoreRequest(BaseModel):
    """批量评分请求"""
    resume_ids: List[str]
    job_type: str
    industry: Optional[str] = None

class ScoreResponse(BaseModel):
    """评分响应"""
    candidate_id: str
    tci_score: float
    dimensional_scores: dict
    dimension_weights: dict
    ranking: int
    analysis: dict

class QARequest(BaseModel):
    """智能问答请求"""
    question: str
    context: Optional[dict] = None

# ============== 初始化函数 ==============

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化模型"""
    global weight_matrix_calculator, scoring_model

    print("="*60)
    print("正在初始化人才简历综合优选系统...")
    print("="*60)

    # 初始化缓存管理器
    cache = get_cache_manager()
    cache_stats = cache.get_cache_stats()
    print(f"[CACHE] 缓存目录: {cache_stats['cache_dir']}")

    # 初始化动态权重计算器
    weight_matrix_calculator = IndustryWeightMatrix(
        alpha=0.5,
        save_dir=str(project_root / "backend" / "output" / "weights"),
        verbose=True
    )

    # 初始化评分模型
    scoring_model = DimensionalScoringModel(
        save_dir=str(project_root / "backend" / "output" / "visualizations"),
        verbose=True
    )

    print("\n[OK] System initialization completed!")
    print("="*60)

# ============== API端点 ==============

@app.get("/")
async def root():
    """根路径 - API信息"""
    return {
        "name": "人才简历综合优选系统 API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "resume": "/api/resume/*",
            "score": "/api/score/*",
            "rank": "/api/rank/*",
            "report": "/api/report/*",
            "qa": "/api/qa/*"
        }
    }

@app.post("/api/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    industry: Optional[str] = Form(None)
):
    """
    上传简历文件
    支持PDF、DOCX、TXT格式
    """
    try:
        # 保存上传文件
        upload_dir = project_root / "backend" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # TODO: 调用简历解析模块
        # 这里返回文件信息，实际应调用ResumeParser
        
        return {
            "status": "success",
            "message": "简历上传成功",
            "data": {
                "filename": file.filename,
                "filepath": str(file_path),
                "industry": industry,
                "upload_time": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

class ParseResumeRequest(BaseModel):
    """简历解析请求"""
    file_path: str
    industry: Optional[str] = None

def _extract_candidate_name(filename: str) -> str:
    """
    从简历文件名中提取候选人姓名

    支持的格式：
    - Java实习生-张泽轩-华南理工大学广州学院-大三.pdf
    - 张泽轩-Java实习生.pdf
    - 20230424-WCG-电子商务总监()-for-电商运营负责人.docx
    - 研发2/20240316-LZ博士-研发总监（）-for研究院院长.docx

    Args:
        filename: 文件名（不含路径和扩展名）

    Returns:
        提取的候选人姓名
    """
    import re

    name = Path(filename).stem

    exclude_keywords = ['for', 'PDF', 'DOCX', 'DOC', 'TXT']
    chinese_name_pattern = re.compile(r'^[\u4e00-\u9fff]{2,4}$')
    english_pattern = re.compile(r'^[A-Z]{2,5}$')
    mixed_pattern = re.compile(r'^([A-Z]{2,5})([\u4e00-\u9fff]{1,3})$')

    job_keywords = ['总监', '经理', '工程师', '研发', '技术', '运营', '主管', '负责人', '专员', '助理', '实习生']

    clean_name = name.replace('（', '-').replace('）', '-').replace('()', '-')
    segments = clean_name.split('-')

    mixed_candidates = []
    english_candidates = []
    chinese_candidates = []

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        if seg.isdigit():
            continue
        seg_upper = seg.upper()
        if seg_upper in exclude_keywords:
            continue

        if mixed_pattern.match(seg):
            mixed_candidates.append(seg)
        elif english_pattern.match(seg):
            english_candidates.append(seg)
        elif chinese_name_pattern.match(seg):
            if seg not in job_keywords and seg not in ['有限公司', '大学', '学院', '公司', '集团', '股份', '华南理工']:
                chinese_candidates.append(seg)

    if mixed_candidates:
        return mixed_candidates[0]
    if english_candidates:
        return english_candidates[0]
    if chinese_candidates:
        return chinese_candidates[0]

    for seg in segments:
        seg = seg.strip()
        if seg and not seg.isdigit():
            seg_upper = seg.upper()
            if seg_upper not in exclude_keywords:
                is_job = any(job in seg for job in job_keywords)
                if not is_job:
                    if re.match(r'^[A-Za-z]+$', seg) and len(seg) <= 10:
                        return seg
                    if re.match(r'^[\u4e00-\u9fff]+$', seg):
                        return seg

    return segments[0] if segments else name


def _infer_industry_from_filename(filename: str) -> str:
    """
    根据文件名关键词推断行业分类

    Args:
        filename: 文件名（不含路径和扩展名）

    Returns:
        推断的行业代码
    """
    filename_lower = filename.lower()

    # 研发/技术类关键词 - 优先级最高，因为最容易识别
    tech_keywords = [
        # 编程语言
        'java', 'python', 'c++', 'c#', 'go', 'rust', 'ruby', 'php',
        # 技术职位
        '前端', '后端', '全栈', '开发', '工程师', '技术', '架构', '算法',
        # IT相关
        '软件', '测试', '运维', 'DBA', '数据库', '网络安全', 'AI', '人工智能',
        '机器学习', '深度学习', '大数据', '云计算', '区块链',
        # 研发相关
        '研发', '研究', '研究员', '科学家', 'lab', 'laboratory',
        # 英文
        'IT', 'programmer', 'developer', 'engineer', 'scientist', 'RD', 'QA', 'DevOps'
    ]

    # 电商类关键词
    ecommerce_keywords = ['电商', '电子商务', '运营', '直播', '客服', '店铺', '商品',
                          '推广', '营销', '淘宝', '京东', '拼多多', '天猫', '跨境',
                          '新媒体', '社群', '私域', '流量', '转化']

    # 品牌/市场类关键词
    brand_keywords = ['品牌', '市场', '策划', '广告', '公关', '媒体', '文案',
                      '创意', '传播', '活动', '会展', '设计']

    # 销售类关键词
    sales_keywords = ['销售', '外贸', '渠道', '客户', '商务', '招商', '代理',
                      '经销商', '业务', 'BD', 'account']

    # 生产/制造类关键词
    production_keywords = ['生产', '制造', '工厂', '厂长', '质量', '采购', '供应链',
                           '仓储', '物流', '车间', '工艺', '工艺', '精益']

    # 人力资源类关键词
    hr_keywords = ['人力', 'HR', '招聘', '薪酬', '绩效', '培训', '员工关系', '人事', 'HRBP']

    # 检测各行业关键词 - 研发优先检测
    for keyword in tech_keywords:
        if keyword in filename_lower:
            return '研发'

    for keyword in ecommerce_keywords:
        if keyword in filename_lower:
            return '电商'

    for keyword in brand_keywords:
        if keyword in filename_lower:
            return '品牌'

    for keyword in sales_keywords:
        if keyword in filename_lower:
            return '销售'

    for keyword in production_keywords:
        if keyword in filename_lower:
            return '生产'

    for keyword in hr_keywords:
        if keyword in filename_lower:
            return '人力资源'

    # 默认返回电商（基于用户反馈的问题）
    return '电商'

@app.post("/api/resume/parse")
async def parse_resume(request: ParseResumeRequest):
    """
    解析简历文件，提取结构化信息
    解析后的数据会自动保存到数据源
    """
    try:
        file_path = request.file_path
        user_industry = request.industry
        
        try:
            from Resume_Recognition_Model.resume_parser import ResumeParser
            parser = ResumeParser()
            result = parser.parse_resume(file_path)
        except ImportError as ie:
            # jieba等模块未安装，返回模拟数据
            print("[WARN] 简历解析模块依赖未安装，使用模拟数据: {}".format(ie))
            
            # 从文件名智能提取候选人姓名
            filename = Path(file_path).stem
            candidate_name = _extract_candidate_name(filename)
            
            # 使用用户选择的行业，如果没有则根据文件名关键词判断
            inferred_industry = user_industry or _infer_industry_from_filename(filename)
            
            result = {
                "status": "success",
                "basic_info": {"name": candidate_name},
                "industry": inferred_industry,
                "industry_confidence": 0.8,
                "education": [],
                "work_experience": [],
                "skills": []
            }
        
        # 将解析结果保存到数据源
        data_manager = get_data_manager(project_root)

        # 确保result包含文件名
        if isinstance(result, dict):
            result['file_name'] = Path(file_path).name

            # 如果用户指定了行业，优先使用用户选择
            if user_industry and 'industry' in result:
                result['industry'] = user_industry
                result['industry_source'] = 'user_selected'

            # 保存到数据源
            data_manager.add_resume(result)
            print("[OK] 简历已解析并保存到数据源: {}, 行业: {}".format(
                result.get('basic_info', {}).get('name', 'Unknown'),
                result.get('industry')
            ))

            # 清除该行业的缓存（因为数据已更新）
            cache = get_cache_manager()
            cache.invalidate_prefix("ranking")
            print("[CACHE] 已清除行业排名缓存")

        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        import traceback
        
        # 将错误写入文件
        error_file = project_root / "backend" / "temp" / "parse_error_log.txt"
        error_file.parent.mkdir(parents=True, exist_ok=True)
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write("简历解析错误\n")
            f.write("="*60 + "\n")
            f.write(f"时间: {datetime.now()}\n")
            f.write(f"文件路径: {request.file_path}\n")
            f.write(f"错误类型: {type(e).__name__}\n")
            f.write(f"错误信息: {str(e)}\n")
            f.write("\n详细堆栈:\n")
            f.write(traceback.format_exc())
        
        error_detail = "解析失败: {}\n\n详细错误已保存到: {}".format(str(e), error_file)
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/api/score/single", response_model=ScoreResponse)
async def score_single_resume(request: ResumeScoreRequest):
    """
    单份简历评分
    """
    try:
        # 检查模型是否已初始化
        global weight_matrix_calculator, scoring_model
        if weight_matrix_calculator is None or scoring_model is None:
            print("[INFO] 模型未初始化，进行延迟初始化...")
            weight_matrix_calculator = IndustryWeightMatrix(
                alpha=0.5,
                save_dir=str(project_root / "backend" / "output" / "weights"),
                verbose=False
            )
            scoring_model = DimensionalScoringModel(
                save_dir=str(project_root / "backend" / "output" / "visualizations"),
                verbose=False
            )
        
        # 使用数据管理器获取简历数据
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        
        # 查找目标简历
        target_resume = None
        for resume in all_resumes:
            candidate_name = resume.get('basic_info', {}).get('name', '')
            file_name = resume.get('file_name', '')
            if candidate_name == request.resume_id or request.resume_id in file_name:
                target_resume = resume
                break
        
        if not target_resume:
            raise HTTPException(status_code=404, detail="未找到指定简历")
        
        # 确定行业
        industry = request.industry or target_resume.get('industry', 'technical')
        
        # 计算动态权重
        temp_resume_file = project_root / "backend" / "temp" / f"{industry}_resumes.json"
        temp_resume_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 过滤同行业的简历
        industry_resumes = [r for r in all_resumes if r.get('industry') == industry]
        with open(temp_resume_file, 'w', encoding='utf-8') as f:
            json.dump(industry_resumes, f, ensure_ascii=False, indent=2)
        
        dimension_weights = weight_matrix_calculator.get_dimension_weights(
            industry=industry,
            resumes=str(temp_resume_file)
        )
        
        # 计算评分
        results = scoring_model.calculate(
            resumes=[target_resume],
            job_type=industry,
            dimension_weights=dimension_weights
        )
        
        candidate = results['candidates'][0]
        
        return ScoreResponse(
            candidate_id=candidate['candidate_id'],
            tci_score=candidate['tci_score'],
            dimensional_scores=candidate['dimensional_scores'],
            dimension_weights=candidate['dimension_weights'],
            ranking=1,
            analysis={
                "penalty_applied": candidate['penalty_applied'],
                "details": candidate['details']
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评分失败: {str(e)}")

@app.post("/api/score/batch")
async def score_batch_resumes(request: BatchScoreRequest):
    """
    批量简历评分并排序
    """
    try:
        # 检查模型是否已初始化
        global weight_matrix_calculator, scoring_model
        if weight_matrix_calculator is None or scoring_model is None:
            # 延迟初始化
            print("[INFO] 模型未初始化，进行延迟初始化...")
            weight_matrix_calculator = IndustryWeightMatrix(
                alpha=0.5,
                save_dir=str(project_root / "backend" / "output" / "weights"),
                verbose=False
            )
            scoring_model = DimensionalScoringModel(
                save_dir=str(project_root / "backend" / "output" / "visualizations"),
                verbose=False
            )
        
        # 使用数据管理器获取简历数据
        data_manager = get_data_manager(project_root)
        
        # 过滤指定行业的简历
        industry = request.industry or request.job_type
        industry_resumes = data_manager.get_resumes_by_industry(industry)
        
        if not industry_resumes:
            raise HTTPException(status_code=404, detail=f"未找到{industry}行业的简历")
        
        # 保存临时文件
        temp_file = project_root / "backend" / "temp" / f"{industry}_batch.json"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(industry_resumes, f, ensure_ascii=False, indent=2)
        
        # 计算动态权重
        dimension_weights = weight_matrix_calculator.get_dimension_weights(
            industry=industry,
            resumes=str(temp_file)
        )
        
        # 批量评分
        results = scoring_model.calculate(
            resumes=str(temp_file),
            job_type=industry,
            dimension_weights=dimension_weights
        )
        
        # 排序
        ranking = scoring_model.get_ranking()
        
        return {
            "status": "success",
            "industry": industry,
            "total": len(results['candidates']),
            "summary": results['summary'],
            "ranking": ranking,
            "candidates": results['candidates']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        
        # 将错误写入文件
        error_file = project_root / "backend" / "temp" / "error_log.txt"
        error_file.parent.mkdir(parents=True, exist_ok=True)
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write("批量评分错误\n")
            f.write("="*60 + "\n")
            f.write(f"时间: {datetime.now()}\n")
            f.write(f"错误类型: {type(e).__name__}\n")
            f.write(f"错误信息: {str(e)}\n")
            f.write("\n详细堆栈:\n")
            f.write(traceback.format_exc())
        
        error_detail = "批量评分失败: {}\n\n详细错误已保存到: {}".format(str(e), error_file)
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/api/rank/industry/{industry}")
async def get_industry_ranking(industry: str, top_n: Optional[int] = 10, use_cache: bool = True):
    """
    获取指定行业的候选人排名

    Args:
        industry: 行业名称
        top_n: 返回前N名
        use_cache: 是否使用缓存（默认True）
    """
    try:
        cache = get_cache_manager()
        cache_key = f"ranking_{industry}_{top_n}"

        # 尝试从缓存获取
        if use_cache:
            cached_result = cache.get("ranking", industry=industry, top_n=top_n)
            if cached_result is not None:
                cached_result['from_cache'] = True
                return cached_result

        request = BatchScoreRequest(
            resume_ids=[],
            job_type=industry,
            industry=industry
        )
        results = await score_batch_resumes(request)

        # 数据验证
        validation = DataValidator.validate_batch_response(results)
        if not validation['valid']:
            print(f"[WARN] 排名数据验证失败: {validation['issues']}")

        # 清理候选人数据
        sanitized_candidates = []
        for candidate in results.get('candidates', []):
            sanitized_candidates.append(DataValidator.sanitize_candidate(candidate))

        # 返回Top N
        ranking = results.get('ranking', [])[:top_n]
        all_candidates = sanitized_candidates

        response = {
            "status": "success",
            "industry": industry,
            "top_n": len(ranking),
            "total": len(all_candidates),
            "ranking": ranking,
            "candidates": all_candidates,
            "from_cache": False,
            "validated": validation['valid'],
            "generated_at": datetime.now().isoformat()
        }

        # 保存到缓存（默认1小时）
        if use_cache:
            cache.set("ranking", response, ttl=3600, industry=industry, top_n=top_n)

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取排名失败: {str(e)}")

@app.post("/api/qa/ask")
async def intelligent_qa(request: QARequest):
    """
    智能问答功能
    基于LLM大模型回答用户问题
    """
    try:
        context = request.context or {}
        llm_service = get_llm_service()

        candidate_id = context.get('candidate_id', '')
        industry = context.get('industry', '')

        full_resume = None
        if candidate_id:
            data_manager = get_data_manager(project_root)
            all_resumes = data_manager.get_all_resumes()
            for r in all_resumes:
                r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
                if r_name == candidate_id:
                    full_resume = r
                    break

        if full_resume:
            full_resume['rank'] = context.get('rank', context.get('ranking', '未知'))
            full_resume['tci_score'] = context.get('tci_score', 0)
            full_resume['penalty_applied'] = context.get('penalty_applied', False)
            full_resume['dimensional_scores'] = context.get('dimensional_scores', {})
            full_resume['industry'] = industry
        else:
            full_resume = context

        if llm_service.is_enabled():
            try:
                messages = llm_service.build_qa_prompt(
                    question=request.question,
                    candidate=full_resume,
                    industry=industry or '通用'
                )

                answer = await llm_service.chat(messages)

                return {
                    "status": "success",
                    "question": html.escape(request.question),
                    "answer": answer,
                    "source": "llm"
                }
            except Exception as llm_error:
                return fallback_qa(request.question, full_resume)

        else:
            return fallback_qa(request.question, full_resume)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


def fallback_qa(question: str, context: dict) -> dict:
    """
    备用问答逻辑（当LLM不可用时）
    """
    question_lower = question.lower()
    answer = ""

    if "排名" in question or "第几" in question:
        candidate = context.get('candidate_id', '该候选人')
        rank = context.get('rank', context.get('ranking', '未知'))
        answer = f"{candidate}在行业内的排名为第{rank}名。"

    elif "得分" in question or "分数" in question:
        tci = context.get('tci_score', 0)
        answer = f"该候选人的TCI综合得分为{float(tci):.2f}分（满分5分）。"

    elif "优势" in question or "优点" in question:
        scores = context.get('dimensional_scores', {})
        if scores:
            max_dim = max(scores.items(), key=lambda x: x[1])
            dim_names = {
                "education": "教育背景",
                "experience": "工作经历",
                "skill_achievement": "技能与成果",
                "comprehensive": "综合素质"
            }
            answer = f"该候选人的主要优势在{dim_names.get(max_dim[0], max_dim[0])}方面，得分{max_dim[1]:.2f}分。"
        else:
            answer = "暂无维度得分信息。"

    elif "风险" in question or "跳槽" in question:
        penalty = context.get('penalty_applied', False)
        if penalty:
            answer = "⚠️ 该候选人可能存在工作稳定性风险，历史上跳槽较为频繁。"
        else:
            answer = "[OK] 该候选人工作稳定性良好。"

    elif "推荐" in question:
        tci = context.get('tci_score', 0)
        tci_float = float(tci)
        if tci_float >= 4:
            answer = "强烈推荐！该候选人综合评分优秀，建议优先录用。"
        elif tci_float >= 3.5:
            answer = "推荐。该候选人综合评分良好，符合岗位要求。"
        elif tci_float >= 3:
            answer = "可考虑。该候选人综合评分中等，建议进一步面试评估。"
        else:
            answer = "不推荐。该候选人综合评分较低，可能不符合岗位要求。"

    elif "教育" in question:
        edu_score = context.get('dimensional_scores', {}).get('education', 0)
        answer = f"该候选人的教育背景维度得分为{float(edu_score):.2f}分。"

    elif "工作" in question or "经历" in question:
        exp_score = context.get('dimensional_scores', {}).get('experience', 0)
        answer = f"该候选人的工作经历维度得分为{float(exp_score):.2f}分。"

    elif "技能" in question or "成果" in question:
        skill_score = context.get('dimensional_scores', {}).get('skill_achievement', 0)
        answer = f"该候选人的技能与成果维度得分为{float(skill_score):.2f}分。"

    else:
        answer = "我是智能问答助手，可以回答关于候选人排名、得分、优势、风险、推荐意见等问题。请尝试问：'排名多少？'、'得分如何？'、'有什么优势？'、'有没有风险？'、'是否推荐？'"

    return {
        "status": "success",
        "question": html.escape(question),
        "answer": answer,
        "source": "template"
    }


class AnalysisRequest(BaseModel):
    """候选人分析请求"""
    candidate_name: str
    industry: str

@app.post("/api/analysis/candidate")
async def analyze_candidate(request: AnalysisRequest):
    """
    LLM智能分析候选人 - 综合所有数据生成分析报告
    """
    try:
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()

        # 查找目标候选人
        target_resume = None
        for r in all_resumes:
            r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
            if r_name == request.candidate_name:
                target_resume = r
                break

        if not target_resume:
            raise HTTPException(status_code=404, detail=f"未找到候选人: {request.candidate_name}")

        industry = request.industry or target_resume.get('industry', '通用')

        # 获取行业内排名
        industry_resumes = [r for r in all_resumes if r.get('industry') == industry]
        sorted_resumes = sorted(
            industry_resumes,
            key=lambda x: x.get('tci_score', 0),
            reverse=True
        )
        rank = 1
        total = len(sorted_resumes)
        for i, r in enumerate(sorted_resumes, 1):
            r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
            if r_name == request.candidate_name:
                rank = i
                break

        # 使用LLM生成分析
        llm_service = get_llm_service()
        if llm_service.is_enabled():
            try:
                messages = llm_service.build_analysis_prompt(
                    candidate=target_resume,
                    industry=industry,
                    rank=rank,
                    total=total
                )
                answer = await llm_service.chat(messages, temperature=0.6)

                # 尝试解析JSON
                import json as json_lib
                try:
                    # 提取JSON部分（LLM可能返回markdown包裹的JSON）
                    json_str = answer
                    if '```json' in json_str:
                        json_str = json_str.split('```json')[1].split('```')[0]
                    elif '```' in json_str:
                        json_str = json_str.split('```')[1].split('```')[0]
                    analysis = json_lib.loads(json_str.strip())
                    analysis['source'] = 'llm'
                    return {"status": "success", "data": analysis}
                except (json_lib.JSONDecodeError, IndexError):
                    # JSON解析失败，返回原文
                    return {
                        "status": "success",
                        "data": {
                            "summary": answer,
                            "strengths": [],
                            "weaknesses": [],
                            "risks": [],
                            "recommendation": "",
                            "development_suggestions": [],
                            "source": "llm"
                        }
                    }
            except Exception as llm_error:
                import traceback
                print(f"[WARN] LLM分析失败，使用规则分析: {llm_error}")
                traceback.print_exc()

        # 规则分析fallback
        return {"status": "success", "data": _rule_based_analysis(target_resume, industry, rank, total)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


def _rule_based_analysis(resume: Dict, industry: str, rank: int, total: int) -> Dict:
    """规则分析 - LLM不可用时的fallback"""
    scores = resume.get('dimensional_scores', {})
    tci = resume.get('tci_score', 0)
    penalty = resume.get('penalty_applied', False)
    entities = resume.get('entities', {})
    work_duration = resume.get('work_duration_months', 0)

    dim_names = {
        "education": "教育背景",
        "experience": "工作经历",
        "skill_achievement": "技能成果",
        "comprehensive": "综合素质"
    }

    strengths = []
    weaknesses = []
    risks = []

    for dim, score in scores.items():
        if score >= 4:
            strengths.append(f"{dim_names.get(dim, dim)}优秀，得分{score:.2f}")
        elif score < 2.5:
            weaknesses.append(f"{dim_names.get(dim, dim)}较弱，得分{score:.2f}")

    if penalty:
        risks.append("工作稳定性风险，跳槽较为频繁")

    if work_duration > 0 and work_duration < 24:
        risks.append(f"工作年限较短（{work_duration/12:.1f}年），经验可能不足")

    if not strengths:
        strengths.append("各项指标表现均衡")

    summary = f"{resume.get('basic_info', {}).get('name', '该候选人')}应聘{industry}行业，"
    summary += f"综合评分{tci:.2f}/5.00，行业排名第{rank}/{total}名。"

    if tci >= 4:
        recommendation = f"强烈推荐录用。综合评分优秀（{tci:.2f}），在行业内排名靠前。"
    elif tci >= 3.5:
        recommendation = f"推荐录用。综合评分良好（{tci:.2f}），符合岗位基本要求。"
    elif tci >= 3:
        recommendation = f"可以考虑。综合评分中等（{tci:.2f}），建议进一步面试评估。"
    else:
        recommendation = f"暂不推荐。综合评分偏低（{tci:.2f}），可能与岗位要求存在差距。"

    return {
        "summary": summary,
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:2],
        "risks": risks[:2],
        "recommendation": recommendation,
        "development_suggestions": ["建议持续提升专业技能", "关注行业发展趋势"],
        "source": "rule"
    }


@app.get("/api/llm/status")
async def llm_status():
    """
    获取LLM服务状态
    """
    llm = get_llm_service()
    return {
        "enabled": llm.is_enabled(),
        "model": llm.model if llm.is_enabled() else None
    }

@app.get("/api/report/generate/{industry}")
async def generate_report(industry: str, format: str = "json"):
    """
    生成行业分析报告
    """
    try:
        output_dir = project_root / "backend" / "output" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            # 生成JSON报告
            request = BatchScoreRequest(
                resume_ids=[],
                job_type=industry,
                industry=industry
            )
            results = await score_batch_resumes(request)
            
            report_file = output_dir / f"report_{industry}.json"
            import json
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            return FileResponse(
                path=str(report_file),
                filename=f"人才优选报告_{industry}.json",
                media_type="application/json"
            )
            
        elif format == "csv":
            # 生成CSV报告
            request = BatchScoreRequest(
                resume_ids=[],
                job_type=industry,
                industry=industry
            )
            results = await score_batch_resumes(request)
            
            # 转换为CSV
            import pandas as pd
            rows = []
            for c in results.get('candidates', []):
                rows.append({
                    "候选人": c['candidate_id'],
                    "TCI得分": c['tci_score'],
                    "教育背景": c['dimensional_scores']['education'],
                    "工作经历": c['dimensional_scores']['experience'],
                    "技能成果": c['dimensional_scores']['skill_achievement'],
                    "综合素质": c['dimensional_scores']['comprehensive'],
                    "跳槽惩罚": "是" if c['penalty_applied'] else "否"
                })
            
            df = pd.DataFrame(rows)
            report_file = output_dir / f"report_{industry}.csv"
            df.to_csv(report_file, index=False, encoding='utf-8-sig')
            
            return FileResponse(
                path=str(report_file),
                filename=f"人才优选报告_{industry}.csv",
                media_type="text/csv"
            )
        else:
            raise HTTPException(status_code=400, detail="不支持的格式，请使用json或csv")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")

@app.get("/api/industries")
async def get_supported_industries():
    """
    获取支持的行业列表
    """
    return {
        "status": "success",
        "industries": [
            {"code": "电商", "name": "电商行业", "description": "电商运营、直播运营等岗位"},
            {"code": "品牌", "name": "品牌市场", "description": "品牌管理、市场推广等岗位"},
            {"code": "销售", "name": "销售业务", "description": "销售、外贸、渠道等岗位"},
            {"code": "研发", "name": "研发技术", "description": "研发、技术、科学家等岗位"},
            {"code": "生产", "name": "生产管理", "description": "生产管理、厂长、质量等岗位"},
            {"code": "人力资源", "name": "人力资源", "description": "HR、招聘、薪酬等岗位"}
        ]
    }

@app.get("/api/data/statistics")
async def get_data_statistics():
    """
    获取数据统计信息
    用于调试数据问题
    """
    try:
        data_manager = get_data_manager(project_root)
        stats = data_manager.get_statistics()
        return {
            "status": "success",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@app.get("/api/data/resumes")
async def get_all_resumes_data():
    """
    获取所有简历数据（调试用）
    """
    try:
        data_manager = get_data_manager(project_root)
        resumes = data_manager.get_all_resumes()
        return {
            "status": "success",
            "count": len(resumes),
            "resumes": resumes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取简历数据失败: {str(e)}")

@app.get("/api/cache/stats")
async def get_cache_stats():
    """
    获取缓存统计信息
    """
    try:
        cache = get_cache_manager()
        stats = cache.get_cache_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存统计失败: {str(e)}")

@app.post("/api/cache/clear")
async def clear_cache(prefix: Optional[str] = None):
    """
    清除缓存

    Args:
        prefix: 可选，指定前缀清除，不指定则清空所有
    """
    try:
        cache = get_cache_manager()
        if prefix:
            count = cache.invalidate_prefix(prefix)
            message = f"已清除 {count} 个缓存: {prefix}*"
        else:
            count = cache.clear_all()
            message = f"已清空所有缓存，共 {count} 个"
        return {
            "status": "success",
            "message": message,
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")

@app.post("/api/cache/invalidate/{industry}")
async def invalidate_industry_cache(industry: str):
    """
    使指定行业的缓存失效

    Args:
        industry: 行业名称
    """
    try:
        cache = get_cache_manager()
        count = cache.invalidate_prefix("ranking")
        return {
            "status": "success",
            "message": f"已使 {industry} 行业的缓存失效",
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")

# ============== 主入口 ==============

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
