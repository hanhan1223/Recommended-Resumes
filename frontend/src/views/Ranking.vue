<template>
  <div class="ranking-page">
    <!-- Filter Bar -->
    <div class="card filter-bar">
      <el-row :gutter="16" align="middle">
        <el-col :span="7">
          <div class="filter-item">
            <label class="filter-label">行业</label>
            <el-select v-model="selectedIndustry" placeholder="选择行业" @change="handleIndustryChange" style="width: 100%">
              <el-option v-for="item in store.industries" :key="item.code" :label="item.name" :value="item.code" />
            </el-select>
          </div>
        </el-col>
        <el-col :span="5">
          <div class="filter-item">
            <label class="filter-label">数量</label>
            <el-select v-model="topN" @change="handleTopNChange" style="width: 100%">
              <el-option label="Top 5" :value="5" />
              <el-option label="Top 10" :value="10" />
              <el-option label="Top 20" :value="20" />
              <el-option label="全部" :value="100" />
            </el-select>
          </div>
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="refreshRankings" :loading="store.loading">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </el-col>
        <el-col :span="6" style="text-align: right">
          <el-button-group>
            <el-button type="success" @click="handleExportExcel" :disabled="!selectedIndustry">
              <el-icon><Download /></el-icon>Excel
            </el-button>
            <el-button type="danger" @click="handleExportPDF" :disabled="!selectedIndustry">
              <el-icon><Document /></el-icon>PDF
            </el-button>
          </el-button-group>
        </el-col>
      </el-row>
    </div>

    <!-- Stats -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" v-for="stat in statCards" :key="stat.label">
        <div class="card stat-card">
          <el-icon :size="28" :color="stat.color"><component :is="stat.icon" /></el-icon>
          <div class="stat-info">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Main Content -->
    <el-row :gutter="16">
      <!-- Ranking Table -->
      <el-col :span="14">
        <div class="card ranking-card">
          <div class="card-header">
            <span class="card-title">{{ currentIndustryName }} 排名榜</span>
            <el-tag type="info" size="small">{{ store.rankings.length }} 人</el-tag>
          </div>

          <el-alert v-if="store.error" :title="store.error" type="warning" :closable="false" show-icon style="margin-bottom: var(--space-md)" />

          <el-empty v-else-if="!store.loading && store.rankings.length === 0 && selectedIndustry" description="暂无数据">
            <el-button type="primary" @click="$router.push('/upload')">上传简历</el-button>
          </el-empty>

          <el-table v-else :data="store.rankings" stripe v-loading="store.loading" style="width: 100%">
            <el-table-column type="index" label="排名" width="70" align="center">
              <template #default="{ $index }">
                <div class="rank-badge" :class="`rank-${$index + 1}`">{{ $index + 1 }}</div>
              </template>
            </el-table-column>

            <el-table-column prop="candidate_id" label="候选人" min-width="120">
              <template #default="{ row }">
                <div class="candidate-cell">
                  <span class="candidate-name">{{ row.candidate_id }}</span>
                  <el-tag v-if="row.penalty_applied" type="danger" size="small" effect="plain">跳槽惩罚</el-tag>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="TCI得分" width="160" sortable>
              <template #default="{ row }">
                <div class="score-cell">
                  <span class="score-val">{{ formatScore(row.tci_score) }}</span>
                  <el-progress
                    :percentage="parseFloat((row.tci_score / 5) * 100)"
                    :color="getScoreColor(row.tci_score)"
                    :show-text="false"
                    :stroke-width="6"
                    style="width: 80px"
                  />
                </div>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button type="primary" link @click="viewDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>

      <!-- Charts -->
      <el-col :span="10">
        <div class="card chart-card">
          <div class="card-header">
            <span class="card-title">得分分布</span>
          </div>
          <v-chart :option="barChartOption" autoresize style="height: 280px" />
        </div>

        <div class="card chart-card" style="margin-top: var(--space-md)">
          <div class="card-header">
            <span class="card-title">维度权重</span>
          </div>
          <v-chart :option="pieChartOption" autoresize style="height: 300px" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResumeStore } from '@/stores'
import { ElMessage } from 'element-plus'
import { formatScore } from '@/utils/format'
import { exportUtils } from '@/utils/export'
import { User, Trophy, TrendCharts, WarnTriangleFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const store = useResumeStore()

const selectedIndustry = ref('')
const topN = ref(10)

const currentIndustryName = computed(() => {
  const industry = store.industries.find(i => i.code === selectedIndustry.value)
  return industry?.name || selectedIndustry.value || '请选择行业'
})

const penaltyCount = computed(() => store.rankings.filter(r => r.penalty_applied).length)

const statCards = computed(() => [
  { label: '候选人总数', value: store.industryStats.count || 0, icon: 'User', color: 'var(--color-primary)' },
  { label: '最高TCI', value: formatScore(store.industryStats.max), icon: 'Trophy', color: 'var(--color-success)' },
  { label: '平均TCI', value: formatScore(store.industryStats.avg), icon: 'TrendCharts', color: 'var(--color-warning)' },
  { label: '跳槽惩罚', value: penaltyCount.value, icon: 'WarnTriangleFilled', color: 'var(--color-danger)' }
])

const barChartOption = computed(() => {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: store.rankings.slice(0, 10).map(r => r.candidate_id),
      axisLabel: { rotate: 30, fontSize: 11, color: isDark ? '#94A3B8' : '#64748B' }
    },
    yAxis: {
      type: 'value', max: 5,
      axisLabel: { color: isDark ? '#94A3B8' : '#64748B' },
      splitLine: { lineStyle: { color: isDark ? '#334155' : '#E2E8F0' } }
    },
    series: [{
      data: store.rankings.slice(0, 10).map(r => ({
        value: parseFloat(r.tci_score.toFixed(2)),
        itemStyle: { color: r.penalty_applied ? '#EF4444' : '#3B82F6', borderRadius: [4, 4, 0, 0] }
      })),
      type: 'bar',
      barWidth: '60%',
      label: { show: true, position: 'insideTop', fontSize: 11, color: '#fff', distance: 6 }
    }]
  }
})

