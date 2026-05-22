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
from Person_job_fit_model import PersonJobFitModel
from standard_weight_provider import get_standard_weights

# 第二轮模型构建新功能
from candidate_comparison import get_comparator
from recommendation_engine import get_recommender
from decision_summary import get_generator

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
person_job_fit_model = None  # 人岗匹配模型

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

# ============== 第二轮模型构建 - 新功能请求模型 ==============

class ComparisonRequest(BaseModel):
    """候选人对比分析请求"""
    resume_ids: List[str]
    job_requirements: Optional[Dict] = None

class RecommendationRequest(BaseModel):
    """多方案推荐请求"""
    resume_ids: List[str]
    job_requirements: Dict
    team_config: Optional[Dict] = None
    budget_constraint: Optional[float] = None

class DecisionSummaryRequest(BaseModel):
    """决策摘要生成请求"""
    resume_id: str
    job_requirements: Optional[Dict] = None

class ExportReportRequest(BaseModel):
    """导出报告请求"""
    report_type: str  # comparison, recommendation, decision
    data: Dict
    format: str = "json"  # json, pdf, excel

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
    
    # 初始化人岗匹配模型
    person_job_fit_model = PersonJobFitModel(verbose=True)

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

        # 解析简历
        try:
            parser = ResumeParser()
            parsed_data = parser.parse_resume(str(file_path))

            # 提取候选人姓名
            candidate_name = _extract_candidate_name(file.filename)
            if not candidate_name:
                candidate_name = parsed_data.get('name', '未知')

            # 获取行业 - 用户选择的行业优先级最高
            # 如果用户通过表单选择了行业，优先使用用户选择的；否则使用ResumeParser识别的；最后默认电商
            detected_industry = industry or parsed_data.get('industry') or '电商'
            print(f"[行业识别] 用户选择: {industry}, 解析器识别: {parsed_data.get('industry')}, 最终使用: {detected_industry}")

            # ========== LLM辅助验证 ==========
            try:
                from llm_parser import create_llm_parser
                import json

                # 读取原始文本
                raw_text = parser.read_file(str(file_path))

                # 创建LLM解析器
                llm_parser = create_llm_parser()

                if llm_parser:
                    # 使用LLM验证和丰富解析结果
                    print(f"[LLM] 开始验证简历: {candidate_name}")
                    llm_result = llm_parser.validate_and_enrich(
                        parsed_data=parsed_data,
                        raw_text=raw_text,
                        job_type=detected_industry
                    )

                    # 检查数据质量
                    quality = llm_result.get('data_quality', {})
                    if isinstance(quality, dict):
                        completeness = quality.get('completeness_score', 0)
                        consistency = quality.get('consistency_score', 0)
                        print(f"[LLM] 数据质量 - 完整度:{completeness}, 一致性:{consistency}")

                        # 如果LLM工作年限更合理，使用LLM结果
                        llm_work_months = llm_result.get('total_work_months')
                        traditional_work_months = parsed_data.get('work_duration_months', 0)

                        if llm_work_months and 0 < llm_work_months < traditional_work_months * 1.5:
                            parsed_data['work_duration_months'] = llm_work_months
                            print(f"[LLM] 使用验证后的工作年限: {llm_work_months}个月")

                        # 将LLM验证结果保存到parsed_data
                        parsed_data['_llm_validation'] = llm_result

                    # 识别数据矛盾
                    contradictions = quality.get('contradictions', []) if isinstance(quality, dict) else []
                    if contradictions:
                        print(f"[LLM] 发现 {len(contradictions)} 条数据矛盾")
                        for i, c in enumerate(contradictions[:3], 1):
                            print(f"  {i}. {c}")

            except Exception as llm_error:
                print(f"[Warning] LLM验证失败: {llm_error}")
                # LLM验证失败不影响主流程，继续使用传统解析结果
            # ========== LLM辅助验证结束 ==========

            # 调用评分模块
            from Dimensional_scoring_model.main import calculate_tci_score
            score_result = calculate_tci_score(
                parsed_data=parsed_data,
                job_type=detected_industry,
                industry=detected_industry
            )

            # 保存到数据库
            db = SessionLocal()
            try:
                # 保存简历记录
                resume = Resume(
                    candidate_name=candidate_name,
                    industry=detected_industry,
                    file_path=str(file_path),
                    parsed_data=parsed_data,
                    tci_score=score_result.get('final_tci_score', 0),
                    dimensional_scores=score_result.get('dimensional_scores', {}),
                    dimension_weights=score_result.get('dimension_weights', {}),
                    penalty_applied=score_result.get('penalty_applied', False)
                )
                db.add(resume)
                db.commit()
                db.refresh(resume)

                # 更新排名
                _update_rankings(db, detected_industry)

                resume_id = resume.id
                tci_score = score_result.get('final_tci_score', 0)
            finally:
                db.close()

            return {
                "status": "success",
                "message": "简历上传并解析成功",
                "data": {
                    "resume_id": resume_id,
                    "candidate_name": candidate_name,
                    "filename": file.filename,
                    "filepath": str(file_path),
                    "industry": detected_industry,
                    "tci_score": tci_score,
                    "work_duration_months": parsed_data.get('work_duration_months', 0),
                    "education_experiences": parsed_data.get('education_experiences', []),
                    "work_experiences": parsed_data.get('work_experiences', []),
                    "llm_validation": parsed_data.get('_llm_validation', {}),
                    "upload_time": datetime.now().isoformat()
                }
            }
        except Exception as e:
            # 解析失败时仍返回成功，但标记警告
            return {
                "status": "warning",
                "message": f"简历保存成功，但解析失败: {str(e)}",
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
    支持多种文件名格式，不依赖特定的for关键词

    Args:
        filename: 文件名（不含路径和扩展名）

    Returns:
        推断的行业代码
    """
    import re

    filename_lower = filename.lower()
    original_filename = filename

    print(f"[文件名识别] 开始分析: {original_filename}")

    # ====== 定义行业关键词映射 ======
    # 按优先级排序：研发 > 品牌/市场 > 电商 > 销售 > 生产 > 人力资源
    industry_keywords = {
        '研发': {
            'keywords': [
                'java', 'python', 'c++', 'c#', 'go', 'rust', 'ruby', 'php',
                '前端', '后端', '全栈', '开发', '工程师', '技术', '架构', '算法',
                '软件', '测试', '运维', 'dba', '数据库', '网络安全', 'ai', '人工智能',
                '机器学习', '深度学习', '大数据', '云计算', '区块链',
                '研发', '研究', '研究员', '科学家', 'lab', 'laboratory',
                'it', 'programmer', 'developer', 'engineer', 'scientist', 'rd', 'qa', 'devops'
            ],
            'priority': 1
        },
        '品牌': {
            'keywords': [
                '品牌', '市场', '策划', '广告', '公关', '媒体', '文案',
                '创意', '传播', '活动', '会展', '设计', 'cmo', 'marketing'
            ],
            'priority': 2
        },
        '电商': {
            'keywords': [
                '电商', '电子商务', '淘宝', '京东', '拼多多', '天猫', '跨境',
                '直播', '店铺', '新媒体', '社群', '私域', '运营'
            ],
            'priority': 3
        },
        '销售': {
            'keywords': [
                '销售', '外贸', '渠道', '客户', '商务', '招商', '代理',
                '经销商', '业务', 'bd', 'account', 'sales'
            ],
            'priority': 4
        },
        '生产': {
            'keywords': [
                '生产', '制造', '工厂', '厂长', '质量', '采购', '供应链',
                '仓储', '物流', '车间', '工艺', '精益'
            ],
            'priority': 5
        },
        '人力资源': {
            'keywords': [
                '人力', 'hr', '招聘', '薪酬', '绩效', '培训', '员工关系', '人事', 'hrbp'
            ],
            'priority': 6
        }
    }

    # ====== 优先级1：从 for/for- 关键词后的内容识别 ======
    # 支持多种for格式: for-xxx, -for xxx, for xxx
    for_patterns = [
        r"(?:^|[^a-zA-Z])for[-\s]*(.+?)(?:\.|$)",  # for-格式
        r"-for\s*([^-]+)",  # -for格式
    ]

    for pattern in for_patterns:
        match = re.search(pattern, filename_lower, re.IGNORECASE)
        if match:
            industry_part = match.group(1).strip()
            print(f"[文件名识别] 从for关键词提取: '{industry_part}'")

            # 按优先级检查行业映射
            for industry in sorted(industry_keywords.keys(), key=lambda x: industry_keywords[x]['priority']):
                for keyword in industry_keywords[industry]['keywords']:
                    if keyword in industry_part:
                        print(f"[文件名识别] 匹配成功: {original_filename} -> {industry} (for关键词: {keyword})")
                        return industry

    # ====== 优先级2：直接在文件名中搜索行业关键词 ======
    print(f"[文件名识别] for关键词未匹配或无法识别，直接搜索文件名")

    # 按优先级顺序检测
    for industry in sorted(industry_keywords.keys(), key=lambda x: industry_keywords[x]['priority']):
        for keyword in industry_keywords[industry]['keywords']:
            if keyword in filename_lower:
                print(f"[文件名识别] 匹配成功: {original_filename} -> {industry} (关键词: {keyword})")
                return industry

    # ====== 优先级3：从简历内容中识别（如果有）======
    # 这里可以添加从文件内容识别的逻辑

    # 默认返回电商
    print(f"[文件名识别] 未匹配任何关键词，默认: {original_filename} -> 电商")
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

        # ========== 使用标准权重 ==========
        # 使用标准行业权重配置，而不是动态计算
        dimension_weights = get_standard_weights(industry)
        print(f"[排名] 使用标准权重 - {industry}: {dimension_weights}")
        # ========== 标准权重结束 ==========
        
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
    支持两种模式：
    1. 选定候选人：针对单个候选人提问
    2. 行业推荐：只选行业，推荐最合适的人选
    """
    try:
        context = request.context or {}
        llm_service = get_llm_service()

        candidate_id = context.get('candidate_id', '')
        industry = context.get('industry', '')
        mode = context.get('mode', '')

        # 行业推荐模式：未选定候选人但选了行业
        if not candidate_id and industry:
            # 调用排名API获取带有TCI分数的候选人数据
            top_candidates = []
            try:
                # 先尝试从缓存获取
                cache = get_cache_manager()
                cached_data = cache.get("ranking", industry, top_n=5)

                if cached_data and cached_data.get('status') == 'success':
                    print(f"[DEBUG] 智能问答从缓存获取排名数据")
                    top_candidates = cached_data.get('ranking', [])
                else:
                    # 缓存未命中，直接调用排名计算逻辑
                    print(f"[DEBUG] 智能问答缓存未命中，直接计算排名")
                    from Dimensional_scoring_model import DimensionalScoringModel
                    from standard_weight_provider import get_standard_weights

                    data_manager = get_data_manager(project_root)
                    industry_resumes = data_manager.get_resumes_by_industry(industry)

                    if industry_resumes:
                        # 保存临时文件
                        temp_file = project_root / "backend" / "temp" / f"{industry}_batch.json"
                        temp_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            json.dump(industry_resumes, f, ensure_ascii=False, indent=2)

                        # 计算排名
                        dimension_weights = get_standard_weights(industry)
                        scoring_model = DimensionalScoringModel(verbose=False)
                        results = scoring_model.calculate(
                            resumes=str(temp_file),
                            job_type=industry,
                            dimension_weights=dimension_weights
                        )
                        top_candidates = scoring_model.get_ranking()[:5]

                # 转换格式以兼容现有代码
                for candidate in top_candidates:
                    candidate['tci_score'] = candidate.get('tci_score', 0)
                    candidate['dimensional_scores'] = candidate.get('dimensional_scores', {})
                    candidate['penalty_applied'] = candidate.get('penalty_applied', False)

            except Exception as e:
                print(f"[ERROR] 智能问答获取排名失败: {e}")
                import traceback
                traceback.print_exc()
                top_candidates = []

            if not top_candidates:
                return {
                    "status": "success",
                    "question": html.escape(request.question),
                    "answer": f"暂未找到【{industry}】行业的候选人数据。",
                    "source": "template"
                }

            if llm_service.is_enabled():
                try:
                    messages = llm_service.build_industry_recommendation_prompt(
                        question=request.question,
                        industry=industry,
                        top_candidates=top_candidates
                    )
                    answer = await llm_service.chat(messages)
                    return {
                        "status": "success",
                        "question": html.escape(request.question),
                        "answer": answer,
                        "source": "llm"
                    }
                except Exception:
                    return fallback_industry_recommendation(request.question, industry, top_candidates)
            else:
                return fallback_industry_recommendation(request.question, industry, top_candidates)

        # 候选人模式：原有逻辑
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


def fallback_industry_recommendation(question: str, industry: str, top_candidates: list) -> dict:
    """
    行业推荐备用逻辑（当LLM不可用时）
    """
    dim_names = {
        "education": "教育背景",
        "experience": "工作经历",
        "skill_achievement": "技能成果",
        "comprehensive": "综合素质"
    }

    answer = f"## 【{industry}行业候选人推荐】\n\n"
    answer += "### 候选人对比\n\n"
    answer += "| 排名 | 候选人 | TCI评分 | 教育背景 | 工作经历 | 技能成果 | 综合素质 | 跳槽风险 |\n"
    answer += "|------|--------|---------|----------|----------|----------|----------|----------|\n"

    for i, c in enumerate(top_candidates[:5], 1):
        basic_info = c.get("basic_info", {})
        name = basic_info.get("name", c.get("candidate_id", "未知"))
        tci = c.get("tci_score", 0)
        scores = c.get("dimensional_scores", {})
        penalty = "有" if c.get("penalty_applied") else "无"
        answer += f"| {i} | {name} | {float(tci):.2f} | {float(scores.get('education', 0)):.2f} | {float(scores.get('experience', 0)):.2f} | {float(scores.get('skill_achievement', 0)):.2f} | {float(scores.get('comprehensive', 0)):.2f} | {penalty} |\n"

    answer += "\n### 推荐排序\n\n"
    for i, c in enumerate(top_candidates[:3], 1):
        basic_info = c.get("basic_info", {})
        name = basic_info.get("name", c.get("candidate_id", "未知"))
        tci = c.get("tci_score", 0)
        scores = c.get("dimensional_scores", {})
        best_dim = max(scores.items(), key=lambda x: x[1]) if scores else ("", 0)
        best_dim_name = dim_names.get(best_dim[0], best_dim[0])
        penalty = c.get("penalty_applied", False)

        recommend = "强烈推荐" if float(tci) >= 4 and not penalty else "推荐" if float(tci) >= 3.5 else "可考虑" if float(tci) >= 3 else "不推荐"
        answer += f"{i}. **{name}** — TCI: {float(tci):.2f}，优势维度: {best_dim_name}，{recommend}\n"

    answer += "\n### 录用建议\n\n"
    answer += "- 以上为该行业排名前3的候选人，建议优先考虑排名靠前且无跳槽风险的候选人\n"
    answer += "- 具体录用决策还需结合面试表现和岗位需求综合判断"

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

        # ========== 获取正确的评分和排名 ==========
        # 调用批量评分API获取所有候选人的真实TCI评分
        global weight_matrix_calculator, scoring_model
        if weight_matrix_calculator is None or scoring_model is None:
            weight_matrix_calculator = IndustryWeightMatrix(
                alpha=0.5,
                save_dir=str(project_root / "backend" / "output" / "weights"),
                verbose=False
            )
            scoring_model = DimensionalScoringModel(
                save_dir=str(project_root / "backend" / "output" / "visualizations"),
                verbose=False
            )

        # 保存临时文件
        temp_file = project_root / "backend" / "temp" / f"{industry}_analysis.json"
        temp_file.parent.mkdir(parents=True, exist_ok=True)

        industry_resumes = [r for r in all_resumes if r.get('industry') == industry]
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(industry_resumes, f, ensure_ascii=False, indent=2)

        # ========== 使用标准权重 ==========
        # 使用标准行业权重配置，而不是动态计算
        dimension_weights = get_standard_weights(industry)
        print(f"[权重] 使用标准权重 - {industry}: {dimension_weights}")
        # ========== 标准权重结束 ==========

        # 批量评分
        results = scoring_model.calculate(
            resumes=str(temp_file),
            job_type=industry,
            dimension_weights=dimension_weights
        )

        # 从结果中提取评分
        candidate_scores = {}
        for candidate in results['candidates']:
            candidate_id = candidate['candidate_id']
            candidate_scores[candidate_id] = {
                'tci_score': candidate['tci_score'],
                'dimensional_scores': candidate['dimensional_scores'],
                'dimension_weights': candidate['dimension_weights'],
                'penalty_applied': candidate['penalty_applied']
            }

        # 使用真实TCI评分排序
        sorted_candidates = sorted(
            candidate_scores.items(),
            key=lambda x: x[1]['tci_score'],
            reverse=True
        )

        # 计算排名
        total = len(sorted_candidates)
        rank = 1
        target_tci_score = 0
        target_dimension_weights = {}
        for i, (candidate_id, scores) in enumerate(sorted_candidates, 1):
            if candidate_id == request.candidate_name:
                rank = i
                target_tci_score = scores['tci_score']
                target_dimension_weights = scores['dimension_weights']
                break

        # 将评分信息合并到简历数据
        target_resume['tci_score'] = target_tci_score
        target_resume['dimensional_scores'] = candidate_scores.get(request.candidate_name, {}).get('dimensional_scores', {})
        # 使用从评分结果中获取的维度权重，而不是重新计算
        target_resume['dimension_weights'] = target_dimension_weights if target_dimension_weights else candidate_scores.get(request.candidate_name, {}).get('dimension_weights', {})
        target_resume['penalty_applied'] = candidate_scores.get(request.candidate_name, {}).get('penalty_applied', False)

        # ========== 评分获取完成 ==========

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

@app.get("/api/industries/supported")
async def get_supported_industries():
    """
    获取系统支持的行业列表（静态配置）
    """
    return {
        "status": "success",
        "industries": [
            {"code": "电商", "name": "电商", "description": "电商运营、直播运营等岗位"},
            {"code": "品牌", "name": "品牌", "description": "品牌管理、市场推广等岗位"},
            {"code": "销售", "name": "销售", "description": "销售、外贸、渠道等岗位"},
            {"code": "研发", "name": "研发", "description": "研发、技术、科学家等岗位"},
            {"code": "生产", "name": "生产", "description": "生产管理、厂长、质量等岗位"},
            {"code": "人力资源", "name": "人力资源", "description": "HR、招聘、薪酬等岗位"}
        ]
    }


# ============== 人岗匹配模块 API ==============

class JobProfileRequest(BaseModel):
    """岗位画像抽取请求"""
    job_description: str
    requirements: Optional[str] = None

class JobMatchingRequest(BaseModel):
    """人岗匹配请求"""
    resume_id: str
    job_profile: Optional[Dict] = None
    job_description: Optional[str] = None
    requirements: Optional[str] = None
    include_details: bool = True

class BatchMatchingRequest(BaseModel):
    """批量人岗匹配请求"""
    resume_ids: List[str]
    job_profile: Optional[Dict] = None
    job_description: Optional[str] = None
    requirements: Optional[str] = None

class RiskAssessmentRequest(BaseModel):
    """风险评估请求"""
    resume_id: str
    job_profile: Optional[Dict] = None

class PotentialEvaluationRequest(BaseModel):
    """潜力评估请求"""
    resume_id: str

class ComprehensiveReportRequest(BaseModel):
    """综合报告请求"""
    resume_id: str
    job_description: Optional[str] = None
    requirements: Optional[str] = None
    include_charts: bool = False

@app.post("/api/job-profile/parse")
async def parse_job_profile(request: JobProfileRequest):
    """
    抽取岗位画像 - 从岗位描述文本提取结构化信息
    """
    try:
        global person_job_fit_model
        if person_job_fit_model is None:
            person_job_fit_model = PersonJobFitModel(verbose=False)
        
        # 抽取岗位画像
        profile = person_job_fit_model.extract_job_profile(
            job_description=request.job_description,
            requirements=request.requirements
        )
        
        return {
            "status": "success",
            "job_profile": profile
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"岗位画像抽取失败：{str(e)}")

@app.post("/api/matching/score")
async def score_job_matching(request: JobMatchingRequest):
    """
    人岗匹配评分 - 计算候选人与岗位的匹配度
    """
    try:
        global person_job_fit_model
        if person_job_fit_model is None:
            person_job_fit_model = PersonJobFitModel(verbose=False)
        
        # 获取简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        
        target_resume = None
        for r in all_resumes:
            r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
            if r_name == request.resume_id:
                target_resume = r
                break
        
        if not target_resume:
            raise HTTPException(status_code=404, detail=f"未找到候选人：{request.resume_id}")
        
        # 处理岗位画像
        if request.job_profile:
            job_profile = request.job_profile
        elif request.job_description:
            job_profile = person_job_fit_model.extract_job_profile(
                job_description=request.job_description,
                requirements=request.requirements,
                save_path=None
            )
        else:
            raise HTTPException(status_code=400, detail="请提供岗位画像或岗位描述")
        
        # 计算匹配度
        result = person_job_fit_model.single_matching(
            resume=target_resume,
            job_profile=job_profile,
            include_details=request.include_details
        )
        
        return {
            "status": "success",
            "matching": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"人岗匹配评分失败：{str(e)}")

@app.post("/api/matching/batch")
async def batch_job_matching(request: BatchMatchingRequest):
    """
    批量人岗匹配评分
    """
    try:
        global person_job_fit_model
        if person_job_fit_model is None:
            person_job_fit_model = PersonJobFitModel(verbose=False)
        
        # 获取简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        
        target_resumes = []
        for resume_id in request.resume_ids:
            for r in all_resumes:
                r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
                if r_name == resume_id:
                    target_resumes.append(r)
                    break
        
        if not target_resumes:
            raise HTTPException(status_code=404, detail="未找到任何候选人简历")
        
        # 处理岗位画像
        if request.job_profile:
            job_profile = request.job_profile
        elif request.job_description:
            job_profile = person_job_fit_model.extract_job_profile(
                job_description=request.job_description,
                requirements=request.requirements,
                save_path=None
            )
        else:
            raise HTTPException(status_code=400, detail="请提供岗位画像或岗位描述")
        
        # 批量计算匹配度
        results = person_job_fit_model.batch_matching(
            resumes=target_resumes,
            job_profile=job_profile,
            include_details=True
        )
        
        return {
            "status": "success",
            "total": len(results),
            "matching_results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量人岗匹配评分失败：{str(e)}")

@app.post("/api/risk/assessment")
async def assess_risk(request: RiskAssessmentRequest):
    """
    风险识别 - 识别候选人简历中的风险因素
    """
    try:
        global person_job_fit_model
        if person_job_fit_model is None:
            person_job_fit_model = PersonJobFitModel(verbose=False)
        
        # 获取简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        
        target_resume = None
        for r in all_resumes:
            r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
            if r_name == request.resume_id:
                target_resume = r
                break
        
        if not target_resume:
            raise HTTPException(status_code=404, detail=f"未找到候选人：{request.resume_id}")
        
        # 识别风险
        result = person_job_fit_model.single_risk_assessment(
            resume=target_resume,
            job_profile=request.job_profile
        )
        
        return {
            "status": "success",
            "risk_assessment": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"风险识别失败：{str(e)}")

@app.post("/api/potential/evaluation")
async def evaluate_potential(request: PotentialEvaluationRequest):
    """
    潜力评估 - 评估候选人的成长潜力
    """
    try:
        global person_job_fit_model
        if person_job_fit_model is None:
            person_job_fit_model = PersonJobFitModel(verbose=False)
        
        # 获取简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        
        target_resume = None
        for r in all_resumes:
            r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
            if r_name == request.resume_id:
                target_resume = r
                break
        
        if not target_resume:
            raise HTTPException(status_code=404, detail=f"未找到候选人：{request.resume_id}")
        
        # 评估潜力
        result = person_job_fit_model.single_potential_evaluation(
            resume=target_resume
        )
        
        return {
            "status": "success",
            "potential_evaluation": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"潜力评估失败：{str(e)}")

@app.post("/api/comprehensive-report")
async def generate_comprehensive_report(request: ComprehensiveReportRequest):
    """
    综合评估报告 - 包含人岗匹配 + 风险识别 + 潜力评估
    """
    try:
        global person_job_fit_model
        if person_job_fit_model is None:
            person_job_fit_model = PersonJobFitModel(verbose=False)
        
        # 获取简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        
        target_resume = None
        for r in all_resumes:
            r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
            if r_name == request.resume_id:
                target_resume = r
                break
        
        if not target_resume:
            raise HTTPException(status_code=404, detail=f"未找到候选人：{request.resume_id}")
        
        # 处理岗位画像
        if request.job_description:
            job_profile = person_job_fit_model.extract_job_profile(
                job_description=request.job_description,
                requirements=request.requirements,
                save_path=None
            )
        else:
            # 使用行业默认岗位
            industry = target_resume.get('industry', '通用')
            job_profile = None
        
        # 生成综合报告
        report = person_job_fit_model.get_comprehensive_report(
            resume=target_resume,
            job_profile=job_profile,
            include_charts=request.include_charts,
            chart_save_dir=str(project_root / "backend" / "output" / "visualizations" / request.resume_id)
        )
        
        return {
            "status": "success",
            "comprehensive_report": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"综合报告生成失败：{str(e)}")

@app.get("/api/model/info")
async def get_model_info():
    """
    获取模型信息
    """
    global person_job_fit_model
    if person_job_fit_model is None:
        person_job_fit_model = PersonJobFitModel(verbose=False)
    
    info = person_job_fit_model.get_model_info()
    
    return {
        "status": "success",
        "model_info": info
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

# ============== 第二轮模型构建 - 新功能API端点 ==============

@app.post("/api/comparison/analyze")
async def analyze_candidates_comparison(request: ComparisonRequest):
    """
    候选人对比分析
    
    对多个候选人进行横向对比分析，包括各维度得分对比、优势分析、差距分析等
    支持跨行业对比
    """
    try:
        # 获取行业信息（从请求，如果不指定则获取所有行业）
        industry = request.job_requirements.get('industry') if request.job_requirements else None
        
        # 从主数据文件加载所有简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        print(f"[DEBUG] 从data_manager加载到 {len(all_resumes)} 份简历")
        
        # 从排名缓存获取TCI分数和维度得分（跨所有行业）
        cache = get_cache_manager()
        
        # 构建候选人完整数据映射（跨所有行业）
        candidate_data_map = {}
        
        # 如果指定了行业，优先从该行业缓存获取
        if industry:
            cached_ranking = cache.get("ranking", industry=industry, top_n=100)
            if cached_ranking and 'candidates' in cached_ranking:
                for c in cached_ranking['candidates']:
                    candidate_id = c.get('candidate_id', '')
                    candidate_data_map[candidate_id] = {
                        'tci_score': c.get('tci_score', 0),
                        'dimensional_scores': c.get('dimensional_scores', {}),
                        'dimension_weights': c.get('dimension_weights', {}),
                        'penalty_applied': c.get('penalty_applied', False)
                    }
                print(f"[DEBUG] 从{industry}行业缓存获取到 {len(candidate_data_map)} 个候选人评分数据")
        
        # 如果没有指定行业或缓存为空，尝试从所有行业缓存获取
        if not candidate_data_map:
            # 获取所有可能的行业
            industries = set()
            for r in all_resumes:
                ind = r.get('industry')
                if ind:
                    industries.add(ind)
            
            for ind in industries:
                cached_ranking = cache.get("ranking", industry=ind, top_n=100)
                if cached_ranking and 'candidates' in cached_ranking:
                    for c in cached_ranking['candidates']:
                        candidate_id = c.get('candidate_id', '')
                        if candidate_id not in candidate_data_map:  # 避免覆盖已有数据
                            candidate_data_map[candidate_id] = {
                                'tci_score': c.get('tci_score', 0),
                                'dimensional_scores': c.get('dimensional_scores', {}),
                                'dimension_weights': c.get('dimension_weights', {}),
                                'penalty_applied': c.get('penalty_applied', False)
                            }
            print(f"[DEBUG] 从所有行业缓存获取到 {len(candidate_data_map)} 个候选人评分数据")
        
        # 初始化人岗匹配模型（用于风险评估）
        global person_job_fit_model
        if person_job_fit_model is None:
            person_job_fit_model = PersonJobFitModel(verbose=False)
        
        # 筛选目标候选人并补充TCI分数和风险因素
        target_resumes = []
        for resume_id in request.resume_ids:
            for r in all_resumes:
                r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
                if r_name == resume_id:
                    # 从缓存补充TCI分数和维度得分
                    cached_data = candidate_data_map.get(r_name, {})
                    r['tci_score'] = cached_data.get('tci_score', 0)
                    r['dimensional_scores'] = cached_data.get('dimensional_scores', {})
                    r['dimension_weights'] = cached_data.get('dimension_weights', {})
                    
                    # 获取风险因素
                    try:
                        risk_result = person_job_fit_model.single_risk_assessment(
                            resume=r,
                            job_profile=request.job_requirements
                        )
                        r['risk_factors'] = risk_result.get('risk_factors', [])
                        print(f"[DEBUG] 候选人 {r_name} 风险因素: {len(r['risk_factors'])} 个")
                    except Exception as e:
                        print(f"[WARNING] 获取候选人 {r_name} 风险因素失败: {e}")
                        r['risk_factors'] = []
                    
                    target_resumes.append(r)
                    print(f"[DEBUG] 找到候选人: {r_name}, TCI: {r['tci_score']}, 风险: {len(r.get('risk_factors', []))}")
                    break
        
        if len(target_resumes) < 2:
            raise HTTPException(status_code=400, detail="至少需要选择2位候选人进行对比")
        
        # 执行对比分析
        comparator = get_comparator()
        result = comparator.compare_candidates(target_resumes, request.job_requirements)
        
        # 生成报告
        report = comparator.generate_comparison_report(result)
        
        return {
            "status": "success",
            "comparison_result": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 对比分析失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"对比分析失败：{str(e)}")

@app.post("/api/recommendation/plans")
async def generate_hire_recommendations(request: RecommendationRequest):
    """
    多方案推荐
    
    基于不同策略生成多种录用方案，包括平衡型、激进型、保守型、性价比型、团队搭配型
    支持跨行业推荐
    """
    try:
        # 获取行业信息（从请求，如果不指定则获取所有行业）
        industry = request.job_requirements.get('industry') if request.job_requirements else None
        
        # 从主数据文件加载所有简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        print(f"[DEBUG] 从data_manager加载到 {len(all_resumes)} 份简历")
        
        # 从排名缓存获取TCI分数和维度得分（跨所有行业）
        cache = get_cache_manager()
        
        # 构建候选人完整数据映射（跨所有行业）
        candidate_data_map = {}
        
        # 如果指定了行业，优先从该行业缓存获取
        if industry:
            cached_ranking = cache.get("ranking", industry=industry, top_n=100)
            if cached_ranking and 'candidates' in cached_ranking:
                for c in cached_ranking['candidates']:
                    candidate_id = c.get('candidate_id', '')
                    candidate_data_map[candidate_id] = {
                        'tci_score': c.get('tci_score', 0),
                        'dimensional_scores': c.get('dimensional_scores', {}),
                        'dimension_weights': c.get('dimension_weights', {})
                    }
                print(f"[DEBUG] 从{industry}行业缓存获取到 {len(candidate_data_map)} 个候选人评分数据")
        
        # 如果没有指定行业或缓存为空，尝试从所有行业缓存获取
        if not candidate_data_map:
            # 获取所有可能的行业
            industries = set()
            for r in all_resumes:
                ind = r.get('industry')
                if ind:
                    industries.add(ind)
            
            for ind in industries:
                cached_ranking = cache.get("ranking", industry=ind, top_n=100)
                if cached_ranking and 'candidates' in cached_ranking:
                    for c in cached_ranking['candidates']:
                        candidate_id = c.get('candidate_id', '')
                        if candidate_id not in candidate_data_map:  # 避免覆盖已有数据
                            candidate_data_map[candidate_id] = {
                                'tci_score': c.get('tci_score', 0),
                                'dimensional_scores': c.get('dimensional_scores', {}),
                                'dimension_weights': c.get('dimension_weights', {})
                            }
            print(f"[DEBUG] 从所有行业缓存获取到 {len(candidate_data_map)} 个候选人评分数据")
        
        # 初始化人岗匹配模型（用于风险评估）
        global person_job_fit_model
        if person_job_fit_model is None:
            person_job_fit_model = PersonJobFitModel(verbose=False)
        
        # 筛选目标候选人并补充TCI分数和风险因素
        target_resumes = []
        for resume_id in request.resume_ids:
            for r in all_resumes:
                r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
                if r_name == resume_id:
                    # 从缓存补充TCI分数和维度得分
                    cached_data = candidate_data_map.get(r_name, {})
                    r['tci_score'] = cached_data.get('tci_score', 0)
                    r['dimensional_scores'] = cached_data.get('dimensional_scores', {})
                    r['dimension_weights'] = cached_data.get('dimension_weights', {})
                    
                    # 获取风险因素
                    try:
                        risk_result = person_job_fit_model.single_risk_assessment(
                            resume=r,
                            job_profile=request.job_requirements
                        )
                        r['risk_factors'] = risk_result.get('risk_factors', [])
                        r['overall_risk_level'] = risk_result.get('overall_risk_level', '低')
                        print(f"[DEBUG] 推荐API - 候选人: {r_name}, TCI: {r['tci_score']}, 风险因素: {len(r['risk_factors'])}个, 风险等级: {r['overall_risk_level']}")
                    except Exception as e:
                        print(f"[WARNING] 获取候选人 {r_name} 风险因素失败: {e}")
                        r['risk_factors'] = []
                        r['overall_risk_level'] = '低'
                    
                    target_resumes.append(r)
                    break
        
        if not target_resumes:
            raise HTTPException(status_code=404, detail="未找到任何候选人")
        
        # 构建团队配置
        team_config = None
        if request.team_config:
            from recommendation_engine import TeamConfig
            team_config = TeamConfig(
                required_skills=request.team_config.get('required_skills', []),
                skill_coverage_target=request.team_config.get('skill_coverage_target', 0.8),
                max_team_size=request.team_config.get('max_team_size', 3),
                min_senior_ratio=request.team_config.get('min_senior_ratio', 0.3)
            )
        
        # 生成推荐方案
        recommender = get_recommender()
        plans = recommender.generate_hire_plans(
            candidates=target_resumes,
            job_requirements=request.job_requirements,
            team_config=team_config,
            budget_constraint=request.budget_constraint
        )
        
        # 生成汇总
        summary = recommender.generate_recommendation_summary(plans)
        
        return {
            "status": "success",
            "recommendation_summary": summary,
            "plans": [
                {
                    "plan_id": plan.plan_id,
                    "name": plan.name,
                    "strategy": plan.strategy.value,
                    "description": plan.description,
                    "risk_level": plan.risk_level,
                    "expected_performance": plan.expected_performance,
                    "team_complementarity": plan.team_complementarity,
                    "recommended_candidates": plan.recommended_candidates,
                    "backup_candidates": plan.backup_candidates,
                    "pros": plan.pros,
                    "cons": plan.cons,
                    "suitable_scenarios": plan.suitable_scenarios
                }
                for plan in plans
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐方案生成失败：{str(e)}")

@app.post("/api/decision/summary")
async def generate_decision_summary(request: DecisionSummaryRequest):
    """
    决策摘要生成

    为单个候选人生成完整的决策摘要，包括决策建议、风险评估、行动建议等
    支持跨行业决策
    """
    try:
        # 获取简历数据
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()

        # 查找目标候选人
        target_resume = None
        candidate_industry = None
        for r in all_resumes:
            r_name = r.get('basic_info', {}).get('name', '') or r.get('candidate_id', '')
            if r_name == request.resume_id:
                target_resume = r
                candidate_industry = r.get('industry', '未知')
                break

        if not target_resume:
            raise HTTPException(status_code=404, detail=f"未找到候选人：{request.resume_id}")

        # 获取TCI分数和维度得分
        # 首先尝试从候选人所在行业的排名缓存获取
        cache_manager = get_cache_manager(str(project_root))
        
        # 获取请求中的行业或使用候选人所属行业
        industry = request.job_requirements.get('industry') if request.job_requirements else None
        if not industry and candidate_industry:
            industry = candidate_industry
        if not industry:
            industry = 'default'
            
        cached_data = cache_manager.get("ranking", industry, top_n=100)

        # 补充TCI分数和维度得分
        tci_score = 0
        dimensional_scores = {}
        dimension_weights = {}

        if cached_data and 'candidates' in cached_data:
            # 从缓存获取
            for c in cached_data['candidates']:
                if c.get('candidate_id', '') == request.resume_id or c.get('name', '') == request.resume_id:
                    tci_score = c.get('tci_score', 0)
                    dimensional_scores = c.get('dimensional_scores', {})
                    dimension_weights = c.get('dimension_weights', {})
                    print(f"[DEBUG] 决策摘要API - 从{industry}行业缓存获取: {request.resume_id}, TCI: {tci_score}")
                    break
        
        # 如果在指定行业缓存中没有，尝试从候选人所在行业缓存获取
        if tci_score == 0 and candidate_industry and candidate_industry != industry:
            cached_data = cache_manager.get("ranking", candidate_industry, top_n=100)
            if cached_data and 'candidates' in cached_data:
                for c in cached_data['candidates']:
                    if c.get('candidate_id', '') == request.resume_id or c.get('name', '') == request.resume_id:
                        tci_score = c.get('tci_score', 0)
                        dimensional_scores = c.get('dimensional_scores', {})
                        dimension_weights = c.get('dimension_weights', {})
                        print(f"[DEBUG] 决策摘要API - 从{candidate_industry}行业缓存获取: {request.resume_id}, TCI: {tci_score}")
                        break

        # 如果缓存中没有，实时计算TCI分数
        if tci_score == 0:
            print(f"[DEBUG] 决策摘要API - 缓存未命中，实时计算TCI: {request.resume_id}")
            try:
                # 初始化评分模型
                from Dimensional_scoring_model import DimensionalScoringModel

                # 使用标准权重提供者获取行业权重
                industry_weights = get_standard_weights(industry)

                scoring_model = DimensionalScoringModel(verbose=False)

                # 使用calculate方法计算得分
                # 注意：与排名API保持一致，使用industry作为job_type
                results = scoring_model.calculate(
                    resumes=[target_resume],
                    dimension_weights=industry_weights,
                    job_type=industry
                )

                # 提取计算结果
                if results and 'candidates' in results and len(results['candidates']) > 0:
                    candidate_result = results['candidates'][0]
                    tci_score = candidate_result.get('tci_score', 0)
                    dimensional_scores = candidate_result.get('dimensional_scores', {})
                    dimension_weights = candidate_result.get('dimension_weights', {})
                    print(f"[DEBUG] 决策摘要API - 实时计算完成: {request.resume_id}, TCI: {tci_score}")
                else:
                    print(f"[WARNING] 决策摘要API - 计算结果为空")
                    tci_score = target_resume.get('tci_score', 0)
                    dimensional_scores = target_resume.get('dimensional_scores', {})
            except Exception as e:
                print(f"[ERROR] 决策摘要API - TCI计算失败: {e}")
                import traceback
                traceback.print_exc()
                tci_score = target_resume.get('tci_score', 0)
                dimensional_scores = target_resume.get('dimensional_scores', {})

        # 设置到候选人数据
        target_resume['tci_score'] = tci_score
        target_resume['dimensional_scores'] = dimensional_scores
        target_resume['dimension_weights'] = dimension_weights

        # 获取风险因素
        global person_job_fit_model
        if person_job_fit_model is None:
            person_job_fit_model = PersonJobFitModel(verbose=False)

        try:
            risk_result = person_job_fit_model.single_risk_assessment(
                resume=target_resume,
                job_profile=request.job_requirements
            )
            target_resume['risk_factors'] = risk_result.get('risk_factors', [])
            target_resume['overall_risk_level'] = risk_result.get('overall_risk_level', '低')
            print(f"[DEBUG] 决策摘要API - 风险因素: {len(target_resume['risk_factors'])}个, 等级: {target_resume['overall_risk_level']}")
        except Exception as e:
            print(f"[WARNING] 获取风险因素失败: {e}")
            target_resume['risk_factors'] = []
            target_resume['overall_risk_level'] = '低'

        # 生成决策摘要
        generator = get_generator()
        summary = generator.generate_summary(
            candidate=target_resume,
            job_requirements=request.job_requirements
        )

        # 生成报告
        report = generator.generate_summary_report(summary)

        return {
            "status": "success",
            "decision_summary": report
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"决策摘要生成失败：{str(e)}")

@app.post("/api/report/export")
async def export_report(request: ExportReportRequest):
    """
    导出报告
    
    支持导出对比报告、推荐方案、决策摘要等，格式包括JSON、PDF、Excel
    """
    try:
        import json
        import base64
        from datetime import datetime

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.report_type}_{timestamp}"
        
        if request.format == "json":
            # JSON格式直接返回
            return {
                "status": "success",
                "format": "json",
                "filename": f"{filename}.json",
                "data": request.data
            }
            
        elif request.format == "excel":
            # Excel格式导出
            try:
                import pandas as pd
                from openpyxl import Workbook
                from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
                from openpyxl.utils.dataframe import dataframe_to_rows
                
                output_dir = project_root / "backend" / "output" / "exports"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                excel_path = output_dir / f"{filename}.xlsx"
                
                # 创建Excel工作簿
                wb = Workbook()
                
                # 根据报告类型生成不同的工作表
                if request.report_type == "comparison":
                    _create_comparison_excel(wb, request.data)
                elif request.report_type == "recommendation":
                    _create_recommendation_excel(wb, request.data)
                elif request.report_type == "decision":
                    _create_decision_excel(wb, request.data)
                else:
                    # 通用数据导出
                    ws = wb.active
                    ws.title = "报告数据"
                    _write_data_to_worksheet(ws, request.data)
                
                # 保存文件
                wb.save(str(excel_path))
                
                # 读取文件内容返回
                with open(excel_path, 'rb') as f:
                    excel_data = f.read()
                
                import base64
                return {
                    "status": "success",
                    "format": "excel",
                    "filename": f"{filename}.xlsx",
                    "data": base64.b64encode(excel_data).decode('utf-8'),
                    "message": "Excel导出成功"
                }
                
            except ImportError:
                return {
                    "status": "error",
                    "format": "excel",
                    "message": "Excel导出需要安装pandas和openpyxl库，请运行: pip install pandas openpyxl",
                    "data": request.data
                }
            except Exception as e:
                print(f"[ERROR] Excel导出失败: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Excel导出失败: {str(e)}")
            
        elif request.format == "pdf":
            # PDF格式 - 使用reportlab生成
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                from reportlab.lib.units import cm
                import textwrap

                # 注册中文字体
                font_paths = [
                    "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                    "C:/Windows/Fonts/simhei.ttf",  # 黑体
                    "C:/Windows/Fonts/simsun.ttc",  # 宋体
                ]
                font_registered = False
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            font_registered = True
                            break
                        except:
                            continue

                if not font_registered:
                    print("[WARNING] 未找到中文字体，PDF将使用默认字体")

                output_dir = project_root / "backend" / "output" / "exports"
                output_dir.mkdir(parents=True, exist_ok=True)
                pdf_path = output_dir / f"{filename}.pdf"

                # 创建PDF
                c = canvas.Canvas(str(pdf_path), pagesize=A4)
                width, height = A4

                def set_font(size=10, bold=False):
                    """设置字体"""
                    if font_registered:
                        c.setFont('ChineseFont', size)
                    else:
                        c.setFont('Helvetica-Bold' if bold else 'Helvetica', size)

                def draw_line(text, x, y, max_width=80):
                    """绘制文本行，自动换行"""
                    if len(text) > max_width:
                        wrapped_lines = textwrap.wrap(text, width=max_width)
                        for wrapped_line in wrapped_lines:
                            c.drawString(x, y, wrapped_line)
                            y -= 0.5*cm
                        return y
                    else:
                        c.drawString(x, y, text)
                        return y - 0.5*cm

                # 标题
                set_font(18, bold=True)
                title = {
                    'comparison': '候选人对比报告',
                    'recommendation': '推荐方案报告',
                    'decision': '决策摘要报告'
                }.get(request.report_type, '报告')
                c.drawString(2*cm, height - 2*cm, title)

                # 分隔线
                c.line(2*cm, height - 2.5*cm, width - 2*cm, height - 2.5*cm)

                y_pos = height - 3.5*cm

                # 根据报告类型添加不同内容
                # 决策报告数据可能直接是decision_summary内容，或者包装在decision_summary字段中
                if request.report_type == "decision":
                    if 'decision_summary' in request.data:
                        summary = request.data['decision_summary']
                    elif 'candidate_name' in request.data:
                        # 数据直接是决策摘要内容
                        summary = request.data
                    else:
                        summary = {}

                    # 候选人基本信息
                    set_font(14, bold=True)
                    c.drawString(2*cm, y_pos, "候选人信息")
                    y_pos -= 0.8*cm

                    set_font(11)
                    y_pos = draw_line(f"姓名: {summary.get('candidate_name', 'N/A')}", 2.5*cm, y_pos)
                    y_pos = draw_line(f"决策建议: {summary.get('decision', 'N/A')}", 2.5*cm, y_pos)
                    y_pos = draw_line(f"置信度: {summary.get('confidence', 'N/A')}", 2.5*cm, y_pos)
                    y_pos = draw_line(f"综合评分: {summary.get('overall_score', 'N/A')}", 2.5*cm, y_pos)
                    y_pos -= 0.5*cm

                    # 执行摘要
                    set_font(14, bold=True)
                    c.drawString(2*cm, y_pos, "执行摘要")
                    y_pos -= 0.8*cm

                    exec_summary = summary.get('executive_summary', {})
                    set_font(11)
                    y_pos = draw_line(f"风险评估: {exec_summary.get('risk_summary', 'N/A')}", 2.5*cm, y_pos)
                    y_pos = draw_line(f"机会评估: {exec_summary.get('opportunity_summary', 'N/A')}", 2.5*cm, y_pos)
                    y_pos = draw_line(f"最终推荐: {exec_summary.get('final_recommendation', 'N/A')}", 2.5*cm, y_pos)
                    y_pos -= 0.5*cm

                    # 关键决策因素
                    key_factors = summary.get('key_factors', [])
                    if key_factors:
                        set_font(14, bold=True)
                        c.drawString(2*cm, y_pos, "关键决策因素")
                        y_pos -= 0.8*cm

                        for factor in key_factors:
                            if y_pos < 3*cm:
                                c.showPage()
                                set_font(11)
                                y_pos = height - 2*cm

                            factor_type = factor.get('type', '')
                            set_font(11, bold=True)
                            c.drawString(2.5*cm, y_pos, f"[{factor_type}] {factor.get('description', '')}")
                            y_pos -= 0.5*cm

                            set_font(10)
                            y_pos = draw_line(f"权重: {factor.get('weight', 'N/A')}", 3*cm, y_pos)

                            evidence = factor.get('evidence', [])
                            if evidence:
                                y_pos = draw_line(f"依据: {', '.join(evidence)}", 3*cm, y_pos)
                            y_pos -= 0.3*cm

                    # 建议行动
                    action_items = summary.get('action_items', {})
                    suggested_actions = action_items.get('suggested_actions', [])
                    if suggested_actions:
                        if y_pos < 5*cm:
                            c.showPage()
                            set_font(11)
                            y_pos = height - 2*cm

                        set_font(14, bold=True)
                        c.drawString(2*cm, y_pos, "建议行动")
                        y_pos -= 0.8*cm

                        set_font(10)
                        for i, action in enumerate(suggested_actions, 1):
                            if y_pos < 2*cm:
                                c.showPage()
                                set_font(10)
                                y_pos = height - 2*cm
                            y_pos = draw_line(f"{i}. {action}", 2.5*cm, y_pos)

                else:
                    # 通用内容 - 简化显示
                    set_font(11)
                    y_pos = draw_line("报告数据:", 2*cm, y_pos)
                    y_pos -= 0.3*cm

                    # 提取关键信息显示
                    data = request.data
                    if isinstance(data, dict):
                        for key, value in list(data.items())[:10]:
                            if y_pos < 2*cm:
                                c.showPage()
                                set_font(10)
                                y_pos = height - 2*cm

                            if isinstance(value, str):
                                y_pos = draw_line(f"{key}: {value}", 2.5*cm, y_pos)
                            elif isinstance(value, (int, float)):
                                y_pos = draw_line(f"{key}: {value}", 2.5*cm, y_pos)
                            else:
                                y_pos = draw_line(f"{key}: {str(value)[:50]}...", 2.5*cm, y_pos)

                # 添加页脚
                c.setFont('Helvetica', 8)
                c.drawString(2*cm, 1*cm, f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                c.save()

                # 读取PDF文件返回
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()

                return {
                    "status": "success",
                    "format": "pdf",
                    "filename": f"{filename}.pdf",
                    "data": base64.b64encode(pdf_data).decode('utf-8'),
                    "message": "PDF导出成功"
                }

            except ImportError:
                return {
                    "status": "error",
                    "format": "pdf",
                    "message": "PDF导出需要安装reportlab库，请运行: pip install reportlab",
                    "data": request.data
                }
            except Exception as e:
                print(f"[ERROR] PDF导出失败: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"PDF导出失败: {str(e)}")
            
        else:
            raise HTTPException(status_code=400, detail=f"不支持的导出格式：{request.format}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告导出失败：{str(e)}")

@app.get("/api/comparison/available-candidates")
async def get_available_candidates_for_comparison(industry: Optional[str] = None, include_all: bool = False):
    """
    获取可用于对比的候选人列表
    从排名缓存获取TCI分数和排名数据
    
    Args:
        industry: 行业名称，如果不指定则返回所有行业
        include_all: 是否包含所有候选人（忽略行业筛选）
    """
    try:
        # 从主数据文件加载所有简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        print(f"[DEBUG] 从data_manager加载到 {len(all_resumes)} 份简历")
        
        # 获取所有行业的排名缓存
        cache = get_cache_manager()
        
        # 构建完整的TCI映射（跨所有行业）
        tci_map = {}
        rank_map = {}
        
        # 如果指定了行业，从该行业缓存获取TCI
        if industry and not include_all:
            cached_ranking = cache.get("ranking", industry=industry, top_n=100)
            if cached_ranking and 'ranking' in cached_ranking:
                for item in cached_ranking['ranking']:
                    candidate_id = item.get('candidate_id', '')
                    tci_map[candidate_id] = item.get('tci_score', 0)
                    rank_map[candidate_id] = item.get('rank', 0)
        
        candidates = []
        for resume in all_resumes:
            try:
                basic_info = resume.get('basic_info', {})
                name = basic_info.get('name', '') or resume.get('candidate_id', '')
                resume_industry = resume.get('industry', '未知')
                
                if not name:
                    continue
                
                # 如果指定了行业且不是包含所有，则过滤
                if industry and not include_all and resume_industry != industry:
                    continue
                
                # 如果没有在缓存中找到TCI，尝试从该行业缓存获取
                tci_score = tci_map.get(name, 0)
                rank = rank_map.get(name, 0)
                
                # 如果TCI为0，尝试从候选人所在行业的缓存获取
                if tci_score == 0 and resume_industry:
                    cached_ranking = cache.get("ranking", industry=resume_industry, top_n=100)
                    if cached_ranking and 'ranking' in cached_ranking:
                        for item in cached_ranking['ranking']:
                            if item.get('candidate_id', '') == name:
                                tci_score = item.get('tci_score', 0)
                                rank = item.get('rank', 0)
                                break
                
                candidates.append({
                    "id": name,
                    "name": name,
                    "tci_score": tci_score,
                    "rank": rank,
                    "industry": resume_industry
                })
            except Exception as e:
                print(f"[WARNING] 处理候选人数据失败: {e}")
                continue
        
        # 按TCI分数排序
        candidates.sort(key=lambda x: x['tci_score'], reverse=True)
        
        # 重新计算排名
        for idx, c in enumerate(candidates, 1):
            c['rank'] = idx
        
        print(f"[DEBUG] 返回 {len(candidates)} 个候选人")
        
        return {
            "status": "success",
            "count": len(candidates),
            "industry": industry if industry else "所有行业",
            "candidates": candidates
        }
        
    except Exception as e:
        print(f"[ERROR] 获取候选人列表失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "success",
            "count": 0,
            "candidates": []
        }


@app.get("/api/industries")
async def get_all_industries():
    """
    获取系统中所有可用的行业列表
    从all_resumes_summary.json中统计所有行业
    兼容前端store中使用的格式: {code, name}
    """
    try:
        # 从主数据文件加载所有简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()

        # 统计行业分布
        industry_stats = {}
        for resume in all_resumes:
            industry = resume.get('industry', '未知')
            if industry not in industry_stats:
                industry_stats[industry] = {
                    "code": industry,
                    "name": industry,
                    "candidate_count": 0,
                    "candidates": []
                }
            industry_stats[industry]["candidate_count"] += 1
            name = resume.get('basic_info', {}).get('name', '未知')
            industry_stats[industry]["candidates"].append(name)

        # 转换为列表并排序
        industries = sorted(industry_stats.values(), key=lambda x: x['candidate_count'], reverse=True)

        print(f"[DEBUG] 发现 {len(industries)} 个行业，共 {len(all_resumes)} 名候选人")

        return {
            "status": "success",
            "count": len(industries),
            "industries": industries
        }

    except Exception as e:
        print(f"[ERROR] 获取行业列表失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "industries": []
        }


@app.get("/api/candidates/by-industry")
async def get_candidates_by_industry(industry: Optional[str] = None, include_all: bool = False):
    """
    获取指定行业的候选人列表
    
    Args:
        industry: 行业名称，如果不指定则返回所有行业
        include_all: 是否包含所有候选人（忽略行业筛选）
    """
    try:
        # 从主数据文件加载所有简历
        data_manager = get_data_manager(project_root)
        all_resumes = data_manager.get_all_resumes()
        
        # 获取所有行业的排名缓存
        cache = get_cache_manager()
        
        # 构建完整的TCI映射（跨所有行业）
        tci_map = {}
        rank_map = {}
        
        # 如果指定了行业，从该行业缓存获取TCI
        if industry and not include_all:
            cached_ranking = cache.get("ranking", industry=industry, top_n=100)
            if cached_ranking and 'ranking' in cached_ranking:
                for item in cached_ranking['ranking']:
                    candidate_id = item.get('candidate_id', '')
                    tci_map[candidate_id] = item.get('tci_score', 0)
                    rank_map[candidate_id] = item.get('rank', 0)
        
        candidates = []
        for resume in all_resumes:
            try:
                basic_info = resume.get('basic_info', {})
                name = basic_info.get('name', '') or resume.get('candidate_id', '')
                resume_industry = resume.get('industry', '未知')
                
                if not name:
                    continue
                
                # 如果指定了行业且不是包含所有，则过滤
                if industry and not include_all and resume_industry != industry:
                    continue
                
                # 如果没有在缓存中找到TCI，尝试从该行业缓存获取
                tci_score = tci_map.get(name, 0)
                rank = rank_map.get(name, 0)
                
                # 如果TCI为0，尝试从候选人所在行业的缓存获取
                if tci_score == 0 and resume_industry:
                    cached_ranking = cache.get("ranking", industry=resume_industry, top_n=100)
                    if cached_ranking and 'ranking' in cached_ranking:
                        for item in cached_ranking['ranking']:
                            if item.get('candidate_id', '') == name:
                                tci_score = item.get('tci_score', 0)
                                rank = item.get('rank', 0)
                                break
                
                candidates.append({
                    "id": name,
                    "name": name,
                    "tci_score": tci_score,
                    "rank": rank,
                    "industry": resume_industry
                })
            except Exception as e:
                print(f"[WARNING] 处理候选人数据失败: {e}")
                continue
        
        # 按TCI分数排序
        candidates.sort(key=lambda x: x['tci_score'], reverse=True)
        
        # 重新计算排名
        for idx, c in enumerate(candidates, 1):
            c['rank'] = idx
        
        print(f"[DEBUG] 返回 {len(candidates)} 个候选人")
        
        return {
            "status": "success",
            "count": len(candidates),
            "industry": industry if industry else "所有行业",
            "candidates": candidates
        }
        
    except Exception as e:
        print(f"[ERROR] 获取候选人列表失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "candidates": []
        }


# ============== Excel导出辅助函数 ==============

def _create_comparison_excel(wb, data):
    """创建对比报告Excel"""
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    # 定义样式
    header_font = Font(name='微软雅黑', size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    title_font = Font(name='微软雅黑', size=14, bold=True)
    normal_font = Font(name='微软雅黑', size=11)
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # 候选人详情表
    ws1 = wb.active
    ws1.title = "候选人对比"
    
    # 标题
    ws1['A1'] = "候选人对比分析报告"
    ws1['A1'].font = Font(name='微软雅黑', size=16, bold=True)
    ws1['A1'].alignment = center_alignment
    ws1.merge_cells('A1:G1')
    ws1.row_dimensions[1].height = 30
    
    # 表头
    headers = ["候选人", "TCI得分", "教育背景", "工作经历", "技能成果", "综合素质", "风险数"]
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        cell.border = thin_border
    
    # 数据行
    candidates = data.get('candidate_details', [])
    for row_idx, candidate in enumerate(candidates, 4):
        ws1.cell(row=row_idx, column=1, value=candidate.get('name', '')).alignment = center_alignment
        ws1.cell(row=row_idx, column=2, value=candidate.get('tci_score', 0)).alignment = center_alignment
        
        dims = candidate.get('dimensional_scores', {})
        ws1.cell(row=row_idx, column=3, value=dims.get('education', 0)).alignment = center_alignment
        ws1.cell(row=row_idx, column=4, value=dims.get('experience', 0)).alignment = center_alignment
        ws1.cell(row=row_idx, column=5, value=dims.get('skill_achievement', 0)).alignment = center_alignment
        ws1.cell(row=row_idx, column=6, value=dims.get('comprehensive', 0)).alignment = center_alignment
        ws1.cell(row=row_idx, column=7, value=candidate.get('risk_count', 0)).alignment = center_alignment
        
        # 添加边框
        for col in range(1, 8):
            ws1.cell(row=row_idx, column=col).border = thin_border
            ws1.cell(row=row_idx, column=col).font = normal_font
    
    # 设置列宽
    ws1.column_dimensions['A'].width = 15
    ws1.column_dimensions['B'].width = 12
    ws1.column_dimensions['C'].width = 12
    ws1.column_dimensions['D'].width = 12
    ws1.column_dimensions['E'].width = 12
    ws1.column_dimensions['F'].width = 12
    ws1.column_dimensions['G'].width = 10
    
    # 优势分析表
    ws2 = wb.create_sheet("优势分析")
    ws2['A1'] = "候选人优势分析"
    ws2['A1'].font = title_font
    ws2.merge_cells('A1:D1')
    
    row = 3
    advantage_matrix = data.get('advantage_matrix', {})
    for name, advantages in advantage_matrix.items():
        ws2.cell(row=row, column=1, value=name).font = Font(name='微软雅黑', size=12, bold=True)
        row += 1
        
        ws2.cell(row=row, column=1, value="最强维度").font = Font(bold=True)
        ws2.cell(row=row, column=2, value=", ".join(advantages.get('top_dimensions', [])))
        row += 1
        
        ws2.cell(row=row, column=1, value="关键成就").font = Font(bold=True)
        achievements = advantages.get('key_achievements', [])
        ws2.cell(row=row, column=2, value="\n".join(achievements) if achievements else "无")
        ws2.row_dimensions[row].height = max(30, len(achievements) * 15) if achievements else 20
        row += 1
        
        ws2.cell(row=row, column=1, value="独特技能").font = Font(bold=True)
        unique_skills = advantages.get('unique_skills', [])
        ws2.cell(row=row, column=2, value=", ".join(unique_skills) if unique_skills else "无")
        row += 1
        
        ws2.cell(row=row, column=1, value="稳定性").font = Font(bold=True)
        stability = advantages.get('stability', [])
        ws2.cell(row=row, column=2, value="\n".join(stability) if stability else "无")
        row += 2
    
    # 设置列宽
    ws2.column_dimensions['A'].width = 15
    ws2.column_dimensions['B'].width = 60


def _create_recommendation_excel(wb, data):
    """创建推荐方案Excel - 表格形式"""
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    # 定义样式
    title_font = Font(name='微软雅黑', size=16, bold=True)
    header_font = Font(name='微软雅黑', size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    normal_font = Font(name='微软雅黑', size=11)
    bold_font = Font(name='微软雅黑', size=11, bold=True)
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 工作表1: 方案对比概览
    ws1 = wb.active
    ws1.title = "方案对比概览"
    
    # 标题
    ws1['A1'] = "候选人推荐方案对比"
    ws1['A1'].font = title_font
    ws1['A1'].alignment = center_alignment
    ws1.merge_cells('A1:F1')
    
    # 获取数据
    summary = data.get('recommendation_summary', {})
    comparison_table = summary.get('comparison_table', [])
    plans = data.get('plans', [])
    
    # 方案对比表头
    headers = ["方案名称", "策略", "风险等级", "预期表现", "推荐人数", "团队互补性"]
    row = 3
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        cell.border = thin_border
    
    # 方案对比数据
    for plan_data in comparison_table:
        row += 1
        ws1.cell(row=row, column=1, value=plan_data.get('方案', '')).border = thin_border
        ws1.cell(row=row, column=2, value=plan_data.get('策略', '')).border = thin_border
        ws1.cell(row=row, column=3, value=plan_data.get('风险等级', '')).border = thin_border
        ws1.cell(row=row, column=4, value=plan_data.get('预期表现', '')).border = thin_border
        ws1.cell(row=row, column=5, value=plan_data.get('推荐人数', '')).border = thin_border
        ws1.cell(row=row, column=6, value=plan_data.get('团队互补性', '')).border = thin_border
    
    # 设置列宽
    ws1.column_dimensions['A'].width = 18
    ws1.column_dimensions['B'].width = 15
    ws1.column_dimensions['C'].width = 12
    ws1.column_dimensions['D'].width = 12
    ws1.column_dimensions['E'].width = 12
    ws1.column_dimensions['F'].width = 12
    
    # 工作表2: 详细方案
    ws2 = wb.create_sheet("详细方案")
    
    # 标题
    ws2['A1'] = "推荐方案详细信息"
    ws2['A1'].font = title_font
    ws2['A1'].alignment = center_alignment
    ws2.merge_cells('A1:F1')
    
    row = 3
    for plan in plans:
        # 方案名称
        ws2.cell(row=row, column=1, value=f"方案: {plan.get('name', '')}")
        ws2.cell(row=row, column=1).font = bold_font
        ws2.merge_cells(f'A{row}:F{row}')
        row += 1
        
        # 方案基本信息
        ws2.cell(row=row, column=1, value="策略:").font = bold_font
        ws2.cell(row=row, column=2, value=plan.get('strategy', ''))
        ws2.cell(row=row, column=3, value="风险等级:").font = bold_font
        ws2.cell(row=row, column=4, value=plan.get('risk_level', ''))
        ws2.cell(row=row, column=5, value="预期表现:").font = bold_font
        ws2.cell(row=row, column=6, value=plan.get('expected_performance', ''))
        row += 1
        
        # 推荐候选人
        ws2.cell(row=row, column=1, value="推荐候选人:").font = bold_font
        row += 1
        
        recommended = plan.get('recommended_candidates', [])
        if recommended:
            # 候选人表头
            cand_headers = ["姓名", "TCI得分", "风险因素数", "教育", "经验", "技能成就"]
            for col, header in enumerate(cand_headers, 1):
                cell = ws2.cell(row=row, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_alignment
                cell.border = thin_border
            row += 1
            
            # 候选人数据
            for cand in recommended:
                dims = cand.get('dimensional_scores', {})
                ws2.cell(row=row, column=1, value=cand.get('name', '')).border = thin_border
                ws2.cell(row=row, column=2, value=round(cand.get('tci_score', 0), 2)).border = thin_border
                ws2.cell(row=row, column=3, value=cand.get('risk_count', 0)).border = thin_border
                ws2.cell(row=row, column=4, value=round(dims.get('education', 0), 2)).border = thin_border
                ws2.cell(row=row, column=5, value=round(dims.get('experience', 0), 2)).border = thin_border
                ws2.cell(row=row, column=6, value=round(dims.get('skill_achievement', 0), 2)).border = thin_border
                row += 1
        else:
            ws2.cell(row=row, column=1, value="无")
            row += 1
        
        # 空行分隔
        row += 1
    
    # 设置列宽
    ws2.column_dimensions['A'].width = 15
    ws2.column_dimensions['B'].width = 12
    ws2.column_dimensions['C'].width = 12
    ws2.column_dimensions['D'].width = 10
    ws2.column_dimensions['E'].width = 10
    ws2.column_dimensions['F'].width = 12


def _create_decision_excel(wb, data):
    """创建决策摘要Excel - 表格形式"""
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    # 定义样式
    title_font = Font(name='微软雅黑', size=16, bold=True)
    header_font = Font(name='微软雅黑', size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    normal_font = Font(name='微软雅黑', size=11)
    bold_font = Font(name='微软雅黑', size=11, bold=True)
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 工作表1: 决策摘要
    ws1 = wb.active
    ws1.title = "决策摘要"
    
    # 标题
    ws1['A1'] = "候选人决策摘要"
    ws1['A1'].font = title_font
    ws1['A1'].alignment = center_alignment
    ws1.merge_cells('A1:E1')
    
    # 获取数据
    summary = data.get('decision_summary', {})
    final_decision = data.get('final_decision', {})
    
    row = 3
    
    # 最终决策
    ws1.cell(row=row, column=1, value="最终决策").font = bold_font
    ws1.merge_cells(f'A{row}:E{row}')
    row += 1
    
    ws1.cell(row=row, column=1, value="推荐候选人:").font = bold_font
    candidates = final_decision.get('candidates', [])
    ws1.cell(row=row, column=2, value=", ".join(candidates) if candidates else "未确定")
    ws1.merge_cells(f'B{row}:E{row}')
    row += 1
    
    ws1.cell(row=row, column=1, value="决策依据:").font = bold_font
    ws1.cell(row=row, column=2, value=final_decision.get('reasoning', ''))
    ws1.merge_cells(f'B{row}:E{row}')
    row += 2
    
    # 决策摘要
    ws1.cell(row=row, column=1, value="决策摘要").font = bold_font
    ws1.merge_cells(f'A{row}:E{row}')
    row += 1
    
    # 摘要表头
    summary_headers = ["维度", "内容"]
    for col, header in enumerate(summary_headers, 1):
        cell = ws1.cell(row=row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        cell.border = thin_border
    row += 1
    
    # 摘要内容
    summary_items = [
        ("核心优势", summary.get('core_advantages', '')),
        ("主要风险", summary.get('main_risks', '')),
        ("建议措施", summary.get('recommended_actions', '')),
        ("预期效果", summary.get('expected_outcome', ''))
    ]
    
    for item_name, item_value in summary_items:
        ws1.cell(row=row, column=1, value=item_name).border = thin_border
        ws1.cell(row=row, column=1).font = bold_font
        ws1.cell(row=row, column=2, value=item_value).border = thin_border
        ws1.merge_cells(f'B{row}:E{row}')
        row += 1
    
    # 设置列宽
    ws1.column_dimensions['A'].width = 15
    ws1.column_dimensions['B'].width = 20
    ws1.column_dimensions['C'].width = 20
    ws1.column_dimensions['D'].width = 20
    ws1.column_dimensions['E'].width = 20
    
    # 工作表2: 候选人对比
    ws2 = wb.create_sheet("候选人对比")
    
    # 标题
    ws2['A1'] = "候选人决策对比"
    ws2['A1'].font = title_font
    ws2['A1'].alignment = center_alignment
    ws2.merge_cells('A1:E1')
    
    row = 3
    
    # 候选人对比表头
    comparison = data.get('candidate_comparison', [])
    if comparison:
        comp_headers = ["候选人", "TCI得分", "优势", "劣势", "建议"]
        for col, header in enumerate(comp_headers, 1):
            cell = ws2.cell(row=row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            cell.border = thin_border
        row += 1
        
        # 对比数据
        for cand in comparison:
            ws2.cell(row=row, column=1, value=cand.get('name', '')).border = thin_border
            ws2.cell(row=row, column=2, value=round(cand.get('tci_score', 0), 2)).border = thin_border
            ws2.cell(row=row, column=3, value=cand.get('advantages', '')).border = thin_border
            ws2.cell(row=row, column=4, value=cand.get('disadvantages', '')).border = thin_border
            ws2.cell(row=row, column=5, value=cand.get('recommendation', '')).border = thin_border
            row += 1
    
    # 设置列宽
    ws2.column_dimensions['A'].width = 12
    ws2.column_dimensions['B'].width = 12
    ws2.column_dimensions['C'].width = 25
    ws2.column_dimensions['D'].width = 25
    ws2.column_dimensions['E'].width = 25


def _write_data_to_worksheet(ws, data):
    """将数据写入工作表"""
    import json
    ws['A1'] = json.dumps(data, ensure_ascii=False, indent=2)
    ws.column_dimensions['A'].width = 100


# ============== 主入口 ==============

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
