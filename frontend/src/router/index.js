import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('@/views/Upload.vue'),
    meta: { title: '简历上传' }
  },
  {
    path: '/ranking',
    name: 'Ranking',
    component: () => import('@/views/Ranking.vue'),
    meta: { title: '排名看板' }
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('@/views/Analysis.vue'),
    meta: { title: '数据分析' }
  },
  {
    path: '/qa',
    name: 'QA',
    component: () => import('@/views/QA.vue'),
    meta: { title: '智能问答' }
  },
  {
    path: '/candidate/:id',
    name: 'CandidateDetail',
    component: () => import('@/views/CandidateDetail.vue'),
    meta: { title: '候选人详情' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 人才简历综合优选系统` : '人才简历综合优选系统'
  next()
})

export default router
