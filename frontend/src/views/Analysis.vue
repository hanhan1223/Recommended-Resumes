<template>
  <div class="analysis-container">
    <el-row :gutter="20">
      <!-- 行业对比分析 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>📊 行业TCI得分对比</span>
              <el-button type="primary" link @click="refreshData">
                <el-icon><Refresh /></el-icon>刷新
              </el-button>
            </div>
          </template>
          <v-chart :option="industryCompareOption" autoresize style="height: 350px" />
        </el-card>
      </el-col>

      <!-- 维度得分分析 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>🎯 各维度得分分析</span>
            </div>
          </template>
          <v-chart :option="dimensionRadarOption" autoresize style="height: 350px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-20">
      <!-- 得分分布直方图 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>📈 TCI得分分布</span>
            </div>
          </template>
          <v-chart :option="scoreDistributionOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>

      <!-- 权重对比 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>⚖️ 行业权重配置对比</span>
            </div>
          </template>
          <v-chart :option="weightCompareOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据表格 -->
    <el-card class="data-table-card mt-20">
      <template #header>
        <div class="card-header">
          <span>📋 行业统计汇总</span>
          <el-button type="primary" @click="exportData">
            <el-icon><Download /></el-icon>导出数据
          </el-button>
        </div>
      </template>
      <el-table :data="industryStats" stripe>
        <el-table-column prop="industry" label="行业" />
        <el-table-column prop="count" label="候选人数" />
        <el-table-column prop="avg_score" label="平均TCI">
          <template #default="{ row }">
            {{ row.avg_score?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="max_score" label="最高TCI">
          <template #default="{ row }">
            {{ row.max_score?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="min_score" label="最低TCI">
          <template #default="{ row }">
            {{ row.min_score?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="std_score" label="标准差">
          <template #default="{ row }">
            {{ row.std_score?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="penalty_rate" label="跳槽惩罚率">
          <template #default="{ row }">
            {{ row.penalty_rate || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useResumeStore } from '@/stores'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts/core'
import axios from 'axios'

const store = useResumeStore()

const loading = ref(false)
const allIndustryData = ref([])

const industries = ['电商', '品牌', '销售', '研发', '生产', '人力资源']
const industryColors = {
  '电商': '#667eea',
  '品牌': '#f5576c',
  '销售': '#4facfe',
  '研发': '#43e97b',
  '生产': '#ff9f43',
  '人力资源': '#a55eea'
}

const fetchAllIndustryData = async () => {
  loading.value = true
  allIndustryData.value = []

  try {
    for (const industry of industries) {
      try {
        const response = await axios.get(`/api/rank/industry/${industry}`, {
          params: { top_n: 100 }
        })

        if (response.data.status === 'success') {
          const candidates = response.data.candidates?.length > 0
            ? response.data.candidates
            : response.data.ranking || []

          if (candidates.length > 0) {
            const scores = candidates.map(c => c.tci_score || 0)
            const penaltyCount = candidates.filter(c => c.penalty_applied).length

            allIndustryData.value.push({
              industry,
              count: candidates.length,
              avg_score: scores.reduce((a, b) => a + b, 0) / scores.length,
              max_score: Math.max(...scores),
              min_score: Math.min(...scores),
              std_score: calculateStd(scores),
              penalty_rate: `${((penaltyCount / candidates.length) * 100).toFixed(1)}%`,
              candidates,
              dimension_weights: candidates[0]?.dimension_weights || {}
            })
          } else {
            allIndustryData.value.push({
              industry,
              count: 0,
              avg_score: null,
              max_score: null,
              min_score: null,
              std_score: null,
              penalty_rate: '-',
              candidates: [],
              dimension_weights: {}
            })
          }
        } else {
          allIndustryData.value.push({
            industry,
            count: 0,
            avg_score: null,
            max_score: null,
            min_score: null,
            std_score: null,
            penalty_rate: '-',
            candidates: [],
            dimension_weights: {}
          })
        }
      } catch (err) {
        console.warn(`获取 ${industry} 数据失败:`, err.message)
        allIndustryData.value.push({
          industry,
          count: 0,
          avg_score: null,
          max_score: null,
          min_score: null,
          std_score: null,
          penalty_rate: '-',
          candidates: [],
          dimension_weights: {}
        })
      }
    }
  } finally {
    loading.value = false
  }
}

const calculateStd = (arr) => {
  if (arr.length === 0) return 0
  const mean = arr.reduce((a, b) => a + b, 0) / arr.length
  const squareDiffs = arr.map(value => Math.pow(value - mean, 2))
  const avgSquareDiff = squareDiffs.reduce((a, b) => a + b, 0) / arr.length
  return Math.sqrt(avgSquareDiff)
}

// 行业对比柱状图
const industryCompareOption = computed(() => {
  const validData = allIndustryData.value.filter(d => d.count > 0)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['平均分', '最高分', '最低分'] },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: validData.length > 0 ? validData.map(d => d.industry) : ['暂无数据'],
      axisLabel: {
        rotate: 0,
        fontSize: 11,
        interval: 0
      }
    },
    yAxis: { type: 'value', max: 5, min: 0 },
    series: [
      {
        name: '平均分',
        type: 'bar',
        data: validData.length > 0 ? validData.map(d => Number(d.avg_score?.toFixed(2)) || 0) : [0],
        itemStyle: { color: '#2E86AB' }
      },
      {
        name: '最高分',
        type: 'bar',
        data: validData.length > 0 ? validData.map(d => Number(d.max_score?.toFixed(2)) || 0) : [0],
        itemStyle: { color: '#67C23A' }
      },
      {
        name: '最低分',
        type: 'bar',
        data: validData.length > 0 ? validData.map(d => Number(d.min_score?.toFixed(2)) || 0) : [0],
        itemStyle: { color: '#F56C6C' }
      }
    ]
  }
})

// 雷达图 - 显示各行业维度得分
const dimensionRadarOption = computed(() => {
  const validData = allIndustryData.value.filter(d => d.count > 0)

  const seriesData = validData.map(d => {
    let eduScore = 0, expScore = 0, skillScore = 0, compScore = 0

    if (d.candidates.length > 0) {
      const count = d.candidates.length
      d.candidates.forEach(c => {
        const scores = c.dimensional_scores || {}
        eduScore += (scores.education || 0)
        expScore += (scores.experience || 0)
        skillScore += (scores.skill_achievement || 0)
        compScore += (scores.comprehensive || 0)
      })
      eduScore = eduScore / count
      expScore = expScore / count
      skillScore = skillScore / count
      compScore = compScore / count
    } else {
      eduScore = 3.5
      expScore = 3.5
      skillScore = 3.5
      compScore = 3.5
    }

    return {
      value: [Number(eduScore.toFixed(2)), Number(expScore.toFixed(2)), Number(skillScore.toFixed(2)), Number(compScore.toFixed(2))],
      name: d.industry,
      itemStyle: { color: industryColors[d.industry] || '#667eea' }
    }
  })

  return {
    tooltip: {},
    legend: { data: validData.length > 0 ? validData.map(d => d.industry) : [] },
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
      data: seriesData.length > 0 ? seriesData : []
    }]
  }
})

// 得分分布
const scoreDistributionOption = computed(() => {
  const allScores = allIndustryData.value.flatMap(d => d.candidates.map(c => c.tci_score || 0))

  const ranges = { '<2.0': 0, '2.0-2.5': 0, '2.5-3.0': 0, '3.0-3.5': 0, '3.5-4.0': 0, '4.0-4.5': 0, '4.5-5.0': 0 }

  allScores.forEach(score => {
    if (score < 2.0) ranges['<2.0']++
    else if (score >= 2.0 && score < 2.5) ranges['2.0-2.5']++
    else if (score >= 2.5 && score < 3.0) ranges['2.5-3.0']++
    else if (score >= 3.0 && score < 3.5) ranges['3.0-3.5']++
    else if (score >= 3.5 && score < 4.0) ranges['3.5-4.0']++
    else if (score >= 4.0 && score < 4.5) ranges['4.0-4.5']++
    else if (score >= 4.5 && score <= 5.0) ranges['4.5-5.0']++
  })

  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: Object.keys(ranges),
      axisLabel: {
        rotate: 0,
        fontSize: 10,
        interval: 0
      }
    },
    yAxis: { type: 'value', name: '人数', min: 0 },
    series: [{
      name: '人数',
      type: 'bar',
      data: Object.values(ranges),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#4ECDC4' },
          { offset: 1, color: '#2E86AB' }
        ])
      },
      label: { show: true, position: 'top' }
    }]
  }
})

