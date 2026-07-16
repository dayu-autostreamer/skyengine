<template>
  <DraggablePanel
    v-if="showPanel"
    :title="currentTab.label"
    :icon="currentTab.icon"
    :width="360"
    :height="480"
    :initial-pos="{ x: 12, y: 12 }"
    :max-height="0"
    @close="$emit('update:showPanel', false)"
  >
    <!-- Tab 栏 -->
    <div class="dp-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="dp-tab-btn"
        :class="{ active: modelValue === tab.key }"
        @click="$emit('update:modelValue', tab.key)"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- 动态 Tab 内容 -->
    <template v-for="tab in tabs" :key="tab.key">
      <slot v-if="modelValue === tab.key" :name="`tab-${tab.key}`">
        <!-- 默认渲染内置面板 -->
        <ControlPanel v-if="tab.key === 'control'" :disabled="isEditMode" />
        <ConfigPanel
          v-else-if="tab.key === 'config'"
          ref="configPanelRef"
          @edit-mode-change="$emit('edit-mode-change', $event)"
        />
        <MetricsPanel v-else-if="tab.key === 'metrics'" :show-chart="true" :factory-type="factoryType" />
        <EventPanel v-else-if="tab.key === 'events'" title="系统日志" />
        <AgentPanel v-else-if="tab.key === 'agent'" />
      </slot>
    </template>
  </DraggablePanel>

  <!-- 边缘切换按钮 -->
  <button v-if="!showPanel" class="panel-toggle left" @click="$emit('update:showPanel', true)">
    ▶ 面板
  </button>
</template>

<script setup>
import { computed } from 'vue';
import DraggablePanel from '@/components/DraggablePanel.vue';
import ControlPanel from '@/components/ControlPanel.vue';
import ConfigPanel from '@/components/ConfigPanel.vue';
import MetricsPanel from '@/components/MetricsPanel.vue';
import EventPanel from '@/components/EventPanel.vue';
import AgentPanel from '@/components/AgentPanel.vue';

const props = defineProps({
  tabs: { type: Array, required: true },
  modelValue: { type: String, default: 'simulation' },
  showPanel: { type: Boolean, default: true },
  isEditMode: { type: Boolean, default: false },
  isRunningTest: { type: Boolean, default: false },
  factoryType: { type: String, default: '' },
});

const emit = defineEmits([
  'update:modelValue',
  'update:showPanel',
  'edit-mode-change',
]);

const currentTab = computed(
  () => props.tabs.find((t) => t.key === props.modelValue) || props.tabs[0],
);
</script>

<style scoped>
@import "../views/styles/FactoryManage.css";
</style>
