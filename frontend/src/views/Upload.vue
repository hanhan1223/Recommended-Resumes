<template>
  <div class="upload-container">
    <el-row :gutter="30">
      <el-col :span="12">
        <el-card class="upload-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="24" color="#2E86AB"><UploadFilled /></el-icon>
              <span>简历上传</span>
            </div>
          </template>

          <el-upload
            class="upload-area"
            drag
            action="/api/resume/upload"
            :data="{ industry: selectedIndustry }"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            accept=".pdf,.docx,.txt"
            multiple
          >
            <el-icon class="el-icon--upload" :size="60"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF、DOCX、TXT 格式，单个文件不超过 10MB
              </div>
            </template>
          </el-upload>

          <div class="upload-options">
            <label>行业分类：</label>
            <el-select v-model="selectedIndustry" placeholder="请选择行业（可选）" clearable>
              <el-option
                v-for="item in store.industries"
                :key="item.code"
                :label="item.name"
                :value="item.code"
              />
            </el-select>
          </div>

          <div class="upload-actions">
            <el-button type="primary" @click="processAllResumes">
              <el-icon><VideoPlay /></el-icon>开始解析
            </el-button>
            <el-button @click="clearUploads">
              <el-icon><Delete /></el-icon>清空列表
            </el-button>
          </div>
        </el-card>

        <!-- 上传历史 -->
        <el-card class="history-card" v-if="uploadHistory.length > 0">
          <template #header>
            <span>📋 上传历史</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="(item, index) in uploadHistory"
              :key="index"
              :type="item.status === 'success' ? 'success' : 'danger'"
              :timestamp="item.time"
            >
              {{ item.filename }}
              <el-tag size="small" :type="item.status === 'success' ? 'success' : 'danger'">
                {{ item.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <!-- 解析结果展示 -->
        <el-card class="result-card" v-if="parsedResults.length > 0">
          <template #header>
            <div class="card-header">
              <span>✅ 解析结果</span>
              <el-button type="primary" link @click="goToRanking(selectedIndustry || '电商')">
                查看排名 <el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
          </template>
          
          <el-table :data="parsedResults" stripe style="width: 100%">
            <el-table-column prop="filename" label="文件名" min-width="180" />
            <el-table-column prop="industry" label="识别行业" width="120">
              <template #default="{ row }">
                <el-tag type="info" size="small">{{ row.industry }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" align="center">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="viewParsedDetail(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="result-actions">
            <el-alert
              title="查看路径说明"
              type="info"
              :closable="false"
              show-icon
            >
              <p>📍 解析完成后，您可以：</p>
              <ul>
                <li>点击<strong>"查看详情"</strong>查看当前简历的详细解析结果</li>
                <li>点击<strong>"查看排名"</strong>进入排名看板，查看该行业内所有候选人排名</li>
                <li>进入<strong>"排名看板"</strong>页面，选择对应行业查看解析后的候选人列表</li>
              </ul>
            </el-alert>
          </div>
        </el-card>

        <!-- 解析详情弹窗 -->
        <el-dialog
          v-model="currentParsedResume"
          title="简历解析详情"
          width="700px"
          v-if="currentParsedResume"
        >
          <div class="parsed-detail">
            <h4>📄 {{ currentParsedResume.filename }}</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="识别行业">{{ currentParsedResume.industry }}</el-descriptions-item>
              <el-descriptions-item label="解析时间">{{ new Date().toLocaleString() }}</el-descriptions-item>
            </el-descriptions>
            
            <div class="detail-actions">
              <el-button type="primary" @click="goToRanking(currentParsedResume.industry)">
                查看该行业排名
              </el-button>
              <el-button @click="closeDetail">关闭</el-button>
            </div>
          </div>
        </el-dialog>
      </el-col>

      <el-col :span="12">
        <el-card class="guide-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="24" color="#2E86AB"><InfoFilled /></el-icon>
              <span>上传指南</span>
            </div>
          </template>

          <div class="guide-content">
            <h4>📄 支持的文件格式</h4>
            <ul>
              <li><strong>PDF</strong> - 推荐使用，格式稳定</li>
              <li><strong>DOCX</strong> - Word文档格式</li>
              <li><strong>TXT</strong> - 纯文本格式</li>
            </ul>

            <h4>📝 简历内容建议</h4>
            <ul>
              <li>包含完整的个人信息（姓名、联系方式）</li>
              <li>详细的教育背景（学历、学校、专业）</li>
              <li>完整的工作经历（公司、职位、时间）</li>
              <li>明确的技能列表和证书</li>
              <li>具体的项目经验和成果</li>
            </ul>

            <h4>⚡ 解析流程</h4>
            <el-steps direction="vertical" :active="3">
              <el-step title="上传文件" description="选择简历文件上传" />
              <el-step title="文本提取" description="自动提取简历内容" />
              <el-step title="智能解析" description="NLP识别关键信息" />
              <el-step title="维度评分" description="计算TCI综合得分" />
            </el-steps>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useResumeStore } from '@/stores'
import { ElMessage } from 'element-plus'

const store = useResumeStore()
const router = useRouter()

const selectedIndustry = ref('')
const uploadHistory = ref([])

const beforeUpload = (file) => {
  const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
  const isAllowed = allowedTypes.includes(file.type) || file.name.endsWith('.docx') || file.name.endsWith('.pdf') || file.name.endsWith('.txt')
  
  if (!isAllowed) {
    ElMessage.error('不支持的文件格式，请上传 PDF、DOCX 或 TXT 文件')
    return false
  }
  
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB')
    return false
  }
  
  return true
}

const handleUploadSuccess = (response, file) => {
  // 保存文件路径供后续解析使用
  const filepath = response?.data?.filepath || file.raw?.path || file.name
  
  uploadHistory.value.unshift({
    filename: file.name,
    filepath: filepath,
    status: 'success',
    time: new Date().toLocaleString(),
    industry: selectedIndustry.value
  })
  ElMessage.success(`${file.name} 上传成功`)
}

const handleUploadError = (error, file) => {
  uploadHistory.value.unshift({
    filename: file.name,
    status: 'error',
    time: new Date().toLocaleString()
  })
  ElMessage.error(`${file.name} 上传失败`)
}

const parsedResults = ref([])
const currentParsedResume = ref(null)

const processAllResumes = async () => {
  if (uploadHistory.value.length === 0) {
    ElMessage.warning('请先上传简历文件')
    return
  }
  
  ElMessage.info('正在解析简历，请稍候...')
  parsedResults.value = [] // 清空之前的结果
  
  const successItems = uploadHistory.value.filter(h => h.status === 'success')
  let successCount = 0
  let failCount = 0
  
  for (const item of successItems) {
    try {
      if (!item.filepath) {
        console.error('文件路径缺失:', item)
        failCount++
        continue
      }
      
      // 调用解析API，传递用户选择的行业
      const industryToUse = item.industry || selectedIndustry.value
      const response = await store.parseResume(item.filepath, industryToUse)
      
      if (response && response.status === 'success' && response.data) {
        // 优先使用解析结果，其次是用户选择，最后是默认
        const finalIndustry = response.data.industry || industryToUse || '未知'
        parsedResults.value.push({
          filename: item.filename,
          parsedData: response.data,
          industry: finalIndustry
        })
        successCount++
        console.log('[OK] 解析成功: ' + item.filename + ' -> 行业: ' + finalIndustry)
      } else {
        console.error('解析返回无效数据:', response)
        failCount++
      }
    } catch (error) {
      console.error('[ERROR] 解析失败 ' + item.filename + ':', error)
      failCount++
    }
  }
  
  if (successCount > 0) {
    ElMessage.success(`简历解析完成：成功 ${successCount} 份，失败 ${failCount} 份`)
    
    // 如果有解析结果，提示用户可以查看排名
    if (parsedResults.value.length > 0) {
      const industries = [...new Set(parsedResults.value.map(r => r.industry))]
      ElMessage.info(`已识别行业: ${industries.join(', ')}，可点击"查看排名"查看结果`)
    }
  } else {
    ElMessage.error('简历解析失败，请检查后端服务是否正常')
  }
}

const viewParsedDetail = (result) => {
  currentParsedResume.value = result
}

const closeDetail = () => {
  currentParsedResume.value = null
}

const goToRanking = (industry) => {
  if (!industry || industry === '未知') {
    ElMessage.warning('无法确定行业，请确保简历解析成功')
    return
  }
  
  console.log('[NAV] 跳转到排名页面，行业: ' + industry)
  router.push({
    path: '/ranking',
    query: { industry: industry }
  })
}

const clearUploads = () => {
  uploadHistory.value = []
  ElMessage.success('上传列表已清空')
}

onMounted(() => {
  store.fetchIndustries()
})
</script>

<style scoped>
.upload-container {
  max-width: 1400px;
  margin: 0 auto;
}

.upload-card, .guide-card, .history-card {
  border-radius: 12px;
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 16px;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  padding: 40px 20px;
  border: 2px dashed #2E86AB;
  border-radius: 12px;
  background: #f8f9fa;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: #4ECDC4;
  background: #f0f7ff;
}

.upload-options {
  margin-top: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
}

.upload-options label {
  font-weight: 500;
  margin-right: 10px;
  color: #666;
}

.upload-actions {
  margin-top: 20px;
  text-align: center;
}

.guide-content h4 {
  color: #2E86AB;
  margin: 20px 0 10px;
  font-size: 15px;
}

.guide-content ul {
  padding-left: 20px;
  color: #666;
  line-height: 1.8;
}

.guide-content li {
  margin-bottom: 5px;
}

.result-card {
  border-radius: 12px;
  margin-top: 20px;
}

.result-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-actions {
  margin-top: 20px;
}

.result-actions ul {
  margin: 10px 0 0 20px;
  padding: 0;
}

.result-actions li {
  margin-bottom: 8px;
  line-height: 1.6;
}

.parsed-detail h4 {
  margin-bottom: 20px;
  color: #2E86AB;
}

.detail-actions {
  margin-top: 20px;
  text-align: center;
}
</style>
