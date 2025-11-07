<template>
  <template>

  </template>
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
  <router-view/>

</template>

<script setup>
import {ref, computed, watch} from "vue"
import {useRouter, useRoute} from "vue-router"

const router = useRouter()
const route = useRoute()

// 模拟工厂方案数据
const factories = [
  {
    id: "packet_factory",
    name: "翼辉电池装配无人产线",
    image: "factory-yihuibase.png",
    description: "地处华东核心制造区，配备智能 AGV 运输与全自动机器人电池装配流水线。",
    component: () => import('./FactoryManage.vue')
  },
  {
    id: "factory",
    name: "翼辉原料分拣货仓",
    image: "factory-yihuiwarehouse.png",
    description: "坐落于华东关键物流节点，拥有 AGV 智能分拣与自动化货物存储管理系统。",
    component: () => import('./GridFactoryManage.vue')
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

const enterFactory = () => {
  const routeName = `factory-${selectedFactory.value.id}`
  const existingRoute = router.getRoutes().find(r => r.name === routeName)

  if (!existingRoute) {
    router.addRoute('factory', {
      path: selectedFactory.value.id, // 相对路径
      name: routeName,
      component: selectedFactory.value.component,
      meta: {title: selectedFactory.value.name}
    })
  }

  router.push({name: routeName})
}

const getImage = () => {
  return `/api/cases/preview?factory_id=${selectedFactory.value.image}`;
}

</script>

<style scoped>
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
</style>
