<template>
  <div class="candidate-detail-container">
    <el-page-header @back="$router.back()" content="候选人详情" />

    <div v-if="candidate" class="candidate-content">
      <!-- Header -->
      <div class="card header-card">
        <div class="candidate-header">
          <el-avatar :size="64" :icon="UserFilled" style="background: var(--color-primary); font-size: 32px" />
          <div class="candidate-basic">
            <h2 class="candidate-name">{{ candidate.candidate_id }}</h2>
            <el-tag v-if="candidate.penalty_applied" type="danger" effect="dark" size="small">跳槽惩罚</el-tag>
            <el-tag v-else type="success" effect="dark" size="small">稳定性良好</el-tag>
          </div>
          <div class="candidate-score">
            <div class="score-circle">
              <span class="score-value">{{ formatScore(candidate.tci_score) }}</span>
              <span class="score-label">TCI</span>
            </div>
            <div class="rank-info">
              <span class="rank-label">排名</span>
              <span class="rank-value">#{{ rank }}</span>
            </div>
            <el-button type="danger" size="small" @click="handleExportPDF">
              <el-icon><Download /></el-icon>PDF
            </el-button>
          </div>
        </div>
      </div>

      <el-row :gutter="20" class="mt-20">
        <!-- 雷达图 -->
        <el-col :span="8">
          <div class="card chart-card">
            <div class="card-header">
              <span class="card-title">维度得分雷达图</span>
            </div>
            <v-chart :option="radarOption" autoresize style="height: 350px" />
          </div>
        </el-col>

        <!-- 维度详情 -->
        <el-col :span="8">
          <div class="card detail-card">
            <div class="card-header">
              <span class="card-title">各维度得分详情</span>
            </div>
            <div class="dimension-list">
              <div class="dimension-item" v-for="(score, key) in candidate.dimensional_scores" :key="key">
                <div class="dim-info">
                  <span class="dim-name">{{ dimensionNames[key] }}</span>
                  <span class="dim-weight">权重: {{ (candidate.dimension_weights[key] * 100).toFixed(1) }}%</span>
                </div>
                <div class="dim-score">
                  <el-progress
                    :percentage="parseFloat(((score / 5) * 100).toFixed(1))"
                    :color="getScoreColor(score)"
                    :stroke-width="12"
                    striped
                  />
                  <span class="score-text">{{ formatScore(score, 1) }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-col>

        <!-- 权重分布 -->
        <el-col :span="8">
          <div class="card chart-card">
            <div class="card-header">
              <span class="card-title">维度权重分布</span>
            </div>
            <v-chart :option="pieOption" autoresize style="height: 350px" />
          </div>
        </el-col>
      </el-row>

      <!-- AI智能分析 -->
      <div class="card analysis-card mt-20">
        <div class="card-header analysis-header">
          <span class="card-title">AI 智能分析</span>
            <el-tag v-if="analysisData" :type="analysisData.source === 'llm' ? 'success' : 'info'" size="small">
              {{ analysisData.source === 'llm' ? 'AI Powered' : '规则分析' }}
            </el-tag>
          </div>

        <div v-if="analysisLoading" class="analysis-loading">
          <el-skeleton :rows="6" animated />
          <p class="loading-tip">AI 正在分析候选人简历数据...</p>
        </div>

        <div v-else-if="analysisData" class="analysis-content">
          <!-- 综合评价 -->
          <div class="analysis-summary">
            <h4>📋 综合评价</h4>
            <p>{{ analysisData.summary }}</p>
          </div>

          <el-row :gutter="20" class="mt-16">
            <!-- 优势 -->
            <el-col :span="8">
              <div class="analysis-section strengths-section">
                <h4>✨ 优势亮点</h4>
                <div class="tag-list">
                  <el-tag v-for="(s, i) in analysisData.strengths" :key="i" type="success" effect="plain" class="analysis-tag">
                    {{ s }}
                  </el-tag>
                  <span v-if="!analysisData.strengths?.length" class="empty-text">暂无</span>
                </div>
              </div>
            </el-col>

            <!-- 不足 -->
            <el-col :span="8">
              <div class="analysis-section weaknesses-section">
                <h4>⚡ 待改进</h4>
                <div class="tag-list">
                  <el-tag v-for="(w, i) in analysisData.weaknesses" :key="i" type="warning" effect="plain" class="analysis-tag">
                    {{ w }}
                  </el-tag>
                  <span v-if="!analysisData.weaknesses?.length" class="empty-text">暂无</span>
                </div>
              </div>
            </el-col>

            <!-- 风险 -->
            <el-col :span="8">
              <div class="analysis-section risks-section">
                <h4>⚠️ 风险提示</h4>
                <div class="tag-list">
                  <el-tag v-for="(r, i) in analysisData.risks" :key="i" type="danger" effect="plain" class="analysis-tag">
                    {{ r }}
                  </el-tag>
                  <span v-if="!analysisData.risks?.length" class="empty-text">暂无风险</span>
                </div>
              </div>
            </el-col>
          </el-row>

          <!-- 录用建议 -->
          <div class="recommendation-box mt-16">
            <h4>🎯 录用建议</h4>
            <p>{{ analysisData.recommendation }}</p>
          </div>

          <!-- 发展建议 -->
          <div v-if="analysisData.development_suggestions?.length" class="development-box mt-16">
            <h4>📈 发展建议</h4>
            <ul>
              <li v-for="(s, i) in analysisData.development_suggestions" :key="i">{{ s }}</li>
            </ul>
          </div>
        </div>

        <div v-else class="analysis-empty">
          <el-empty description="暂无分析数据" />
        </div>
      </div>

      <!-- 风险评估卡片 -->
      <div class="card risk-card mt-20">
        <div class="card-header risk-header">
          <span class="card-title">风险评估</span>
            <el-tag v-if="riskData" :type="getRiskLevelType(riskData.overall_risk_level)" effect="dark" size="small">
              {{ riskData.overall_risk_level === '高' ? '高风险' : riskData.overall_risk_level === '中' ? '中风险' : '低风险' }}
            </el-tag>
          </div>

        <div v-if="riskLoading" class="analysis-loading">
          <el-skeleton :rows="4" animated />
        </div>

        <div v-else-if="riskData" class="risk-content">
          <!-- 综合风险评分 -->
          <div class="risk-score-box mb-20">
            <div class="risk-score-circle" :class="'risk-' + riskData.overall_risk_level">
              <span class="risk-score-value">{{ riskData.overall_risk_score }}</span>
              <span class="risk-score-label">风险分</span>
            </div>
            <div class="risk-comment">
              <h4>{{ riskData.risk_comment }}</h4>
              <p>发现 {{ riskData.risk_factors?.length || 0 }} 个风险因素</p>
            </div>
          </div>

          <!-- 风险因素列表 -->
          <div v-if="riskData.risk_factors?.length" class="risk-factors-list">
            <el-row :gutter="12">
              <el-col :span="12" v-for="(factor, index) in riskData.risk_factors" :key="index">
                <div class="risk-factor-item" :class="'risk-level-' + factor.level">
                  <div class="risk-factor-header">
                    <span class="risk-type">{{ factor.type }}</span>
                    <el-tag :type="getRiskLevelType(factor.level)" size="small">{{ factor.level }}风险</el-tag>
                  </div>
                  <p class="risk-factor-desc">{{ factor.description }}</p>
                </div>
              </el-col>
            </el-row>
          </div>
          <div v-else class="no-risk">
            <el-icon color="#67C23A" :size="32"><CircleCheckFilled /></el-icon>
            <p>未发现明显风险因素</p>
          </div>
        </div>

        <div v-else class="analysis-empty">
          <el-empty description="暂无风险评估数据" />
        </div>
      </div>

      <!-- 潜力评估卡片 -->
      <div class="card potential-card mt-20">
        <div class="card-header potential-header">
          <span class="card-title">潜力评估</span>
            <el-tag v-if="potentialData" type="success" effect="dark" size="small">
              {{ potentialData.talent_type }}
            </el-tag>
          </div>

        <div v-if="potentialLoading" class="analysis-loading">
          <el-skeleton :rows="4" animated />
        </div>

        <div v-else-if="potentialData" class="potential-content">
          <!-- 综合潜力评分 -->
          <div class="potential-score-box mb-20">
            <div class="potential-score-circle">
              <span class="potential-score-value">{{ potentialData.potential_score }}</span>
              <span class="potential-score-label">潜力分</span>
            </div>
            <div class="potential-comment">
              <h4>{{ potentialData.talent_type }}</h4>
              <p>{{ potentialData.potential_comment }}</p>
            </div>
          </div>

          <!-- 潜力维度雷达图 -->
          <el-row :gutter="20">
            <el-col :span="12">
              <v-chart :option="potentialRadarOption" autoresize style="height: 300px" />
            </el-col>
            <el-col :span="12">
              <div class="potential-dimensions">
                <div v-for="(score, key) in potentialData.dimension_scores" :key="key" class="potential-dim-item">
                  <div class="dim-header">
                    <span class="dim-name">{{ getPotentialDimName(key) }}</span>
                    <span class="dim-score">{{ score.toFixed(2) }}</span>
                  </div>
                  <el-progress
                    :percentage="(score / 10) * 100"
                    :color="getScoreColor(score)"
                    :stroke-width="10"
                    striped
                  />
                </div>
              </div>
            </el-col>
          </el-row>
        </div>

        <div v-else class="analysis-empty">
          <el-empty description="暂无潜力评估数据" />
        </div>
      </div>
    </div>

    <div v-else class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useResumeStore } from '@/stores'
