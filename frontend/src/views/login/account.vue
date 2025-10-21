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

          <el-button type="primary" @click="enterFactory">进入工厂管理</el-button>
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
import {storeToRefs} from 'pinia';
import {Session} from '/@/utils/storage';
import Cookies from 'js-cookie';

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
    id: "factory",
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
})

const onSignIn = async () => {
  state.loading.signIn = true;
  // 存储 token 到浏览器缓存
  Session.set('token', Math.random().toString(36).substr(0));
  // 模拟数据，对接接口时，记得删除多余代码及对应依赖的引入。用于 `/src/stores/userInfo.ts` 中不同用户登录判断（模拟数据）
  Cookies.set('userName', state.ruleForm.userName);
  if (!themeConfig.value.isRequestRoutes) {
    // 前端控制路由，2、请注意执行顺序
    const isNoPower = await initFrontEndControlRoutes();
    signInSuccess(isNoPower);
  } else {
    // 模拟后端控制路由，isRequestRoutes 为 true，则开启后端控制路由
    // 添加完动态路由，再进行 router 跳转，否则可能报错 No match found for location with path "/"
    const isNoPower = await initBackEndControlRoutes();
    // 执行完 initBackEndControlRoutes，再执行 signInSuccess
    signInSuccess(isNoPower);
  }
};

const enterFactory = () => {
  const routeName = 'factory'
  const factoryId = selectedFactory.value.id
  const newComponent = selectedFactory.value.component
  const newTitle = selectedFactory.value.name

  // 先删除旧的 factory 路由
  const existingRoute = router.getRoutes().find(r => r.name === routeName)
  if (existingRoute) {
    router.removeRoute(routeName)
  }

  // 添加新的 factory 路由，直接替换成新的组件
  router.addRoute({
    path: '/factory',
    name: routeName,
    component: newComponent,
    meta: {
      title: newTitle,
      roles: ['tiangong', 'common'],
      icon: 'iconfont icon-zidingyibuju',
      isKeepAlive: true,
    },
  })

  // 登录状态更新
  onSignIn()

  // 跳转到新的 factory 页面
  router.push({name: routeName})
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

const switchMode = (mode) => {
  if (mode === 'factory') {
    previewImage.value = '/assets/factory-preview-2.jpg'
    ElMessage.info('已切换至工厂预览模式')
  } else {
    previewImage.value = '/assets/factory-admin.jpg'
    ElMessage.info('已切换至管理员预览')
  }
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
