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
    if (industries.value.length > 0) {
      return
    }

    try {
      const response = await axios.get(`${API_BASE}/industries`, { timeout: 5000 })
      if (response.data.status === 'success') {
        industries.value = response.data.industries
      }
    } catch (err) {
      console.error('获取行业列表失败:', err.message)
      error.value = '获取行业列表失败: ' + err.message
    }
  }

  // 获取行业排名
  const fetchRankings = async (industry, topN = 10) => {
    loading.value = true
    error.value = null

    try {
      const response = await axios.get(`${API_BASE}/rank/industry/${industry}`, {
        params: { top_n: topN }
      })

      if (response.data.status === 'success') {
        rankings.value = response.data.ranking || []
        currentIndustry.value = industry

        // 同时保存完整的candidate数据
        if (response.data.candidates && response.data.candidates.length > 0) {
          candidates.value = response.data.candidates
        }

        if (rankings.value.length === 0) {
          error.value = '该行业暂无候选人数据，请先上传并解析简历'
        }
      } else {
        error.value = response.data.message || '获取排名数据失败'
      }
    } catch (err) {
      console.error('获取排名失败:', err)
      if (err.response?.status === 404) {
        error.value = '未找到"' + industry + '"行业的简历数据，请先上传并解析该行业的简历'
        rankings.value = []
      } else {
        error.value = '获取排名失败: ' + (err.response?.data?.detail || err.message)
      }
    } finally {
      loading.value = false
    }
  }

  // 批量评分
  const batchScore = async (industry) => {
    loading.value = true
    error.value = null

    try {
      const response = await axios.post(`${API_BASE}/score/batch`, {
        resume_ids: [],
        job_type: industry,
        industry: industry
      })
      if (response.data.status === 'success') {
        candidates.value = response.data.candidates
        rankings.value = response.data.ranking
      } else {
        error.value = '批量评分失败'
      }
    } catch (err) {
      console.error('批量评分失败:', err)
      error.value = '批量评分失败: ' + (err.response?.data?.detail || err.message)
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
      throw err
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
      throw err
    }
  }

  // 生成报告
  const generateReport = async (industry, format = 'json') => {
    try {
      const response = await axios.get(`${API_BASE}/report/generate/${industry}`, {
        params: { format },
        responseType: 'blob'
      })

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
      throw err
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
      throw err
    }
  }

  // LLM智能分析候选人
  const analyzeCandidate = async (candidateName, industry) => {
    try {
      const response = await axios.post(`${API_BASE}/analysis/candidate`, {
        candidate_name: candidateName,
        industry: industry
      })
      return response.data
    } catch (err) {
      console.error('候选人分析失败:', err)
      throw err
    }
  }

  // 岗位画像抽取
  const parseJobProfile = async (jobDescription, requirements = '') => {
    try {
      const response = await axios.post(`${API_BASE}/job-profile/parse`, {
        job_description: jobDescription,
        requirements: requirements
      })
      return response.data
    } catch (err) {
      console.error('岗位画像抽取失败:', err)
      throw err
    }
  }

  // 人岗匹配评分
  const scoreJobMatching = async (resumeId, jobDescription = '', jobProfile = null) => {
    try {
      const payload = {
        resume_id: resumeId,
        include_details: true
      }
      if (jobProfile) {
        payload.job_profile = jobProfile
      } else if (jobDescription) {
        payload.job_description = jobDescription
      }
      const response = await axios.post(`${API_BASE}/matching/score`, payload)
      return response.data
    } catch (err) {
      console.error('人岗匹配评分失败:', err)
      throw err
    }
  }

  // 批量人岗匹配评分
  const batchJobMatching = async (resumeIds, jobDescription = '', jobProfile = null) => {
    try {
      const payload = {
        resume_ids: resumeIds,
        include_details: true
      }
      if (jobProfile) {
        payload.job_profile = jobProfile
      } else if (jobDescription) {
        payload.job_description = jobDescription
      }
      const response = await axios.post(`${API_BASE}/matching/batch`, payload)
      return response.data
    } catch (err) {
      console.error('批量人岗匹配评分失败:', err)
      throw err
    }
  }

  // 风险识别评估
  const assessRisk = async (resumeId, jobProfile = null) => {
    try {
      const payload = { resume_id: resumeId }
      if (jobProfile) {
        payload.job_profile = jobProfile
      }
      const response = await axios.post(`${API_BASE}/risk/assessment`, payload)
      return response.data
    } catch (err) {
      console.error('风险评估失败:', err)
      throw err
    }
  }

  // 潜力评估
  const evaluatePotential = async (resumeId) => {
    try {
      const response = await axios.post(`${API_BASE}/potential/evaluation`, {
        resume_id: resumeId
      })
      return response.data
    } catch (err) {
      console.error('潜力评估失败:', err)
      throw err
    }
  }

  // 综合评估报告
  const getComprehensiveReport = async (resumeId, jobDescription = '', requirements = '') => {
    try {
      const payload = { resume_id: resumeId }
      if (jobDescription) {
        payload.job_description = jobDescription
        payload.requirements = requirements
      }
      const response = await axios.post(`${API_BASE}/comprehensive-report`, payload)
      return response.data
    } catch (err) {
      console.error('综合报告获取失败:', err)
      throw err
    }
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
    askQuestion,
    analyzeCandidate,
    parseJobProfile,
    scoreJobMatching,
    batchJobMatching,
    assessRisk,
    evaluatePotential,
    getComprehensiveReport
  }
})