import { formatScore } from '@/utils/format'
import { exportUtils } from '@/utils/export'
import { ElMessage } from 'element-plus'

const route = useRoute()
const store = useResumeStore()

const candidate = ref(null)
const rank = ref(0)
const analysisData = ref(null)
const analysisLoading = ref(false)
const riskData = ref(null)
const riskLoading = ref(false)
const potentialData = ref(null)
const potentialLoading = ref(false)

const dimensionNames = {
  education: '教育背景',
  experience: '工作经历',
  skill_achievement: '技能成果',
  comprehensive: '综合素质',
  growth_potential: '成长潜力',
  job_matching: '岗位匹配'
}

const potentialDimNames = {
  career_continuity: '职业发展连续性',
  responsibility_growth: '职责提升轨迹',
  project_complexity: '项目复杂度',
  learning_ability: '学习能力',
  company_platform_growth: '公司平台跃迁'
}

const getPotentialDimName = (key) => {
  return potentialDimNames[key] || key
}

const getRiskLevelType = (level) => {
  if (level === '高') return 'danger'
  if (level === '中') return 'warning'
  return 'success'
}

const potentialRadarOption = computed(() => {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    tooltip: {},
    radar: {
      indicator: [
        { name: '职业发展连续性', max: 10 },
        { name: '职责提升轨迹', max: 10 },
        { name: '项目复杂度', max: 10 },
        { name: '学习能力', max: 10 },
        { name: '公司平台跃迁', max: 10 }
      ],
      axisName: { color: isDark ? '#94A3B8' : '#64748B' },
      splitLine: { lineStyle: { color: isDark ? '#334155' : '#E2E8F0' } },
      splitArea: { areaStyle: { color: ['transparent'] } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: [
          potentialData.value?.dimension_scores?.career_continuity || 0,
          potentialData.value?.dimension_scores?.responsibility_growth || 0,
          potentialData.value?.dimension_scores?.project_complexity || 0,
          potentialData.value?.dimension_scores?.learning_ability || 0,
          potentialData.value?.dimension_scores?.company_platform_growth || 0
        ],
        name: '潜力得分',
        areaStyle: { opacity: 0.3 },
        lineStyle: { width: 2 }
      }]
    }]
  }
})

