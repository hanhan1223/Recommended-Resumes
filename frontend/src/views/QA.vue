<template>
  <div class="qa-container">
    <el-row :gutter="30">
      <!-- 左侧问答区 -->
      <el-col :span="16">
        <el-card class="chat-card">
          <template #header>
            <div class="chat-header">
              <el-icon :size="24" color="#2E86AB"><ChatDotRound /></el-icon>
              <span>智能问答助手</span>
              <el-tag :type="llmEnabled ? 'success' : 'warning'" size="small">
                {{ llmEnabled ? 'Qwen LLM' : 'Template' }}
              </el-tag>
            </div>
          </template>

          <!-- 对话区域 -->
          <div class="chat-messages" ref="chatContainer">
            <div 
              v-for="(msg, index) in messages" 
              :key="index"
              class="message"
              :class="msg.type"
            >
              <div class="message-avatar">
                <el-avatar 
                  :size="40" 
                  :icon="msg.type === 'user' ? UserFilled : Service"
                  :style="{ background: msg.type === 'user' ? '#409EFF' : '#2E86AB' }"
                />
              </div>
              <div class="message-content">
                <div class="message-text" v-html="formatMessage(msg.content)"></div>
                <div class="message-time">{{ msg.time }}</div>
              </div>
            </div>
            
            <!-- 加载状态 -->
            <div v-if="loading" class="message assistant">
              <div class="message-avatar">
                <el-avatar :size="40" :icon="Service" style="background: #2E86AB" />
              </div>
              <div class="message-content">
                <el-skeleton :rows="2" animated />
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="chat-input">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="2"
              placeholder="请输入您的问题，例如：排名多少？得分如何？有什么优势？是否推荐？"
              @keyup.enter="sendMessage"
            />
            <el-button 
              type="primary" 
              @click="sendMessage"
              :loading="loading"
              :disabled="!inputMessage.trim()"
            >
              <el-icon><Promotion /></el-icon>发送
            </el-button>
          </div>
        </el-card>

        <!-- 快捷问题 -->
        <el-card class="quick-questions" shadow="never">
          <template #header>
            <span>💡 快捷问题</span>
          </template>
          <div class="question-tags">
            <el-tag
              v-for="q in quickQuestions"
              :key="q"
              class="question-tag"
              effect="plain"
              @click="quickAsk(q)"
            >
              {{ q }}
            </el-tag>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧信息区 -->
      <el-col :span="8">
        <!-- 行业选择 -->
        <el-card class="info-card">
          <template #header>
            <span>🏢 选择行业</span>
          </template>
          <el-select
            v-model="selectedIndustry"
            placeholder="请选择行业"
            style="width: 100%"
            @change="onIndustryChange"
          >
            <el-option
              v-for="item in store.industries"
              :key="item.code"
              :label="item.name"
              :value="item.code"
            />
          </el-select>
        </el-card>

        <!-- 候选人选择 -->
        <el-card class="info-card">
          <template #header>
            <span>👤 选择候选人</span>
          </template>
          <el-select
            v-model="selectedCandidate"
            placeholder="请先选择行业"
            style="width: 100%"
            :disabled="!selectedIndustry"
            @change="onCandidateChange"
          >
            <el-option
              v-for="c in store.rankings"
              :key="c.candidate_id"
              :label="`${c.candidate_id} (TCI: ${formatScore(c.tci_score)})`"
              :value="c.candidate_id"
            />
          </el-select>
        </el-card>

        <!-- 候选人信息 -->
        <el-card class="info-card" v-if="currentCandidate">
          <template #header>
            <span>📊 候选人信息</span>
          </template>
          <div class="candidate-info">
            <div class="info-item">
              <label>TCI综合得分：</label>
              <span class="score">{{ formatScore(currentCandidate.tci_score) }}</span>
            </div>
            <div class="info-item">
              <label>当前排名：</label>
              <span class="rank">第 {{ currentCandidate.rank }} 名</span>
            </div>
            <div class="info-item">
              <label>跳槽惩罚：</label>
              <el-tag :type="currentCandidate.penalty_applied ? 'danger' : 'success'" size="small">
                {{ currentCandidate.penalty_applied ? '已触发' : '未触发' }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <!-- 问答提示 -->
        <el-card class="info-card">
          <template #header>
            <span>❓ 可以问什么</span>
          </template>
          <ul class="qa-tips">
            <li>排名情况和位次</li>
            <li>TCI综合得分详情</li>
            <li>各维度得分分析</li>
            <li>优势和亮点</li>
            <li>风险和注意事项</li>
            <li>录用推荐建议</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useResumeStore } from '@/stores'
import { ElMessage } from 'element-plus'
import { formatScore } from '@/utils/format'

const store = useResumeStore()

const messages = ref([
  {
    type: 'assistant',
    content: '您好！我是智能问答助手，可以帮您分析候选人的评分情况、排名信息、优势和风险等。请先选择一位候选人，然后向我提问吧！',
    time: new Date().toLocaleTimeString()
  }
])

const inputMessage = ref('')
const loading = ref(false)
const selectedCandidate = ref('')
const selectedIndustry = ref('')
const chatContainer = ref(null)

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const llmEnabled = ref(false)

