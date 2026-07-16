/**
 * Hook 注册中心 — 列出所有可用 Hook
 *
 * Hook 契约：
 * {
 *   id: 'machine_util',         // 与 dashboard 配置里的 hook 字段对应
 *   label: '机器利用率',
 *   unit: '%',
 *   series: (ctx) => [{x, y}, ...]
 * }
 *
 * 这些 hook 是纯函数，对数据来源无感知；由 caller 归一化 ctx 后即可复用：
 *   实时：{ metrics: monitor.metricsTimeline, frames: [...], source: 'live' }
 *   存档：{ metrics: run.metricsTimeline, frames: run.frames, source: 'archive' }
 */
import machineUtil from './machine_util.js'
import agvActivity from './agv_activity.js'
import jobProgress from './job_progress.js'
import eventTimeline from './event_timeline.js'
import machineLoad from './machine_load.js'
import agvStats from './agv_stats.js'
import efficiency from './efficiency.js'
import exceptionSummary from './exception_summary.js'

export const HOOKS = {
  machine_util: machineUtil,
  efficiency,
  agv_activity: agvActivity,
  agv_stats: agvStats,
  job_progress: jobProgress,
  event_timeline: eventTimeline,
  exception_summary: exceptionSummary,
  machine_load: machineLoad,
}

export function getHook(id) {
  return HOOKS[id] || null
}

export function listHooks() {
  return Object.values(HOOKS)
}
