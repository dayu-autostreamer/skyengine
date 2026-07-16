<template>
  <div class="job-status-panel">
    <div class="panel-header">
      <h3>📦 Job 状态</h3>
      <span class="summary" v-if="hasData">
        完成 {{ summary.done }}/{{ summary.total }}
        <span v-if="summary.overdue" class="overdue-tag">⚠️ 超期 {{ summary.overdue }}</span>
      </span>
      <span class="hint" v-else>等待 frame 数据...</span>
    </div>

    <div v-if="hasData" class="job-list">
      <div
        v-for="job in jobList"
        :key="job.job_id"
        class="job-card"
        :class="{ selected: job.job_id === store.selectedJobId, completed: job.is_completed }"
        @click="store.selectJob(job.job_id)"
      >
        <div class="job-head">
          <span class="j-id">Job{{ job.job_id }}</span>
          <span class="j-state" :class="job.stateClass">{{ job.stateLabel }}</span>
          <span v-if="job.dueInfo" class="j-due" :class="{ overdue: job.dueInfo.overdue }">
            📅 {{ job.dueInfo.text }}
          </span>
        </div>

        <div class="progress-row">
          <div class="bar-wrap">
            <div class="bar" :style="{ width: job.progressPct + '%' }"></div>
          </div>
          <span class="progress-val">{{ job.progress.done }}/{{ job.progress.total }}</span>
        </div>

        <!-- op 时间轴 -->
        <div class="op-timeline">
          <div
            v-for="op in job.ops"
            :key="op.op_id"
            class="op-cell"
            :class="`op-${op.status.toLowerCase()}`"
            :title="op.title"
            @click.stop="op.assigned_machine != null && store.selectMachine(`M${op.assigned_machine}`)"
          >
            <span class="op-id">Op{{ op.op_id }}</span>
            <span class="op-time">{{ op.proc_time }}t</span>
          </div>
        </div>

        <!-- 展开明细 -->
        <div v-if="job.job_id === store.selectedJobId" class="op-details">
          <div v-for="op in job.ops" :key="op.op_id" class="op-detail-row">
            <span class="od-id">Op{{ op.op_id }}</span>
            <span class="od-status" :class="`op-${op.status.toLowerCase()}`">{{ op.status }}</span>
            <span class="od-mach" :title="op.assigned_machine != null ? `运行 ID: M${op.assigned_machine}` : ''">
              {{ store.getMachineDisplayName(op.assigned_machine, store.currentState) }}
            </span>
            <span class="od-time">proc {{ op.proc_time }}t</span>
            <span class="od-time">wait {{ op.wait_for_machine_time }}t</span>
            <span class="od-ts" v-if="op.start_process_at >= 0">
              [{{ op.start_process_at }}→{{ op.finish_process_at >= 0 ? op.finish_process_at : '?' }}]
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useFactoryStore } from '@/stores/factory'

const store = useFactoryStore()

const rawJobs = computed(() => store.currentState?.jobs || [])
const hasData = computed(() => rawJobs.value.length > 0)

function envTimelineStep() {
  const envTl = store.currentState?.env_timeline
  const m = String(envTl ?? '').match(/(\d+)/)
  return m ? Number(m[1]) : null
}

const summary = computed(() => {
  let done = 0
  let total = 0
  let overdue = 0
  const stepNum = envTimelineStep()
  rawJobs.value.forEach((j) => {
    if (j.is_completed) done += 1
    total += 1
    if (!j.is_completed && j.due != null && stepNum != null && stepNum > j.due) {
      overdue += 1
    }
  })
  return { done, total, overdue }
})

function buildDueInfo(job) {
  if (job.due == null) return null
  const stepNum = envTimelineStep()
  if (job.is_completed) {
    return {
      text: `交期 t${job.due} · 完工 t${job.completion_time}`,
      overdue: job.completion_time > job.due,
    }
  }
  if (stepNum != null) {
    return {
      text: `交期 t${job.due} · 当前 t${stepNum}`,
      overdue: stepNum > job.due,
    }
  }
  return { text: `交期 t${job.due}`, overdue: false }
}