const dimensionColors = {
  education: '#667eea',
  experience: '#f5576c',
  skill_achievement: '#4facfe',
  comprehensive: '#43e97b',
  growth_potential: '#fa709a',
  job_matching: '#fee140'
}

const radarOption = computed(() => {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    tooltip: {},
    radar: {
      indicator: [
        { name: '教育背景', max: 5 },
        { name: '工作经历', max: 5 },
        { name: '技能成果', max: 5 },
        { name: '综合素质', max: 5 },
        { name: '成长潜力', max: 5 },
        { name: '岗位匹配', max: 5 }
      ],
      axisName: { color: isDark ? '#94A3B8' : '#64748B' },
      splitLine: { lineStyle: { color: isDark ? '#334155' : '#E2E8F0' } },
      splitArea: { areaStyle: { color: ['transparent'] } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: [
          candidate.value?.dimensional_scores?.education || 0,
          candidate.value?.dimensional_scores?.experience || 0,
          candidate.value?.dimensional_scores?.skill_achievement || 0,
          candidate.value?.dimensional_scores?.comprehensive || 0,
          candidate.value?.dimensional_scores?.growth_potential || 0,
          candidate.value?.dimensional_scores?.job_matching || 0
        ],
        name: '得分',
        areaStyle: { opacity: 0.3 },
        lineStyle: { width: 2 }
      }]
    }]
  }
})

