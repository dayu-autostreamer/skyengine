<template>
  <div class="login-container">
    <!-- 左侧：系统品牌区 -->
    <div class="login-left">
      <div class="brand-info">
        <!-- 品牌文字LOGO -->
<!--        <div class="login-left-img">-->
<!--          <img :src="loginMain"/>-->
<!--        </div>-->
        <div class="brand-logo-wrapper">
          <h1 class="brand-logo-text">TianGong</h1>
        </div>

        <!-- 系统文字信息 -->
        <h1 class="title">TianGong System</h1>
        <p class="subtitle">提供灵活制造数据分析的基础支撑平台</p>
        <el-tag type="success" class="version-tag">
          System Version: {{ $t('message.version') }}
        </el-tag>
      </div>
    </div>

    <!-- 右侧：工厂预览 + 登录 -->
    <div class="login-right">
      <div class="factory-preview-wrapper">
        <AccountLogin/>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AccountLogin from './account.vue';
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
  color: #fff;
  padding: 0 60px;
  position: relative;
  background: linear-gradient(145deg, #ff9966 0%, #ff5e62 100%);
  background-size: cover;
  background-position: center;
  overflow: hidden;

  /* 增加柔光覆盖层，让背景更柔和 */
  &::after {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.15), transparent 70%);
    mix-blend-mode: screen;
  }

  .brand-info {
    text-align: left;
    max-width: 420px;
    animation: fadeIn 1s ease-out;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    position: relative;
    z-index: 2; /* 覆盖柔光层 */

    /* 品牌文字Logo样式 */
    .brand-logo-wrapper {
      margin-bottom: 10px;

      .brand-logo-text {
        font-family: 'Cinzel Decorative', 'Playfair Display', serif;
        font-size: 58px;
        font-weight: 700;
        letter-spacing: 2px;
        background: linear-gradient(90deg, #fff2cc, #ffe0b2, #ffffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 2px 10px rgba(255, 255, 255, 0.25);
        animation: shimmer 3s infinite linear;
      }
    }

    .title {
      font-size: 38px;
      font-weight: 600;
      margin-bottom: 6px;
      letter-spacing: 1px;
    }

    .subtitle {
      font-size: 18px;
      opacity: 0.9;
      margin-bottom: 20px;
      line-height: 1.6;
      color: rgba(255, 255, 255, 0.95);
    }

    .version-tag {
      font-size: 15px;
      background-color: rgba(255, 255, 255, 0.25);
      border: none;
      color: #fff;
      padding: 10px 18px;
      border-radius: 18px;
      backdrop-filter: blur(4px);
    }
  }
}

/* 动画：文字光泽流动 */
@keyframes shimmer {
  0% {
    background-position: 0% 50%;
  }
  100% {
    background-position: 200% 50%;
  }
}

/* 入场动画 */
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

.login-right {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: radial-gradient(circle at 30% 40%, #ffe0b2 0%, #ffb199 50%, #ff9966 100%);
  display: flex;
  justify-content: center;
  align-items: center;

  &::before {
    content: "";
    position: absolute;
    inset: 0;
    background: url("/assets/factory-bg.jpg") center/cover no-repeat;
    opacity: 0.25;
    filter: blur(8px);
  }
}

.factory-preview-wrapper {
  width: 100%;
  height: 100%;
  position: relative;

  display: flex;
  justify-content: center;
  align-items: center;
}

/* 让登录框居中，而不是固定在右下角 */
.login-floating-box {
  position: relative; /* 改为相对定位，以便容器居中 */
  width: 460px;
  padding: 36px 42px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(8px);
  animation: fadeUp 0.8s ease-out;

  /* 居中对齐 */
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
