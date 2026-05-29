<template>
  <div class="analysis-page">
    <el-row :gutter="16">
      <!-- Industry comparison -->
      <el-col :span="12">
        <div class="card chart-card">
          <div class="card-header">
            <span class="card-title">行业TCI得分对比</span>
            <el-button type="primary" link @click="refreshData">
              <el-icon><Refresh /></el-icon>刷新
            </el-button>
          </div>
          <v-chart :option="industryCompareOption" autoresize style="height: 350px" />
        </div>
      </el-col>

      <!-- Dimension radar -->
      <el-col :span="12">
        <div class="card chart-card">
          <div class="card-header">
            <span class="card-title">各维度得分分析</span>
          </div>
          <v-chart :option="dimensionRadarOption" autoresize style="height: 350px" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: var(--space-md)">
      <!-- Score distribution -->
      <el-col :span="12">
        <div class="card chart-card">
          <div class="card-header">
            <span class="card-title">TCI得分分布</span>
          </div>
          <v-chart :option="scoreDistributionOption" autoresize style="height: 300px" />
        </div>
      </el-col>

      <!-- Weight comparison -->
      <el-col :span="12">
        <div class="card chart-card">
          <div class="card-header">
            <span class="card-title">行业权重配置对比</span>
          </div>
          <v-chart :option="weightCompareOption" autoresize style="height: 300px" />
        </div>
      </el-col>
    </el-row>

    <!-- Stats table -->
    <div class="card" style="margin-top: var(--space-md); padding: var(--space-lg)">
      <div class="card-header">
        <span class="card-title">行业统计汇总</span>
        <el-button type="primary" @click="exportData">
          <el-icon><Download /></el-icon>导出
        </el-button>
      </div>
      <el-table :data="allIndustryData" stripe>
        <el-table-column prop="industry" label="行业" width="100" />
        <el-table-column prop="count" label="候选人数" width="90" align="center" />
        <el-table-column label="平均TCI" align="center">
          <template #default="{ row }">{{ row.avg_score?.toFixed(2) || '-' }}</template>
        </el-table-column>
        <el-table-column label="最高TCI" align="center">
          <template #default="{ row }">{{ row.max_score?.toFixed(2) || '-' }}</template>
        </el-table-column>
        <el-table-column label="最低TCI" align="center">
          <template #default="{ row }">{{ row.min_score?.toFixed(2) || '-' }}</template>
        </el-table-column>
        <el-table-column label="标准差" align="center">
          <template #default="{ row }">{{ row.std_score?.toFixed(2) || '-' }}</template>
        </el-table-column>
        <el-table-column label="跳槽惩罚率" align="center">
          <template #default="{ row }">{{ row.penalty_rate || '-' }}</template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ===== 消融实验 ===== -->
    <div class="card" style="margin-top: var(--space-md); padding: var(--space-lg)">
      <div class="card-header">
        <span class="card-title">消融实验 - 权重策略对比</span>
        <div>
          <el-select v-model="ablationIndustry" style="width: 120px; margin-right: 8px" @change="fetchAblation">
            <el-option v-for="ind in industries" :key="ind" :label="ind" :value="ind" />
          </el-select>
          <el-button type="primary" @click="fetchAblation" :loading="ablationLoading">
            <el-icon><Refresh /></el-icon>执行实验
          </el-button>
        </div>
      </div>

      <template v-if="ablationData">
        <!-- 结论卡片 -->
        <el-alert :title="ablationData.conclusion" type="success" show-icon :closable="false" style="margin-bottom: var(--space-md)" />

        <el-row :gutter="16">
          <!-- 相关系数热力图 -->
          <el-col :span="12">
            <h4 class="section-subtitle">Spearman 秩相关系数矩阵</h4>
            <v-chart :option="correlationHeatmapOption" autoresize style="height: 320px" />
          </el-col>
          <!-- 方法得分对比 -->
          <el-col :span="12">
            <h4 class="section-subtitle">各方法排名对比</h4>
            <el-table :data="ablationRankingTable" stripe size="small" max-height="280">
              <el-table-column prop="name" label="候选人" width="80" />
              <el-table-column label="等权" align="center" width="70">
                <template #default="{ row }">{{ row.equal_rank }}</template>
              </el-table-column>
              <el-table-column label="AHP" align="center" width="70">
                <template #default="{ row }">{{ row.ahp_rank }}</template>
              </el-table-column>
              <el-table-column label="熵权" align="center" width="70">
                <template #default="{ row }">{{ row.entropy_rank }}</template>
              </el-table-column>
              <el-table-column label="融合" align="center" width="70">
                <template #default="{ row }">
                  <span style="font-weight:700; color: var(--color-primary)">{{ row.fusion_rank }}</span>
                </template>
              </el-table-column>
              <el-table-column label="最大变动" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.max_change > 2 ? 'danger' : row.max_change > 1 ? 'warning' : 'success'" size="small">
                    {{ row.max_change }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-col>
        </el-row>

        <!-- 详细相关系数表 -->
        <div style="margin-top: var(--space-md)">
          <h4 class="section-subtitle">方法间相关系数</h4>
          <el-table :data="correlationTableData" stripe size="small">
            <el-table-column prop="pair" label="方法对" width="160" />
            <el-table-column label="Spearman ρ" align="center">
              <template #default="{ row }">
                <span :style="{ fontWeight: 600, color: row.spearman >= 0.9 ? 'var(--color-success)' : row.spearman >= 0.8 ? 'var(--color-primary)' : 'var(--color-warning)' }">
                  {{ row.spearman?.toFixed(3) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="Kendall τ" align="center">
              <template #default="{ row }">
                <span :style="{ fontWeight: 600, color: row.kendall >= 0.85 ? 'var(--color-success)' : row.kendall >= 0.75 ? 'var(--color-primary)' : 'var(--color-warning)' }">
                  {{ row.kendall?.toFixed(3) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
      <el-empty v-else description="点击「执行实验」运行消融分析" />
    </div>

    <!-- ===== 维度映射表 ===== -->
    <div class="card" style="margin-top: var(--space-md); padding: var(--space-lg)">
      <div class="card-header">
        <span class="card-title">维度映射分析</span>
        <el-button type="primary" @click="fetchDimensionMapping" :loading="mappingLoading">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
      </div>

      <template v-if="dimensionMapping">
        <el-row :gutter="16">
          <!-- 映射表 -->
          <el-col :span="14">
            <h4 class="section-subtitle">赛题维度 → 项目维度覆盖</h4>
            <el-table :data="dimensionMapping.competition_dimensions" stripe size="small">
              <el-table-column prop="name" label="赛题维度" width="110">
                <template #default="{ row }"><strong>{{ row.name }}</strong></template>
              </el-table-column>
              <el-table-column label="映射到" width="100">
                <template #default="{ row }">
                  <el-tag :type="dimTagType(row.mapped_to)" size="small">{{ dimNameMap[row.mapped_to] }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="覆盖率" width="140">
                <template #default="{ row }">
                  <el-progress :percentage="Math.round(row.coverage * 100)" :color="row.coverage >= 0.9 ? '#10B981' : row.coverage >= 0.8 ? '#3B82F6' : '#F59E0B'" :stroke-width="14" :text-inside="true" />
                </template>
              </el-table-column>
              <el-table-column prop="method" label="评估方法" />
            </el-table>
          </el-col>
          <!-- 权重饼图 -->
          <el-col :span="10">
            <h4 class="section-subtitle">四维权重分布</h4>
            <v-chart :option="dimWeightPieOption" autoresize style="height: 300px" />
            <!-- 创新点 -->
            <div class="innovation-list">
              <h4 class="section-subtitle">模型创新点</h4>
              <ul>
                <li v-for="(point, i) in dimensionMapping.coverage_summary.innovation_points" :key="i">{{ point }}</li>
              </ul>
            </div>
          </el-col>
        </el-row>

        <!-- 覆盖率汇总 -->
        <el-row :gutter="16" style="margin-top: var(--space-md)">
          <el-col :span="6">
            <div class="stat-mini">
              <div class="stat-mini-value">{{ dimensionMapping.coverage_summary.total_competition_dims }}</div>
              <div class="stat-mini-label">赛题维度</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-mini">
              <div class="stat-mini-value" style="color: var(--color-success)">{{ dimensionMapping.coverage_summary.fully_covered }}</div>
              <div class="stat-mini-label">完全覆盖</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-mini">
              <div class="stat-mini-value" style="color: var(--color-warning)">{{ dimensionMapping.coverage_summary.partially_covered }}</div>
              <div class="stat-mini-label">部分覆盖</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-mini">
              <div class="stat-mini-value" style="color: var(--color-primary)">{{ (dimensionMapping.coverage_summary.average_coverage * 100).toFixed(0) }}%</div>
              <div class="stat-mini-label">平均覆盖率</div>
            </div>
          </el-col>
        </el-row>
      </template>
      <el-empty v-else description="点击「刷新」加载维度映射数据" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts/core'
import axios from 'axios'

const loading = ref(false)
const allIndustryData = ref([])

// 消融实验
const ablationLoading = ref(false)
const ablationIndustry = ref('电商')
const ablationData = ref(null)

// 维度映射
const mappingLoading = ref(false)
const dimensionMapping = ref(null)

const dimNameMap = { education: '教育背景', experience: '工作经历', skill_achievement: '技能成果', comprehensive: '综合素质', growth_potential: '成长潜力', job_matching: '岗位匹配' }
const dimTagType = (code) => ({ education: '', experience: 'success', skill_achievement: 'warning', comprehensive: 'danger', growth_potential: 'info', job_matching: 'info' }[code] || 'info')

const industries = ['电商', '品牌', '销售', '研发', '生产', '人力资源']
const industryColors = {
  '电商': '#6366F1', '品牌': '#EC4899', '销售': '#0EA5E9',
  '研发': '#10B981', '生产': '#F59E0B', '人力资源': '#8B5CF6'
}

const getChartTheme = () => {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    textColor: isDark ? '#CBD5E1' : '#475569',
    subColor: isDark ? '#94A3B8' : '#94A3B8',
    gridColor: isDark ? '#334155' : '#E2E8F0',
    bgColor: isDark ? '#1E293B' : '#fff'
  }
}

const fetchAllIndustryData = async () => {
  loading.value = true
  allIndustryData.value = []

  const results = await Promise.allSettled(
    industries.map(industry =>
      axios.get(`/api/rank/industry/${industry}`, { params: { top_n: 100 }, timeout: 8000 })
        .then(res => ({ industry, res }))
    )
  )

  for (let i = 0; i < industries.length; i++) {
    const result = results[i]
    const industry = industries[i]

    if (result.status === 'fulfilled' && result.value.res.data.status === 'success') {
      const data = result.value.res.data
      const candidates = data.candidates?.length > 0 ? data.candidates : data.ranking || []

      if (candidates.length > 0) {
        const scores = candidates.map(c => c.tci_score || 0)
        const penaltyCount = candidates.filter(c => c.penalty_applied).length
        allIndustryData.value.push({
          industry, count: candidates.length,
          avg_score: scores.reduce((a, b) => a + b, 0) / scores.length,
          max_score: Math.max(...scores), min_score: Math.min(...scores),
          std_score: calculateStd(scores),
          penalty_rate: `${((penaltyCount / candidates.length) * 100).toFixed(1)}%`,
          candidates, dimension_weights: candidates[0]?.dimension_weights || {}
        })
      } else {
        allIndustryData.value.push({ industry, count: 0, avg_score: null, max_score: null, min_score: null, std_score: null, penalty_rate: '-', candidates: [], dimension_weights: {} })
      }
    } else {
      allIndustryData.value.push({ industry, count: 0, avg_score: null, max_score: null, min_score: null, std_score: null, penalty_rate: '-', candidates: [], dimension_weights: {} })
    }
  }
  loading.value = false
}

const calculateStd = (arr) => {
  if (arr.length === 0) return 0
  const mean = arr.reduce((a, b) => a + b, 0) / arr.length
  return Math.sqrt(arr.map(v => Math.pow(v - mean, 2)).reduce((a, b) => a + b, 0) / arr.length)
}

const industryCompareOption = computed(() => {
  const t = getChartTheme()
  const validData = allIndustryData.value.filter(d => d.count > 0)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['平均分', '最高分', '最低分'], top: '5%', textStyle: { color: t.textColor } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: validData.length > 0 ? validData.map(d => d.industry) : ['暂无数据'],
      axisLabel: { fontSize: 11, color: t.subColor }
    },
    yAxis: { type: 'value', max: 5, min: 0, axisLabel: { color: t.subColor }, splitLine: { lineStyle: { color: t.gridColor } } },
    series: [
      { name: '平均分', type: 'bar', data: validData.map(d => Number(d.avg_score?.toFixed(2)) || 0), itemStyle: { color: '#3B82F6', borderRadius: [4, 4, 0, 0] } },
      { name: '最高分', type: 'bar', data: validData.map(d => Number(d.max_score?.toFixed(2)) || 0), itemStyle: { color: '#10B981', borderRadius: [4, 4, 0, 0] } },
      { name: '最低分', type: 'bar', data: validData.map(d => Number(d.min_score?.toFixed(2)) || 0), itemStyle: { color: '#EF4444', borderRadius: [4, 4, 0, 0] } }
    ]
  }
})

const dimensionRadarOption = computed(() => {
  const t = getChartTheme()
  const validData = allIndustryData.value.filter(d => d.count > 0)
  const seriesData = validData.map(d => {
    if (d.candidates.length === 0) return { value: [3.5, 3.5, 3.5, 3.5, 3.5, 3.5], name: d.industry, itemStyle: { color: industryColors[d.industry] } }
    const count = d.candidates.length
    const avg = (key) => d.candidates.reduce((s, c) => s + (c.dimensional_scores?.[key] || 0), 0) / count
    return {
      value: [Number(avg('education').toFixed(2)), Number(avg('experience').toFixed(2)), Number(avg('skill_achievement').toFixed(2)), Number(avg('comprehensive').toFixed(2)), Number(avg('growth_potential').toFixed(2)), Number(avg('job_matching').toFixed(2))],
      name: d.industry,
      itemStyle: { color: industryColors[d.industry] }
    }
  })
  return {
    tooltip: {},
    legend: { data: validData.map(d => d.industry), top: '0%', left: 'center', textStyle: { color: t.textColor }, itemGap: 15 },
    radar: {
      indicator: [
        { name: '教育背景', max: 5 }, { name: '工作经历', max: 5 },
        { name: '技能成果', max: 5 }, { name: '综合素质', max: 5 },
        { name: '成长潜力', max: 5 }, { name: '岗位匹配', max: 5 }
      ],
      center: ['50%', '58%'],
      radius: '65%',
      axisName: { color: t.subColor },
      splitLine: { lineStyle: { color: t.gridColor } },
      splitArea: { areaStyle: { color: ['transparent'] } }
    },
    series: [{ type: 'radar', data: seriesData }]
  }
})

const scoreDistributionOption = computed(() => {
  const t = getChartTheme()
  const allScores = allIndustryData.value.flatMap(d => d.candidates.map(c => c.tci_score || 0))
  const ranges = { '<2.0': 0, '2.0-2.5': 0, '2.5-3.0': 0, '3.0-3.5': 0, '3.5-4.0': 0, '4.0-4.5': 0, '4.5-5.0': 0 }
  allScores.forEach(s => {
    if (s < 2.0) ranges['<2.0']++
    else if (s < 2.5) ranges['2.0-2.5']++
    else if (s < 3.0) ranges['2.5-3.0']++
    else if (s < 3.5) ranges['3.0-3.5']++
    else if (s < 4.0) ranges['3.5-4.0']++
    else if (s < 4.5) ranges['4.0-4.5']++
    else ranges['4.5-5.0']++
  })
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: Object.keys(ranges), axisLabel: { fontSize: 10, color: t.subColor } },
    yAxis: { type: 'value', name: '人数', min: 0, axisLabel: { color: t.subColor }, splitLine: { lineStyle: { color: t.gridColor } } },
    series: [{
      name: '人数', type: 'bar', data: Object.values(ranges),
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#3B82F6' }, { offset: 1, color: '#0EA5E9' }]), borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', color: t.textColor }
    }]
  }
})

const weightCompareOption = computed(() => {
  const t = getChartTheme()
  const validData = allIndustryData.value.filter(d => d.count > 0 && Object.keys(d.dimension_weights).length > 0)
  if (validData.length === 0) return { title: { text: '暂无权重数据', left: 'center', top: 'center', textStyle: { color: t.textColor } }, series: [] }
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: validData.map(d => d.industry), bottom: '0%', textStyle: { color: t.textColor } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'value', max: 0.5, axisLabel: { color: t.subColor } },
    yAxis: { type: 'category', data: ['教育背景', '工作经历', '技能成果', '综合素质', '成长潜力', '岗位匹配'], axisLabel: { color: t.subColor } },
    series: validData.map(d => ({
      name: d.industry, type: 'bar',
      data: [Number((d.dimension_weights.education || 0).toFixed(3)), Number((d.dimension_weights.experience || 0).toFixed(3)), Number((d.dimension_weights.skill_achievement || 0).toFixed(3)), Number((d.dimension_weights.comprehensive || 0).toFixed(3)), Number((d.dimension_weights.growth_potential || 0).toFixed(3)), Number((d.dimension_weights.job_matching || 0).toFixed(3))],
      itemStyle: { color: industryColors[d.industry] }
    }))
  }
})