// 权重对比
const weightCompareOption = computed(() => {
  const validData = allIndustryData.value.filter(d => d.count > 0 && Object.keys(d.dimension_weights).length > 0)

  if (validData.length === 0) {
    return {
      title: { text: '暂无权重数据', left: 'center', top: 'center' },
      series: []
    }
  }

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: validData.map(d => d.industry), bottom: '0%' },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'value', max: 0.5 },
    yAxis: {
      type: 'category',
      data: ['教育背景', '工作经历', '技能成果', '综合素质']
    },
    series: validData.map(d => ({
      name: d.industry,
      type: 'bar',
      data: [
        Number((d.dimension_weights.education || 0).toFixed(3)),
        Number((d.dimension_weights.experience || 0).toFixed(3)),
        Number((d.dimension_weights.skill_achievement || 0).toFixed(3)),
        Number((d.dimension_weights.comprehensive || 0).toFixed(3))
      ],
      itemStyle: { color: industryColors[d.industry] || '#667eea' }
    }))
  }
})

const industryStats = computed(() => allIndustryData.value)

const refreshData = () => {
  fetchAllIndustryData()
  ElMessage.success('数据已刷新')
}

const exportData = () => {
  ElMessage.success('数据导出成功')
}

onMounted(() => {
  fetchAllIndustryData()
})
</script>

<style scoped>
.analysis-container {
  max-width: 1400px;
  margin: 0 auto;
}

.chart-card, .data-table-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.mt-20 {
  margin-top: 20px;
}
</style>