<template>
  <div class="home-container">
    <!-- 欢迎区域 -->
    <div class="hero-section">
      <el-row :gutter="40" align="middle">
        <el-col :span="12">
          <div class="hero-content">
            <h1 class="hero-title">
              <span class="highlight">AI驱动</span>的人才优选系统
            </h1>
            <p class="hero-desc">
              基于AHP层次分析法与熵权法融合的多维度评分模型，
              为6大行业提供科学的简历评价与人才排名服务。
            </p>
            <div class="hero-actions">
              <el-button type="primary" size="large" @click="$router.push('/upload')">
                <el-icon><Upload /></el-icon>上传简历
              </el-button>
              <el-button size="large" @click="$router.push('/ranking')">
                <el-icon><View /></el-icon>查看排名
              </el-button>
            </div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="hero-stats">
            <el-row :gutter="20">
              <el-col :span="12" v-for="stat in stats" :key="stat.label">
                <div class="stat-card" :class="stat.type">
                  <el-icon :size="40"><component :is="stat.icon" /></el-icon>
                  <div class="stat-value">{{ stat.value }}</div>
                  <div class="stat-label">{{ stat.label }}</div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 行业卡片 -->
    <div class="industry-section">
      <h2 class="section-title">支持行业领域</h2>
      <el-row :gutter="20">
        <el-col :span="8" v-for="industry in industries" :key="industry.code">
          <el-card class="industry-card" shadow="hover" @click="selectIndustry(industry.code)">
            <div class="industry-icon" :style="{ background: industry.color }">
              <el-icon :size="32" color="#fff"><component :is="industry.icon" /></el-icon>
            </div>
            <h3 class="industry-name">{{ industry.name }}</h3>
            <p class="industry-desc">{{ industry.description }}</p>
            <div class="industry-action">
              <el-button type="primary" text>查看排名 <el-icon><ArrowRight /></el-icon></el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 模型说明 -->
    <div class="model-section">
      <h2 class="section-title">评分模型架构</h2>
      <el-row :gutter="30">
        <el-col :span="6" v-for="(dim, index) in dimensions" :key="index">
          <div class="dimension-card">
            <div class="dim-icon" :style="{ background: dim.color }">{{ dim.icon }}</div>
            <h4 class="dim-name">{{ dim.name }}</h4>
            <p class="dim-desc">{{ dim.description }}</p>
            <div class="dim-formula">{{ dim.formula }}</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 流程说明 -->
    <div class="process-section">
      <h2 class="section-title">系统工作流程</h2>
      <div class="process-flow">
        <div class="process-step" v-for="(step, index) in processSteps" :key="index">
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-content">
            <el-icon :size="32" color="#2E86AB"><component :is="step.icon" /></el-icon>
            <h4>{{ step.title }}</h4>
            <p>{{ step.desc }}</p>
          </div>
          <div class="step-arrow" v-if="index < processSteps.length - 1">
            <el-icon><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useResumeStore } from '@/stores'

const router = useRouter()
const store = useResumeStore()

const stats = ref([
  { label: '支持行业', value: '6+', icon: 'OfficeBuilding', type: 'primary' },
  { label: '评分维度', value: '4', icon: 'DataAnalysis', type: 'success' },
  { label: '评估指标', value: '10+', icon: 'List', type: 'warning' },
  { label: '准确率', value: '95%', icon: 'CircleCheck', type: 'danger' }
])

