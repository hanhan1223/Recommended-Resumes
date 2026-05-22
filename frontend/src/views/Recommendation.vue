<template>
  <div class="recommendation-page">
    <h1>多方案推荐</h1>
    
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
        <span class="industry-hint">选择特定行业可进行更精准的推荐分析</span>
      </div>
    </div>
    
    <!-- 候选人选择区 -->
    <div class="selection-section">
      <h2>选择候选人</h2>
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
        </div>
      </div>
      
      <!-- 岗位要求配置 -->
      <div class="job-requirements">
        <h3>岗位要求</h3>
        <div class="form-group">
          <label>岗位名称:</label>
          <input v-model="jobRequirements.title" type="text" placeholder="请输入岗位名称">
        </div>
        <div class="form-group">
          <label>所需技能 (逗号分隔):</label>
          <input v-model="skillsInput" type="text" placeholder="例如: Python, 数据分析, 团队管理">
        </div>
        <div class="form-group">
          <label>招聘人数:</label>
          <input v-model.number="jobRequirements.hire_count" type="number" min="1" max="5">
        </div>
      </div>
      
      <div class="selection-actions">
        <button 
          class="btn-primary" 
          @click="generateRecommendations"
          :disabled="selectedCandidates.length < 2"
        >
          生成推荐方案
        </button>
        <button class="btn-secondary" @click="clearSelection">清空</button>
      </div>
    </div>

    <!-- 推荐方案展示区 -->
    <div v-if="recommendationData" class="recommendation-result">
      <h2>推荐方案汇总</h2>
      
      <!-- 方案概览 -->
      <div class="summary-cards">
        <div class="summary-card">
          <h4>总方案数</h4>
          <div class="big-number">{{ recommendationData.recommendation_summary.total_plans }}</div>
        </div>
        <div class="summary-card">
          <h4>首推方案</h4>
          <div class="plan-name">{{ recommendationData.recommendation_summary.top_recommendation.plan_name }}</div>
        </div>
        <div class="summary-card">
          <h4>预期表现</h4>
          <div class="big-number">{{ recommendationData.recommendation_summary.top_recommendation.expected_performance.toFixed(2) }}</div>
        </div>
      </div>

      <!-- 方案对比表 -->
      <div class="comparison-table-section">
        <h3>方案对比</h3>
        <table class="comparison-table">
          <thead>
            <tr>
              <th>方案</th>
              <th>策略</th>
              <th>风险等级</th>
              <th>预期表现</th>
              <th>推荐人数</th>
              <th>团队互补性</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="plan in recommendationData.recommendation_summary.comparison_table" 
              :key="plan.方案"
              :class="{ 'top-plan': plan.方案 === recommendationData.recommendation_summary.top_recommendation.plan_name }"
            >
              <td><strong>{{ plan.方案 }}</strong></td>
              <td>{{ plan.策略 }}</td>
              <td :class="'risk-' + plan.风险等级">{{ plan.风险等级 }}</td>
              <td class="score-highlight">{{ plan.预期表现.toFixed(2) }}</td>
              <td>{{ plan.推荐人数 }}</td>
              <td>{{ plan.团队互补性 }}%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 详细方案卡片 -->
      <div class="plans-detail">
        <h3>详细方案</h3>
        <div class="plans-grid">
          <div 
            v-for="plan in recommendationData.plans" 
            :key="plan.plan_id"
            class="plan-card"
            :class="{ 'top-plan-card': plan.plan_id === 'plan_balanced' }"
          >
            <div class="plan-header">
              <h4>{{ plan.name }}</h4>
              <span class="risk-badge" :class="'risk-' + plan.risk_level">{{ plan.risk_level }}风险</span>
            </div>
            
            <p class="plan-description">{{ plan.description }}</p>
            
            <div class="plan-metrics">
              <div class="metric">
                <span class="metric-label">预期表现</span>
                <span class="metric-value">{{ plan.expected_performance.toFixed(2) }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">团队互补性</span>
                <span class="metric-value">{{ plan.team_complementarity }}%</span>
              </div>
            </div>

            <div class="recommended-candidates">
              <strong>推荐候选人:</strong>
              <div class="candidate-tags">
                <span 
                  v-for="c in plan.recommended_candidates" 
                  :key="c.candidate_id"
                  class="candidate-tag"
                >
                  {{ c.name }} ({{ c.tci_score.toFixed(2) }})
                </span>
              </div>
            </div>

            <div class="backup-candidates" v-if="plan.backup_candidates.length">
              <strong>备选:</strong>
              <span 
                v-for="c in plan.backup_candidates" 
                :key="c.candidate_id"
                class="backup-tag"
              >
                {{ c.name }}
              </span>
            </div>

            <div class="pros-cons">
              <div class="pros">
                <strong>优点:</strong>
                <ul>
                  <li v-for="(pro, idx) in plan.pros" :key="idx">{{ pro }}</li>
                </ul>
              </div>
              <div class="cons">
                <strong>缺点:</strong>
                <ul>
                  <li v-for="(con, idx) in plan.cons" :key="idx">{{ con }}</li>
                </ul>
              </div>
            </div>

            <div class="suitable-scenarios">
              <strong>适用场景:</strong>
              <div class="scenario-tags">
                <span 
                  v-for="(scenario, idx) in plan.suitable_scenarios" 
                  :key="idx"
                  class="scenario-tag"
                >
                  {{ scenario }}
                </span>
              </div>
            </div>
          </div>
        </div>
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
      <p>正在生成推荐方案...</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'Recommendation',
  setup() {
    const availableCandidates = ref([])
    const selectedCandidates = ref([])
    const recommendationData = ref(null)
    const loading = ref(false)
    const industries = ref([])
    const selectedIndustry = ref('')
    
    const jobRequirements = ref({
      title: '',
      skills: [],
      hire_count: 1
    })
    const skillsInput = ref('')

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
          recommendationData.value = null
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

    // 切换候选人选择
    const toggleCandidate = (id) => {
      const index = selectedCandidates.value.indexOf(id)
      if (index > -1) {
        selectedCandidates.value.splice(index, 1)
      } else {
        if (selectedCandidates.value.length < 10) {
          selectedCandidates.value.push(id)
        } else {
          alert('最多只能选择10位候选人')
        }
      }
    }

    // 清空选择
    const clearSelection = () => {
      selectedCandidates.value = []
      recommendationData.value = null
      jobRequirements.value = { title: '', skills: [], hire_count: 1 }
      skillsInput.value = ''
    }

    // 生成推荐方案
    const generateRecommendations = async () => {
      if (selectedCandidates.value.length < 2) {
        alert('请至少选择2位候选人')
        return
      }

      // 解析技能
      if (skillsInput.value) {
        jobRequirements.value.skills = skillsInput.value.split(',').map(s => s.trim()).filter(s => s)
      }

      loading.value = true
      try {
        const response = await axios.post('/api/recommendation/plans', {
          resume_ids: selectedCandidates.value,
          job_requirements: jobRequirements.value,
          team_config: null
        })
        
        if (response.data.status === 'success') {
          recommendationData.value = response.data
        }
      } catch (error) {
        console.error('生成推荐方案失败:', error)
        alert('生成推荐方案失败: ' + (error.response?.data?.detail || '未知错误'))
      } finally {
        loading.value = false
      }
    }

    // 导出报告
    const exportReport = async (format) => {
      try {
        const response = await axios.post('/api/report/export', {
          report_type: 'recommendation',
          data: recommendationData.value,
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
      selectedCandidates,
      recommendationData,
      loading,
      industries,
      selectedIndustry,
      onIndustryChange,
      jobRequirements,
      skillsInput,
      toggleCandidate,
      clearSelection,
      generateRecommendations,
      exportReport
    }
  }
}
</script>

<style scoped>
.recommendation-page {
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

h3 {
  color: #555;
  margin: 20px 0 15px;
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
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
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

/* 岗位要求样式 */
.job-requirements {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin: 20px 0;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
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
  margin-left: 10px;
}

.btn-export {
  background: #28a745;
  color: white;
  margin: 5px;
}

/* 结果区样式 */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.summary-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.big-number {
  font-size: 36px;
  font-weight: bold;
  color: #007bff;
  margin: 10px 0;
}

.plan-name {
  font-size: 18px;
  font-weight: 500;
  color: #28a745;
  margin: 10px 0;
}

/* 表格样式 */
.comparison-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
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
}

.top-plan {
  background: #fff3cd !important;
}

.score-highlight {
  font-weight: bold;
  color: #007bff;
}

.risk-高 { color: #dc3545; font-weight: bold; }
.risk-中 { color: #ffc107; font-weight: bold; }
.risk-低 { color: #28a745; font-weight: bold; }

/* 方案卡片样式 */
.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.plan-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
}

.top-plan-card {
  border: 2px solid #ffc107;
  box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.plan-header h4 {
  margin: 0;
  color: #333;
}

.risk-badge {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
}

.risk-badge.risk-高 { background: #dc3545; color: white; }
.risk-badge.risk-中 { background: #ffc107; color: #333; }
.risk-badge.risk-低 { background: #28a745; color: white; }

.plan-description {
  color: #666;
  margin-bottom: 15px;
  font-size: 14px;
}

.plan-metrics {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.metric {
  text-align: center;
}

.metric-label {
  display: block;
  font-size: 12px;
  color: #666;
}

.metric-value {
  font-size: 20px;
  font-weight: bold;
  color: #007bff;
}

.candidate-tags, .scenario-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.candidate-tag, .scenario-tag, .backup-tag {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.candidate-tag {
  background: #007bff;
  color: white;
}

.backup-tag {
  background: #6c757d;
  color: white;
}

.scenario-tag {
  background: #e9ecef;
  color: #495057;
}

.pros-cons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin: 15px 0;
}

.pros ul, .cons ul {
  margin: 5px 0;
  padding-left: 20px;
  font-size: 13px;
}

.pros li { color: #28a745; }
.cons li { color: #dc3545; }

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
</style>
