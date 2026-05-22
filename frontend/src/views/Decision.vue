<template>
  <div class="decision-page">
    <h1>决策报告</h1>
    
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
        <span class="industry-hint">选择特定行业可生成更精准的决策报告</span>
      </div>
    </div>
    
    <!-- 候选人选择 -->
    <div class="selection-section">
      <h2>选择候选人</h2>
      <div class="candidate-selector">
        <div 
          v-for="candidate in availableCandidates" 
          :key="candidate.id"
          class="candidate-card"
          :class="{ selected: selectedCandidate === candidate.id }"
          @click="selectCandidate(candidate.id)"
        >
          <div class="candidate-name">{{ candidate.name }}</div>
          <div class="candidate-score">TCI: {{ candidate.tci_score.toFixed(2) }}</div>
          <div class="candidate-rank">排名: {{ candidate.rank }}</div>
        </div>
      </div>
      
      <div class="selection-actions">
        <button 
          class="btn-primary" 
          @click="generateDecision"
          :disabled="!selectedCandidate"
        >
          生成决策报告
        </button>
      </div>
    </div>

    <!-- 决策报告展示区 -->
    <div v-if="decisionData" class="decision-result">
      <h2>决策报告</h2>
      
      <!-- 决策概览 -->
      <div class="overview-card">
        <div class="decision-header">
          <h3>{{ decisionData.candidate_name }}</h3>
          <div class="decision-badge" :class="'decision-' + getDecisionClass(decisionData.decision)">
            {{ decisionData.decision }}
          </div>
        </div>
        
        <div class="metrics-row">
          <div class="metric">
            <span class="metric-label">置信度</span>
            <span class="metric-value">{{ decisionData.confidence }}</span>
          </div>
          <div class="metric">
            <span class="metric-label">综合得分</span>
            <span class="metric-value">{{ decisionData.overall_score }}</span>
          </div>
        </div>
      </div>

      <!-- 执行摘要 -->
      <div class="executive-summary">
        <h3>执行摘要</h3>
        <div class="summary-cards">
          <div class="summary-card risk">
            <h4>风险评估</h4>
            <p>{{ decisionData.executive_summary.risk_summary }}</p>
          </div>
          <div class="summary-card opportunity">
            <h4>机会评估</h4>
            <p>{{ decisionData.executive_summary.opportunity_summary }}</p>
          </div>
        </div>
        
        <div class="final-recommendation">
          <h4>最终推荐</h4>
          <p>{{ decisionData.executive_summary.final_recommendation }}</p>
        </div>
      </div>

      <!-- 关键决策因素 -->
      <div class="key-factors">
        <h3>关键决策因素</h3>
        <div class="factors-list">
          <div 
            v-for="(factor, index) in decisionData.key_factors" 
            :key="index"
            class="factor-card"
            :class="'factor-' + getFactorClass(factor.type)"
          >
            <div class="factor-header">
              <span class="factor-type">{{ factor.type }}</span>
              <span class="factor-weight">权重: {{ factor.weight }}</span>
            </div>
            <div class="factor-description">{{ factor.description }}</div>
            <div class="factor-evidence" v-if="factor.evidence.length">
              <strong>依据:</strong>
              <ul>
                <li v-for="(evidence, idx) in factor.evidence" :key="idx">{{ evidence }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- 行动建议 -->
      <div class="action-items">
        <h3>行动建议</h3>
        <div class="action-sections">
          <div class="action-section">
            <h4>建议行动</h4>
            <ul class="action-list">
              <li v-for="(action, index) in decisionData.action_items.suggested_actions" :key="index">
                {{ action }}
              </li>
            </ul>
          </div>
          <div class="action-section">
            <h4>面试重点</h4>
            <ul class="action-list">
              <li v-for="(focus, index) in decisionData.action_items.interview_focus" :key="index">
                {{ focus }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- 导出按钮 -->
      <div class="export-section">
        <button class="btn-export" @click="exportReport('json')">
          导出JSON报告
        </button>
        <button class="btn-export" @click="exportReport('pdf')">
          导出PDF报告
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>正在生成决策报告...</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'Decision',
  setup() {
    const availableCandidates = ref([])
    const selectedCandidate = ref(null)
    const decisionData = ref(null)
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
          selectedCandidate.value = null
          decisionData.value = null
        }
      } catch (error) {
        console.error('获取候选人列表失败:', error)
        alert('获取候选人列表失败')
      }
    }

    // 行业切换处理
    const onIndustryChange = () => {
      fetchCandidates()
    }

    // 选择候选人
    const selectCandidate = (id) => {
      selectedCandidate.value = id
      decisionData.value = null
    }

    // 生成决策报告
    const generateDecision = async () => {
      if (!selectedCandidate.value) {
        alert('请选择候选人')
        return
      }

      loading.value = true
      try {
        const response = await axios.post('/api/decision/summary', {
          resume_id: selectedCandidate.value,
          job_requirements: null
        })
        
        if (response.data.status === 'success') {
          decisionData.value = response.data.decision_summary
        }
      } catch (error) {
        console.error('生成决策报告失败:', error)
        alert('生成决策报告失败: ' + (error.response?.data?.detail || '未知错误'))
      } finally {
        loading.value = false
      }
    }

    // 获取决策样式类
    const getDecisionClass = (decision) => {
      const map = {
        '强烈推荐': 'strongly-recommend',
        '推荐': 'recommend',
        '可以考虑': 'consider',
        '不推荐': 'not-recommend'
      }
      return map[decision] || 'consider'
    }

    // 获取因素样式类
    const getFactorClass = (type) => {
      const map = {
        '优势': 'advantage',
        '劣势': 'disadvantage',
        '风险': 'risk',
        '机会': 'opportunity'
      }
      return map[type] || 'other'
    }

    // 导出报告
    const exportReport = async (format) => {
      try {
        const response = await axios.post('/api/report/export', {
          report_type: 'decision',
          data: decisionData.value,
          format: format
        })

        if (response.data.status === 'success') {
          let blob
          if (format === 'json') {
            // JSON格式：data是对象，需要stringify
            blob = new Blob([JSON.stringify(response.data.data, null, 2)], {
              type: 'application/json'
            })
          } else if (format === 'excel') {
            // Excel格式：data是base64字符串，需要解码
            const binaryString = atob(response.data.data)
            const bytes = new Uint8Array(binaryString.length)
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i)
            }
            blob = new Blob([bytes], {
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
        }
      } catch (error) {
        console.error('导出失败:', error)
        alert('导出失败')
      }
    }

    onMounted(() => {
      fetchIndustries()
      fetchCandidates()
    })

    return {
      availableCandidates,
      selectedCandidate,
      decisionData,
      loading,
      industries,
      selectedIndustry,
      onIndustryChange,
      selectCandidate,
      generateDecision,
      getDecisionClass,
      getFactorClass,
      exportReport
    }
  }
}
</script>

