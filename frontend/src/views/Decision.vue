<template>
  <div class="decision-page">
    <h1 class="page-title">决策报告</h1>

    <!-- Filters -->
    <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <div class="filter-item">
            <label class="filter-label">行业</label>
            <el-select v-model="selectedIndustry" placeholder="全部行业" @change="onIndustryChange" style="width: 100%">
              <el-option value="" label="全部行业" />
              <el-option v-for="ind in industries" :key="ind.code" :label="ind.name" :value="ind.code" />
            </el-select>
          </div>
        </el-col>
        <el-col :span="10">
          <span class="hint-text">选择候选人生成决策报告</span>
        </el-col>
        <el-col :span="6" style="text-align: right">
          <el-button type="primary" @click="generateDecision" :disabled="!selectedCandidate" :loading="loading">
            生成报告
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- Candidate Selection -->
    <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
      <div class="section-header">
        <span class="section-title">选择候选人</span>
      </div>
      <el-row :gutter="12">
        <el-col :span="4" v-for="c in availableCandidates" :key="c.id">
          <div class="candidate-pick" :class="{ selected: selectedCandidate === c.id }" @click="selectCandidate(c.id)">
            <div class="pick-name">{{ c.name }}</div>
            <div class="pick-score">TCI: {{ c.tci_score?.toFixed(2) || '-' }}</div>
            <div class="pick-rank">排名 #{{ c.rank }}</div>
          </div>
        </el-col>
      </el-row>
      <el-empty v-if="availableCandidates.length === 0" description="暂无候选人数据" />
    </div>

    <!-- Decision Report -->
    <template v-if="decisionData">
      <!-- Overview -->
      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="decision-header">
          <span class="candidate-name">{{ decisionData.candidate_name }}</span>
          <el-tag :type="getDecisionType(decisionData.decision)" effect="dark" size="large">
            {{ decisionData.decision }}
          </el-tag>
        </div>
        <el-row :gutter="16" style="margin-top: var(--space-md)">
          <el-col :span="12">
            <div class="metric-box">
              <span class="metric-label">置信度</span>
              <span class="metric-value">{{ decisionData.confidence }}</span>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="metric-box">
              <span class="metric-label">综合得分</span>
              <span class="metric-value">{{ decisionData.overall_score }}</span>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- Executive Summary -->
      <el-row :gutter="16" style="margin-bottom: var(--space-md)">
        <el-col :span="12">
          <div class="card summary-card risk-card">
            <div class="summary-title">风险评估</div>
            <p class="summary-text">{{ decisionData.executive_summary.risk_summary }}</p>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="card summary-card opportunity-card">
            <div class="summary-title">机会评估</div>
            <p class="summary-text">{{ decisionData.executive_summary.opportunity_summary }}</p>
          </div>
        </el-col>
      </el-row>

      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="final-recommendation">
          <div class="final-title">最终推荐</div>
          <p class="final-text">{{ decisionData.executive_summary.final_recommendation }}</p>
        </div>
      </div>

      <!-- Key Factors -->
      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="section-header">
          <span class="section-title">关键决策因素</span>
        </div>
        <el-row :gutter="12">
          <el-col :span="12" v-for="(factor, i) in decisionData.key_factors" :key="i">
            <div class="factor-card" :class="`factor-${getFactorClass(factor.type)}`">
              <div class="factor-header">
                <span class="factor-type">{{ factor.type }}</span>
                <span class="factor-weight">权重: {{ factor.weight }}</span>
              </div>
              <p class="factor-desc">{{ factor.description }}</p>
              <div v-if="factor.evidence?.length" class="factor-evidence">
                <span class="evidence-label">依据:</span>
                <ul><li v-for="(e, j) in factor.evidence" :key="j">{{ e }}</li></ul>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- Action Items -->
      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="section-header">
          <span class="section-title">行动建议</span>
        </div>
        <el-row :gutter="16">
          <el-col :span="12">
            <div class="action-block">
              <div class="action-title">建议行动</div>
              <ul class="action-list">
                <li v-for="(action, i) in decisionData.action_items.suggested_actions" :key="i">{{ action }}</li>
              </ul>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="action-block">
              <div class="action-title">面试重点</div>
              <ul class="action-list">
                <li v-for="(focus, i) in decisionData.action_items.interview_focus" :key="i">{{ focus }}</li>
              </ul>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- Export -->
      <div style="text-align: center; padding: var(--space-md)">
        <el-button type="success" @click="exportReport('json')">导出JSON</el-button>
        <el-button type="primary" @click="exportReport('pdf')">导出PDF</el-button>
      </div>
    </template>

    <!-- Loading -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="loading-icon" :size="40"><Loading /></el-icon>
      <p>正在生成决策报告...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import axios from 'axios'

const availableCandidates = ref([])
const selectedCandidate = ref(null)
const decisionData = ref(null)
const loading = ref(false)
const industries = ref([])
const selectedIndustry = ref('')