const pieChartOption = computed(() => {
  const weights = store.candidates[0]?.dimension_weights || {
    education: 0.12, experience: 0.25, skill_achievement: 0.32, comprehensive: 0.15, growth_potential: 0.10, job_matching: 0.10
  }
  const isDark = document.documentElement.classList.contains('dark')
  return {
    tooltip: { trigger: 'item' },
    legend: {
      orient: 'horizontal',
      bottom: '0%',
      itemGap: 16,
      textStyle: { color: isDark ? '#CBD5E1' : '#475569', fontSize: 11 }
    },
    series: [{
      type: 'pie',
      radius: ['35%', '50%'],
      center: ['50%', '40%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: isDark ? '#1E293B' : '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 11, lineHeight: 14 },
      data: [
        { value: (weights.education || 0) * 100, name: '教育背景', itemStyle: { color: '#6366F1' } },
        { value: (weights.experience || 0) * 100, name: '工作经历', itemStyle: { color: '#EC4899' } },
        { value: (weights.skill_achievement || 0) * 100, name: '技能成果', itemStyle: { color: '#0EA5E9' } },
        { value: (weights.comprehensive || 0) * 100, name: '综合素质', itemStyle: { color: '#10B981' } },
        { value: (weights.growth_potential || 0) * 100, name: '成长潜力', itemStyle: { color: '#F59E0B' } },
        { value: (weights.job_matching || 0) * 100, name: '岗位匹配', itemStyle: { color: '#8B5CF6' } }
      ]
    }]
  }
})

const getScoreColor = (score) => {
  if (score >= 4) return '#16A34A'
  if (score >= 3) return '#D97706'
  return '#DC2626'
}

const handleIndustryChange = () => {
  store.fetchRankings(selectedIndustry.value, topN.value)
  store.batchScore(selectedIndustry.value)
}

const handleTopNChange = () => {
  if (selectedIndustry.value) store.fetchRankings(selectedIndustry.value, topN.value)
}

const refreshRankings = () => {
  if (selectedIndustry.value) {
    handleIndustryChange()
    ElMessage.success('排名已刷新')
  } else {
    ElMessage.warning('请先选择行业')
  }
}

const viewDetail = (row) => router.push(`/candidate/${row.candidate_id}`)

const handleExportExcel = () => {
  if (!selectedIndustry.value || !store.rankings.length) {
    ElMessage.warning('没有数据可导出')
    return
  }
  try {
    exportUtils.exportToExcel(store.rankings, selectedIndustry.value, `${selectedIndustry.value}_排名报告`)
    ElMessage.success('Excel报告已下载')
  } catch (e) {
    ElMessage.error('导出失败: ' + e.message)
  }
}

const handleExportPDF = async () => {
  if (!selectedIndustry.value || !store.rankings.length) {
    ElMessage.warning('没有数据可导出')
    return
  }
  try {
    ElMessage.info('正在生成PDF...')
    await exportUtils.exportToPDF({ rankings: store.rankings, industry: selectedIndustry.value, candidates: store.candidates }, `${selectedIndustry.value}_排名报告`)
    ElMessage.success('PDF已下载')
  } catch (e) {
    ElMessage.error('导出失败: ' + e.message)
  }
}

onMounted(() => {
  store.fetchIndustries()
  const industryFromQuery = route.query.industry
  if (industryFromQuery) {
    selectedIndustry.value = industryFromQuery
    handleIndustryChange()
  }
})
</script>

<style scoped>
.ranking-page {
  max-width: 1200px;
  margin: 0 auto;
}

.filter-bar {
  padding: var(--space-md) var(--space-lg);
  margin-bottom: var(--space-md);
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

.stats-row {
  margin-bottom: var(--space-md);
}

.stat-card {
  padding: var(--space-md) var(--space-lg);
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.ranking-card, .chart-card {
  padding: var(--space-lg);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
}

.card-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.rank-badge {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--font-size-sm);
  margin: 0 auto;
}

.rank-1 { background: #FBBF24; color: #78350F; }
.rank-2 { background: #9CA3AF; color: #1F2937; }
.rank-3 { background: #D97706; color: #fff; }
.rank-badge:not(.rank-1):not(.rank-2):not(.rank-3) { background: var(--color-primary-bg); color: var(--color-primary); }

.candidate-cell {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.candidate-name {
  font-weight: 500;
  color: var(--color-text-primary);
}

.score-cell {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.score-val {
  font-weight: 700;
  font-size: var(--font-size-base);
  color: var(--color-primary);
  min-width: 36px;
}
</style>
