<template>
  <div class="recommendation-page">
    <h1 class="page-title">多方案推荐</h1>

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
          <span class="hint-text">选择2-10位候选人生成推荐方案</span>
        </el-col>
        <el-col :span="6" style="text-align: right">
          <el-button type="primary" @click="generateRecommendations" :disabled="selectedCandidates.length < 2" :loading="loading">
            生成方案
          </el-button>
          <el-button @click="clearSelection">清空</el-button>
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
          <div class="candidate-pick" :class="{ selected: selectedCandidates.includes(c.id) }" @click="toggleCandidate(c.id)">
            <div class="pick-name">{{ c.name }}</div>
            <div class="pick-score">TCI: {{ c.tci_score?.toFixed(2) || '-' }}</div>
          </div>
        </el-col>
      </el-row>
      <el-empty v-if="availableCandidates.length === 0" description="暂无候选人数据" />
    </div>

    <!-- Job Requirements -->
    <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
      <div class="section-header">
        <span class="section-title">岗位要求</span>
      </div>
      <el-row :gutter="16">
        <el-col :span="8">
          <div class="form-item">
            <label class="form-label">岗位名称</label>
            <el-input v-model="jobRequirements.title" placeholder="请输入岗位名称" />
          </div>
        </el-col>
        <el-col :span="10">
          <div class="form-item">
            <label class="form-label">所需技能 (逗号分隔)</label>
            <el-input v-model="skillsInput" placeholder="例如: Python, 数据分析, 团队管理" />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="form-item">
            <label class="form-label">招聘人数</label>
            <el-input-number v-model="jobRequirements.hire_count" :min="1" :max="5" style="width: 100%" />
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Results -->
    <template v-if="recommendationData">
      <!-- Summary Cards -->
      <el-row :gutter="16" style="margin-bottom: var(--space-md)">
        <el-col :span="8">
          <div class="card summary-card">
            <div class="summary-label">总方案数</div>
            <div class="summary-value">{{ recommendationData.recommendation_summary.total_plans }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="card summary-card">
            <div class="summary-label">首推方案</div>
            <div class="summary-value text-success">{{ recommendationData.recommendation_summary.top_recommendation.plan_name }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="card summary-card">
            <div class="summary-label">预期表现</div>
            <div class="summary-value">{{ recommendationData.recommendation_summary.top_recommendation.expected_performance.toFixed(2) }}</div>
          </div>
        </el-col>
      </el-row>

      <!-- Comparison Table -->
      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="section-header">
          <span class="section-title">方案对比</span>
        </div>
        <el-table :data="recommendationData.recommendation_summary.comparison_table" stripe>
          <el-table-column prop="方案" label="方案" width="120">
            <template #default="{ row }"><strong>{{ row.方案 }}</strong></template>
          </el-table-column>
          <el-table-column prop="策略" label="策略" />
          <el-table-column label="风险等级" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.风险等级 === '高' ? 'danger' : row.风险等级 === '中' ? 'warning' : 'success'" size="small">
                {{ row.风险等级 }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="预期表现" width="100" align="center">
            <template #default="{ row }"><span class="score-highlight">{{ row.预期表现.toFixed(2) }}</span></template>
          </el-table-column>
          <el-table-column prop="推荐人数" label="人数" width="80" align="center" />
          <el-table-column label="互补性" width="100" align="center">
            <template #default="{ row }">{{ row.团队互补性 }}%</template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Plan Cards -->
      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="section-header">
          <span class="section-title">详细方案</span>
        </div>
        <el-row :gutter="16">
          <el-col :span="12" v-for="plan in recommendationData.plans" :key="plan.plan_id">
            <div class="plan-card" :class="{ 'top-plan': plan.plan_id === 'plan_balanced' }">
              <div class="plan-header">
                <span class="plan-name">{{ plan.name }}</span>
                <el-tag :type="plan.risk_level === '高' ? 'danger' : plan.risk_level === '中' ? 'warning' : 'success'" size="small">
                  {{ plan.risk_level }}风险
                </el-tag>
              </div>
              <p class="plan-desc">{{ plan.description }}</p>
              <div class="plan-metrics">
                <div class="metric">
                  <span class="metric-label">预期表现</span>
                  <span class="metric-value">{{ plan.expected_performance.toFixed(2) }}</span>
                </div>
                <div class="metric">
                  <span class="metric-label">互补性</span>
                  <span class="metric-value">{{ plan.team_complementarity }}%</span>
                </div>
              </div>
              <div class="plan-candidates">
                <span class="candidates-label">推荐:</span>
                <el-tag v-for="c in plan.recommended_candidates" :key="c.candidate_id" size="small" class="candidate-tag">
                  {{ c.name }} ({{ c.tci_score.toFixed(2) }})
                </el-tag>
              </div>
              <div v-if="plan.backup_candidates?.length" class="plan-candidates">
                <span class="candidates-label">备选:</span>
                <el-tag v-for="c in plan.backup_candidates" :key="c.candidate_id" size="small" type="info">
                  {{ c.name }}
                </el-tag>
              </div>
              <div class="pros-cons">
                <div class="pros">
                  <span class="pros-label">优点:</span>
                  <ul><li v-for="(p, i) in plan.pros" :key="i">{{ p }}</li></ul>
                </div>
                <div class="cons">
                  <span class="cons-label">缺点:</span>
                  <ul><li v-for="(c, i) in plan.cons" :key="i">{{ c }}</li></ul>
                </div>
              </div>
              <div v-if="plan.suitable_scenarios?.length" class="scenarios">
                <span class="scenarios-label">适用场景:</span>
                <el-tag v-for="(s, i) in plan.suitable_scenarios" :key="i" type="info" size="small" effect="plain">{{ s }}</el-tag>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- Export -->
      <div style="text-align: center; padding: var(--space-md)">
        <el-button type="success" @click="exportReport('json')">导出JSON</el-button>
        <el-button type="primary" @click="exportReport('excel')">导出Excel</el-button>
      </div>
    </template>

    <!-- Loading -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="loading-icon" :size="40"><Loading /></el-icon>
      <p>正在生成推荐方案...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import axios from 'axios'

const availableCandidates = ref([])
const selectedCandidates = ref([])
const recommendationData = ref(null)
const loading = ref(false)
const industries = ref([])
const selectedIndustry = ref('')
const jobRequirements = ref({ title: '', skills: [], hire_count: 1 })
const skillsInput = ref('')

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
      selectedCandidates.value = []
      recommendationData.value = null
    }
  } catch (e) { ElMessage.error('获取候选人列表失败') }
}