const fetchIndustries = async () => {
  try {
    const res = await axios.get('/api/industries')
    if (res.data.status === 'success') industries.value = res.data.industries
  } catch (e) { console.error('获取行业列表失败:', e) }
}

const fetchCandidates = async () => {
  try {
    const params = selectedIndustry.value ? { industry: selectedIndustry.value } : {}
    const res = await axios.get('/api/comparison/available-candidates', { params })
    if (res.data.status === 'success') {
      availableCandidates.value = res.data.candidates
      selectedCandidate.value = null
      decisionData.value = null
    }
  } catch (e) { ElMessage.error('获取候选人列表失败') }
}

const onIndustryChange = () => fetchCandidates()
const selectCandidate = (id) => { selectedCandidate.value = id; decisionData.value = null }

const generateDecision = async () => {
  if (!selectedCandidate.value) { ElMessage.warning('请选择候选人'); return }
  loading.value = true
  try {
    const res = await axios.post('/api/decision/summary', { resume_id: selectedCandidate.value, job_requirements: null })
    if (res.data.status === 'success') decisionData.value = res.data.decision_summary
  } catch (e) { ElMessage.error('生成决策报告失败: ' + (e.response?.data?.detail || '未知错误')) }
  finally { loading.value = false }
}

const getDecisionType = (decision) => {
  const map = { '强烈推荐': 'success', '推荐': 'primary', '可以考虑': 'warning', '不推荐': 'danger' }
  return map[decision] || 'info'
}

const getFactorClass = (type) => {
  const map = { '优势': 'advantage', '劣势': 'disadvantage', '风险': 'risk', '机会': 'opportunity' }
  return map[type] || 'other'
}

const exportReport = async (format) => {
  try {
    const res = await axios.post('/api/report/export', { report_type: 'decision', data: decisionData.value, format })
    if (res.data.status === 'success') {
      let blob
      if (format === 'json') blob = new Blob([JSON.stringify(res.data.data, null, 2)], { type: 'application/json' })
      else {
        const bytes = atob(res.data.data)
        const arr = new Uint8Array(bytes.length)
        for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i)
        blob = new Blob([arr], { type: format === 'pdf' ? 'application/pdf' : 'application/octet-stream' })
      }
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url; link.download = res.data.filename; link.click()
      URL.revokeObjectURL(url)
      ElMessage.success('导出成功')
    }
  } catch (e) { ElMessage.error('导出失败') }
}

onMounted(() => { fetchIndustries(); fetchCandidates() })
</script>

<style scoped>
.decision-page {
  max-width: 1200px;
  margin: 0 auto;
  position: relative;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-lg);
}

.filter-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.filter-label {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.hint-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.section-header {
  margin-bottom: var(--space-md);
}

.section-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.candidate-pick {
  background: var(--color-bg-card);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: var(--space-sm);
  text-align: center;
}

.candidate-pick:hover {
  border-color: var(--color-primary-lighter);
}

.candidate-pick.selected {
  border-color: var(--color-success);
  background: var(--color-success-bg);
}

.pick-name {
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.pick-score {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
}

.pick-rank {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.decision-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.candidate-name {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.metric-box {
  text-align: center;
  padding: var(--space-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
}

.metric-label {
  display: block;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--space-xs);
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-primary);
}

.summary-card {
  padding: var(--space-lg);
  height: 100%;
}

.summary-card.risk-card {
  border-left: 4px solid var(--color-danger);
}

.summary-card.opportunity-card {
  border-left: 4px solid var(--color-success);
}

.summary-title {
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-sm);
}

.summary-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin: 0;
}

.final-recommendation {
  background: var(--color-primary-bg);
  padding: var(--space-lg);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-primary);
}

.final-title {
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: var(--space-sm);
}

.final-text {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  line-height: 1.7;
  margin: 0;
}

.factor-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  margin-bottom: var(--space-sm);
  border-left: 4px solid var(--color-border);
}

.factor-card.factor-advantage { border-left-color: var(--color-success); }
.factor-card.factor-disadvantage { border-left-color: var(--color-warning); }
.factor-card.factor-risk { border-left-color: var(--color-danger); }
.factor-card.factor-opportunity { border-left-color: var(--color-primary); }

.factor-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
}

.factor-type {
  font-weight: 600;
  color: var(--color-text-primary);
}

.factor-weight {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.factor-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-sm);
}

.evidence-label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-primary);
}

.factor-evidence ul {
  margin: 4px 0 0;
  padding-left: 16px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.action-block {
  background: var(--color-bg-hover);
  padding: var(--space-md);
  border-radius: var(--radius-md);
}

.action-title {
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-sm);
}

.action-list {
  margin: 0;
  padding-left: 16px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.action-list li {
  margin-bottom: var(--space-xs);
}

.loading-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  color: #fff;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
