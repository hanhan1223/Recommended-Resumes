<template>
  <div class="ranking-container">
    <!-- 筛选栏 -->
    <el-card class="filter-card" shadow="never">
      <el-row :gutter="20" align="middle">
        <el-col :span="8">
          <label class="filter-label">选择行业：</label>
          <el-select v-model="selectedIndustry" placeholder="请选择行业" @change="handleIndustryChange" style="width: 200px;">
            <el-option
              v-for="item in store.industries"
              :key="item.code"
              :label="item.name"
              :value="item.code"
            />
          </el-select>
        </el-col>
        <el-col :span="5">
          <label class="filter-label">显示数量：</label>
          <el-select v-model="topN" @change="handleTopNChange" style="width: 120px;">
            <el-option label="Top 5" :value="5" />
            <el-option label="Top 10" :value="10" />
            <el-option label="Top 20" :value="20" />
            <el-option label="全部" :value="100" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-button type="primary" @click="refreshRankings" :loading="store.loading">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </el-col>
        <el-col :span="6" style="text-align: right;">
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
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-box primary">
          <el-icon :size="32"><User /></el-icon>
          <div class="stat-info">
            <div class="stat-value">{{ store.industryStats.count || 0 }}</div>
            <div class="stat-label">候选人总数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-box success">
          <el-icon :size="32"><Trophy /></el-icon>
          <div class="stat-info">
            <div class="stat-value">{{ formatScore(store.industryStats.max) }}</div>
            <div class="stat-label">最高TCI得分</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-box warning">
          <el-icon :size="32"><TrendCharts /></el-icon>
          <div class="stat-info">
            <div class="stat-value">{{ formatScore(store.industryStats.avg) }}</div>
            <div class="stat-label">平均TCI得分</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-box danger">
          <el-icon :size="32"><WarnTriangleFilled /></el-icon>
          <div class="stat-info">
            <div class="stat-value">{{ penaltyCount }}</div>
            <div class="stat-label">跳槽惩罚人数</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 主内容区 -->
    <el-row :gutter="20">
      <!-- 排名列表 -->
      <el-col :span="14">
        <el-card class="ranking-card">
          <template #header>
            <div class="card-header">
              <span>🏆 {{ currentIndustryName }}排名榜</span>
              <el-tag type="info">共 {{ store.rankings.length }} 人</el-tag>
            </div>
          </template>
          
          <!-- 错误提示 -->
          <el-alert
            v-if="store.error"
            :title="store.error"
            type="warning"
            :closable="false"
            show-icon
            style="margin-bottom: 15px"
          />
          
          <!-- 空状态提示 -->
          <el-empty
            v-else-if="!store.loading && store.rankings.length === 0 && selectedIndustry"
            description="该行业暂无候选人数据"
          >
            <template #description>
              <p>该行业暂无候选人数据</p>
              <p style="font-size: 12px; color: #999; margin-top: 10px;">
                请先上传并解析该行业的简历文件
              </p>
            </template>
            <el-button type="primary" @click="$router.push('/upload')">
              去上传简历
            </el-button>
          </el-empty>
          
          <el-table
            v-else
            :data="store.rankings"
            stripe
            v-loading="store.loading"
            style="width: 100%"
          >
            <el-table-column type="index" label="排名" width="80" align="center">
              <template #default="{ $index }">
                <div class="rank-badge" :class="`rank-${$index + 1}`">
                  {{ $index + 1 }}
                </div>
              </template>
            </el-table-column>
            
            <el-table-column prop="candidate_id" label="候选人" min-width="120">
              <template #default="{ row }">
                <div class="candidate-name">
                  <el-avatar :size="32" :icon="UserFilled" />
                  <span>{{ row.candidate_id }}</span>
                  <el-tag v-if="row.penalty_applied" type="danger" size="small" effect="plain">
                    跳槽惩罚
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            
            <el-table-column label="TCI得分" width="150" sortable>
              <template #default="{ row }">
                <div class="score-display">
                  <span class="score-value">{{ formatScore(row.tci_score) }}</span>
                  <el-progress
                    :percentage="parseFloat((row.tci_score / 5) * 100).toFixed(1)"
                    :color="getScoreColor(row.tci_score)"
                    :show-text="false"
                    style="width: 80px"
                  />
                </div>
              </template>
            </el-table-column>
            
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button type="primary" link @click="viewDetail(row)">
                  详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 可视化图表 -->
      <el-col :span="10">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>📊 得分分布</span>
            </div>
          </template>
          <div class="chart-container">
            <v-chart :option="barChartOption" autoresize style="height: 300px" />
          </div>
        </el-card>

        <el-card class="chart-card" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>🎯 维度权重</span>
            </div>
          </template>
          <div class="chart-container">
            <v-chart :option="pieChartOption" autoresize style="height: 250px" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResumeStore } from '@/stores'
import { ElMessage } from 'element-plus'
import { formatScore, formatPercentage } from '@/utils/format'
import { exportUtils } from '@/utils/export'

