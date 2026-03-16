<template>
  <div class="factory-container">
    <div class="bg-overlay"></div>

    <transition name="fade" mode="out-in">
      <div class="factory-selector" v-if="!isInFactory" key="selector">
        <div class="nav-bar">
          <button class="btn-home" @click="backToHome">
            <span class="icon">←</span>
            <span class="text">返回主页</span>
          </button>
        </div>

        <div class="selector-content">
          <div class="selector-header">
            <h1>工作空间选择</h1>
            <p>Select Your Factory Workspace</p>
            <div class="deco-line"></div>
          </div>

          <div class="scroll-box-container">
            <div class="factory-grid">
              <div v-for="factory in factories" :key="factory.id" class="factory-card"
                @click="enterFactory(factory.id)">
                <div class="card-image">
                  <img :src="factory.image ||
                    'https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=800'
                    " :alt="factory.name" />
                  <div class="hover-overlay">
                    <span class="enter-btn">进入车间 →</span>
                  </div>
                </div>
                <div class="card-content">
                  <div class="content-top">
                    <h3>{{ factory.name }}</h3>
                    <div class="status-dot"></div>
                  </div>
                  <span class="id-tag">ID: {{ factory.id }}</span>
                  <p class="desc">{{ factory.description }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="factory-content" v-else key="content">
        <div class="content-header">
          <div class="header-left">
            <button class="btn-back-internal" @click="backToSelector">
              <span class="icon">✕</span> 退出工作台
            </button>
            <div class="divider"></div>
            <div class="header-info">
              <h2>{{ currentFactory.name }}</h2>
              <span class="header-badge">LIVE</span>
            </div>
          </div>
        </div>

        <div class="component-wrapper">
          <component :is="currentFactoryComponent" :factory="currentFactory" />
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, defineAsyncComponent } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import FactoryPlayerSSE from "@/components/FactoryPlayerSSE.vue";
import { useFactoryStore } from "@/stores/factory";
import { apiPost, API_ROUTES } from "@/utils/api";

const factoryStore = useFactoryStore();
const router = useRouter();
const isInFactory = ref(false);
const currentFactoryId = ref(null);

// 工厂配置列表
const factories = computed(() => factoryStore.getFactories());

const currentFactory = computed(
  () => factories.value.find((f) => f.id === currentFactoryId.value) || {},
);

// 进入工厂
const enterFactory = async (factoryId) => {
  try {
    // 先调用后端切换工厂接口，确保工厂代理已初始化
    console.log("切换工厂到ID:", factoryId);
    const response = await apiPost(API_ROUTES.FACTORY_CONTROL_SWITCH, {
      factory_id: factoryId,
    });
    console.log("Factory switch response:", response);
    if (response.status === "ok") {
      currentFactoryId.value = factoryId;
      factoryStore.setCurrentFactory(factoryId);

      isInFactory.value = true;

      // 快速切换，减少卡顿
      const factory = factories.value.find((f) => f.id === factoryId);
      if (factory) {
        ElMessage.success({
          message: `已连接: ${factory.name}`,
          type: "success",
          duration: 1500,
        });
      }
    } else {
      ElMessage.error({
        message: `切换工厂失败: ${response.message || "未知错误"}`,
        type: "error",
        duration: 3000,
      });
    }
  } catch (error) {
    console.error("切换工厂时出错:", error);
    ElMessage.error({
      message: `切换工厂失败: ${error.message || "网络错误"}`,
      type: "error",
      duration: 3000,
    });
  }
};

// 返回选择列表
const backToSelector = () => {
  isInFactory.value = false;
  currentFactoryId.value = null;
};

// 返回主页 (Router)
const backToHome = () => {
  router.push("/");
};

const currentFactoryComponent = computed(() => {
  if (!currentFactory.value) return null;
  const factoryId = currentFactory.value.id;

  // 根据工厂类型加载不同的管理组件
  switch (factoryId) {
    case "grid_factory":
      return defineAsyncComponent(
        () => import("@/views/factory/GridFactoryManage.vue"),
      );
    case "packet_factory":
      return defineAsyncComponent(
        () => import("@/views/factory/PacketFactoryManage.vue"),
      );
    case "northeast_center":
      return defineAsyncComponent(
        () => import("@/views/factory/StaticFactoryManage.vue"),
      );
    case "southwest_logistics":
      return defineAsyncComponent(
        () => import("@/views/factory/ComingSoonFactory.vue"),
      );
    default:
      return defineAsyncComponent(
        () => import("@/views/factory/FactoryManage.vue"),
      );
  }
});
</script>

<style scoped>
@import "./styles/FactoryView.scss";
</style>
