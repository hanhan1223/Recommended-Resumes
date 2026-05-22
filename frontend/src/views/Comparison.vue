<template>
  <div class="comparison-page">
    <h1>候选人对比分析</h1>
    
    <!-- 行业选择区 -->
    <div class="industry-section">
      <h2>选择行业</h2>
      <div class="industry-selector">
        <select v-model="selectedIndustry" @change="onIndustryChange" class="industry-select">
          <option value="">全部行业</option>
          <option v-for="industry in industries" :key="industry.code" :value="industry.code">
            {{ industry.name }} ({{ industry.candidate_count }}人)
          </option>
        </select>
        <span class="industry-hint">选择特定行业可进行更精准的对比分析</span>
      </div>
    </div>
    
    <!-- 候选人选择区 -->
    <div class="selection-section">
      <h2>选择对比候选人</h2>
      <div class="candidate-selector">
        <div 
          v-for="candidate in availableCandidates" 
          :key="candidate.id"
          class="candidate-card"
          :class="{ selected: selectedCandidates.includes(candidate.id) }"
          @click="toggleCandidate(candidate.id)"
        >
          <div class="candidate-name">{{ candidate.name }}</div>
          <div class="candidate-score">TCI: {{ candidate.tci_score.toFixed(2) }}</div>
          <div class="candidate-rank">排名: {{ candidate.rank }}</div>
        </div>
      </div>
      <div class="selection-actions">
        <button 
          class="btn-primary" 
          @click="startComparison"
          :disabled="selectedCandidates.length < 2"
        >
          开始对比 (已选{{ selectedCandidates.length }}人)
        </button>
        <button class="btn-secondary" @click="clearSelection">清空选择</button>
      </div>
    </div>

    <!-- 对比结果展示区 -->
    <div v-if="comparisonResult" class="comparison-result">
      <h2>对比结果</h2>
      
      <!-- 对比总结 -->
      <div class="summary-card">
        <h3>对比总结</h3>
        <p>{{ comparisonResult.summary }}</p>
        <div class="recommendation-order">
          <strong>推荐排序:</strong>
          <span 
            v-for="(name, index) in comparisonResult.recommendation_order" 
            :key="name"
            class="order-item"
          >
            {{ index + 1 }}. {{ name }}
          </span>
        </div>
      </div>

      <!-- 各维度对比 -->
      <div class="dimensions-comparison">
        <h3>各维度得分对比</h3>
        <div class="dimension-charts">
          <div 
            v-for="(ranking, dimension) in comparisonResult.dimension_comparison" 
            :key="dimension"
            class="dimension-card"
          >
            <h4>{{ getDimensionName(dimension) }}</h4>
            <div class="ranking-list">
              <div 
                v-for="(item, index) in ranking.slice(0, 3)" 
                :key="item[0]"
                class="ranking-item"
                :class="{ 'top-rank': index === 0 }"
              >
                <span class="rank">{{ index + 1 }}</span>
                <span class="name">{{ item[0] }}</span>
                <span class="score">{{ item[1].toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 优势分析 -->
      <div class="advantage-analysis">
        <h3>优势分析</h3>
        <div class="advantage-grid">
          <div 
            v-for="(advantages, name) in comparisonResult.advantage_matrix" 
            :key="name"
            class="advantage-card"
          >
            <h4>{{ name }}</h4>
            <div class="advantage-section" v-if="advantages.top_dimensions.length">
              <strong>最强维度:</strong>
              <span>{{ advantages.top_dimensions.join(', ') }}</span>
            </div>
            <div class="advantage-section" v-if="advantages.key_achievements.length">
              <strong>关键成就:</strong>
              <ul>
                <li v-for="(achievement, idx) in advantages.key_achievements.slice(0, 2)" :key="idx">
                  {{ achievement.substring(0, 50) }}...
                </li>
              </ul>
            </div>
            <div class="advantage-section" v-if="advantages.unique_skills.length">
              <strong>独特技能:</strong>
              <span>{{ advantages.unique_skills.slice(0, 5).join(', ') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 差距分析 -->
      <div class="gap-analysis" v-if="Object.keys(comparisonResult.gap_analysis).length">
        <h3>差距分析</h3>
        <div class="gap-list">
          <div 
            v-for="(gap, name) in comparisonResult.gap_analysis" 
            :key="name"
            class="gap-item"
            :class="{ 'is-top': gap.is_top }"
          >
            <span class="gap-name">{{ name }}</span>
            <span v-if="gap.is_top" class="gap-badge top">第一名</span>
            <span v-else class="gap-badge">
              差距: {{ gap.overall_gap.toFixed(2) }}分
            </span>
          </div>
        </div>
      </div>

      <!-- 候选人详情对比表 -->
      <div class="candidate-details">
        <h3>候选人详情</h3>
        <table class="comparison-table">
          <thead>
            <tr>
              <th>候选人</th>
              <th>TCI得分</th>
              <th>教育背景</th>
              <th>工作经历</th>
              <th>技能成果</th>
              <th>综合素质</th>
              <th>风险数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="candidate in comparisonResult.candidate_details" :key="candidate.name">
              <td><strong>{{ candidate.name }}</strong></td>
              <td class="score-highlight">{{ candidate.tci_score.toFixed(2) }}</td>
              <td>{{ candidate.dimensional_scores.education?.toFixed(2) || '-' }}</td>
              <td>{{ candidate.dimensional_scores.experience?.toFixed(2) || '-' }}</td>
              <td>{{ candidate.dimensional_scores.skill_achievement?.toFixed(2) || '-' }}</td>
              <td>{{ candidate.dimensional_scores.comprehensive?.toFixed(2) || '-' }}</td>
              <td :class="{ 'risk-high': candidate.risk_count > 0 }">
                {{ candidate.risk_count }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 导出按钮 -->
      <div class="export-section">
        <button class="btn-export" @click="exportReport('json')">
          导出JSON报告
        </button>
        <button class="btn-export" @click="exportReport('excel')">
          导出Excel报告
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>正在分析对比数据...</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'Comparison',
  setup() {
    const availableCandidates = ref([])
    const selectedCandidates = ref([])
    const comparisonResult = ref(null)
    const loading = ref(false)
    const industries = ref([])
    const selectedIndustry = ref('')

    // 获取行业列表
    const fetchIndustries = async () => {
      try {
        const response = await axios.get('/api/industries')
        if (response.data.status === 'success') {
          industries.value = response.data.industries
        }
      } catch (error) {
        console.error('获取行业列表失败:', error)
      }
    }

    // 获取可用候选人列表
    const fetchCandidates = async () => {
      try {
        const params = selectedIndustry.value ? { industry: selectedIndustry.value } : {}
        const response = await axios.get('/api/comparison/available-candidates', { params })
        if (response.data.status === 'success') {
          availableCandidates.value = response.data.candidates
          // 清空已选择的候选人（因为行业变了）
          selectedCandidates.value = []
          comparisonResult.value = null
        }
      } catch (error) {
        console.error('获取候选人列表失败:', error)
        alert('获取候选人列表失败，请稍后重试')
      }
    }

    // 行业切换处理
    const onIndustryChange = () => {
      fetchCandidates()
    }

    // 切换候选人选择
    const toggleCandidate = (id) => {
      const index = selectedCandidates.value.indexOf(id)
      if (index > -1) {
        selectedCandidates.value.splice(index, 1)
      } else {
        if (selectedCandidates.value.length < 5) {
          selectedCandidates.value.push(id)
        } else {
          alert('最多只能选择5位候选人进行对比')
        }
      }
    }

    // 清空选择
    const clearSelection = () => {
      selectedCandidates.value = []
      comparisonResult.value = null
    }

    // 开始对比
    const startComparison = async () => {
      if (selectedCandidates.value.length < 2) {
        alert('请至少选择2位候选人')
        return
      }

      loading.value = true
      try {
        const response = await axios.post('/api/comparison/analyze', {
          resume_ids: selectedCandidates.value,
          job_requirements: null
        })
        
        if (response.data.status === 'success') {
          comparisonResult.value = response.data.comparison_result
        }
      } catch (error) {
        console.error('对比分析失败:', error)
        alert('对比分析失败: ' + (error.response?.data?.detail || '未知错误'))
      } finally {
        loading.value = false
      }
    }

    // 获取维度中文名
    const getDimensionName = (dimension) => {
      const names = {
        'overall': '综合评分',
        'education': '教育背景',
        'experience': '工作经历',
        'skill_achievement': '技能成果',
        'comprehensive': '综合素质'
      }
      return names[dimension] || dimension
    }

    // 导出报告
    const exportReport = async (format) => {
      try {
        const response = await axios.post('/api/report/export', {
          report_type: 'comparison',
          data: comparisonResult.value,
          format: format
        })
        
        if (response.data.status === 'success') {
          let blob
          
          if (format === 'json') {
            // JSON格式直接转换
            blob = new Blob([JSON.stringify(response.data.data, null, 2)], {
              type: 'application/json'
            })
          } else if (format === 'excel') {
            // Excel格式需要解码base64
            const byteCharacters = atob(response.data.data)
            const byteNumbers = new Array(byteCharacters.length)
            for (let i = 0; i < byteCharacters.length; i++) {
              byteNumbers[i] = byteCharacters.charCodeAt(i)
            }
            const byteArray = new Uint8Array(byteNumbers)
            blob = new Blob([byteArray], {
              type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            })
          } else if (format === 'pdf') {
            // PDF格式：data是base64字符串，需要解码
            const binaryString = atob(response.data.data)
            const bytes = new Uint8Array(binaryString.length)
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i)
            }
            blob = new Blob([bytes], {
              type: 'application/pdf'
            })
          } else {
            // 其他格式
            blob = new Blob([response.data.data], {
              type: 'application/octet-stream'
            })
          }
          
          const url = window.URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = response.data.filename
          link.click()
          window.URL.revokeObjectURL(url)
        } else {
          alert('导出失败: ' + (response.data.message || '未知错误'))
        }
      } catch (error) {
        console.error('导出失败:', error)
        alert('导出失败: ' + (error.response?.data?.detail || '未知错误'))
      }
    }

    onMounted(() => {
      fetchIndustries()
      fetchCandidates()
    })

    return {
      availableCandidates,
      selectedCandidates,
      comparisonResult,
      loading,
      industries,
      selectedIndustry,
      onIndustryChange,
      toggleCandidate,
      clearSelection,
      startComparison,
      getDimensionName,
      exportReport
    }
  }
}
</script>

<style scoped>
.comparison-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
}

h2 {
  color: #444;
  margin-bottom: 20px;
  border-bottom: 2px solid #007bff;
  padding-bottom: 10px;
}

/* 行业选择区样式 */
.industry-section {
  background: #e3f2fd;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #007bff;
}

.industry-selector {
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}

.industry-select {
  padding: 10px 15px;
  font-size: 16px;
  border: 2px solid #007bff;
  border-radius: 6px;
  background: white;
  color: #333;
  cursor: pointer;
  min-width: 200px;
}

.industry-select:focus {
  outline: none;
  border-color: #0056b3;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
}

.industry-hint {
  color: #666;
  font-size: 14px;
}

h3 {
  color: #555;
  margin: 20px 0 15px;
}

/* 选择区样式 */
.selection-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.candidate-selector {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.candidate-card {
  background: white;
  border: 2px solid #ddd;
  border-radius: 8px;
  padding: 15px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.candidate-card:hover {
  border-color: #007bff;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.candidate-card.selected {
  border-color: #28a745;
  background: #f0fff4;
}

.candidate-name {
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 8px;
}

.candidate-score {
  color: #007bff;
  font-size: 14px;
}

.candidate-rank {
  color: #666;
  font-size: 12px;
}

.selection-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
}

/* 按钮样式 */
.btn-primary, .btn-secondary, .btn-export {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #545b62;
}

.btn-export {
  background: #28a745;
  color: white;
  margin: 5px;
}

.btn-export:hover {
  background: #218838;
}

/* 对比结果样式 */
.comparison-result {
  margin-top: 30px;
}

.summary-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.recommendation-order {
  margin-top: 15px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
}

.order-item {
  margin-left: 15px;
  padding: 5px 10px;
  background: #007bff;
  color: white;
  border-radius: 4px;
  font-size: 14px;
}

/* 维度对比样式 */
.dimension-charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.dimension-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
}

.dimension-card h4 {
  margin-bottom: 15px;
  color: #333;
  text-align: center;
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ranking-item {
  display: flex;
  align-items: center;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
}

.ranking-item.top-rank {
  background: #fff3cd;
  border: 1px solid #ffc107;
}

.ranking-item .rank {
  width: 30px;
  height: 30px;
  background: #007bff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 10px;
}

.ranking-item.top-rank .rank {
  background: #ffc107;
  color: #333;
}

.ranking-item .name {
  flex: 1;
  font-weight: 500;
}

.ranking-item .score {
  font-weight: bold;
  color: #007bff;
}

/* 优势分析样式 */
.advantage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.advantage-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
}

.advantage-card h4 {
  margin-bottom: 15px;
  color: #28a745;
  border-bottom: 2px solid #28a745;
  padding-bottom: 8px;
}

.advantage-section {
  margin-bottom: 12px;
  font-size: 14px;
}

.advantage-section strong {
  color: #333;
  display: block;
  margin-bottom: 5px;
}

.advantage-section ul {
  margin: 0;
  padding-left: 20px;
}

.advantage-section li {
  margin-bottom: 5px;
  color: #666;
}

/* 差距分析样式 */
.gap-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.gap-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.gap-item.is-top {
  background: #d4edda;
  border-color: #28a745;
}

.gap-name {
  font-weight: bold;
  font-size: 16px;
}

.gap-badge {
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 14px;
}

.gap-badge.top {
  background: #28a745;
  color: white;
}

.gap-badge:not(.top) {
  background: #ffc107;
  color: #333;
}

/* 表格样式 */
.comparison-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.comparison-table th,
.comparison-table td {
  padding: 12px;
  text-align: center;
  border-bottom: 1px solid #ddd;
}

.comparison-table th {
  background: #007bff;
  color: white;
  font-weight: 600;
}

.comparison-table tr:hover {
  background: #f8f9fa;
}

.score-highlight {
  font-weight: bold;
  color: #007bff;
  font-size: 16px;
}

.risk-high {
  color: #dc3545;
  font-weight: bold;
}

/* 导出区样式 */
.export-section {
  margin-top: 30px;
  text-align: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

/* 加载样式 */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-overlay p {
  margin-top: 20px;
  color: #666;
  font-size: 16px;
}
</style>
