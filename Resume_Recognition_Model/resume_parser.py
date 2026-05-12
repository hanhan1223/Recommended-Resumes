"""
简历解析与特征提取模块
功能：
1. 读取 docx、PDF 格式简历
2. 使用 jieba+ 规则进行命名实体识别
3. 时间标准化（统一为月单位）
4. 非结构化转结构化（成果提取）
5. 公司/高校实力量化
6. 行业自动识别
7. 输出 JSON 格式结构化数据
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import jieba
from docx import Document

try:
    import pdfplumber
    PDF_PARSER_AVAILABLE = True
except ImportError:
    PDF_PARSER_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class ResumeParser:
    """简历解析器"""

    def __init__(self, config_path: str = None):
        """
        初始化解析器
        :param config_path: 配置文件路径
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__),
            'config',
            'company_rating.json'
        )
        self.config = self._load_config()
        self._init_entity_patterns()
        self._init_industry_keywords()

    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告：配置文件加载失败 {e}，使用默认配置")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "company_rating_knowledge_base": {
                "rating_scale": {
                    "5": "世界 500 强企业",
                    "4": "上市公司",
                    "3": "中型企业",
                    "2": "小型企业",
                    "1": "微型企业"
                },
                "companies": {
                    "5": [],
                    "4": [],
                    "3": [],
                    "2": [],
                    "1": []
                },
                "university_examples": {
                    "5": ["清华大学", "北京大学"],
                    "4": [],
                    "3": [],
                    "2": [],
                    "1": []
                }
            }
        }

    def _init_entity_patterns(self):
        """初始化实体识别规则"""
        self.time_patterns = [
            (r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', 'YMD'),
            (r'(\d{4})[-/](\d{1,2})', 'YM'),
            (r'(\d{4}) 年 (\d{1,2}) 月 (\d{1,2}) 日', 'YMD_CN'),
            (r'(\d{4}) 年 (\d{1,2}) 月', 'YM_CN'),
            (r'(\d{4}) 年', 'Y_CN'),
            (r'(\d{4})', 'Y'),
        ]

        self.email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        self.phone_pattern = r'1[3-9]\d{9}'
        self.salary_pattern = r'(\d+(?:\.\d+)?)\s*(k|K|千|万)\s*(?:元 | 元/月 | 元/年 | 月薪 | 年薪)?'
        self.percentage_pattern = r'(\d+(?:\.\d+)?)\s*%'
        self.money_pattern = r'(\d+(?:\.\d+)?)\s*(万 | 亿)\s*(?:元 | 万)?'
        self.people_pattern = r'(\d+(?:\.\d+)?)\s*(人 | 名 | 位)'

    def _init_industry_keywords(self):
        """初始化行业关键词"""
        self.industry_keywords = {
            '电商': [
                '电商', '淘宝', '天猫', '京东', '拼多多', '抖音电商', '快手电商',
                '电子商务', '电商运营', '店铺运营', '网店', '线上销售',
                'GMV', 'ROI', '转化率', '客单价', '流量', '直通车', '钻展',
                '跨境电商', '亚马逊', 'eBay', '独立站', '直播运营'
            ],
            '人力资源': [
                '人力资源', 'HR', '招聘', '培训', '薪酬', '绩效', '员工关系',
                'HRBP', 'COE', 'SSC', '猎头', '简历', '面试', '背调',
                '组织发展', '人才发展', '企业文化', '人力资源规划', 'HRD'
            ],
            '品牌': [
                '品牌', '品牌推广', '品牌管理', '品牌总监', '市场总监',
                '产品推广', '活动策划', '整合营销', '数字营销', '内容营销',
                '社交媒体', '新媒体运营', 'CMO', '市场经理', '品牌经理',
                '公关', '媒介', '广告'
            ],
            '生产': [
                '生产', '工厂', '制造', '车间', '产线', '工艺', '质量',
                '生产计划', '生产管理', '精益生产', '6S', 'ISO',
                '厂长', '生产总监', '生产经理', '车间主任',
                '产能', '良率', '合格率', '生产效率', '副厂长'
            ],
            '研发': [
                '研发', '研究', '开发', '技术', '实验', '测试', '专利',
                '工程师', '科学家', '博士', '硕士', '技术创新',
                '产品设计', '配方', '工艺研发', '技术研发',
                '论文', '发明专利', '实用新型', 'SCI', '核心期刊',
                '首席科学家', '研究院', '研发总监'
            ],
            '销售': [
                '销售', '销售渠道', '代理商', '经销商',
                '大客户', '区域销售', '销售代表', '销售经理', '销售总监',
                '业绩', '回款', '签单', '合同', '订单',
                '外贸', '海外销售', '国际贸易', '出口', '业务员',
                '客户', '签单'
            ]
        }

        self.high_priority_keywords = {
            '电商': ['电商', '电子商务', '淘宝', '天猫', '京东', '拼多多', 'GMV', '直播运营'],
            '人力资源': ['HR', 'HRBP', 'HRD', '招聘', '薪酬', '绩效'],
            '品牌': ['品牌总监', '市场总监', 'CMO', '品牌经理', '品牌推广'],
            '生产': ['厂长', '生产总监', '副厂长', '车间主任', '精益生产'],
            '研发': ['研发总监', '首席科学家', '研究院', '博士', '博士后', '研究员'],
            '销售': ['销售总监', '外贸', '代理商', '经销商', '签单', '回款']
        }

    def read_file(self, file_path: str) -> str:
        """
        根据文件扩展名自动选择读取方法
        :param file_path: 文件路径
        :return: 简历文本内容
        """
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            return self.read_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return self.read_docx(file_path)
        elif ext == '.txt':
            return self.read_txt(file_path)
        else:
            raise Exception(f"不支持的文件格式：{ext}，仅支持 PDF、DOCX、DOC、TXT")

    def read_pdf(self, file_path: str) -> str:
        """
        读取 PDF 文件，使用多种方案确保最佳提取效果
        方案1: pdfplumber (优先)
        方案2: pypdf 直接提取
        方案3: PyMuPDF (fitz)
        方案4: OCR.space API (如安装了ocrsdk)
        :param file_path: 文件路径
        :return: 简历文本内容
        """
        if not PDF_PARSER_AVAILABLE and not PYPDF_AVAILABLE and not PYMUPDF_AVAILABLE:
            raise Exception("PDF 解析模块未安装，请安装 pdfplumber 或 pypdf：pip install pdfplumber pypdf")

        text = ""
        methods_tried = []

        if PDF_PARSER_AVAILABLE:
            try:
                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                text = '\n'.join(text_parts)
                if text.strip():
                    methods_tried.append('pdfplumber')
                    print(f"[OCR] pdfplumber 提取了 {len(text)} 字符")
            except Exception as e:
                print(f"[OCR] pdfplumber 失败: {e}")

        if not text.strip() and PYMUPDF_AVAILABLE:
            try:
                import pymupdf
                text_parts = []
                with pymupdf.open(file_path) as doc:
                    for page in doc:
                        page_text = page.get_text()
                        if page_text:
                            text_parts.append(page_text)
                text = '\n'.join(text_parts)
                if text.strip():
                    methods_tried.append('pymupdf')
                    print(f"[OCR] PyMuPDF 提取了 {len(text)} 字符")
            except Exception as e:
                print(f"[OCR] PyMuPDF 失败: {e}")

        if not text.strip() and PYPDF_AVAILABLE:
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                text_parts = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                text = '\n'.join(text_parts)
                if text.strip():
                    methods_tried.append('pypdf')
                    print(f"[OCR] pypdf 提取了 {len(text)} 字符")
            except Exception as e:
                print(f"[OCR] pypdf 失败: {e}")

        if not text.strip():
            raise Exception(f"所有 PDF 解析方案均失败，文件: {file_path}")

        fixed_text = self._fix_common_encoding_issues(text)
        if fixed_text != text:
            print(f"[OCR] 编码修复: {len(text)} -> {len(fixed_text)} 字符")

        return fixed_text

    def _fix_common_encoding_issues(self, text: str) -> str:
        """
        修复常见的中文编码问题
        处理由字体映射错误导致的乱码
        """
        if not text:
            return text

        replacements = {
            '⼀': '一', '⼁': '二', '⼂': '三', '⼃': '四', '⼄': '五',
            '⼆': '六', '⼇': '七', '⼈': '八', '⼉': '九', '⼊': '十',
            '⼋': '百', '⼌': '千', '⼍': '万', '⼎': '亿', '⼏': '兆',
            '⼐': '元', '⼑': '年', '⼒': '月', '⼓': '日', '⼔': '时',
            '⼕': '分', '⼖': '秒', '⼗': '人', '⼘': '名', '⼙': '女',
            '⼚': '男', '⼛': '大', '⼜': '小', '⼝': '中', '⼞': '上',
            '⼟': '下', '⼠': '本', '⼡': '公', '⼢': '司', '⼣': '公',
            '⼤': '学', '⼥': '校', '⼦': '子', '⼧': '公', '⼨': '会',
            '⼩': '公', '⼪': '室', '⼫': '部', '⼬': '门', '⼭': '公',
            '⼮': '司', '⼯': '内', '⼰': '容', '⼱': '工', '⼲': '作',
            '⼳': '经', '⼴': '历', '⼵': '验', '⼶': '公', '⼷': '司',
            '⼸': '名', '⼹': '称', '⼺': '岗', '⼻': '位', '⼼': '心',
            '⼽': '理', '⼾': '学', '⼿': '习', '⽀': '持', '⽁': '开',
            '⽂': '发', '⽂': '文', '⽆': '无', '⽇': '日', '⽈': '曰',
            '⽉': '月', '⽊': '木', '⽋': '欠', '⽌': '不', '⽍': '可',
            '⽎': '打', '⽏': '算', '⽐': '布', '⽑': '局', '⽒': '式',
            '⽓': '气', '⽔': '水', '⽕': '火', '⽖': '爪', '⽗': '父',
            '⽘': '交', '⽙': '互', '⽚': '片', '⽛': '牙', '⽜': '牛',
            '⽝': '犬', '⽞': '玄', '⽟': '玉', '⽠': '瓜', '⽡': '瓦',
            '⽢': '甘', '⽣': '生', '⽤': '用', '⽡': '田', '⽢': '甘',
            '⽣': '产', '⽥': '田', '⽦': '疋', '⽧': '示', '⽨': '禹',
            '⽩': '白', '⽪': '百', '⽫': '皂', '⽬': '目', '⽭': '矛',
            '⽮': '矢', '⽯': '石', '⽰': '示', '⽱': '内', '⽲': '禾',
            '⽳': '穴', '⽴': '立', '⽴': '竹', '⽵': '竹', '⽶': '米',
            '⽷': '糸', '⽸': '缶', '⽹': '网', '⽺': '羊', '⽻': '羽',
            '⽼': '老', '⽽': '而', '⽾': '耒', '⽿': '耳', '⾀': '聿',
            '⾁': '臣', '⾂': '自', '⾃': '自', '⾄': '至', '⾅': '臼',
            '⾆': '舌', '⾇': '舛', '⾈': '舟', '⾉': '艮', '⾊': '色',
            '⾋': '艸', '⾌': '虐', '⾍': '虫', '⾎': '血', '⾏': '行',
            '⾐': '衣', '⾑': '衤', '⾒': '见', '⾓': '角', '⾔': '言',
            '⾕': '谷', '⾖': '豆', '⾗': '豕', '⾘': '豸', '⾙': '貝',
            '⾚': '赤', '⾛': '走', '⾜': '足', '⾝': '身', '⾞': '車',
            '⾟': '辛', '⾠': '辰', '⾡': '辵', '⾢': '邑', '⾣': '阜',
            '⾤': '隶', '⾥': '里', '⾦': '金', '⾧': '長', '⾨': '門',
            '⾩': '阜', '⾪': '隶', '⾫': '隹', '⾬': '雨', '⾭': '靑',
            '⾮': '非', '⾯': '面', '⾰': '革', '⾱': '韋', '⾲': '韭',
            '⾳': '音', '⾴': '頁', '⾵': '風', '⾶': '飛', '⾷': '食',
            '⾸': '首', '⾹': '香', '⾺': '馬', '⾻': '骨', '⾼': '高',
            '⾽': '髟', '⾾': '鬥', '⾿': '鬲',
        }

        result = text
        for wrong, correct in replacements.items():
            if wrong in result:
                result = result.replace(wrong, correct)

        import re
        common_garbled_patterns = [
            (r'项⽬', r'项目'),
            (r'经验', r'经验'),
            (r'华南理⼤学', r'华南理工'),
            (r'华南理工大学广州学院', r'华南理工大学广州学院'),
            (r'华南理内学学历州学院', r'华南理工大学广州学院'),
            (r'华南理エ学厉州学院', r'华南理工大学广州学院'),
            (r'华南理功学厉州学院', r'华南理工大学广州学院'),
            (r'⼴州学院', r'广州学院'),
            (r'软件⼯程', r'软件工程'),
            (r'软件内程', r'软件工程'),
            (r'软件エ程', r'软件工程'),
            (r'掌握 Java 核⼼基础', r'掌握Java核心基础'),
            (r'掌握 Java核心基础', r'掌握Java核心基础'),
            (r'熟悉 MySQL 核⼼机制', r'熟悉MySQL核心机制'),
            (r'熟悉 MySQL核心机制', r'熟悉MySQL核心机制'),
            (r'熟悉 Redis 持久化', r'熟悉Redis持久化'),
            (r'熟悉 Spring Boot', r'熟悉SpringBoot'),
            (r'熟悉SpringBoot', r'熟悉SpringBoot'),
            (r'熟悉 LangChain', r'熟悉LangChain'),
            (r'熟悉LangChainj', r'熟悉LangChain'),
            (r'应用产成', r'应用生成'),
            (r'网站产成', r'网站生成'),
            (r'代码产成', r'代码生成'),
            (r'项目构建', r'项目构建'),
            (r'用学', r'用户'),
            (r'用十', r'输入'),
            (r'拓宽 AI 能月', r'拓宽 AI 能力'),
            (r'防不', r'防止'),
            (r'防十', r'防止'),
            (r'接中', r'接口'),
            (r'内程', r'工程师'),
            (r'内具', r'工具'),
            (r'厉史', r'历史'),
            (r'持持', r'支持'),
            (r'多用学会话', r'多用户会话'),
            (r'并发线程安全', r'并发线程安全'),
            (r'内存', r'内存'),
            (r'省赛', r'省赛'),
            (r'校级', r'校级'),
            (r'六等奖', r'二等奖'),
            (r'奖学金', r'奖学金'),
            (r'校园经历', r'校园经历'),
            (r'后端部作事', r'后端部干事'),
            (r'产成', r'生成'),
            (r'网⻚截图', r'网页截图'),
            (r'深', r'深'),
            (r'度分⻚', r'度分页'),
            (r'常⻚问题', r'常见问题'),
            (r'⻚', r'页'),
            (r' ⼯作', r'工作'),
            (r'后台', r'后台'),
            (r'宝塔面版', r'宝塔面板'),
            (r'非阻塞', r'非阻塞'),
        ]
        for pattern, replacement in common_garbled_patterns:
            if re.search(pattern, result):
                result = re.sub(pattern, replacement, result)

        result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', result)

        return result

    def read_docx(self, file_path: str) -> str:
        """
        读取 docx 文件
        :param file_path: 文件路径
        :return: 简历文本内容
        """
        try:
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return '\n'.join(paragraphs)
        except Exception as e:
            raise Exception(f"读取文件失败：{file_path}, 错误：{e}")

    def read_txt(self, file_path: str) -> str:
        """
        读取 txt 文件
        :param file_path: 文件路径
        :return: 简历文本内容
        """
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise Exception(f"读取 TXT 文件失败：{file_path}，无法识别编码")

    def extract_time_to_months(self, time_str: str) -> Optional[float]:
        """提取时间并转换为月数"""
        time_str = time_str.strip()

        if any(word in time_str for word in ['至今', '当前', 'present', 'Present']):
            end_date = datetime.now()
        else:
            end_date = None

        for pattern, time_type in self.time_patterns:
            matches = re.findall(pattern, time_str)
            if matches:
                if len(matches) >= 2 and end_date is None:
                    start_match = matches[0]
                    end_match = matches[1]

                    if time_type == 'YMD':
                        start_year, start_month = int(start_match[0]), int(start_match[1])
                    elif time_type == 'YM':
                        start_year, start_month = int(start_match[0]), int(start_match[1])
                    elif time_type == 'YMD_CN':
                        start_year, start_month = int(start_match[0]), int(start_match[1])
                    elif time_type == 'YM_CN':
                        start_year, start_month = int(start_match[0]), int(start_match[1])
                    elif time_type == 'Y_CN':
                        start_year, start_month = int(start_match[0]), 1
                    else:
                        start_year, start_month = int(start_match[0]), 1

                    if time_type == 'YMD':
                        end_year, end_month = int(end_match[0]), int(end_match[1])
                    elif time_type == 'YM':
                        end_year, end_month = int(end_match[0]), int(end_match[1])
                    elif time_type == 'YMD_CN':
                        end_year, end_month = int(end_match[0]), int(end_match[1])
                    elif time_type == 'YM_CN':
                        end_year, end_month = int(end_match[0]), int(end_match[1])
                    elif time_type == 'Y_CN':
                        end_year, end_month = int(end_match[0]), 1
                    else:
                        end_year, end_month = int(end_match[0]), 1

                    months = (end_year - start_year) * 12 + (end_month - start_month)
                    return max(0, months)

                elif len(matches) == 1 and end_date:
                    match = matches[0]
                    if time_type in ['YMD', 'YMD_CN']:
                        start_year, start_month = int(match[0]), int(match[1])
                    elif time_type in ['YM', 'YM_CN']:
                        start_year, start_month = int(match[0]), int(match[1])
                    elif time_type in ['Y_CN', 'Y']:
                        start_year, start_month = int(match[0]), 1
                    else:
                        start_year, start_month = int(match[0]), 1

                    months = (end_date.year - start_year) * 12 + (end_date.month - start_month)
                    return max(0, months)

                elif len(matches) == 1:
                    match = matches[0]
                    year = int(match[0])
                    return (datetime.now().year - year) * 12

        return None

    def extract_achievements(self, text: str) -> List[Dict]:
        """提取成果（非结构化转结构化）"""
        achievements = []

        metric_keywords = [
            '销售', '销售额', '营收', '收入', '业绩', 'GMV',
            '利润', '毛利率', '净利率',
            '效率', '生产效率', '人均效率', '周转率',
            '成本', '生产成本', '运营成本',
            '良率', '合格率', '质量',
            '团队', '人数', '人员', '规模',
            '市场', '市场份额', '占有率',
            '流量', '用户', '客户', '订单',
            '库存', '面积', '空间'
        ]

        increase_verbs = ['提升', '增长', '提高', '增加', '上升', '扩大', '突破', '达到', '从', '到']
        decrease_verbs = ['降低', '减少', '下降', '缩减', '节约', '节省']

        sentences = re.split(r'[;,.!?。！？；，]', text)

        for sentence in sentences:
            if not sentence.strip():
                continue

            achievement = {
                'original_text': sentence.strip(),
                'metric': None,
                'value': None,
                'unit': None,
                'change_type': None,
                'from_value': None,
                'to_value': None
            }

            if any(verb in sentence for verb in increase_verbs):
                achievement['change_type'] = 'increase'
            elif any(verb in sentence for verb in decrease_verbs):
                achievement['change_type'] = 'decrease'

            percentages = re.findall(self.percentage_pattern, sentence)
            if percentages:
                achievement['value'] = float(percentages[0])
                achievement['unit'] = '%'

            money_matches = re.findall(self.money_pattern, sentence)
            if money_matches:
                achievement['value'] = float(money_matches[0][0])
                achievement['unit'] = money_matches[0][1] + '元'

            people_matches = re.findall(self.people_pattern, sentence)
            if people_matches:
                achievement['value'] = float(people_matches[0][0])
                achievement['unit'] = '人'

            from_to_pattern = r'从\s*(\d+(?:\.\d+)?)\s*(万 | 亿|千|人 | 元)?\s*(?:到 | 至)\s*(\d+(?:\.\d+)?)\s*(万 | 亿|千|人 | 元)?'
            from_to_matches = re.findall(from_to_pattern, sentence)
            if from_to_matches:
                match = from_to_matches[0]
                achievement['from_value'] = {
                    'value': float(match[0]),
                    'unit': match[1] if match[1] else ''
                }
                achievement['to_value'] = {
                    'value': float(match[2]),
                    'unit': match[3] if match[3] else ''
                }
                achievement['change_type'] = 'increase'

            for metric in metric_keywords:
                if metric in sentence:
                    achievement['metric'] = metric
                    break

            if achievement['value'] or achievement['from_value'] or achievement['to_value']:
                if not achievement['metric']:
                    if '销售' in sentence or '业绩' in sentence or '营收' in sentence:
                        achievement['metric'] = '销售'
                    elif '效率' in sentence or '效率提升' in sentence:
                        achievement['metric'] = '效率'
                    elif '成本' in sentence:
                        achievement['metric'] = '成本'
                    elif '团队' in sentence or '人数' in sentence or '人员' in sentence:
                        achievement['metric'] = '团队规模'

                achievements.append(achievement)

        return achievements

    def extract_entities(self, text: str) -> Dict:
        """提取命名实体"""
        entities = {
            'companies': [],
            'schools': [],
            'positions': [],
            'skills': [],
            'times': [],
            'locations': [],
            'certifications': []
        }

        company_suffixes = ['公司', '有限公司', '股份有限公司', '集团', '集团有限公司', '科技', '网络科技', '实业']
        for suffix in company_suffixes:
            pattern = r'([\u4e00-\u9fa5A-Z0-9]+)' + suffix
            matches = re.findall(pattern, text)
            for match in matches:
                company_name = match + suffix
                if company_name not in entities['companies'] and len(company_name) > 3:
                    entities['companies'].append(company_name)

        school_suffixes = ['大学', '学院', '学校', '中学', '小学']
        for suffix in school_suffixes:
            pattern = r'([\u4e00-\u9fa5A-Z]+)' + suffix
            matches = re.findall(pattern, text)
            for match in matches:
                school_name = match + suffix
                if school_name not in entities['schools'] and len(school_name) > 2:
                    entities['schools'].append(school_name)

        position_keywords = [
            '总监', '经理', '主管', '主任', '总裁', '副总裁', '总经理', '副总经理',
            '工程师', '架构师', '分析师', '设计师', '研究员', '科学家',
            '董事长', 'CEO', 'COO', 'CFO', 'CTO', 'CMO', 'VP',
            '合伙人', '创始人', '联合创始人',
            '专员', '助理', '秘书', '顾问', '代表',
            '厂长', '车间主任', '班组长',
            '博士', '硕士', '博士后'
        ]
        for keyword in position_keywords:
            pattern = r'([\u4e00-\u9fa5A-Z]{2,8})' + keyword
            matches = re.findall(pattern, text)
            for match in matches:
                position = match + keyword
                if position not in entities['positions'] and len(position) >= 2:
                    entities['positions'].append(position)

        skill_patterns = [
            r'熟悉\s*([\u4e00-\u9fa5A-Z,，、\s]+?)(?:，|。|;|；|$)',
            r'精通\s*([\u4e00-\u9fa5A-Z,，、\s]+?)(?:，|。|;|；|$)',
            r'掌握\s*([\u4e00-\u9fa5A-Z,，、\s]+?)(?:，|。|;|；|$)',
            r'擅长\s*([\u4e00-\u9fa5A-Z,，、\s]+?)(?:，|。|;|；|$)',
        ]
        for pattern in skill_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                skills = re.split(r'[,，、\s]', match)
                for skill in skills:
                    skill = skill.strip()
                    if skill and len(skill) >= 2 and skill not in entities['skills']:
                        entities['skills'].append(skill)

        for pattern, _ in self.time_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    time_str = ''.join(match)
                else:
                    time_str = match
                if time_str not in entities['times']:
                    entities['times'].append(time_str)

        location_keywords = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '西安', '重庆', '天津', '苏州', '青岛', '大连', '厦门', '长沙', '郑州']
        for loc in location_keywords:
            if loc in text and loc not in entities['locations']:
                entities['locations'].append(loc)

        cert_keywords = ['证书', '资格证', '认证', '执照', 'PMP', 'CPA', 'CFA', 'FRM', 'MBA', 'EMBA']
        for cert in cert_keywords:
            pattern = r'([\u4e00-\u9fa5A-Z0-9]{2,20}?)' + cert
            matches = re.findall(pattern, text)
            for match in matches:
                cert_name = match + cert
                if cert_name not in entities['certifications']:
                    entities['certifications'].append(cert_name)

        return entities

    def rate_company(self, company_name: str) -> Tuple[int, str]:
        """对公司进行评级"""
        kb = self.config['company_rating_knowledge_base']

        for rating, info in kb['companies'].items():
            examples = info.get('examples', [])
            for example in examples:
                if example in company_name or company_name in example:
                    return int(rating), f"匹配到已知公司：{example}"

        if any(word in company_name for word in ['500 强', '世界 500', ' Fortune 500']):
            return 5, "包含 500 强关键词"
        elif any(word in company_name for word in ['股份', '上市', '集团', '控股']):
            return 4, "可能为上市公司或大型集团"
        elif any(word in company_name for word in ['科技', '网络', '创新', '创业']):
            return 3, "科技/创新型企业"
        elif '公司' in company_name:
            return 2, "普通公司"
        else:
            return 1, "未知公司"

    def rate_university(self, uni_name: str) -> Tuple[int, str]:
        """对高校进行评级"""
        kb = self.config['company_rating_knowledge_base']

        for rating, examples in kb.get('university_examples', {}).items():
            for example in examples:
                if example in uni_name or uni_name in example:
                    return int(rating), f"匹配到已知高校：{example}"

        if any(word in uni_name for word in ['清华', '北大', '复旦', '上交', '浙大']):
            return 5, "顶尖高校"
        elif '985' in uni_name or '211' in uni_name or '双一流' in uni_name:
            return 4, "985/211/双一流高校"
        elif '大学' in uni_name:
            return 3, "普通本科院校"
        elif '学院' in uni_name:
            return 3, "本科院校"
        elif '职业' in uni_name or '专科' in uni_name:
            return 2, "专科院校"
        else:
            return 1, "未知院校"

    def identify_industry(self, text: str, file_path: str = "") -> str:
        """识别简历所属行业"""
        if file_path:
            path_parts = file_path.replace('\\', '/').split('/')
            for part in path_parts:
                if part in ['人力资源', '品牌', '生产', '电商', '研发', '销售', '电商 2']:
                    if part == '电商 2':
                        return '电商'
                    return part

        if file_path:
            file_name = file_path.split('\\')[-1] if '\\' in file_path else file_path
            for_match = re.search(r'-for\s*([^\uff08]+)', file_name)
            if for_match:
                industry_from_filename = for_match.group(1).strip()
                industry_mapping = {
                    '电商': '电商',
                    '电子商务': '电商',
                    '外贸': '销售',
                    '销售': '销售',
                    '业务': '销售',
                    '品牌': '品牌',
                    '市场': '品牌',
                    '生产': '生产',
                    '厂长': '生产',
                    '研发': '研发',
                    '人力': '人力资源',
                    'HR': '人力资源',
                    'HRD': '人力资源',
                    'HRBP': '人力资源'
                }
                for key, value in industry_mapping.items():
                    if key in industry_from_filename:
                        return value

        for industry, keywords in self.high_priority_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return industry

        industry_scores = {}
        for industry, keywords in self.industry_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            industry_scores[industry] = score

        if industry_scores:
            best_industry = max(industry_scores, key=industry_scores.get)
            if industry_scores[best_industry] > 0:
                return best_industry

        return '未知'

    def parse_resume(self, file_path: str) -> Dict:
        """
        解析完整简历
        自动识别文件类型（PDF、DOCX、DOC、TXT）
        :param file_path: 文件路径
        :return: 结构化简历数据
        """
        text = self.read_file(file_path)

        basic_info = self._extract_basic_info(text, file_path)
        entities = self.extract_entities(text)
        work_experiences = self._extract_work_experiences(text)
        education_experiences = self._extract_education_experiences(text)
        project_experiences = self._extract_project_experiences(text)
        achievements = self.extract_achievements(text)
        industry = self.identify_industry(text, file_path)
        work_duration, gap_periods = self._calculate_work_duration(work_experiences)

        structured_resume = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'industry': industry,
            'basic_info': basic_info,
            'entities': entities,
            'work_experiences': work_experiences,
            'education_experiences': education_experiences,
            'project_experiences': project_experiences,
            'achievements': achievements,
            'work_duration_months': work_duration,
            'gap_periods': gap_periods,
            'company_ratings': self._rate_all_companies(entities['companies']),
            'university_ratings': self._rate_all_universities(entities['schools'])
        }

        return structured_resume

    def _extract_basic_info(self, text: str, file_path: str = "") -> Dict:
        """提取基本信息"""
        info = {}

        name_pattern = r'姓\s*名 [：:\s]+([\u4e00-\u9fa5]{2,4})'
        match = re.search(name_pattern, text)
        info['name'] = match.group(1) if match else None

        if not info['name'] and file_path:
            file_name = file_path.split('\\')[-1] if '\\' in file_path else file_path
            name_from_file = re.search(r'\d{7,8}\s*[-_]\s*([A-Z]{2,4}|[A-Z]先生)', file_name)
            if name_from_file:
                info['name'] = name_from_file.group(1)
            else:
                name_from_file2 = re.search(r'\d{7,8}[-_][^-]+[-_]\s*([A-Z]{2,4})', file_name)
                if name_from_file2:
                    info['name'] = name_from_file2.group(1)
                else:
                    name_from_file3 = re.search(r'推荐 ([A-Z]{2,4})', file_name)
                    if not name_from_file3:
                        name_from_file3 = re.search(r'推荐([A-Z]{2,4})', file_name)
                    if not name_from_file3:
                        name_from_file3 = re.search(r'([A-Z]{2,4}) 负责人', file_name)
                    if name_from_file3:
                        info['name'] = name_from_file3.group(1)

        gender_pattern = r'性\s*别 [：:\s]+([男女])'
        match = re.search(gender_pattern, text)
        info['gender'] = match.group(1) if match else None

        birth_pattern = r'出\s*生\s*(?:日\s*)?[：:\s]*(\d{4})'
        match = re.search(birth_pattern, text)
        info['birth_year'] = int(match.group(1)) if match else None

        origin_pattern = r'籍\s*贯 [：:\s]+([\u4e00-\u9fa5]+)'
        match = re.search(origin_pattern, text)
        info['origin'] = match.group(1) if match else None

        location_pattern = r'现\s*居\s*(?:住\s*)?[：:\s]+([\u4e00-\u9fa5，、\s]+)'
        match = re.search(location_pattern, text)
        info['location'] = match.group(1).strip() if match else None

        marriage_pattern = r'婚\s*姻\s*状\s*况 [：:\s]+([\u4e00-\u9fa5]+)'
        match = re.search(marriage_pattern, text)
        info['marital_status'] = match.group(1) if match else None

        language_pattern = r'语\s*言\s*能\s*力 [：:\s]+([\u4e00-\u9fa5A-Z，、\s]+)'
        match = re.search(language_pattern, text)
        info['languages'] = match.group(1).strip() if match else None

        current_salary_pattern = r'目\s*前\s*薪\s*资 [：:\s]+([\u4e00-\u9fa5A-Z0-9，、\s]+)'
        match = re.search(current_salary_pattern, text)
        info['current_salary'] = match.group(1).strip() if match else None

        expected_salary_pattern = r'期\s*望\s*薪\s*资 [：:\s]+([\u4e00-\u9fa5A-Z0-9，、\s]+)'
        match = re.search(expected_salary_pattern, text)
        info['expected_salary'] = match.group(1).strip() if match else None

        email_match = re.search(self.email_pattern, text)
        info['email'] = email_match.group(0) if email_match else None

        phone_match = re.search(self.phone_pattern, text)
        info['phone'] = phone_match.group(0) if phone_match else None

        return info

    def _extract_work_experiences(self, text: str) -> List[Dict]:
        """提取工作经历"""
        experiences = []

        lines = text.split('\n')

        current_exp = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            time_company_pattern = r'(\d{4}[/\-\u5e74]\d{0,2}[/\-\u6708]?\d{0,2}[\u65e5]?\s*[-–—至]\s*\d{4}[/\-\u5e74]\d{0,2}[/\-\u6708]?\d{0,2}[\u65e5]?|至今 | 当前)[\s\t]+([\u4e00-\u9fa5A-Z0-9()（）]+?)[\s\t]+([总监经理工程师主管主任厂长总裁总经理副总裁董事长专员助理代表分析师设计师研究员科学家博士博士后])'
            match = re.search(time_company_pattern, line)

            if match:
                if current_exp:
                    experiences.append(current_exp)

                current_exp = {
                    'time_period': match.group(1),
                    'company': match.group(2),
                    'position': match.group(3),
                    'responsibilities': [],
                    'achievements': []
                }
            elif current_exp:
                if '职责' in line or '业绩' in line or '工作' in line:
                    continue
                current_exp['responsibilities'].append(line)

        if current_exp:
            experiences.append(current_exp)

        return experiences

    def _extract_education_experiences(self, text: str) -> List[Dict]:
        """提取教育经历"""
        experiences = []

        edu_pattern = r'(\d{4}[/\-\u5e74]\d{0,2}[/\-\u6708]?\d{0,2}[\u65e5]?\s*[-–—]\s*\d{4}[/\-\u5e74]\d{0,2}[/\-\u6708]?\d{0,2}[\u65e5]?)\s+([\u4e00-\u9fa5A-Z]+?(?:大学 | 学院 | 学校))\s+([\u4e00-\u9fa5A-Z]+?(?:工程 | 技术 | 科学 | 管理 | 经济 | 文学 | 法学 | 教育 | 艺术|语言)?)\s+(本科 | 硕士 | 博士 | 大专 | 专科|学士|硕士|博士)'

        matches = re.findall(edu_pattern, text)
        for match in matches:
            experiences.append({
                'time_period': match[0],
                'school': match[1],
                'major': match[2],
                'degree': match[3]
            })

        return experiences

    def _extract_project_experiences(self, text: str) -> List[Dict]:
        """提取项目经验"""
        projects = []

        lines = text.split('\n')
        current_project = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if '项目' in line and ('20' in line or re.search(r'\d{4}', line)):
                if current_project:
                    projects.append(current_project)
                current_project = {
                    'name': line,
                    'time_period': '',
                    'role': '',
                    'description': []
                }
            elif current_project:
                current_project['description'].append(line)

        if current_project:
            projects.append(current_project)

        return projects

    def _calculate_work_duration(self, work_experiences: List[Dict]) -> Tuple[float, List[Dict]]:
        """计算工作时长和空窗期"""
        total_months = 0
        gaps = []

        periods = []
        for exp in work_experiences:
            time_str = exp.get('time_period', '')
            months = self.extract_time_to_months(time_str)
            if months and months > 0:
                total_months += months
                periods.append(months)

        return total_months, gaps

    def _rate_all_companies(self, companies: List[str]) -> List[Dict]:
        """对所有公司进行评级"""
        ratings = []
        for company in companies:
            rating, reason = self.rate_company(company)
            ratings.append({
                'company': company,
                'rating': rating,
                'reason': reason
            })
        return ratings

    def _rate_all_universities(self, universities: List[str]) -> List[Dict]:
        """对所有高校进行评级"""
        ratings = []
        for uni in universities:
            rating, reason = self.rate_university(uni)
            ratings.append({
                'university': uni,
                'rating': rating,
                'reason': reason
            })
        return ratings

    def save_to_json(self, data: Dict, output_path: str):
        """保存为 JSON 文件"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存到：{output_path}")


def batch_parse_resumes(input_dir: str, output_dir: str):
    """批量解析简历"""
    parser = ResumeParser()

    input_path = Path(input_dir)
    docx_files = list(input_path.glob('**/*.docx'))
    pdf_files = list(input_path.glob('**/*.pdf'))
    all_files = docx_files + pdf_files

    print(f"找到 {len(all_files)} 个简历文件")

    all_resumes = []

    for i, file_path in enumerate(all_files, 1):
        print(f"\n处理 [{i}/{len(all_files)}]: {file_path.name}")
        try:
            resume_data = parser.parse_resume(str(file_path))
            all_resumes.append(resume_data)

            output_file = Path(output_dir) / f"{file_path.stem}_parsed.json"
            parser.save_to_json(resume_data, str(output_file))

        except Exception as e:
            print(f"处理失败：{e}")

    summary_file = Path(output_dir) / "all_resumes_summary.json"
    parser.save_to_json(all_resumes, str(summary_file))

    print(f"\n批量处理完成！共处理 {len(all_resumes)} 份简历")


if __name__ == '__main__':
    base_dir = Path(__file__).parent
    input_dir = Path(r"d:\desktop\统计课论文\code\.venv\数据")
    output_dir = base_dir / 'output'

    batch_parse_resumes(str(input_dir), str(output_dir))