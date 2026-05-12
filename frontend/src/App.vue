<template>
  <div class="app-container">
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="app-header">
        <div class="header-content">
          <div class="logo">
            <el-icon size="24" color="#fff"><Document /></el-icon>
            <span class="title">人才简历优选系统</span>
          </div>
          <div class="nav-menu">
            <el-menu
              :default-active="activeRoute"
              mode="horizontal"
              background-color="transparent"
              text-color="#fff"
              active-text-color="#ffd04b"
              :ellipsis="false"
              router
            >
              <el-menu-item index="/">
                <el-icon><HomeFilled /></el-icon>首页
              </el-menu-item>
              <el-menu-item index="/upload">
                <el-icon><UploadFilled /></el-icon>上传
              </el-menu-item>
              <el-menu-item index="/ranking">
                <el-icon><Trophy /></el-icon>排名
              </el-menu-item>
              <el-menu-item index="/analysis">
                <el-icon><DataAnalysis /></el-icon>分析
              </el-menu-item>
              <el-menu-item index="/qa">
                <el-icon><ChatDotRound /></el-icon>问答
              </el-menu-item>
            </el-menu>
          </div>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>

      <!-- 底部 -->
      <el-footer class="app-footer">
        <p>人才简历综合优选系统 © 2024 | 基于AHP+熵权法的多维度评分模型</p>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeRoute = computed(() => route.path)
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.app-header {
  background: linear-gradient(135deg, #2E86AB 0%, #4ECDC4 100%);
  padding: 0;
  height: 56px !important;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 16px;
  max-width: 1600px;
  margin: 0 auto;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.logo .title {
  font-size: 16px;
  font-weight: bold;
  color: #fff;
  letter-spacing: 1px;
  white-space: nowrap;
}

.nav-menu {
  flex: 1;
  display: flex;
  justify-content: flex-end;
  overflow: visible;
}

.nav-menu :deep(.el-menu) {
  border-bottom: none;
  background: transparent !important;
  display: flex;
  flex-wrap: nowrap;
}

.nav-menu :deep(.el-menu-item) {
  font-size: 13px;
  font-weight: 500;
  padding: 0 14px !important;
  height: 56px;
  line-height: 56px;
}

.nav-menu :deep(.el-menu-item .el-icon) {
  margin-right: 4px;
  font-size: 16px;
}

.app-main {
  padding: 16px 20px;
  min-height: calc(100vh - 112px);
}

.app-footer {
  background: #2c3e50;
  color: #fff;
  text-align: center;
  line-height: 48px;
  height: 48px !important;
}

.app-footer p {
  margin: 0;
  font-size: 13px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