const route = useRoute()
const router = useRouter()
const store = useResumeStore()

const selectedIndustry = ref('')
const topN = ref(10)

const currentIndustryName = computed(() => {
  const industry = store.industries.find(i => i.code === selectedIndustry.value)
  return industry?.name || selectedIndustry.value
})

const penaltyCount = computed(() => {
  return store.rankings.filter(r => r.penalty_applied).length
})

// 柱状图配置
const barChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: {
    type: 'category',
    data: store.rankings.slice(0, 10).map(r => r.candidate_id),
    axisLabel: { rotate: 30 }
  },
  yAxis: { type: 'value', max: 5 },
  series: [{
    data: store.rankings.slice(0, 10).map(r => ({
      value: parseFloat(r.tci_score.toFixed(2)),
      itemStyle: { color: r.penalty_applied ? '#ff6b6b' : '#4ECDC4' }
    })),
    type: 'bar',
    barWidth: '60%',
    label: { show: true, position: 'top', formatter: '{c}' }
  }]
}))

// 饼图配置
const pieChartOption = computed(() => {
  const weights = store.candidates[0]?.dimension_weights || {
    education: 0.15,
    experience: 0.30,
    skill_achievement: 0.40,
    comprehensive: 0.15
  }
  
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}: {d}%' },
      data: [
        { value: weights.education * 100, name: '教育背景', itemStyle: { color: '#667eea' } },
        { value: weights.experience * 100, name: '工作经历', itemStyle: { color: '#f5576c' } },
        { value: weights.skill_achievement * 100, name: '技能成果', itemStyle: { color: '#4facfe' } },
        { value: weights.comprehensive * 100, name: '综合素质', itemStyle: { color: '#43e97b' } }
      ]
    }]
  }
})

const getScoreColor = (score) => {
  if (score >= 4) return '#67C23A'
  if (score >= 3) return '#E6A23C'
  return '#F56C6C'
}

const handleIndustryChange = () => {
  store.fetchRankings(selectedIndustry.value, topN.value)
  store.batchScore(selectedIndustry.value)
}

const handleTopNChange = () => {
  if (selectedIndustry.value) {
    store.fetchRankings(selectedIndustry.value, topN.value)
  }
}

const refreshRankings = () => {
  if (selectedIndustry.value) {
    handleIndustryChange()
    ElMessage.success('排名已刷新')
  } else {
    ElMessage.warning('请先选择行业')
  }
}

const viewDetail = (row) => {
  router.push(`/candidate/${row.candidate_id}`)
}

const handleExportExcel = () => {
  if (!selectedIndustry.value) {
    ElMessage.warning('请先选择行业')
    return
  }
  if (!store.rankings || store.rankings.length === 0) {
    ElMessage.warning('没有数据可导出')
    return
  }
  try {
    exportUtils.exportToExcel(store.rankings, selectedIndustry.value, `${selectedIndustry.value}_排名报告`)
    ElMessage.success('Excel报告已下载')
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  }
}

const handleExportPDF = async () => {
  if (!selectedIndustry.value) {
    ElMessage.warning('请先选择行业')
    return
  }
  if (!store.rankings || store.rankings.length === 0) {
    ElMessage.warning('没有数据可导出')
    return
  }
  try {
    ElMessage.info('正在生成PDF报告...')
    await exportUtils.exportToPDF({
      rankings: store.rankings,
      industry: selectedIndustry.value,
      candidates: store.candidates
    }, `${selectedIndustry.value}_排名报告`)
    ElMessage.success('PDF报告已下载')
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  }
}

onMounted(() => {
  store.fetchIndustries()
  
  // 从URL参数获取行业
  const industryFromQuery = route.query.industry
  if (industryFromQuery) {
    selectedIndustry.value = industryFromQuery
    handleIndustryChange()
  }
})
</script>

<style scoped>
.ranking-container {
  max-width: 1400px;
  margin: 0 auto;
}

.filter-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.filter-label {
  font-weight: 500;
  margin-right: 10px;
  color: #666;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-box {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.stat-box.primary { border-left: 4px solid #409EFF; }
.stat-box.success { border-left: 4px solid #67C23A; }
.stat-box.warning { border-left: 4px solid #E6A23C; }
.stat-box.danger { border-left: 4px solid #F56C6C; }

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #2c3e50;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.ranking-card, .chart-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.rank-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin: 0 auto;
}

.rank-1 { background: #FFD700; color: #fff; }
.rank-2 { background: #C0C0C0; color: #fff; }
.rank-3 { background: #CD7F32; color: #fff; }
.rank-badge:not(.rank-1):not(.rank-2):not(.rank-3) { background: #2E86AB; color: #fff; }

.candidate-name {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-display {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-value {
  font-weight: bold;
  font-size: 16px;
  color: #2E86AB;
}

.chart-container {
  padding: 10px;
}
</style>
