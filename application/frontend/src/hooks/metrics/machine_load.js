/**
 * 各机器负载快照。
 * 容器模式用 queue_length，静态模式优先使用 load；仅展示当前值和近期均值，
 * 避免把“机器数 x 运行帧数”全部展开成无法阅读的分组柱。
 */
const RECENT_FRAME_COUNT = 60

function machineValue(machine) {
  if (typeof machine?.load === 'number') return machine.load
  if (typeof machine?.queue_length === 'number') return machine.queue_length
  return null
}

function getMachine(machines, label) {
  if (Array.isArray(machines)) return machines.find((machine) => machine.id === label)
  return machines?.[label]
}

export default {
  id: 'machine_load',
  label: '各机器负载',
  unit: '',
  multiSeries: true,
  series: (ctx) => {
    const frames = ctx.frames || []
    if (frames.length === 0) return []

    const lastMachines = frames[frames.length - 1]?.machines || {}
    const labels = Array.isArray(lastMachines)
      ? lastMachines.map((m) => m.id)
      : Object.keys(lastMachines)
    if (labels.length === 0) return []

    const recentFrames = frames.slice(-RECENT_FRAME_COUNT)
    const records = labels.map((label) => {
      const values = recentFrames
        .map((frame) => machineValue(getMachine(frame.machines || {}, label)))
        .filter(Number.isFinite)
      const current = machineValue(getMachine(lastMachines, label))
      const average = values.length > 0
        ? values.reduce((sum, value) => sum + value, 0) / values.length
        : null
      const machine = getMachine(lastMachines, label)
      return {
        label,
        displayLabel: machine?.display_name || machine?.name || label,
        current,
        average,
      }
    })
      .filter((record) => Number.isFinite(record.current) || Number.isFinite(record.average))
      .sort((a, b) => (b.average ?? b.current ?? 0) - (a.average ?? a.current ?? 0))

    return [
      {
        name: '当前',
        color: '#64b5ff',
        data: records.map((record) => ({ x: record.displayLabel, y: record.current ?? 0 })),
      },
      {
        name: `近 ${Math.min(RECENT_FRAME_COUNT, frames.length)} 帧均值`,
        color: '#66d06a',
        data: records.map((record) => ({
          x: record.displayLabel,
          y: Number((record.average ?? 0).toFixed(2)),
        })),
      },
    ]
  },
}