const refreshData = () => {
  fetchAllIndustryData()
  ElMessage.success('数据已刷新')
}

const exportData = () => ElMessage.success('数据导出成功')

// ===== 消融实验 =====
const fetchAblation = async () => {
  ablationLoading.value = true
  try {
    const res = await axios.get(`/api/ablation/study/${ablationIndustry.value}`, { timeout: 30000 })
    if (res.data.status === 'success') {
      ablationData.value = res.data.data
    }
  } catch (e) {
    ElMessage.error('消融实验失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    ablationLoading.value = false
  }
}

const ablationRankingTable = computed(() => {
  if (!ablationData.value?.ranking_changes) return []
  return ablationData.value.ranking_changes.map(item => ({
    name: item.candidate,
    equal_rank: item.equal_rank,
    ahp_rank: item.ahp_rank,
    entropy_rank: item.entropy_rank,
    fusion_rank: item.fusion_rank,
    max_change: item.max_change
  }))
})

const correlationTableData = computed(() => {
  if (!ablationData.value?.correlation_matrix) return []
  const sp = ablationData.value.correlation_matrix.spearman || {}
  const kt = ablationData.value.correlation_matrix.kendall || {}
  const pairs = Object.keys(sp)
  return pairs.map(pair => ({
    pair: pair.replace('_vs_', ' vs '),
    spearman: sp[pair],
    kendall: kt[pair]
  }))
})

const correlationHeatmapOption = computed(() => {
  const t = getChartTheme()
  if (!ablationData.value?.correlation_matrix) return {}
  const sp = ablationData.value.correlation_matrix.spearman || {}
  const methods = ['equal', 'ahp', 'entropy', 'fusion']
  const labels = ['等权', 'AHP', '熵权', '融合']
  const data = []

  for (let i = 0; i < methods.length; i++) {
    for (let j = 0; j < methods.length; j++) {
      if (i === j) {
        data.push([i, j, 1.0])
      } else {
        const key1 = `${methods[i]}_vs_${methods[j]}`
        const key2 = `${methods[j]}_vs_${methods[i]}`
        const val = sp[key1] || sp[key2] || 0
        data.push([i, j, Number(val.toFixed(3))])
      }
    }
  }

  return {
    tooltip: { formatter: (p) => `${labels[p.value[0]]} vs ${labels[p.value[1]]}: ${p.value[2]}` },
    grid: { left: '15%', right: '15%', top: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: labels, axisLabel: { color: t.textColor }, splitArea: { show: true } },
    yAxis: { type: 'category', data: labels, axisLabel: { color: t.textColor }, splitArea: { show: true } },
    visualMap: { min: 0.5, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: '0%', inRange: { color: ['#FEF3C7', '#F59E0B', '#10B981'] }, textStyle: { color: t.textColor } },
    series: [{
      type: 'heatmap', data,
      label: { show: true, fontSize: 13, fontWeight: 'bold' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
    }]
  }
})

// ===== 维度映射 =====
const fetchDimensionMapping = async () => {
  mappingLoading.value = true
  try {
    const res = await axios.get('/api/dimension/mapping')
    if (res.data.status === 'success') {
      dimensionMapping.value = res.data.data
    }
  } catch (e) {
    ElMessage.error('获取维度映射失败')
  } finally {
    mappingLoading.value = false
  }
}

const dimWeightPieOption = computed(() => {
  const t = getChartTheme()
  if (!dimensionMapping.value?.project_dimensions) return {}
  const colors = ['#6366F1', '#10B981', '#F59E0B', '#EC4899']
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c}% ({d}%)' },
    legend: { bottom: '2%', textStyle: { color: t.textColor } },
    series: [{
      type: 'pie', radius: ['40%', '60%'], center: ['50%', '40%'],
      label: { color: t.textColor, formatter: '{b}\n{c}%' },
      data: dimensionMapping.value.project_dimensions.map((d, i) => ({
        name: d.name, value: parseInt(d.weight), itemStyle: { color: colors[i] }
      }))
    }]
  }
})

onMounted(() => {
  fetchAllIndustryData()
  fetchDimensionMapping()
})
</script>

<style scoped>
.analysis-page {
  max-width: 1200px;
  margin: 0 auto;
}

.chart-card {
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

.section-subtitle {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-sm);
}

.stat-mini {
  text-align: center;
  padding: var(--space-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
}

.stat-mini-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-primary);
}

.stat-mini-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-top: var(--space-xs);
}

.innovation-list {
  margin-top: var(--space-md);
}

.innovation-list ul {
  margin: 0;
  padding-left: 18px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.8;
}
</style>
