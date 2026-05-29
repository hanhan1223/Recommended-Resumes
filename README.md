# 人才简历综合优选系统

基于AHP层次分析法与熵权法融合的多维度简历评分系统，支持6大行业的人才竞争力评估与排名。

## 系统特点

- **多维度评分模型**：教育背景、工作经历、技能成果、综合素质、成长潜力、岗位匹配六大维度
- **动态权重计算**：AHP主观权重 + 熵权法客观权重融合
- **行业自适应**：支持电商、品牌、销售、研发、生产、人力资源六大行业
- **AI智能分析**：基于通义千问大模型的候选人综合分析与录用建议
- **智能问答**：基于LLM的智能问答与推荐理由生成
- **可视化展示**：雷达图、柱状图、饼图等多维度数据可视化
- **报告导出**：支持JSON、CSV格式报告导出

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    系统架构层次图                             │
├─────────────────────────────────────────────────────────────┤
│  展示输出层: Vue3 + Element Plus + ECharts                   │
├─────────────────────────────────────────────────────────────┤
│  API服务层: FastAPI + Pydantic                               │
├─────────────────────────────────────────────────────────────┤
│  AI服务层: 通义千问 (Qwen) LLM                               │
├─────────────────────────────────────────────────────────────┤
│  模型层: Dimensional_scoring_model + weight_model            │
├─────────────────────────────────────────────────────────────┤
│  数据层: Resume_Recognition_Model + MySQL + Redis            │
└─────────────────────────────────────────────────────────────┘
```

## 功能模块

### 1. 简历解析模块
- 支持PDF、DOCX、TXT格式
- 基于规则+NER的实体识别
- 自动行业分类

### 2. 维度评分模块
- 教育背景评分（学历、学校、专业）
- 工作经历评分（公司、稳定性、升职）
- 技能成果评分（技能匹配、重大成果）
- 综合素质评分（软技能、跳槽惩罚）

### 3. 权重计算模块
- AHP层次分析法（主观权重）
- 熵权法（客观权重）
- 组合权重融合（alpha=0.5）

### 4. AI智能分析模块
- 基于通义千问大模型的候选人综合分析
- 自动生成优势、风险、录用建议
- 支持规则分析fallback

### 5. 前端界面模块
- 简历上传页面
- 排名看板（支持行业筛选）
- 数据分析页面
- 智能问答页面
- 候选人详情页（含AI分析）

## 快速开始

### 方式一：Conda 环境部署（推荐）

#### 1. 创建 Conda 环境

```bash
# 创建 Python 3.10 环境
conda create -n resume_system python=3.10 -y

# 激活环境
conda activate resume_system
```

#### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 3. 配置 LLM API（可选）

**方式一：使用环境变量（推荐，更安全）**

```bash
# Linux/Mac
export DASHSCOPE_API_KEY="your-dashscope-api-key"

# Windows PowerShell
$env:DASHSCOPE_API_KEY="your-dashscope-api-key"
```

**方式二：使用配置文件**

复制模板文件并编辑：

```bash
cp backend/config.json.template backend/config.json
```

编辑 `backend/config.json`，填入通义千问 API Key：

```json
{
  "llm": {
    "api_key": "your-dashscope-api-key",
    "model": "qwen3.6-flash"
  }
}
```

⚠️ **注意**：`backend/config.json` 已被添加到 `.gitignore`，不会被提交到代码仓库。

#### 4. 启动后端服务

```bash
cd backend
python run_server.py

# 或直接使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5. 安装并启动前端

```bash
cd frontend
npm install
npm run dev
```

#### 6. 访问系统

- 前端界面: http://localhost:5173
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 方式二：直接使用 Python

#### 环境要求
- Python 3.8+
- Node.js 16+

#### 安装依赖

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

#### 启动服务

```bash
# 后端
cd backend
python run_server.py

# 前端（另一个终端）
cd frontend
npm run dev
```

## Conda 环境管理

```bash
# 查看所有环境
conda env list

# 激活环境
conda activate resume_system

# 退出环境
conda deactivate

# 删除环境
conda remove -n resume_system --all

# 导出环境配置
conda env export > environment.yml

# 从配置文件创建环境
conda env create -f environment.yml
```

## API 接口