const pieOption = computed(() => {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: '2%', textStyle: { color: isDark ? '#CBD5E1' : '#475569' } },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: isDark ? '#1E293B' : '#fff', borderWidth: 2 },
      label: { show: true, formatter: (params) => `${params.name}: ${params.value.toFixed(1)}%`, color: isDark ? '#CBD5E1' : '#475569' },
      data: candidate.value ? [
        { value: (candidate.value.dimension_weights.education || 0) * 100, name: '教育背景', itemStyle: { color: '#6366F1' } },
        { value: (candidate.value.dimension_weights.experience || 0) * 100, name: '工作经历', itemStyle: { color: '#EC4899' } },
        { value: (candidate.value.dimension_weights.skill_achievement || 0) * 100, name: '技能成果', itemStyle: { color: '#0EA5E9' } },
        { value: (candidate.value.dimension_weights.comprehensive || 0) * 100, name: '综合素质', itemStyle: { color: '#10B981' } },
        { value: (candidate.value.dimension_weights.growth_potential || 0) * 100, name: '成长潜力', itemStyle: { color: '#F59E0B' } },
        { value: (candidate.value.dimension_weights.job_matching || 0) * 100, name: '岗位匹配', itemStyle: { color: '#8B5CF6' } }
      ] : []
    }]
  }
})

const getScoreColor = (score) => {
  if (score >= 4) return '#16A34A'
  if (score >= 3) return '#D97706'
  return '#DC2626'
}

const handleExportPDF = async () => {
  if (!candidate.value) {
    ElMessage.warning('没有候选人数据')
    return
  }
  try {
    ElMessage.info('正在生成PDF报告...')
    const exportData = {
      ...candidate.value,
      industry: store.currentIndustry,
      rank: rank.value
    }
    await exportUtils.exportCandidatePDF(exportData, '候选人评估报告')
    ElMessage.success('PDF报告已下载')
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  }
}

onMounted(async () => {
  const candidateId = route.params.id

  // 从store中查找候选人
  if (store.candidates.length === 0) {
    await store.fetchRankings('电商', 10)
  }

  let found = store.candidates.find(c => c.candidate_id === candidateId)

  // 如果没找到，尝试调用单份评分API
  if (!found) {
    try {
      const scoreResult = await store.scoreResume(candidateId, store.currentIndustry || '电商')
      if (scoreResult) {
        found = {
          candidate_id: scoreResult.candidate_id,
          tci_score: scoreResult.tci_score,
          dimensional_scores: scoreResult.dimensional_scores,
          dimension_weights: scoreResult.dimension_weights,
          penalty_applied: scoreResult.analysis?.penalty_applied || false
        }
      }
    } catch (err) {
      console.error('获取候选人评分失败:', err)
    }
  }

  if (found) {
    candidate.value = found
    const rankIndex = store.rankings.findIndex(r => r.candidate_id === candidateId)
    rank.value = rankIndex + 1

    // 调用LLM分析
    analysisLoading.value = true
    try {
      const result = await store.analyzeCandidate(
        candidateId,
        store.currentIndustry || found.job_type || '电商'
      )
      if (result.status === 'success' && result.data) {
        analysisData.value = result.data
      }
    } catch (err) {
      console.error('分析失败:', err)
    } finally {
      analysisLoading.value = false
    }

    // 调用风险评估
    riskLoading.value = true
    try {
      const riskResult = await store.assessRisk(candidateId)
      if (riskResult.status === 'success' && riskResult.risk_assessment) {
        riskData.value = riskResult.risk_assessment
      }
    } catch (err) {
      console.error('风险评估失败:', err)
    } finally {
      riskLoading.value = false
    }

    // 调用潜力评估
    potentialLoading.value = true
    try {
      const potentialResult = await store.evaluatePotential(candidateId)
      if (potentialResult.status === 'success' && potentialResult.potential_evaluation) {
        potentialData.value = potentialResult.potential_evaluation
      }
    } catch (err) {
      console.error('潜力评估失败:', err)
    } finally {
      potentialLoading.value = false
    }
  } else {
    console.error('未找到候选人:', candidateId)
  }
})
</script>

<style scoped>
.candidate-detail-container {
  max-width: 1200px;
  margin: 0 auto;
}

.chart-card, .detail-card, .analysis-card, .risk-card, .potential-card {
  padding: var(--space-lg);
}

.card-header {
  margin-bottom: var(--space-md);
}

.card-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.header-card {
  margin-top: var(--space-md);
  padding: var(--space-lg);
}

.candidate-header {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
}

.candidate-name {
  margin: 0 0 var(--space-sm);
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.candidate-score {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-lg);
}

.score-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.score-value {
  font-size: 28px;
  font-weight: 700;
}

.score-label {
  font-size: var(--font-size-xs);
  opacity: 0.85;
}

.rank-info {
  text-align: center;
}

.rank-label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: 2px;
}

.rank-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-warning);
}

.dimension-list {
  padding: 10px 0;
}

