<template>
  <div class="login-card">
    <!-- 上半部分：系统预览图 -->

    <div class="factory-dashboard" v-if="!isChildRoute">
      <!-- 上方选择/预览/控制栏，只有在不是子路由时显示 -->
      <!-- 工厂选择展示部分 -->
      <el-card class="preview-card" shadow="hover">
        <div class="image-wrapper">
          <el-image :src="getImage()" class="factory-image" fit="contain"/>
        </div>
      </el-card>
      <el-card class="info-card" shadow="never">
        <h2>{{ selectedFactory?.name }}</h2>
        <p>{{ selectedFactory?.description }}</p>
      </el-card>
      <!-- 控制栏 -->
      <el-card class="control-card" shadow="never">
        <div class="control-bar">
          <el-select v-model="selectedFactoryId" placeholder="选择工厂方案" style="width: 240px"
                     @change="updateFactory">
            <el-option
                v-for="factory in factories"
                :key="factory.id"
                :label="factory.name"
                :value="factory.id"
            />
          </el-select>

          <el-button type="primary" @click="onSignIn">进入工厂管理</el-button>
        </div>
      </el-card>

      <!-- 子路由渲染区域，总是显示 -->
    </div>
  </div>
</template>

<script setup>
import {ElMessage} from 'element-plus'

import {ref, computed, watch, reactive} from "vue"
import {useRouter, useRoute} from "vue-router"
import {useThemeConfig} from '/@/stores/themeConfig';
import {initFrontEndControlRoutes} from '/@/router/frontEnd';
import {NextLoading} from '/@/utils/loading';
import {storeToRefs} from 'pinia';
import {Session} from '/@/utils/storage';
import Cookies from 'js-cookie';
import {dynamicRoutes} from '/@/router/route'

const storesThemeConfig = useThemeConfig();
const {themeConfig} = storeToRefs(storesThemeConfig);
const route = useRoute();
const router = useRouter();
const state = reactive({
  ruleForm: {
    userName: 'tiangong',
  },
  loading: {
    signIn: false,
  },
});

// 模拟工厂方案数据
const factories = [
  {
    id: "packet_factory",
    name: "翼辉电池装配无人产线",
    image: "factory-yihuibase.png",
    description: "地处华东核心制造区，配备智能 AGV 运输与全自动机器人电池装配流水线。",
    component: () => import('../factory/FactoryManage.vue')
  },
  {
    id: "grid_factory",
    name: "翼辉原料分拣货仓",
    image: "factory-yihuiwarehouse.png",
    description: "坐落于华东关键物流节点，拥有 AGV 智能分拣与自动化货物存储管理系统。",
    component: () => import('../factory/GridFactoryManage.vue')
  },
  {
    id: "f2",
    name: "华东智能制造中心",
    image: "factory-east.png",
    description: "位于华东地区的核心制造基地，拥有先进的AGV调度系统与机器人装配线。",
  },
  {
    id: "f3",
    name: "西南仓储物流中心",
    image: "factory-southwest.png",
    description: "以仓储和物流为核心，集成多层货架系统与智能搬运路径规划。",
  },
  {
    id: "f4",
    name: "北方无人化装配厂",
    image: "factory-north.png",
    description: "实现高度自动化的装配流水线，支持数字孪生与实时数据采集。",
  },
]

const selectedFactoryId = ref("packet_factory")
const selectedFactory = computed(() => factories.find(f => f.id === selectedFactoryId.value))

const updateFactory = (id) => {
  console.log("切换到工厂：", id)
}
// 计算当前是否在子路由
const isChildRoute = computed(() => {
  // 当前路由路径以 /factory/开头且不等于 /factory 本身
  return route.path.startsWith('/factory/') && route.path !== '/factory'
})// 登录主函数
const onSignIn = async () => {
  state.loading.signIn = true

  // 写入登录 token & 用户信息
  Session.set('token', Math.random().toString(36).substr(0))
  Cookies.set('userName', state.ruleForm.userName)

  if (!themeConfig.value.isRequestRoutes) {
    const isNoPower = await initFrontEndControlRoutes()
    await signInSuccess(isNoPower)
  }

  state.loading.signIn = false
}

// 登录成功后的流程
const signInSuccess = async (isNoPower) => {
  if (isNoPower) {
    ElMessage.warning('Sorry, you do not have login permissions')
    Session.clear()
    return
  }

  // 注册 dynamicRoutes
  const existingFactory = router.getRoutes().find(r => r.name === 'factory')
  if (!existingFactory) {
    dynamicRoutes.forEach(route => {
      router.addRoute(route)
    })
    console.log('[✅ 路由已注册]:', router.getRoutes().map(r => r.name))
  }

  // 登录成功提示
  ElMessage.success('登录成功!')
  NextLoading.start()

  // 如果有 redirect 参数，优先跳转
  if (route.query && route.query.redirect) {
    const redirectPath = route.query.redirect
    let redirectParams = ''
    try {
      if (route.query.params && Object.keys(route.query.params).length > 0) {
        redirectParams = JSON.parse(route.query.params)
      }
    } catch (e) {
      console.warn('redirect params parse error:', e)
    }
    router.push({path: redirectPath, query: redirectParams})
    return
  }

  // 否则直接进入工厂页面
  await enterFactory()
}


const enterFactory = async () => {
  const factoryId = selectedFactory.value?.id || 'default'
  const newComponent = selectedFactory.value.component
  const newTitle = selectedFactory.value?.name || '默认工厂'

  const childRouteName = `factory-${factoryId}`

  const factoryRoute = router.getRoutes().find(r => r.name === 'factory')
  if (!factoryRoute) {
    console.error('❌ 未找到 factory 路由，请确保 dynamicRoutes 已注册')
    return
  }

  // 若还没有该子路由则添加
  const existingChild = router.getRoutes().find(r => r.name === childRouteName)
  if (!existingChild) {
    router.addRoute('factory', {
      path: factoryId, // 相对路径
      name: childRouteName,
      component: newComponent,
      meta: {
        title: newTitle,
        roles: ['tiangong', 'common'],
        icon: 'iconfont icon-zidingyibuju',
        isKeepAlive: true,
      },
    })
  }

  // 动态修改 factory 的 redirect 指向当前工厂
  factoryRoute.redirect = `/factory/${factoryId}`

  // 跳转进去
  await router.push(`/factory/${factoryId}`)
}
const loginForm = reactive({
  username: '',
  password: ''
})
const getImage = () => {
  return `/api/cases/preview?factory_id=${selectedFactory.value.image}`;
}

const previewImage = ref('/assets/factory-default.jpg')

const handleLogin = () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  // 登录逻辑...
  ElMessage.success(`欢迎回来，${loginForm.username}`)
}

</script>

<style scoped>
.login-card {
  width: 800px;
  background: #fff;
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  animation: slideUp 0.8s ease-out;
}

.factory-dashboard {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px;
  gap: 20px;
}

/* 图片展示卡片 */
.preview-card {
  width: 80%;
  max-width: 900px;
  height: 600px;
  border-radius: 16px;
  overflow: hidden;
  justify-content: center; /* 水平居中 */
  align-items: center; /* 垂直居中 */
}

.image-wrapper {
  max-width: 100%;
  max-height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.factory-image {
  max-width: 100%;
  max-height: 100%;
}

/* 文字说明 */
.info-card {
  width: 80%;
  max-width: 900px;
  text-align: center;
  background: transparent;
}

/* 控制栏 */
.control-card {
  width: 80%;
  max-width: 900px;
  background: transparent;
}

.control-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