### 简历上传
```http
POST /api/resume/upload
Content-Type: multipart/form-data

file: <简历文件>
industry: <行业代码>
```

### 简历解析
```http
POST /api/resume/parse
Content-Type: application/json

{
  "file_path": "uploads/xxx.pdf",
  "industry": "电商"
}
```

### 单份评分
```http
POST /api/score/single
Content-Type: application/json

{
  "resume_id": "候选人姓名",
  "job_type": "technical",
  "industry": "电商"
}
```

### 批量评分
```http
POST /api/score/batch
Content-Type: application/json

{
  "resume_ids": [],
  "job_type": "technical",
  "industry": "电商"
}
```

### 行业排名
```http
GET /api/rank/industry/{industry}?top_n=10
```

### AI候选人分析
```http
POST /api/analysis/candidate
Content-Type: application/json

{
  "candidate_name": "候选人姓名",
  "industry": "电商"
}
```

响应：
```json
{
  "status": "success",
  "data": {
    "summary": "综合评价...",
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["不足1"],
    "risks": ["风险1"],
    "recommendation": "录用建议...",
    "development_suggestions": ["建议1", "建议2"],
    "source": "llm"
  }
}
```

### 智能问答
```http
POST /api/qa/ask
Content-Type: application/json

{
  "question": "排名多少？",
  "context": {
    "candidate_id": "张三",
    "tci_score": 4.25
  }
}
```

### 其他接口
```http
GET /api/industries          # 获取支持的行业列表
GET /api/data/statistics     # 获取数据统计
GET /api/data/resumes        # 获取所有简历数据
GET /api/llm/status          # 获取LLM服务状态
GET /api/cache/stats         # 获取缓存统计
POST /api/cache/clear        # 清除缓存
```

## 评分模型

### TCI综合得分公式

```
D-TCI = Σ(Wi×Si) + 成长轨迹加分 + 潜力加分 + 风险惩罚项 + 岗位匹配修正项
```

### 维度权重示例

| 行业 | 教育背景 | 工作经历 | 技能成果 | 综合素质 | 成长潜力 | 岗位匹配 |
|------|----------|----------|----------|----------|----------|----------|
| 电商 | 8% | 25% | 32% | 15% | 10% | 10% |
| 研发 | 15% | 25% | 32% | 8% | 12% | 8% |
| 销售 | 8% | 28% | 32% | 12% | 8% | 12% |
| 品牌 | 12% | 25% | 28% | 15% | 10% | 10% |
| 生产 | 12% | 28% | 28% | 12% | 10% | 10% |
| 人力资源 | 12% | 25% | 28% | 15% | 10% | 10% |

### 跳槽惩罚机制

- 条件：5年内跳槽次数 > 3次
- 惩罚：TCI总分 x 0.9

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI主入口
│   │   ├── llm_service.py       # LLM服务（通义千问）
│   │   ├── data_manager.py      # 数据管理
│   │   ├── cache_manager.py     # 缓存管理
│   │   └── data_validator.py    # 数据验证
│   ├── Dimensional_scoring_model/  # 维度评分模型
│   ├── weight_model/               # 权重计算模型
│   ├── database.py              # 数据库配置
│   ├── config.json              # LLM配置
│   ├── requirements.txt         # Python依赖
│   └── run_server.py            # 启动脚本
├── frontend/
│   ├── src/
│   │   ├── views/               # 页面组件
│   │   │   ├── Home.vue         # 首页
│   │   │   ├── Upload.vue       # 上传页
│   │   │   ├── Ranking.vue      # 排名页
│   │   │   ├── Analysis.vue     # 分析页
│   │   │   ├── QA.vue           # 问答页
│   │   │   └── CandidateDetail.vue  # 候选人详情（含AI分析）
│   │   ├── stores/              # Pinia状态管理
│   │   ├── router/              # Vue Router配置
│   │   └── App.vue              # 根组件
│   ├── package.json             # Node依赖
│   └── vite.config.js           # Vite配置
├── Resume_Recognition_Model/    # 简历解析模块
│   ├── resume_parser.py         # 简历解析器
│   └── config/
│       └── company_rating.json  # 公司/高校评级知识库
├── Dynamic_Industry_Weight_Matrix/  # 行业权重矩阵模块
└── README.md
```

## 许可证

MIT License
