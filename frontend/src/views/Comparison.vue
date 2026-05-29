<template>
  <div class="comparison-page">
    <h1 class="page-title">候选人对比分析</h1>

    <!-- Industry & Candidate Selection -->
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
          <span class="hint-text">选择2-5位候选人进行对比分析</span>
        </el-col>
        <el-col :span="6" style="text-align: right">
          <el-button type="primary" @click="startComparison" :disabled="selectedCandidates.length < 2" :loading="loading">
            开始对比 ({{ selectedCandidates.length }})
          </el-button>
          <el-button @click="clearSelection">清空</el-button>
        </el-col>
      </el-row>
    </div>

    <!-- Candidate Grid -->
    <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
      <div class="card-header">
        <span class="card-title">选择候选人</span>
      </div>
      <el-row :gutter="12">
        <el-col :span="6" v-for="c in availableCandidates" :key="c.id">
          <div
            class="candidate-pick"
            :class="{ selected: selectedCandidates.includes(c.id) }"
            @click="toggleCandidate(c.id)"
          >
            <div class="pick-name">{{ c.name }}</div>
            <div class="pick-score">TCI: {{ c.tci_score?.toFixed(2) || '-' }}</div>
            <div class="pick-rank">排名 #{{ c.rank }}</div>
          </div>
        </el-col>
      </el-row>
      <el-empty v-if="availableCandidates.length === 0" description="暂无候选人数据" />
    </div>

    <!-- Comparison Results -->
    <template v-if="comparisonResult">
      <!-- Summary -->
      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="card-header">
          <span class="card-title">对比总结</span>
        </div>
        <p class="summary-text">{{ comparisonResult.summary }}</p>
        <div class="recommendation-order" v-if="comparisonResult.recommendation_order?.length">
          <span class="order-label">推荐排序:</span>
          <el-tag v-for="(name, i) in comparisonResult.recommendation_order" :key="name" :type="i === 0 ? 'success' : 'info'" class="order-tag">
            {{ i + 1 }}. {{ name }}
          </el-tag>
        </div>
      </div>

      <!-- Dimension Comparison -->
      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="card-header">
          <span class="card-title">各维度得分对比</span>
        </div>
        <el-row :gutter="12">
          <el-col :span="6" v-for="(ranking, dimension) in comparisonResult.dimension_comparison" :key="dimension">
            <div class="dim-compare-card">
              <div class="dim-compare-title">{{ getDimensionName(dimension) }}</div>
              <div class="dim-rank-list">
                <div v-for="(item, index) in ranking.slice(0, 3)" :key="item[0]" class="dim-rank-item" :class="{ top: index === 0 }">
                  <span class="dim-rank-num">{{ index + 1 }}</span>
                  <span class="dim-rank-name">{{ item[0] }}</span>
                  <span class="dim-rank-score">{{ item[1].toFixed(2) }}</span>
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- Advantage Matrix -->
      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="card-header">
          <span class="card-title">优势分析</span>
        </div>
        <el-row :gutter="12">
          <el-col :span="8" v-for="(advantages, name) in comparisonResult.advantage_matrix" :key="name">
            <div class="advantage-card">
              <div class="advantage-name">{{ name }}</div>
              <div v-if="advantages.top_dimensions?.length" class="adv-section">
                <span class="adv-label">最强维度:</span>
                <span class="adv-value">{{ advantages.top_dimensions.join(', ') }}</span>
              </div>
              <div v-if="advantages.unique_skills?.length" class="adv-section">
                <span class="adv-label">独特技能:</span>
                <span class="adv-value">{{ advantages.unique_skills.slice(0, 5).join(', ') }}</span>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- Gap Analysis -->
      <div v-if="Object.keys(comparisonResult.gap_analysis || {}).length" class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="card-header">
          <span class="card-title">差距分析</span>
        </div>
        <el-row :gutter="12">
          <el-col :span="12" v-for="(gap, name) in comparisonResult.gap_analysis" :key="name">
            <div class="gap-item" :class="{ 'is-top': gap.is_top }">
              <span class="gap-name">{{ name }}</span>
              <el-tag v-if="gap.is_top" type="success" size="small">第一名</el-tag>
              <el-tag v-else type="warning" size="small">差距: {{ gap.overall_gap?.toFixed(2) }}分</el-tag>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- Detail Table -->
      <div class="card" style="padding: var(--space-lg); margin-bottom: var(--space-md)">
        <div class="card-header">
          <span class="card-title">候选人详情</span>
        </div>
        <el-table :data="comparisonResult.candidate_details" stripe>
          <el-table-column prop="name" label="候选人" width="120">
            <template #default="{ row }"><strong>{{ row.name }}</strong></template>
          </el-table-column>
          <el-table-column label="TCI得分" align="center">
            <template #default="{ row }"><span class="score-highlight">{{ row.tci_score?.toFixed(2) }}</span></template>
          </el-table-column>
          <el-table-column label="教育背景" align="center">
            <template #default="{ row }">{{ row.dimensional_scores?.education?.toFixed(2) || '-' }}</template>
          </el-table-column>
          <el-table-column label="工作经历" align="center">
            <template #default="{ row }">{{ row.dimensional_scores?.experience?.toFixed(2) || '-' }}</template>
          </el-table-column>
          <el-table-column label="技能成果" align="center">
            <template #default="{ row }">{{ row.dimensional_scores?.skill_achievement?.toFixed(2) || '-' }}</template>
          </el-table-column>
          <el-table-column label="综合素质" align="center">
            <template #default="{ row }">{{ row.dimensional_scores?.comprehensive?.toFixed(2) || '-' }}</template>
          </el-table-column>
          <el-table-column label="风险数" align="center" width="80">
            <template #default="{ row }">
              <span :class="{ 'risk-high': row.risk_count > 0 }">{{ row.risk_count }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Export -->
      <div style="text-align: center; padding: var(--space-md)">
        <el-button type="success" @click="exportReport('json')">导出JSON</el-button>
        <el-button type="primary" @click="exportReport('excel')">导出Excel</el-button>
      </div>
    </template>

    <!-- Loading overlay -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="loading-icon" :size="40"><Loading /></el-icon>
      <p>正在分析对比数据...</p>
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
const comparisonResult = ref(null)
const loading = ref(false)
const industries = ref([])
const selectedIndustry = ref('')

const fetchIndustries = async () => {
  try {
    const res = await axios.get('/api/industries')
    if (res.data.status === 'success') industries.value = res.data.industries
  } catch (e) {
    console.error('获取行业列表失败:', e)
  }
}

const fetchCandidates = async () => {
  try {
    const params = selectedIndustry.value ? { industry: selectedIndustry.value } : {}
    const res = await axios.get('/api/comparison/available-candidates', { params })
    if (res.data.status === 'success') {
      availableCandidates.value = res.data.candidates
      selectedCandidates.value = []
      comparisonResult.value = null
    }
  } catch (e) {
    console.error('获取候选人列表失败:', e)
    ElMessage.error('获取候选人列表失败')
  }
}

const onIndustryChange = () => fetchCandidates()

const toggleCandidate = (id) => {
  const idx = selectedCandidates.value.indexOf(id)
  if (idx > -1) {
    selectedCandidates.value.splice(idx, 1)
  } else if (selectedCandidates.value.length < 5) {
    selectedCandidates.value.push(id)
  } else {
    ElMessage.warning('最多选择5位候选人')
  }
}

const clearSelection = () => {
  selectedCandidates.value = []
  comparisonResult.value = null
}

const startComparison = async () => {
  if (selectedCandidates.value.length < 2) {
    ElMessage.warning('请至少选择2位候选人')
    return
  }
  loading.value = true
  try {
    const res = await axios.post('/api/comparison/analyze', {
      resume_ids: selectedCandidates.value,
      job_requirements: null
    })
    if (res.data.status === 'success') {
      comparisonResult.value = res.data.comparison_result
    }
  } catch (e) {
    ElMessage.error('对比分析失败: ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    loading.value = false
  }
}

const getDimensionName = (dim) => {
  const names = { overall: '综合评分', education: '教育背景', experience: '工作经历', skill_achievement: '技能成果', comprehensive: '综合素质', growth_potential: '成长潜力', job_matching: '岗位匹配' }
  return names[dim] || dim
}

const exportReport = async (format) => {
  try {
    const res = await axios.post('/api/report/export', { report_type: 'comparison', data: comparisonResult.value, format })
    if (res.data.status === 'success') {
      let blob
      if (format === 'json') {
        blob = new Blob([JSON.stringify(res.data.data, null, 2)], { type: 'application/json' })
      } else if (format === 'excel') {
        const bytes = atob(res.data.data)
        const arr = new Uint8Array(bytes.length)
        for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i)
        blob = new Blob([arr], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      }
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = res.data.filename
      link.click()
      URL.revokeObjectURL(url)
      ElMessage.success('导出成功')
    }
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchIndustries()
  fetchCandidates()
})
</script>

<style scoped>
.comparison-page {
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

.card-header {
  margin-bottom: var(--space-md);
}

.card-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.candidate-pick {
  background: var(--color-bg-card);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: var(--space-sm);
}

.candidate-pick:hover {
  border-color: var(--color-primary-lighter);
  box-shadow: var(--shadow-md);
}

.candidate-pick.selected {
  border-color: var(--color-success);
  background: var(--color-success-bg);
}

.pick-name {
  font-weight: 600;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.pick-score {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  font-weight: 500;
}

.pick-rank {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.summary-text {
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin: 0 0 var(--space-md);
}

.recommendation-order {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.order-label {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.order-tag {
  font-size: var(--font-size-sm);
}

.dim-compare-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
}

.dim-compare-title {
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  text-align: center;
  margin-bottom: var(--space-sm);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border-light);
}

.dim-rank-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  margin-bottom: 4px;
  background: var(--color-bg-hover);
}

.dim-rank-item.top {
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning);
}

.dim-rank-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.dim-rank-item.top .dim-rank-num {
  background: var(--color-warning);
  color: #fff;
}

.dim-rank-name {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.dim-rank-score {
  font-weight: 700;
  font-size: var(--font-size-sm);
  color: var(--color-primary);
}

.advantage-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  margin-bottom: var(--space-sm);
}

.advantage-name {
  font-weight: 600;
  color: var(--color-success);
  margin-bottom: var(--space-sm);
  padding-bottom: var(--space-sm);
  border-bottom: 2px solid var(--color-success);
}

.adv-section {
  margin-bottom: var(--space-sm);
  font-size: var(--font-size-sm);
}

.adv-label {
  font-weight: 600;
  color: var(--color-text-primary);
  display: block;
  margin-bottom: 2px;
}

.adv-value {
  color: var(--color-text-secondary);
}

.gap-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-sm);
}

.gap-item.is-top {
  background: var(--color-success-bg);
  border-color: var(--color-success);
}

.gap-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.score-highlight {
  font-weight: 700;
  color: var(--color-primary);
  font-size: var(--font-size-lg);
}

.risk-high {
  color: var(--color-danger);
  font-weight: 700;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
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
