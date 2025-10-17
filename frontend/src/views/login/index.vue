<template>
  <div class="login-container">
    <!-- 左侧：系统品牌区 -->
    <div class="login-left">
      <div class="brand-info">
        <h1 class="title">TianGong System</h1>
        <p class="subtitle">
          提供灵活制造数据分析的基础支撑平台
        </p>
        <el-tag type="success" class="version-tag">
          System Version: {{ tiangongVersion }}
        </el-tag>
      </div>
    </div>

    <!-- 右侧：工厂预览 + 登录 -->
    <div class="login-right">
      <div class="factory-preview-wrapper">
        <el-image
          v-if="factoryImage"
          class="factory-preview"
          :src="factoryImage"
          fit="cover"
        />
        <div v-else class="factory-preview factory-placeholder">
          <span>正在加载工厂预览...</span>
        </div>

        <!-- 悬浮登录框 -->
        <div class="login-floating-box">
          <AccountLogin />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import axios from 'axios';
import AccountLogin from './account.vue';

const tiangongVersion = import.meta.env.VITE_TIANGONG_VERSION || 'v1.0';
const factoryImage = ref<string | null>(null);

const loadFactoryPreview = async () => {
  try {
    const { data } = await axios.get('/api/factory/preview', { responseType: 'blob' });
    factoryImage.value = URL.createObjectURL(data);
  } catch (err) {
    console.error(err);
    ElMessage.error('加载工厂预览失败');
  }
};

onMounted(() => loadFactoryPreview());
</script>

<style scoped lang="scss">
.login-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #f8f9fb;
}

/* 左侧系统信息区 */
.login-left {
  flex: 0 0 40%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(160deg, #2d5be3 0%, #4f87ff 100%);
  color: #fff;
  padding: 0 60px;
  position: relative;

  .brand-info {
    text-align: left;
    max-width: 420px;
    animation: fadeIn 1s ease-out;

    .title {
      font-size: 46px;
      font-weight: 600;
      margin-bottom: 12px;
    }

    .subtitle {
      font-size: 18px;
      opacity: 0.9;
      margin-bottom: 25px;
      line-height: 1.6;
    }

    .version-tag {
      font-size: 15px;
      background-color: rgba(255, 255, 255, 0.2);
      border: none;
      color: #fff;
      padding: 10px 18px;
      border-radius: 18px;
    }
  }
}

/* 右侧预览+登录区 */
.login-right {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #000;
}

.factory-preview-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.factory-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: brightness(0.75);
}

.factory-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc;
  font-size: 18px;
}

/* 悬浮登录框 */
.login-floating-box {
  position: absolute;
  bottom: 8%;
  right: 8%;
  width: 380px;
  padding: 28px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(8px);
  animation: fadeUp 0.8s ease-out;
}

/* 动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes fadeUp {
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
