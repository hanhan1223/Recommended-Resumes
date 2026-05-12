import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

// API基础URL
const API_BASE = '/api'

export const useResumeStore = defineStore('resume', () => {
  // ========== State ==========
  const industries = ref([])
  const currentIndustry = ref('')
  const rankings = ref([])
  const candidates = ref([])
  const loading = ref(false)
  const error = ref(null)

  // ========== Getters ==========
  const topCandidates = computed(() => {
    return rankings.value.slice(0, 10)
  })

  const industryStats = computed(() => {
    if (!candidates.value.length) return {}
    
    const scores = candidates.value.map(c => c.tci_score)
    return {
      avg: scores.reduce((a, b) => a + b, 0) / scores.length,
      max: Math.max(...scores),
      min: Math.min(...scores),
      count: candidates.value.length
    }
  })

  // ========== Actions ==========
  
  // 获取行业列表
  const fetchIndustries = async () => {
    // 如果已有数据，不再重复请求
    if (industries.value.length > 0) {
      return
    }
    
    try {
      const response = await axios.get(`${API_BASE}/industries`, { timeout: 5000 })
      if (response.data.status === 'success') {
        industries.value = response.data.industries
      }
    } catch (err) {
      console.warn('获取行业列表失败，使用默认数据:', err.message)
      error.value = err.message
      // 默认行业数据
      industries.value = [
        { code: '电商', name: '电商行业', description: '电商运营、直播运营等岗位' },
        { code: '品牌', name: '品牌市场', description: '品牌管理、市场推广等岗位' },
        { code: '销售', name: '销售业务', description: '销售、外贸、渠道等岗位' },
        { code: '研发', name: '研发技术', description: '研发、技术、科学家等岗位' },
        { code: '生产', name: '生产管理', description: '生产管理、厂长、质量等岗位' },
        { code: '人力资源', name: '人力资源', description: 'HR、招聘、薪酬等岗位' }
      ]
    }
  }

  // 获取行业排名
  const fetchRankings = async (industry, topN = 10) => {
    loading.value = true
    error.value = null
    
    console.log('[API] 正在获取排名数据: industry=' + industry + ', topN=' + topN)
    
    try {
      const response = await axios.get(`${API_BASE}/rank/industry/${industry}`, {
        params: { top_n: topN }
      })
      
      console.log('[API] 响应:', response.data)
      
      if (response.data.status === 'success') {
        rankings.value = response.data.ranking || []
        currentIndustry.value = industry
        
        if (rankings.value.length === 0) {
          console.warn('[WARN] 排名列表为空，该行业暂无候选人数据')
          error.value = '该行业暂无候选人数据，请先上传并解析简历'
        } else {
          console.log('[OK] 成功获取 ' + rankings.value.length + ' 条排名数据')
        }
      } else {
        console.error('[ERROR] API返回错误状态:', response.data)
        error.value = response.data.message || '获取排名数据失败'
        generateMockRankings(industry)
      }
    } catch (err) {
      console.error('[ERROR] 获取排名失败:', err)
      error.value = err.message
      
      // 如果是404错误，说明该行业没有数据
      if (err.response?.status === 404) {
        error.value = '未找到"' + industry + '"行业的简历数据，请先上传并解析该行业的简历'
        rankings.value = []
      } else {
        // 其他错误使用模拟数据
        generateMockRankings(industry)
      }
    } finally {
      loading.value = false
    }
  }

  // 批量评分
  const batchScore = async (industry) => {
    loading.value = true
    try {
      const response = await axios.post(`${API_BASE}/score/batch`, {
        resume_ids: [],
        job_type: industry,
        industry: industry
      })
      if (response.data.status === 'success') {
        candidates.value = response.data.candidates
        rankings.value = response.data.ranking
      }
    } catch (err) {
      error.value = err.message
      // 模拟数据
      generateMockCandidates(industry)
    } finally {
      loading.value = false
    }
  }

  // 单份简历评分
  const scoreResume = async (resumeId, industry) => {
    try {
      const response = await axios.post(`${API_BASE}/score/single`, {
        resume_id: resumeId,
        job_type: industry,
        industry: industry
      })
      return response.data
    } catch (err) {
      console.error('评分失败:', err)
      return null
    }
  }

  // 上传简历
  const uploadResume = async (file, industry) => {
    const formData = new FormData()
    formData.append('file', file)
    if (industry) {
      formData.append('industry', industry)
    }
    
    try {
      const response = await axios.post(`${API_BASE}/resume/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return response.data
    } catch (err) {
      console.error('上传失败:', err)
      throw err
    }
  }

  // 解析简历
  const parseResume = async (filePath, industry = null) => {
    try {
      const payload = { file_path: filePath }
      if (industry) {
        payload.industry = industry
      }
      
      const response = await axios.post(`${API_BASE}/resume/parse`, payload)
      return response.data
    } catch (err) {
      console.error('解析失败:', err)
      // 返回模拟数据用于演示
      return {
        status: 'success',
        data: {
          basic_info: { name: '候选人' },
          industry: industry || '电商',
          industry_confidence: 0.85
        }
      }
    }
  }

  // 生成报告
  const generateReport = async (industry, format = 'json') => {
    try {
      const response = await axios.get(`${API_BASE}/report/generate/${industry}`, {
        params: { format },
        responseType: 'blob'
      })
      
      // 下载文件
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `人才优选报告_${industry}.${format}`
      link.click()
      window.URL.revokeObjectURL(url)
      
      return true
    } catch (err) {
      console.error('报告生成失败:', err)
      return false
    }
  }

  // 智能问答
  const askQuestion = async (question, context = {}) => {
    try {
      const response = await axios.post(`${API_BASE}/qa/ask`, {
        question,
        context
      })
      return response.data
    } catch (err) {
      console.error('问答失败:', err)
      return {
        status: 'error',
        answer: '抱歉，暂时无法回答您的问题。'
      }
    }
  }

  // ========== Mock数据生成 ==========
  const generateMockRankings = (industry) => {
    const names = ['张伟', '李娜', '王强', '刘洋', '陈静', '杨帆', '赵敏', '黄磊', '周杰', '吴倩']
    rankings.value = names.map((name, i) => ({
      rank: i + 1,
      candidate_id: name,
      tci_score: parseFloat((5 - i * 0.3 + Math.random() * 0.5).toFixed(2)),
      penalty_applied: i === 3 || i === 7
    }))
    currentIndustry.value = industry
  }

  const generateMockCandidates = (industry) => {
    const names = ['张伟', '李娜', '王强', '刘洋', '陈静', '杨帆', '赵敏', '黄磊']
    candidates.value = names.map((name, i) => ({
      candidate_id: name,
      tci_score: parseFloat((4.5 - i * 0.2).toFixed(2)),
      dimensional_scores: {
        education: parseFloat((4 + Math.random()).toFixed(2)),
        experience: parseFloat((4 + Math.random()).toFixed(2)),
        skill_achievement: parseFloat((4 + Math.random()).toFixed(2)),
        comprehensive: parseFloat((3.5 + Math.random()).toFixed(2))
      },
      dimension_weights: {
        education: 0.15,
        experience: 0.30,
        skill_achievement: 0.40,
        comprehensive: 0.15
      },
      penalty_applied: i === 2
    }))

    rankings.value = candidates.value
      .sort((a, b) => b.tci_score - a.tci_score)
      .map((c, i) => ({
        rank: i + 1,
        candidate_id: c.candidate_id,
        tci_score: c.tci_score,
        penalty_applied: c.penalty_applied
      }))
  }

  return {
    // State
    industries,
    currentIndustry,
    rankings,
    candidates,
    loading,
    error,
    // Getters
    topCandidates,
    industryStats,
    // Actions
    fetchIndustries,
    fetchRankings,
    batchScore,
    scoreResume,
    uploadResume,
    parseResume,
    generateReport,
    askQuestion
  }
})
