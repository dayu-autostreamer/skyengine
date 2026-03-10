<template>
  <div class="coming-soon-container">
    <div class="content-wrapper">
      <div class="icon-area">
        <span class="construction-icon">🚧</span>
      </div>

      <h1 class="title">工厂功能开发中</h1>
      <p class="subtitle">{{ factory.name }}</p>

      <div class="info-box">
        <div class="info-item">
          <span class="label">工厂 ID:</span>
          <span class="value">{{ factory.id }}</span>
        </div>
        <div class="info-item">
          <span class="label">状态:</span>
          <span class="value status">开发中</span>
        </div>
        <div class="info-item">
          <span class="label">描述:</span>
          <span class="value">{{ factory.description }}</span>
        </div>
      </div>

      <div class="features">
        <h3>计划功能</h3>
        <ul>
          <li>🎯 生产管理系统</li>
          <li>📊 实时数据监控</li>
          <li>🚀 生产任务调度</li>
          <li>📈 性能分析报告</li>
        </ul>
      </div>

      <p class="coming-text">敬请期待...</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  factory: {
    type: Object,
    required: true,
  },
})
</script>

<style scoped>
@import '../styles/ComingSoonFactory.css';
</style>