// template 直接消费的派生列表
const jobList = computed(() =>
  rawJobs.value.map((job) => {
    const pct = job.progress.total > 0
      ? Math.round((job.progress.done / job.progress.total) * 100)
      : 0
    return {
      ...job,
      progressPct: pct,
      stateLabel: job.is_completed ? '已完成' : `${job.progress.done}/${job.progress.total}`,
      stateClass: job.is_completed ? 'completed' : 'progress',
      dueInfo: buildDueInfo(job),
      ops: job.ops.map((op) => ({
        ...op,
        title:
          `Op${op.op_id} [${op.status}]\n` +
          `proc_time=${op.proc_time}, machine=${store.getMachineDisplayName(op.assigned_machine, store.currentState)}\n` +
          `wait=${op.wait_for_machine_time}t\n` +
          `start=${op.start_process_at}, finish=${op.finish_process_at}`,
      })),
    }
  })
)
</script>

<style scoped>
.job-status-panel {
  height: 100%;
  overflow-y: auto;
  padding: 8px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.panel-header h3 { font-size: 14px; margin: 0; color: #c0d0e0; }
.summary { font-size: 11px; color: #b0d0ff; }
.overdue-tag { color: #ff6464; margin-left: 6px; }
.hint { font-size: 11px; color: #707070; }

.job-list { display: flex; flex-direction: column; gap: 6px; }
.job-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  transition: all .15s;
}
.job-card:hover { background: rgba(255,255,255,0.08); }
.job-card.selected {
  border-color: #66d06a;
  box-shadow: 0 0 0 2px rgba(102,208,106,0.25);
}
.job-card.completed { opacity: 0.7; }

.job-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}
.j-id { font-weight: 600; color: #e0e8f0; }
.j-state {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(255,255,255,0.08);
  color: #b0b8c0;
}
.j-state.completed { background: rgba(102,208,106,0.2); color: #66d06a; }
.j-state.progress { background: rgba(100,181,255,0.2); color: #64b5ff; }
.j-due { margin-left: auto; font-size: 11px; color: #a0a0a0; }
.j-due.overdue { color: #ff6464; }

.progress-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0;
}
.bar-wrap {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.06);
  border-radius: 3px;
  overflow: hidden;
}
.bar { height: 100%; background: linear-gradient(90deg, #66d06a, #4CAF50); border-radius: 3px; transition: width .2s; }
.progress-val { width: 40px; text-align: right; font-size: 11px; font-variant-numeric: tabular-nums; color: #b0b8c0; }

.op-timeline {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-top: 6px;
}
.op-cell {
  font-size: 10px;
  padding: 2px 5px;
  border-radius: 3px;
  background: rgba(255,255,255,0.06);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 36px;
  transition: all .1s;
}
.op-cell:hover { transform: scale(1.05); }
.op-id { font-weight: 600; color: #c0c8d0; }
.op-time { color: #808890; font-size: 9px; }
.op-pending { background: rgba(160,160,160,0.15); }
.op-processing { background: rgba(100,181,255,0.25); }
.op-processing .op-id { color: #64b5ff; }
.op-finished { background: rgba(102,208,106,0.22); }
.op-finished .op-id { color: #66d06a; }

.op-details {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed rgba(255,255,255,0.08);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.op-detail-row {
  display: grid;
  grid-template-columns: 40px 70px 40px 60px 60px 1fr;
  gap: 4px;
  font-size: 10px;
  color: #a0a8b0;
  font-variant-numeric: tabular-nums;
}
.od-id { font-weight: 600; color: #c0c8d0; }
.od-status.op-processing { color: #64b5ff; }
.od-status.op-finished { color: #66d06a; }
.od-status.op-pending { color: #a0a0a0; }
.od-mach { color: #b0d0ff; cursor: pointer; }
.od-ts { color: #808890; }
</style>
