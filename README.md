# 人才简历综合优选系统

基于AHP层次分析法与熵权法融合的多维度简历评分系统，支持6大行业的人才竞争力评估与排名。

## 🎯 系统特点

- **多维度评分模型**：教育背景、工作经历、技能成果、综合素质四大维度
- **动态权重计算**：AHP主观权重 + 熵权法客观权重融合
- **行业自适应**：支持电商、品牌、销售、研发、生产、人力资源六大行业
- **智能问答**：基于评分结果的智能问答与推荐理由生成
- **可视化展示**：雷达图、柱状图、饼图等多维度数据可视化
- **报告导出**：支持JSON、CSV格式报告导出

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    系统架构层次图                             │
├─────────────────────────────────────────────────────────────┤
│  展示输出层: Vue3 + Element Plus + ECharts                   │
├─────────────────────────────────────────────────────────────┤
│  API服务层: FastAPI + Pydantic                               │
├─────────────────────────────────────────────────────────────┤
│  模型层: Dimensional_scoring_model + weight_model            │
├─────────────────────────────────────────────────────────────┤
│  数据层: Resume_Recognition_Model + MySQL + Redis            │
└─────────────────────────────────────────────────────────────┘
```

## 📋 功能模块

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
- 组合权重融合（α=0.5）

### 4. 前端界面模块
- 简历上传页面
- 排名看板（支持行业筛选）
- 数据分析页面
- 智能问答页面
- 候选人详情页

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- MySQL 8.0
- Redis 6.0

### 安装依赖

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 配置数据库

编辑 `backend/database.py` 中的数据库配置：

```python
MYSQL_CONFIG = {
    'host': '14.103.124.109',
    'port': 3306,
    'database': 'jianli',
    'user': 'jianli',
    'password': 'aS4QKY5znfZDn4Ts'
}

REDIS_CONFIG = {
    'host': '14.103.124.109',
    'port': 6379,
    'password': 'redis_b3ZReQ',
    'db': 9
}
```

### 启动服务

```bash
# 方法1: 使用启动脚本
python start_servers.py

# 方法2: 分别启动
# 后端
cd backend/app
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm run dev
```

### 访问系统

- 前端界面: http://localhost:5173
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 📊 评分模型

### TCI综合得分公式

```
TCI = Wedu × Sedu + Wexp × Sexp + Wskill × Sskill + Wadj × Sadj
```

### 维度权重示例

| 维度 | 技术类 | 管理类 |
|------|--------|--------|
| 教育背景 | 15% | 20% |
| 工作经历 | 30% | 35% |
| 技能成果 | 40% | 25% |
| 综合素质 | 15% | 20% |

### 跳槽惩罚机制

- 条件：5年内跳槽次数 > 3次
- 惩罚：TCI总分 × 0.9

## 🔌 API接口

### 简历上传
```http
POST /api/resume/upload
Content-Type: multipart/form-data

file: <简历文件>
industry: <行业代码>
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

## 📁 项目结构

```
.
├── backend/
│   ├── app/
│   │   └── main.py          # FastAPI主入口
│   ├── database.py          # 数据库配置
│   ├── requirements.txt     # Python依赖
│   └── output/              # 输出目录
├── frontend/
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   ├── stores/          # Pinia状态管理
│   │   ├── router/          # Vue Router配置
│   │   └── App.vue          # 根组件
│   ├── package.json         # Node依赖
│   └── vite.config.js       # Vite配置
├── .venv/                   # 模型代码
│   ├── Resume_Recognition_Model/
│   ├── Dimensional_scoring_model/
│   ├── weight_model/
│   └── Dynamic_Industry_Weight_Matrix/
├── start_servers.py         # 启动脚本
└── README.md               # 项目说明
```

## 🎓 开源项目参考

本项目参考了以下开源项目：

1. **teash1rt/resume-analysis-system** - Vue3+SpringBoot架构
2. **Greyisheep/resume-ranking-assessment** - FastAPI+sentence-transformers
3. **vectornguyen76/resume-ranking** - LLM+LangChain集成
4. **WhiteNight123/parser-resume** - PaddleOCR解析

## 📄 许可证

MIT License

## 👥 开发者

- 基于数学建模竞赛《人才简历综合优选》赛题开发
- 采用AHP+熵权法融合模型
