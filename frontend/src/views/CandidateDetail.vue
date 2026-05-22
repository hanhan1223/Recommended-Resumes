<template>
  <div class="candidate-detail-container">
    <el-page-header @back="$router.back()" content="候选人详情" />
    
    <div v-if="candidate" class="candidate-content">
      <!-- 头部信息 -->
      <el-card class="header-card">
        <div class="candidate-header">
          <el-avatar :size="80" :icon="UserFilled" style="background: #2E86AB; font-size: 40px" />
          <div class="candidate-basic">
            <h2>{{ candidate.candidate_id }}</h2>
            <el-tag v-if="candidate.penalty_applied" type="danger" effect="dark">
              ⚠️ 跳槽惩罚
            </el-tag>
            <el-tag v-else type="success" effect="dark">
              ✅ 稳定性良好
            </el-tag>
          </div>
          <div class="candidate-score">
            <div class="score-circle">
              <span class="score-value">{{ formatScore(candidate.tci_score) }}</span>
              <span class="score-label">TCI得分</span>
            </div>
            <div class="rank-info">
              <span class="rank-label">行业排名</span>
              <span class="rank-value">第 {{ rank }} 名</span>
            </div>
            <div class="export-actions" style="margin-top: 10px;">
              <el-button type="danger" size="small" @click="handleExportPDF">
                <el-icon><Download /></el-icon>导出PDF
              </el-button>
            </div>
          </div>
        </div>
      </el-card>

      <el-row :gutter="20" class="mt-20">
        <!-- 雷达图 -->
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header>
              <span>🎯 维度得分雷达图</span>
            </template>
            <v-chart :option="radarOption" autoresize style="height: 350px" />
          </el-card>
        </el-col>

        <!-- 维度详情 -->
        <el-col :span="8">
          <el-card class="detail-card">
            <template #header>
              <span>📊 各维度得分详情</span>
            </template>
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
          </el-card>
        </el-col>

        <!-- 权重分布 -->
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header>
              <span>⚖️ 维度权重分布</span>
            </template>
            <v-chart :option="pieOption" autoresize style="height: 350px" />
          </el-card>
        </el-col>
      </el-row>

      <!-- AI智能分析 -->
      <el-card class="analysis-card mt-20">
        <template #header>
          <div class="analysis-header">
            <span>🤖 AI 智能分析</span>
            <el-tag v-if="analysisData" :type="analysisData.source === 'llm' ? 'success' : 'info'" size="small">
              {{ analysisData.source === 'llm' ? 'AI Powered' : '规则分析' }}
            </el-tag>
          </div>
        </template>

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
      </el-card>

      <!-- 风险评估卡片 -->
      <el-card class="risk-card mt-20">
        <template #header>
          <div class="risk-header">
            <span>⚠️ 风险评估</span>
            <el-tag v-if="riskData" :type="getRiskLevelType(riskData.overall_risk_level)" effect="dark" size="small">
              {{ riskData.overall_risk_level === '高' ? '高风险' : riskData.overall_risk_level === '中' ? '中风险' : '低风险' }}
            </el-tag>
          </div>
        </template>

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
      </el-card>

      <!-- 潜力评估卡片 -->
      <el-card class="potential-card mt-20">
        <template #header>
          <div class="potential-header">
            <span>🚀 潜力评估</span>
            <el-tag v-if="potentialData" type="success" effect="dark" size="small">
              {{ potentialData.talent_type }}
            </el-tag>
          </div>
        </template>

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
      </el-card>
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
  comprehensive: '综合素质'
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

const potentialRadarOption = computed(() => ({
  tooltip: {},
  radar: {
    indicator: [
      { name: '职业发展连续性', max: 10 },
      { name: '职责提升轨迹', max: 10 },
      { name: '项目复杂度', max: 10 },
      { name: '学习能力', max: 10 },
      { name: '公司平台跃迁', max: 10 }
    ]
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
}))

const dimensionColors = {
  education: '#667eea',
  experience: '#f5576c',
  skill_achievement: '#4facfe',
  comprehensive: '#43e97b'
}

const radarOption = computed(() => ({
  tooltip: {},
  radar: {
    indicator: [
      { name: '教育背景', max: 5 },
      { name: '工作经历', max: 5 },
      { name: '技能成果', max: 5 },
      { name: '综合素质', max: 5 }
    ]
  },
  series: [{
    type: 'radar',
    data: [{
      value: [
        candidate.value?.dimensional_scores?.education || 0,
        candidate.value?.dimensional_scores?.experience || 0,
        candidate.value?.dimensional_scores?.skill_achievement || 0,
        candidate.value?.dimensional_scores?.comprehensive || 0
      ],
      name: '得分',
      areaStyle: { opacity: 0.3 },
      lineStyle: { width: 2 }
    }]
  }]
}))

const pieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: '5%' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
    label: { show: true, formatter: (params) => `${params.name}: ${params.value.toFixed(1)}%` },
    data: candidate.value ? [
      { value: candidate.value.dimension_weights.education * 100, name: '教育背景', itemStyle: { color: '#667eea' } },
      { value: candidate.value.dimension_weights.experience * 100, name: '工作经历', itemStyle: { color: '#f5576c' } },
      { value: candidate.value.dimension_weights.skill_achievement * 100, name: '技能成果', itemStyle: { color: '#4facfe' } },
      { value: candidate.value.dimension_weights.comprehensive * 100, name: '综合素质', itemStyle: { color: '#43e97b' } }
    ] : []
  }]
}))

