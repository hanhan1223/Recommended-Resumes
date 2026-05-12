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

      <!-- 分析总结 -->
      <el-card class="analysis-card mt-20">
        <template #header>
          <span>💡 智能分析</span>
        </template>
        <el-row :gutter="30">
          <el-col :span="12">
            <div class="analysis-section">
              <h4>✨ 优势亮点</h4>
              <ul>
                <li v-for="(adv, i) in advantages" :key="i">{{ adv }}</li>
              </ul>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="analysis-section">
              <h4>⚠️ 风险提示</h4>
              <ul>
                <li v-for="(risk, i) in risks" :key="i">{{ risk }}</li>
              </ul>
            </div>
          </el-col>
        </el-row>
        <div class="recommendation mt-20">
          <h4>🎯 综合推荐</h4>
          <p>{{ recommendation }}</p>
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

const dimensionNames = {
  education: '教育背景',
  experience: '工作经历',
  skill_achievement: '技能成果',
  comprehensive: '综合素质'
}

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

const advantages = computed(() => {
  if (!candidate.value) return []
  const scores = candidate.value.dimensional_scores
  const advs = []
  
  if (scores.education >= 4) advs.push('教育背景优秀，毕业于知名院校')
  if (scores.experience >= 4) advs.push('工作经历丰富，曾在知名企业任职')
  if (scores.skill_achievement >= 4) advs.push('专业技能突出，有显著成果')
  if (scores.comprehensive >= 4) advs.push('综合素质优秀，软实力突出')
  
  if (advs.length === 0) advs.push('各项指标均衡，综合表现稳定')
  return advs
})

const risks = computed(() => {
  if (!candidate.value) return []
  const rks = []
  
  if (candidate.value.penalty_applied) {
    rks.push('5年内跳槽次数超过3次，稳定性存在风险')
  }
  
  const scores = candidate.value.dimensional_scores
  if (scores.education < 3) rks.push('教育背景相对薄弱')
  if (scores.experience < 3) rks.push('工作经历相对不足')
  if (scores.skill_achievement < 3) rks.push('专业技能有待提升')
  
  if (rks.length === 0) rks.push('暂无显著风险')
  return rks
})

const recommendation = computed(() => {
  if (!candidate.value) return ''
  
  const tci = candidate.value.tci_score
  if (tci >= 4) {
    return '⭐⭐⭐⭐⭐ 强烈推荐！该候选人综合评分优秀，各项指标均衡发展，建议优先录用。'
  } else if (tci >= 3.5) {
    return '⭐⭐⭐⭐ 推荐。该候选人综合评分良好，符合岗位要求，建议录用。'
  } else if (tci >= 3) {
    return '⭐⭐⭐ 可考虑。该候选人综合评分中等，部分指标有提升空间，建议进一步面试评估。'
  } else {
    return '⭐⭐ 不推荐。该候选人综合评分较低，可能不符合岗位要求，建议谨慎考虑。'
  }
})

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
  
  const found = store.candidates.find(c => c.candidate_id === candidateId)
  if (found) {
    candidate.value = found
    const rankIndex = store.rankings.findIndex(r => r.candidate_id === candidateId)
    rank.value = rankIndex + 1
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

.analysis-section h4 {
  color: #2E86AB;
  margin-bottom: 15px;
  font-size: 16px;
}

.analysis-section ul {
  padding-left: 20px;
  color: #666;
  line-height: 1.8;
}

.analysis-section li {
  margin-bottom: 8px;
}

.recommendation {
  background: #f0f7ff;
  padding: 20px;
  border-radius: 8px;
}

.recommendation h4 {
  color: #2E86AB;
  margin-bottom: 10px;
}

.recommendation p {
  color: #2c3e50;
  line-height: 1.6;
  font-size: 15px;
}

.mt-20 {
  margin-top: 20px;
}

.loading-container {
  padding: 40px;
}
</style>
