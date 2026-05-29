<template>
  <div class="app-container">
    <el-container>
      <!-- Header -->
      <el-header class="app-header" height="var(--header-height)">
        <div class="header-content">
          <div class="logo" @click="$router.push('/')">
            <div class="logo-icon">
              <el-icon size="20"><DataAnalysis /></el-icon>
            </div>
            <span class="logo-text">人才简历优选系统</span>
          </div>

          <nav class="nav-main">
            <router-link
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              class="nav-link"
              :class="{ active: isActive(item.path) }"
            >
              <el-icon :size="16"><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </router-link>
          </nav>

          <div class="header-actions">
            <button class="theme-toggle" @click="themeStore.toggle()" :title="themeStore.isDark ? '切换浅色' : '切换深色'">
              <el-icon :size="18">
                <Sunny v-if="themeStore.isDark" />
                <Moon v-else />
              </el-icon>
            </button>
          </div>
        </div>
      </el-header>

      <!-- Main Content -->
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>

      <!-- Footer -->
      <el-footer class="app-footer" height="40px">
        <span>人才简历综合优选系统 &copy; 2026 | D-TCI + AHP-熵权法</span>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from '@/stores/theme'
import { DataAnalysis, UploadFilled, Trophy, PieChart, Sunny, Moon } from '@element-plus/icons-vue'

const route = useRoute()
const themeStore = useThemeStore()

const navItems = [
  { path: '/upload', label: '简历上传', icon: 'UploadFilled' },
  { path: '/ranking', label: '排名看板', icon: 'Trophy' },
  { path: '/analysis', label: '数据分析', icon: 'PieChart' },
  { path: '/comparison', label: '候选人对比', icon: 'Connection' },
  { path: '/recommendation', label: '智能推荐', icon: 'MagicStick' },
  { path: '/decision', label: '决策报告', icon: 'Document' },
  { path: '/qa', label: '智能问答', icon: 'ChatDotRound' }
]

const isActive = (path) => {
  if (path === '/ranking') return route.path === '/ranking' || route.path.startsWith('/candidate')
  return route.path === path
}

onMounted(() => {
  themeStore.init()
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: var(--color-bg-page);
}

.app-header {
  background: var(--header-bg);
  padding: 0;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 var(--space-lg);
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  cursor: pointer;
  flex-shrink: 0;
}

.logo-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.logo-text {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: #fff;
  letter-spacing: 0.5px;
}

.nav-main {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  overflow-x: auto;
  scrollbar-width: none;
}
.nav-main::-webkit-scrollbar {
  display: none;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  font-size: var(--font-size-sm);
  font-weight: 500;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.12);
}

.nav-link.active {
  color: #fff;
  background: rgba(255, 255, 255, 0.2);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.theme-toggle {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  border: none;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.theme-toggle:hover {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.app-main {
  padding: var(--space-lg);
  min-height: calc(100vh - var(--header-height) - 40px);
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.app-footer {
  background: var(--footer-bg);
  color: var(--footer-text);
  text-align: center;
  line-height: 40px;
  font-size: var(--font-size-xs);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .nav-link span {
    display: none;
  }
  .logo-text {
    font-size: var(--font-size-base);
  }
  .app-main {
    padding: var(--space-md);
  }
}
</style>