const onIndustryChange = () => fetchCandidates()

const toggleCandidate = (id) => {
  const idx = selectedCandidates.value.indexOf(id)
  if (idx > -1) selectedCandidates.value.splice(idx, 1)
  else if (selectedCandidates.value.length < 10) selectedCandidates.value.push(id)
  else ElMessage.warning('最多选择10位候选人')
}

const clearSelection = () => {
  selectedCandidates.value = []
  recommendationData.value = null
  jobRequirements.value = { title: '', skills: [], hire_count: 1 }
  skillsInput.value = ''
}

const generateRecommendations = async () => {
  if (selectedCandidates.value.length < 2) { ElMessage.warning('请至少选择2位候选人'); return }
  if (skillsInput.value) jobRequirements.value.skills = skillsInput.value.split(',').map(s => s.trim()).filter(s => s)
  loading.value = true
  try {
    const res = await axios.post('/api/recommendation/plans', {
      resume_ids: selectedCandidates.value,
      job_requirements: jobRequirements.value,
      team_config: null
    })
    if (res.data.status === 'success') recommendationData.value = res.data
  } catch (e) { ElMessage.error('生成推荐方案失败: ' + (e.response?.data?.detail || '未知错误')) }
  finally { loading.value = false }
}

const exportReport = async (format) => {
  try {
    const res = await axios.post('/api/report/export', { report_type: 'recommendation', data: recommendationData.value, format })
    if (res.data.status === 'success') {
      let blob
      if (format === 'json') blob = new Blob([JSON.stringify(res.data.data, null, 2)], { type: 'application/json' })
      else {
        const bytes = atob(res.data.data)
        const arr = new Uint8Array(bytes.length)
        for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i)
        blob = new Blob([arr], { type: format === 'excel' ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'application/pdf' })
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
.recommendation-page {
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

.form-item {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xs);
}

.summary-card {
  padding: var(--space-lg);
  text-align: center;
}

.summary-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--space-xs);
}

.summary-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-primary);
}

.text-success {
  color: var(--color-success) !important;
  font-size: 18px !important;
}

.score-highlight {
  font-weight: 700;
  color: var(--color-primary);
}

.plan-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  margin-bottom: var(--space-md);
}

.plan-card.top-plan {
  border: 2px solid var(--color-warning);
  box-shadow: 0 0 0 1px var(--color-warning-bg);
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
}

.plan-name {
  font-weight: 700;
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.plan-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-md);
  line-height: 1.6;
}

.plan-metrics {
  display: flex;
  gap: var(--space-lg);
  margin-bottom: var(--space-md);
}

.metric {
  text-align: center;
}

.metric-label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-primary);
}

.plan-candidates {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
  margin-bottom: var(--space-sm);
}

.candidates-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.candidate-tag {
  margin: 0;
}

.pros-cons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
  margin: var(--space-md) 0;
}

.pros-label, .cons-label, .scenarios-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  display: block;
  margin-bottom: 4px;
}

.pros ul, .cons ul {
  margin: 4px 0 0;
  padding-left: 16px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.pros li { color: var(--color-success); }
.cons li { color: var(--color-danger); }

.scenarios {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
  margin-top: var(--space-sm);
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