<style scoped>
.decision-page {
  padding: 20px;
  max-width: 1200px;
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

h3 {
  color: #555;
  margin: 20px 0 15px;
}

h4 {
  color: #666;
  margin-bottom: 10px;
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
}

.candidate-card.selected {
  border-color: #28a745;
  background: #f0fff4;
}

.candidate-name {
  font-weight: bold;
  margin-bottom: 5px;
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
  text-align: center;
}

/* 按钮样式 */
.btn-primary, .btn-export {
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

.btn-export {
  background: #28a745;
  color: white;
  margin: 5px;
}

.btn-export:hover {
  background: #218838;
}

/* 概览卡片样式 */
.overview-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.decision-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.decision-header h3 {
  margin: 0;
  font-size: 24px;
}

.decision-badge {
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 16px;
}

.decision-strongly-recommend {
  background: #28a745;
  color: white;
}

.decision-recommend {
  background: #17a2b8;
  color: white;
}

.decision-consider {
  background: #ffc107;
  color: #333;
}

.decision-not-recommend {
  background: #dc3545;
  color: white;
}

.metrics-row {
  display: flex;
  gap: 30px;
}

.metric {
  text-align: center;
}

.metric-label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 5px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #007bff;
}

/* 执行摘要样式 */
.executive-summary {
  margin: 20px 0;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.summary-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
}

.summary-card.risk {
  border-left: 4px solid #dc3545;
}

.summary-card.opportunity {
  border-left: 4px solid #28a745;
}

.summary-card h4 {
  margin-top: 0;
  color: #333;
}

.final-recommendation {
  background: #e7f3ff;
  border: 1px solid #007bff;
  border-radius: 8px;
  padding: 15px;
}

.final-recommendation h4 {
  color: #007bff;
  margin-top: 0;
}

/* 关键因素样式 */
.key-factors {
  margin: 20px 0;
}

.factors-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 15px;
}

.factor-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
  border-left: 4px solid #ccc;
}

.factor-advantage {
  border-left-color: #28a745;
}

.factor-disadvantage {
  border-left-color: #ffc107;
}

.factor-risk {
  border-left-color: #dc3545;
}

.factor-opportunity {
  border-left-color: #17a2b8;
}

.factor-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.factor-type {
  font-weight: bold;
  color: #333;
}

.factor-weight {
  font-size: 12px;
  color: #666;
}

.factor-description {
  margin-bottom: 10px;
  color: #555;
}

.factor-evidence {
  font-size: 13px;
  color: #666;
}

.factor-evidence ul {
  margin: 5px 0;
  padding-left: 20px;
}

/* 行动建议样式 */
.action-items {
  margin: 20px 0;
}

.action-sections {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.action-section {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
}

.action-list {
  margin: 0;
  padding-left: 20px;
}

.action-list li {
  margin-bottom: 8px;
  color: #555;
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