const getScoreColor = (score) => {
  if (score >= 4) return '#67C23A'
  if (score >= 3) return '#E6A23C'
  return '#F56C6C'
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
  max-width: 1400px;
  margin: 0 auto;
}

.header-card {
  margin-top: 20px;
  border-radius: 12px;
}

.candidate-header {
  display: flex;
  align-items: center;
  gap: 30px;
}

.candidate-basic h2 {
  margin: 0 0 10px;
  font-size: 28px;
  color: #2c3e50;
}

.candidate-score {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 30px;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2E86AB 0%, #4ECDC4 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.score-value {
  font-size: 36px;
  font-weight: bold;
}

.score-label {
  font-size: 14px;
}

.rank-info {
  text-align: center;
}

.rank-label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 5px;
}

.rank-value {
  font-size: 32px;
  font-weight: bold;
  color: #E6A23C;
}

.chart-card, .detail-card, .analysis-card {
  border-radius: 12px;
}

.dimension-list {
  padding: 10px 0;
}

.dimension-item {
  padding: 15px 0;
  border-bottom: 1px solid #eee;
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
  color: #2c3e50;
}

.dim-weight {
  font-size: 13px;
  color: #999;
}

.dim-score {
  display: flex;
  align-items: center;
  gap: 15px;
}

.score-text {
  font-weight: bold;
  font-size: 18px;
  color: #2E86AB;
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
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ee 100%);
  padding: 20px;
  border-radius: 10px;
  border-left: 4px solid #2E86AB;
}

.analysis-summary h4 {
  color: #2E86AB;
  margin-bottom: 10px;
  font-size: 15px;
}

.analysis-summary p {
  color: #2c3e50;
  line-height: 1.8;
  font-size: 14px;
  margin: 0;
}

.analysis-section {
  background: #fafafa;
  padding: 16px;
  border-radius: 10px;
  height: 100%;
}

.analysis-section h4 {
  color: #2E86AB;
  margin-bottom: 12px;
  font-size: 15px;
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
  color: #c0c4cc;
  font-size: 13px;
}

.recommendation-box {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  padding: 20px;
  border-radius: 10px;
  border-left: 4px solid #67C23A;
}

.recommendation-box h4 {
  color: #67C23A;
  margin-bottom: 10px;
  font-size: 15px;
}

.recommendation-box p {
  color: #2c3e50;
  line-height: 1.8;
  font-size: 14px;
  margin: 0;
}

.development-box {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  padding: 20px;
  border-radius: 10px;
  border-left: 4px solid #E6A23C;
}

.development-box h4 {
  color: #E6A23C;
  margin-bottom: 10px;
  font-size: 15px;
}

.development-box ul {
  padding-left: 20px;
  color: #2c3e50;
  line-height: 1.8;
  font-size: 14px;
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
  background: linear-gradient(135deg, #f56c6c 0%, #ef5350 100%);
}

.risk-score-circle.risk-中 {
  background: linear-gradient(135deg, #e6a23c 0%, #f5a623 100%);
}

.risk-score-circle.risk-低 {
  background: linear-gradient(135deg, #67c23a 0%, #53d17a 100%);
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
  color: #2c3e50;
  font-size: 18px;
}

.risk-comment p, .potential-comment p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.risk-factor-item {
  background: #fafafa;
  padding: 16px;
  border-radius: 10px;
  margin-bottom: 12px;
  border-left: 4px solid;
}

.risk-factor-item.risk-level-高 {
  border-left-color: #f56c6c;
}

.risk-factor-item.risk-level-中 {
  border-left-color: #e6a23c;
}

.risk-factor-item.risk-level-低 {
  border-left-color: #67c23a;
}

.risk-factor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.risk-type {
  font-weight: 600;
  color: #2c3e50;
  font-size: 15px;
}

.risk-factor-desc {
  margin: 0;
  color: #666;
  font-size: 13px;
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
  color: #67c23a;
  font-size: 16px;
}

/* 潜力评估样式 */
.potential-score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff 0%, #53a8ff 100%);
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
  border-bottom: 1px solid #eee;
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
  color: #2c3e50;
  font-size: 14px;
}

.dim-header .dim-score {
  font-weight: bold;
  color: #409eff;
  font-size: 16px;
}
</style>
