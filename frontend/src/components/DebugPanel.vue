<template>
  <el-card class="debug-panel" v-if="showDebug">
    <template #header>
      <div class="debug-header">
        <span>🔧 调试面板</span>
        <el-button type="danger" link @click="showDebug = false">关闭</el-button>
      </div>
    </template>
    
    <div class="debug-content">
      <h4>📊 Store状态</h4>
      <pre>{{ JSON.stringify(storeState, null, 2) }}</pre>
      
      <h4>📡 API响应</h4>
      <pre>{{ JSON.stringify(apiResponse, null, 2) }}</pre>
      
      <h4>❌ 错误信息</h4>
      <div v-if="errors.length === 0" class="no-errors">无错误</div>
      <ul v-else>
        <li v-for="(err, i) in errors" :key="i" class="error-item">{{ err }}</li>
      </ul>
      
      <div class="debug-actions">
        <el-button type="primary" @click="testApi">测试API</el-button>
        <el-button @click="clearErrors">清空错误</el-button>
      </div>
    </div>
  </el-card>
  
  <el-button 
    v-else 
    class="debug-toggle" 
    type="info" 
    size="small"
    @click="showDebug = true"
  >
    显示调试
  </el-button>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useResumeStore } from '@/stores'
import axios from 'axios'

const showDebug = ref(false)
const store = useResumeStore()
const apiResponse = ref({})
const errors = ref([])

const storeState = computed(() => ({
  industriesCount: store.industries.length,
  currentIndustry: store.currentIndustry,
  rankingsCount: store.rankings.length,
  candidatesCount: store.candidates.length,
  loading: store.loading,
  error: store.error
}))

const testApi = async () => {
  try {
    const response = await axios.get('/api/industries')
    apiResponse.value = response.data
    
    if (store.currentIndustry) {
      const rankResponse = await axios.get(`/api/rank/industry/${store.currentIndustry}?top_n=5`)
      apiResponse.value = { ...apiResponse.value, ranking: rankResponse.data }
    }
  } catch (err) {
    errors.value.push(`API错误: ${err.message}`)
    apiResponse.value = { error: err.message }
  }
}

const clearErrors = () => {
  errors.value = []
}
</script>

<style scoped>
.debug-panel {
  position: fixed;
  right: 20px;
  top: 80px;
  width: 400px;
  max-height: 80vh;
  overflow-y: auto;
  z-index: 9999;
  background: #1e1e1e;
  color: #d4d4d4;
  border: 1px solid #444;
}

.debug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.debug-content h4 {
  margin: 15px 0 10px;
  color: #4ec9b0;
}

.debug-content pre {
  background: #252526;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
}

.no-errors {
  color: #4ec9b0;
}

.error-item {
  color: #f48771;
  margin: 5px 0;
}

.debug-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.debug-toggle {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 9998;
}
</style>