.dimension-item {
  padding: 15px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.dimension-item:last-child {
  border-bottom: none;
}

.dim-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.dim-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.dim-weight {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.dim-score {
  display: flex;
  align-items: center;
  gap: 15px;
}

.score-text {
  font-weight: 700;
  font-size: var(--font-size-lg);
  color: var(--color-primary);
  min-width: 50px;
}

.analysis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.analysis-loading {
  padding: 10px 0;
}

.loading-tip {
  text-align: center;
  color: #909399;
  font-size: 14px;
  margin-top: 10px;
}

.analysis-summary {
  background: var(--color-primary-bg);
  padding: var(--space-lg);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-primary);
}

.analysis-summary h4 {
  color: var(--color-primary);
  margin-bottom: var(--space-sm);
  font-size: var(--font-size-base);
}

.analysis-summary p {
  color: var(--color-text-primary);
  line-height: 1.8;
  font-size: var(--font-size-base);
  margin: 0;
}

.analysis-section {
  background: var(--color-bg-hover);
  padding: var(--space-md);
  border-radius: var(--radius-md);
  height: 100%;
}

.analysis-section h4 {
  color: var(--color-primary);
  margin-bottom: var(--space-sm);
  font-size: var(--font-size-base);
}

.tag-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.analysis-tag {
  white-space: normal;
  height: auto;
  padding: 8px 12px;
  line-height: 1.5;
  font-size: 13px;
}

.empty-text {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.recommendation-box {
  background: var(--color-success-bg);
  padding: var(--space-lg);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-success);
}

.recommendation-box h4 {
  color: var(--color-success);
  margin-bottom: var(--space-sm);
  font-size: var(--font-size-base);
}

.recommendation-box p {
  color: var(--color-text-primary);
  line-height: 1.8;
  font-size: var(--font-size-base);
  margin: 0;
}

.development-box {
  background: var(--color-warning-bg);
  padding: var(--space-lg);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-warning);
}

.development-box h4 {
  color: var(--color-warning);
  margin-bottom: var(--space-sm);
  font-size: var(--font-size-base);
}

.development-box ul {
  padding-left: 20px;
  color: var(--color-text-primary);
  line-height: 1.8;
  font-size: var(--font-size-base);
  margin: 0;
}

.development-box li {
  margin-bottom: 6px;
}

.analysis-empty {
  padding: 40px 0;
}

.mt-16 {
  margin-top: 16px;
}

.mb-20 {
  margin-bottom: 20px;
}

.mt-20 {
  margin-top: 20px;
}

.loading-container {
  padding: 40px;
}

/* 风险评估样式 */
.risk-header, .potential-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.risk-content, .potential-content {
  padding: 10px 0;
}

.risk-score-box, .potential-score-box {
  display: flex;
  align-items: center;
  gap: 30px;
}

.risk-score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.risk-score-circle.risk-高 {
  background: linear-gradient(135deg, var(--color-danger), #B91C1C);
}

.risk-score-circle.risk-中 {
  background: linear-gradient(135deg, var(--color-warning), #B45309);
}

.risk-score-circle.risk-低 {
  background: linear-gradient(135deg, var(--color-success), #15803D);
}

.risk-score-value {
  font-size: 36px;
  font-weight: bold;
}

.risk-score-label {
  font-size: 14px;
}

.risk-comment h4, .potential-comment h4 {
  margin: 0 0 5px;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
}

.risk-comment p, .potential-comment p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

.risk-factor-item {
  background: var(--color-bg-hover);
  padding: var(--space-md);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-sm);
  border-left: 4px solid;
}

.risk-factor-item.risk-level-高 {
  border-left-color: var(--color-danger);
}

.risk-factor-item.risk-level-中 {
  border-left-color: var(--color-warning);
}

.risk-factor-item.risk-level-低 {
  border-left-color: var(--color-success);
}

.risk-factor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.risk-type {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.risk-factor-desc {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}

.no-risk {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
}

.no-risk p {
  margin: 10px 0 0;
  color: var(--color-success);
  font-size: var(--font-size-lg);
}

/* 潜力评估样式 */
.potential-score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.potential-score-value {
  font-size: 36px;
  font-weight: bold;
}

.potential-score-label {
  font-size: 14px;
}

.potential-dimensions {
  padding: 10px 0;
}

.potential-dim-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.potential-dim-item:last-child {
  border-bottom: none;
}

.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.dim-header .dim-name {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.dim-header .dim-score {
  font-weight: 700;
  color: var(--color-primary);
  font-size: var(--font-size-lg);
}
</style>