const checkLLMStatus = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/llm/status`)
    const data = await response.json()
    llmEnabled.value = data.enabled
  } catch {
    llmEnabled.value = false
  }
}

const quickQuestions = [
  '排名多少？',
  '得分如何？',
  '有什么优势？',
  '有什么风险？',
  '是否推荐录用？',
  '工作稳定性如何？'
]

const currentCandidate = computed(() => {
  if (!selectedCandidate.value) return null

  const candidateId = selectedCandidate.value
  const rankIndex = store.rankings.findIndex(r => r.candidate_id === candidateId)
  const candidate = rankIndex >= 0 ? store.rankings[rankIndex] : null

  if (!candidate) return null

  const detail = store.candidates.find(c => c.candidate_id === candidateId)

  return {
    ...candidate,
    rank: rankIndex >= 0 ? rankIndex + 1 : 'N/A',
    dimensional_scores: detail?.dimensional_scores || candidate.dimensional_scores || {},
    dimension_weights: detail?.dimension_weights || candidate.dimension_weights || {}
  }
})

const formatMessage = (content) => {
  if (!content) return ''

  let html = content
    .replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/^## (.+)$/gm, '<h3 style="margin: 10px 0 5px; color: #2E86AB;">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 style="margin: 10px 0 5px; color: #2E86AB;">$1</h2>')
    .replace(/^---$/gm, '<hr style="border: none; border-top: 1px solid #eee; margin: 10px 0;">')
    .replace(/✅/g, '<span style="color: #67C23A;">✅</span>')
    .replace(/⚠️/g, '<span style="color: #E6A23C;">⚠️</span>')
    .replace(/❌/g, '<span style="color: #F56C6C;">❌</span>')
    .replace(/⭐/g, '<span style="color: #FFD700;">⭐</span>')
    .replace(/\n/g, '<br>')
    .replace(/<br><ul>/g, '<ul>')
    .replace(/<\/ul><br>/g, '</ul>')

  return html
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return
  
  const userMsg = inputMessage.value.trim()
  messages.value.push({
    type: 'user',
    content: userMsg,
    time: new Date().toLocaleTimeString()
  })
  
  inputMessage.value = ''
  loading.value = true
  await scrollToBottom()
  
  try {
    // 构建上下文
    const context = currentCandidate.value ? {
      candidate_id: currentCandidate.value.candidate_id,
      industry: selectedIndustry.value,
      rank: currentCandidate.value.rank,
      tci_score: currentCandidate.value.tci_score,
      penalty_applied: currentCandidate.value.penalty_applied,
      dimensional_scores: currentCandidate.value.dimensional_scores,
      dimension_weights: currentCandidate.value.dimension_weights
    } : {}

    const response = await store.askQuestion(userMsg, context)
    
    messages.value.push({
      type: 'assistant',
      content: response.answer || response.data?.answer || '抱歉，我暂时无法回答这个问题。',
      time: new Date().toLocaleTimeString()
    })
  } catch (err) {
    messages.value.push({
      type: 'assistant',
      content: '抱歉，系统出现错误，请稍后重试。',
      time: new Date().toLocaleTimeString()
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const quickAsk = (question) => {
  inputMessage.value = question
  sendMessage()
}

const onCandidateChange = () => {
  if (currentCandidate.value) {
    messages.value.push({
      type: 'assistant',
      content: `已选择候选人：${currentCandidate.value.candidate_id}。您可以询问关于该候选人的排名、得分、优势、风险等问题。`,
      time: new Date().toLocaleTimeString()
    })
    scrollToBottom()
  }
}

const onIndustryChange = async () => {
  selectedCandidate.value = ''
  if (selectedIndustry.value) {
    await store.fetchRankings(selectedIndustry.value, 20)
    await store.batchScore(selectedIndustry.value)
  }
}

onMounted(() => {
  // 检查LLM状态
  checkLLMStatus()
})
</script>

<style scoped>
.qa-container {
  max-width: 1400px;
  margin: 0 auto;
}

.chat-card {
  border-radius: 12px;
  height: calc(100vh - 250px);
  display: flex;
  flex-direction: column;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 16px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 15px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.message.user .message-content {
  background: #2E86AB;
  color: #fff;
}

.message-text {
  line-height: 1.6;
  font-size: 14px;
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 5px;
}

.message.user .message-time {
  color: rgba(255,255,255,0.7);
}

.chat-input {
  display: flex;
  gap: 10px;
}

.chat-input .el-textarea {
  flex: 1;
}

.quick-questions {
  margin-top: 20px;
  border-radius: 12px;
}

.question-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.question-tag {
  cursor: pointer;
  transition: all 0.3s;
}

.question-tag:hover {
  background: #2E86AB;
  color: #fff;
}

.info-card {
  border-radius: 12px;
  margin-bottom: 20px;
}

.candidate-info {
  padding: 10px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item label {
  color: #666;
}

.info-item .score {
  font-size: 24px;
  font-weight: bold;
  color: #2E86AB;
}

.info-item .rank {
  font-size: 18px;
  font-weight: bold;
  color: #E6A23C;
}

.qa-tips {
  list-style: none;
  padding: 0;
}

.qa-tips li {
  padding: 8px 0;
  color: #666;
  border-bottom: 1px dashed #eee;
}

.qa-tips li::before {
  content: '•';
  color: #2E86AB;
  font-weight: bold;
  margin-right: 8px;
}

.qa-tips li:last-child {
  border-bottom: none;
}
</style>