const industries = ref([
  { code: '电商', name: '电商行业', description: '电商运营、直播运营、电商总监等岗位', icon: 'ShoppingCart', color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { code: '品牌', name: '品牌市场', description: '品牌管理、市场推广、品牌总监等岗位', icon: 'Flag', color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { code: '销售', name: '销售业务', description: '销售、外贸、渠道、业务负责人等岗位', icon: 'Sell', color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' },
  { code: '研发', name: '研发技术', description: '研发、技术、科学家、研究院院长等岗位', icon: 'Cpu', color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' },
  { code: '生产', name: '生产管理', description: '生产管理、厂长、质量、生产总监等岗位', icon: 'FirstAidKit', color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' },
  { code: '人力资源', name: '人力资源', description: 'HR、招聘、薪酬、HRD、HRBP等岗位', icon: 'UserFilled', color: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)' }
])

const dimensions = ref([
  { name: '教育背景', icon: '🎓', color: '#667eea', description: '学历水平、毕业院校、专业匹配度', formula: 'Sedu = w1×学历 + w2×学校 + w3×专业' },
  { name: '工作经历', icon: '💼', color: '#f5576c', description: '公司实力、稳定性、升职速度', formula: 'Sexp = w1×公司 + w2×稳定性 + w3×升职' },
  { name: '技能成果', icon: '🏆', color: '#4facfe', description: '技能匹配度、重大成果、项目经验', formula: 'Sskill = w1×技能 + w2×成果' },
  { name: '综合素质', icon: '⭐', color: '#43e97b', description: '软技能、情商、跳槽惩罚', formula: 'Sadj = 软技能 - 跳槽惩罚' }
])

const processSteps = ref([
  { title: '简历上传', desc: '支持PDF、DOCX、TXT格式', icon: 'Upload' },
  { title: '智能解析', desc: 'NLP提取关键信息', icon: 'DataLine' },
  { title: '维度评分', desc: '四维度综合评估', icon: 'Histogram' },
  { title: '动态权重', desc: 'AHP+熵权法计算', icon: 'ScaleToOriginal' },
  { title: '生成排名', desc: 'TCI综合得分排序', icon: 'Trophy' }
])

const selectIndustry = (code) => {
  store.currentIndustry = code
  router.push(`/ranking?industry=${code}`)
}

onMounted(() => {
  store.fetchIndustries()
})
</script>

<style scoped>
.home-container {
  max-width: 1400px;
  margin: 0 auto;
}

.hero-section {
  padding: 40px 0;
}

.hero-content {
  padding-right: 40px;
}

.hero-title {
  font-size: 42px;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 20px;
  line-height: 1.3;
}

.hero-title .highlight {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-desc {
  font-size: 18px;
  color: #666;
  line-height: 1.8;
  margin-bottom: 30px;
}

.hero-actions {
  display: flex;
  gap: 15px;
}

.hero-actions .el-button {
  padding: 12px 30px;
  font-size: 16px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 25px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  margin-bottom: 20px;
  transition: transform 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #2E86AB;
  margin: 10px 0;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.section-title {
  font-size: 28px;
  font-weight: bold;
  color: #2c3e50;
  text-align: center;
  margin: 50px 0 30px;
  position: relative;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 4px;
  background: linear-gradient(135deg, #2E86AB 0%, #4ECDC4 100%);
  border-radius: 2px;
}

.industry-card {
  border-radius: 16px;
  margin-bottom: 20px;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
}

.industry-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 30px rgba(0,0,0,0.12);
}

.industry-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 15px;
}

.industry-name {
  font-size: 20px;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 8px;
}

.industry-desc {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 15px;
  height: 44px;
}

.industry-action {
  text-align: right;
}

.dimension-card {
  background: #fff;
  border-radius: 16px;
  padding: 25px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  height: 100%;
}

.dim-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 15px;
  font-size: 28px;
}

.dim-name {
  font-size: 18px;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 10px;
}

.dim-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 15px;
}

.dim-formula {
  font-size: 12px;
  color: #2E86AB;
  background: #f0f7ff;
  padding: 8px;
  border-radius: 8px;
  font-family: monospace;
}

.process-flow {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 20px;
  padding: 30px 0;
}

.process-step {
  display: flex;
  align-items: center;
  gap: 15px;
}

.step-number {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #2E86AB 0%, #4ECDC4 100%);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 18px;
}

.step-content {
  text-align: center;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.08);
  min-width: 150px;
}

.step-content h4 {
  margin: 10px 0 5px;
  color: #2c3e50;
}

.step-content p {
  font-size: 12px;
  color: #666;
  margin: 0;
}

.step-arrow {
  color: #2E86AB;
  font-size: 24px;
}
</style>
