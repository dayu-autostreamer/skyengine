<template>
  <div class="factory-visualization">
    <div class="hud-header">
      <slot name="header"></slot>
    </div>
    <div
      class="canvas-wrapper"
      ref="containerRef"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
      @wheel.prevent="handleWheel"
    >
      <canvas ref="canvasRef"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useFactoryStore } from '@/stores/factory'
import { el } from 'element-plus/es/locales.mjs'

// --- Props ---
const props = defineProps({
  // 静态配置由父组件传入 (墙、机器、点位)
  staticConfig: {
    type: Object,
    required: false,
    default: () => ({ machines: {}, zones: [], waypoints: {} }),
  },
  baseGridSize: { type: Number, default: 40 },
  defaultGridWidth: { type: Number, default: 20 },
  defaultGridHeight: { type: Number, default: 14 },
})

// --- Store & State ---
const store = useFactoryStore()
const containerRef = ref(null)
const canvasRef = ref(null)

// 视觉状态 (用于平滑插值，不存入 Store)
const agvVisuals = ref([])

// ============ 组件状态管理 (Component State Management) ============
// 缓存各组件的上一次绘制状态，用于检测是否需要重绘
const componentCache = ref({
  machines: {
    list: [], // 机器列表的快照
    stateMap: {}, // 每个机器的动态状态映射 { machineId: { status, load } }
  },
  zones: {
    list: [], // 区域列表的快照
  },
  waypoints: {
    list: [], // 路由点列表的快照
  },
  agvs: {
    positions: [], // AGV 位置列表
    visuals: [], // AGV 视觉位置列表
  },
})

// ============ 重绘检测函数 ============
/**
 * 检测是否需要重绘
 * @returns {Object} { needsRedraw: boolean, reason: string }
 */
function checkRedrawNeeded() {
  const reasons = []

  // 1. 检测机器状态变化
  const currentMachines = store.currentState?.machines || {}
  const currentMachineList = Object.values(topology.value.machines || {})

  // 机器列表长度改变
  if (currentMachineList.length !== componentCache.value.machines.list.length) {
    reasons.push('machine_count_changed')
  } else {
    // 检查每个机器的动态状态是否改变
    currentMachineList.forEach((m) => {
      const machineId = m.id
      const dynamicState = currentMachines[machineId] || {}
      const cachedState = componentCache.value.machines.stateMap[machineId] || {}

      if (dynamicState.status !== cachedState.status || dynamicState.load !== cachedState.load) {
        reasons.push(`machine_${machineId}_state_changed`)
      }
    })
  }

  // 2. 检测区域变化
  const currentZones = topology.value.zones || []
  if (currentZones.length !== componentCache.value.zones.list.length) {
    reasons.push('zones_count_changed')
  }

  // 3. 检测路由点变化
  const currentWaypoints = Object.values(topology.value.waypoints || {})
  if (currentWaypoints.length !== componentCache.value.waypoints.list.length) {
    reasons.push('waypoints_count_changed')
  }

  // 4. 检测 AGV 位置变化
  const currentPositions = store.currentState?.grid_state?.positions_xy || []
  if (currentPositions.length !== componentCache.value.agvs.positions.length) {
    reasons.push('agv_count_changed')
  } else {
    // 检查位置是否改变
    currentPositions.forEach((pos, i) => {
      const cached = componentCache.value.agvs.positions[i]
      if (!cached || pos[0] !== cached[0] || pos[1] !== cached[1]) {
        reasons.push(`agv_${i}_position_changed`)
      }
    })
  }

  const needsRedraw = reasons.length > 0
  return { needsRedraw, reasons }
}

/**
 * 更新组件缓存
 */
function updateComponentCache() {
  // 缓存机器状态
  const currentMachines = store.currentState?.machines || {}
  const machineList = Object.values(topology.value.machines || {})
  componentCache.value.machines.list = machineList.map((m) => ({
    id: m.id,
    name: m.name,
    location: m.location,
  }))

  machineList.forEach((m) => {
    const dynamicState = currentMachines[m.id] || {}
    componentCache.value.machines.stateMap[m.id] = {
      status: dynamicState.status || m.status || 'IDLE',
      load: dynamicState.load || m.load || 0,
    }
  })

  // 缓存区域
  componentCache.value.zones.list = (topology.value.zones || []).map((z) => ({
    id: z.id,
    name: z.name,
    area: { ...z.area },
  }))

  // 缓存路由点
  const wpList = Object.values(topology.value.waypoints || {})
  componentCache.value.waypoints.list = wpList.map((wp) => ({
    id: wp.id,
    type: wp.type,
    location: wp.location,
  }))

  // 缓存 AGV 位置
  const currentPositions = store.currentState?.grid_state?.positions_xy || []
  componentCache.value.agvs.positions = currentPositions.map((p) => [...p])
  componentCache.value.agvs.visuals = agvVisuals.value.map((v) => ({ x: v.x, y: v.y }))
}

// --- 1. 响应式拓扑结构 (Reactive Topology) ---
// 使用 computed，这样当父组件切换 staticConfig 时，这里会自动更新
const topology = computed(() => {
  const config = props.staticConfig || {}
  // 正确的数据结构：config.topology 包含 zones、machines、waypoints
  const topoData = config.topology || config
  return {
    zones: topoData.zones || [],
    machines: topoData.machines || {},
    waypoints: topoData.waypoints || {},
  }
})

// 自动生成边界墙的 zones
const zonesWithBoundary = computed(() => {
  const boundary = [
    {
      id: 'wall_top',
      name: '上边界',
      area: { x: 0, y: 0, w: view.value.gridWidth, h: 1 },
      type: 'obstacle',
      color: 'rgba(100, 100, 100, 0.3)',
    },
    {
      id: 'wall_bottom',
      name: '下边界',
      area: { x: 0, y: view.value.gridHeight - 1, w: view.value.gridWidth, h: 1 },
      type: 'obstacle',
      color: 'rgba(100, 100, 100, 0.3)',
    },
    {
      id: 'wall_left',
      name: '左边界',
      area: { x: 0, y: 0, w: 1, h: view.value.gridHeight },
      type: 'obstacle',
      color: 'rgba(100, 100, 100, 0.3)',
    },
    {
      id: 'wall_right',
      name: '右边界',
      area: { x: view.value.gridWidth - 1, y: 0, w: 1, h: view.value.gridHeight },
      type: 'obstacle',
      color: 'rgba(100, 100, 100, 0.3)',
    },
  ]
  return [...boundary, ...topology.value.zones]
})

// 视图配置 (Zoom/Pan)
const view = ref({
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  gridWidth: props.defaultGridWidth,
  gridHeight: props.defaultGridHeight,
})
const interaction = { isDragging: false, lastX: 0, lastY: 0 }

let ctx = null
let animationFrameId = null

// --- Lifecycle ---
onMounted(() => {
  initCanvas()
  updateComponentCache() // 初始化组件缓存
  shouldForceDraw = true
  animationFrameId = requestAnimationFrame(loop)
  window.addEventListener('resize', initCanvas)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animationFrameId)
  window.removeEventListener('resize', initCanvas)
})

// 监听拓扑变化，重置视图或重新计算布局
watch(
  () => props.staticConfig,
  () => {
    calculateLayout()
    shouldForceDraw = true // 配置改变时强制重绘
    updateComponentCache()
  },
  { deep: true },
)

// 监听 Store 状态变化，当机器状态改变时强制重绘
watch(
  () => store.currentState?.machines,
  () => {
    shouldForceDraw = true // 状态改变时标记需要重绘
  },
  { deep: true },
)

// --- 渲染循环 (Render Loop) ---
let lastTime = 0
let waitTimeLeft = 0
const STEP_WAIT_TIME = 800 // 节点停留时间
let shouldForceDraw = true // 强制重绘标志
let lastRedrawTime = 0
const REDRAW_INTERVAL = 10 // 重绘频率：每 200ms 最多检查一次（降低 CPU 消耗）

function loop(timestamp) {
  if (!ctx || !canvasRef.value) return
  const deltaTime = timestamp - lastTime
  lastTime = timestamp

  updatePhysics(deltaTime)

  // 只在指定时间间隔内检查是否需要重绘
  if (timestamp - lastRedrawTime >= REDRAW_INTERVAL || shouldForceDraw) {
    // 检测是否需要重绘
    const { needsRedraw, reasons } = checkRedrawNeeded()

    // 如果检测到状态变化或强制重绘，则进行绘制
    if (needsRedraw || shouldForceDraw) {
      if (needsRedraw) {
        // console.log(`[Redraw] 检测到变化: ${reasons.join(', ')}`)
        updateComponentCache()
      }
      draw()
      lastRedrawTime = timestamp
      shouldForceDraw = false
    }
  }

  animationFrameId = requestAnimationFrame(loop)
}

/**
 * 物理引擎：负责计算插值和驱动 Store 步进
 */
function updatePhysics(deltaTime) {
  // 1. 从 Store 获取当前帧的目标位置
  const currentState = store.currentState
  const targets = currentState?.grid_state?.positions_xy || []

  // 如果视觉对象数量不匹配（例如重置了或刚加载），重置视觉对象
  if (agvVisuals.value.length !== targets.length) {
    agvVisuals.value = targets.map((p) => ({ x: p[0], y: p[1] }))
    return
  }

  // 2. 计算插值移动
  let allArrived = true

  targets.forEach((targetArr, i) => {
    const target = { x: targetArr[0], y: targetArr[1] }
    const current = agvVisuals.value[i]

    const dx = target.x - current.x
    const dy = target.y - current.y
    const dist = Math.hypot(dx, dy)

    // 动态调整速度：如果是手动拖拽进度条(非播放状态)，速度要极快以便跟手
    const speed = store.isPlaying ? 0.15 : 0.5

    if (dist > 0.05) {
      current.x += dx * speed
      current.y += dy * speed
      allArrived = false
    } else {
      // 吸附
      current.x = target.x
      current.y = target.y
    }
  })

  // 3. 自动播放逻辑 (仅在 Playing 模式下触发)
  if (store.isPlaying && allArrived) {
    if (waitTimeLeft > 0) {
      waitTimeLeft -= deltaTime
    } else {
      const hasNext = store.nextStep()
      if (hasNext) {
        waitTimeLeft = STEP_WAIT_TIME
      }
    }
  }
}

// --- 绘图函数 ---
function draw() {
  const canvas = canvasRef.value
  // 清空
  ctx.save()
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.fillStyle = '#ECEFF1'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.restore()

  // 视图变换
  ctx.save()
  ctx.translate(view.value.offsetX, view.value.offsetY)
  ctx.scale(view.value.scale, view.value.scale)

  // 绘制层级
  drawGrid()
  drawWaypoints()
  drawZones()

  drawMachines()
  drawAGVs()

  ctx.restore()
}

// ---------- 函数式声明绘图 ----------
function drawWaypoints() {
  const wps = topology.value.waypoints
  const { baseGridSize } = props
  Object.values(wps).forEach((wp) => {
    const [gx, gy] = wp.location
    const cx = gx * baseGridSize + baseGridSize / 2
    const cy = gy * baseGridSize + baseGridSize / 2
    if (wp.type === 'dock') {
      // 绘制 dock 节点：方形框 + 内部圆形
      const dockSize = baseGridSize * 0.35
      ctx.fillStyle = '#1565C0'
      ctx.fillRect(cx - dockSize, cy - dockSize, dockSize * 2, dockSize * 2)
      ctx.strokeStyle = 'rgba(21,101,192,0.5)'
      ctx.lineWidth = 2
      ctx.strokeRect(cx - dockSize, cy - dockSize, dockSize * 2, dockSize * 2)

      // 内部装饰圆形
      ctx.beginPath()
      ctx.fillStyle = '#42A5F5'
      ctx.arc(cx, cy, baseGridSize * 0.15, 0, Math.PI * 2)
      ctx.fill()

      // 显示 dock 名称在中心（白色）
      ctx.fillStyle = '#FFF'
      ctx.font = `bold ${baseGridSize * 0.18}px Arial`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(wp.name, cx, cy)
    } else if (wp.type === 'route') {
      // route 节点保持不变
      ctx.beginPath()
      ctx.fillStyle = '#4CAF50'
      ctx.arc(cx, cy, baseGridSize * 0.2, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = 'rgba(76,175,80,0.3)'
      ctx.lineWidth = 2
      ctx.stroke()
      ctx.fillStyle = '#FFF'
      ctx.font = '9px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('R', cx, cy)
    } else if (wp.type === 'AGV') {
    }
  })
}

function drawAGVs() {
  const { baseGridSize } = props
  agvVisuals.value.forEach((v, i) => {
    const cx = v.x * baseGridSize + baseGridSize / 2
    const cy = v.y * baseGridSize + baseGridSize / 2

    // 绘制AGV emoji
    ctx.font = `${baseGridSize * 0.6}px Arial`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('🤖', cx, cy)
  })
}

function drawMachines() {
  const staticMachines = topology.value.machines || {}
  // 获取动态状态数据（从 Store.currentState 中获取实时机器状态）
  const dynamicMachineStates = store.currentState?.machines || {}
  const { baseGridSize } = props

  Object.values(staticMachines).forEach((m) => {
    const [gx, gy] = m.location
    const cx = gx * baseGridSize + baseGridSize / 2
    const cy = gy * baseGridSize + baseGridSize / 2
    const radius = baseGridSize * 0.3

    // 【关键】从动态状态中读取机器状态，动态状态优先级最高
    const dynamicState = dynamicMachineStates[m.id] || {}
    const status = dynamicState.status || m.status || 'IDLE'
    const load = dynamicState.load || m.load || 0

    // 绘制星形（使用动态状态）
    drawStar(cx, cy, radius, status)

    // 绘制机器名称（在星形下方）
    ctx.fillStyle = '#333'
    ctx.font = `bold ${baseGridSize * 0.2}px Arial`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText(m.name, cx, cy + radius + 4)

    // 如果有负载，在星形上方显示负载百分比
    if (load > 0) {
      ctx.fillStyle = '#666'
      ctx.font = `${baseGridSize * 0.15}px Arial`
      ctx.fillText(`${load}%`, cx, cy - radius - 4)
    }
  })
}

/**
 * 绘制星形
 * @param {number} cx - 中心 X 坐标
 * @param {number} cy - 中心 Y 坐标
 * @param {number} radius - 星形外半径
 * @param {string} status - 机器状态 ('WORKING' | 'IDLE' | 'BROKEN' | 'MAINTENANCE')
 */
function drawStar(cx, cy, radius, status) {
  const points = 5 // 5角星
  const innerRadius = radius * 0.4

  // 绘制星形路径
  ctx.beginPath()
  for (let i = 0; i < points * 2; i++) {
    const r = i % 2 === 0 ? radius : innerRadius
    const angle = (i * Math.PI) / points - Math.PI / 2
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)

    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  }
  ctx.closePath()

  // 根据状态填充颜色
  switch (status) {
    case 'WORKING':
      ctx.fillStyle = '#FFD700' // 金色 - 工作中
      break
    case 'BROKEN':
      ctx.fillStyle = '#F44336' // 红色 - 故障
      break
    case 'MAINTENANCE':
      ctx.fillStyle = '#FF9800' // 橙色 - 维护中
      break
    case 'IDLE':
    default:
      ctx.fillStyle = '#90EE90' // 浅绿色 - 空闲
      break
  }
  ctx.fill()

  // 绘制边框
  ctx.strokeStyle = '#333'
  ctx.lineWidth = 2
  ctx.stroke()
}

function drawGrid() {
  const { baseGridSize } = props
  const w = view.value.gridWidth * baseGridSize
  const h = view.value.gridHeight * baseGridSize
  ctx.beginPath()
  ctx.strokeStyle = '#CFD8DC'
  ctx.lineWidth = 1 / view.value.scale
  for (let x = 0; x <= view.value.gridWidth; x++) {
    ctx.moveTo(x * baseGridSize, 0)
    ctx.lineTo(x * baseGridSize, h)
  }
  for (let y = 0; y <= view.value.gridHeight; y++) {
    ctx.moveTo(0, y * baseGridSize)
    ctx.lineTo(w, y * baseGridSize)
  }
  ctx.stroke()
}

function drawZones() {
  const zones = zonesWithBoundary.value
  const { baseGridSize } = props
  zones.forEach((z) => {
    ctx.fillStyle = z.color
    ctx.fillRect(
      z.area.x * baseGridSize,
      z.area.y * baseGridSize,
      z.area.w * baseGridSize,
      z.area.h * baseGridSize,
    )

    if (z.type === 'restricted') {
      ctx.save()
      ctx.beginPath()
      ctx.rect(
        z.area.x * baseGridSize,
        z.area.y * baseGridSize,
        z.area.w * baseGridSize,
        z.area.h * baseGridSize,
      )
      ctx.clip()
      ctx.strokeStyle = 'rgba(255,152,0,1)'
      ctx.lineWidth = 4
      for (
        let i = -z.area.h * baseGridSize;
        i < z.area.w * baseGridSize + z.area.h * baseGridSize;
        i += 20
      ) {
        ctx.moveTo(z.area.x * baseGridSize + i, z.area.y * baseGridSize)
        ctx.lineTo(
          z.area.x * baseGridSize + i - z.area.h * baseGridSize,
          z.area.y * baseGridSize + z.area.h * baseGridSize,
        )
      }
      ctx.stroke()
      ctx.restore()
    } else if (z.type === 'workbench') {
      ctx.save()
      ctx.beginPath()
      ctx.rect(
        z.area.x * baseGridSize,
        z.area.y * baseGridSize,
        z.area.w * baseGridSize,
        z.area.h * baseGridSize,
      )
      ctx.clip()

      // 绘制竖直线（稀疏）
      ctx.strokeStyle = 'rgba(33,150,243,0.6)'
      ctx.lineWidth = 2
      for (let i = 1; i < z.area.w; i++) {
        ctx.moveTo(z.area.x * baseGridSize + i * baseGridSize, z.area.y * baseGridSize)
        ctx.lineTo(
          z.area.x * baseGridSize + i * baseGridSize,
          z.area.y * baseGridSize + z.area.h * baseGridSize,
        )
      }
      // 绘制水平线（稀疏）
      for (let j = 1; j < z.area.h; j++) {
        ctx.moveTo(z.area.x * baseGridSize, z.area.y * baseGridSize + j * baseGridSize)
        ctx.lineTo(
          z.area.x * baseGridSize + z.area.w * baseGridSize,
          z.area.y * baseGridSize + j * baseGridSize,
        )
      }
      ctx.stroke()
      ctx.restore()

      // 边框（更粗）
      ctx.strokeStyle = 'rgba(33,150,243,1)'
      ctx.lineWidth = 4
      ctx.strokeRect(
        z.area.x * baseGridSize,
        z.area.y * baseGridSize,
        z.area.w * baseGridSize,
        z.area.h * baseGridSize,
      )
    } else if (z.type === 'obstacle') {
      ctx.save()
      ctx.beginPath()
      ctx.rect(
        z.area.x * baseGridSize,
        z.area.y * baseGridSize,
        z.area.w * baseGridSize,
        z.area.h * baseGridSize,
      )
      ctx.clip()
      ctx.strokeStyle = 'rgba(33,150,243,0.5)'
      ctx.lineWidth = 4
      // 绘制交叉线（X 图案）
      for (
        let i = -z.area.h * baseGridSize;
        i < z.area.w * baseGridSize + z.area.h * baseGridSize;
        i += 25
      ) {
        ctx.moveTo(z.area.x * baseGridSize + i, z.area.y * baseGridSize)
        ctx.lineTo(
          z.area.x * baseGridSize + i + z.area.h * baseGridSize,
          z.area.y * baseGridSize + z.area.h * baseGridSize,
        )
        ctx.moveTo(z.area.x * baseGridSize + i, z.area.y * baseGridSize + z.area.h * baseGridSize)
        ctx.lineTo(z.area.x * baseGridSize + i + z.area.h * baseGridSize, z.area.y * baseGridSize)
      }
      ctx.stroke()
      ctx.restore()
    } else if (z.type === 'workarea') {
      ctx.save()
      ctx.beginPath()
      ctx.rect(
        z.area.x * baseGridSize,
        z.area.y * baseGridSize,
        z.area.w * baseGridSize,
        z.area.h * baseGridSize,
      )
      ctx.clip()
      ctx.fillStyle = 'rgba(76,175,80,0.3)'
      // 绘制点阵
      const dotRadius = baseGridSize * 0.15
      for (let x = z.area.x; x < z.area.x + z.area.w; x += 0.5) {
        for (let y = z.area.y; y < z.area.y + z.area.h; y += 0.5) {
          ctx.beginPath()
          ctx.arc(
            x * baseGridSize + baseGridSize / 2,
            y * baseGridSize + baseGridSize / 2,
            dotRadius,
            0,
            Math.PI * 2,
          )
          ctx.fill()
        }
      }
      ctx.restore()
      // 绘制边框
      ctx.strokeStyle = 'rgba(76,175,80,1)'
      ctx.lineWidth = 4
      ctx.strokeRect(
        z.area.x * baseGridSize,
        z.area.y * baseGridSize,
        z.area.w * baseGridSize,
        z.area.h * baseGridSize,
      )
    }
    // 绘制 Zone 名称
    const textX = z.area.x * baseGridSize + (z.area.w * baseGridSize) / 2
    const textY = z.area.y * baseGridSize + (z.area.h * baseGridSize) / 2
    ctx.fillStyle = '#FFF'
    ctx.font = `bold ${baseGridSize * 0.35}px Arial`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(z.name, textX, textY)
  })
}

// --- 交互 & 初始化 ---
function initCanvas() {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container) return
  const dpr = window.devicePixelRatio || 1
  const rect = container.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${rect.height}px`
  ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)
  calculateLayout()
}

function calculateLayout() {
  const container = containerRef.value
  if (!container) return
  const rect = container.getBoundingClientRect()

  // 根据拓扑数据动态计算网格范围
  let maxX = props.defaultGridWidth
  let maxY = props.defaultGridHeight

  // 检查机器的范围
  Object.values(topology.value.machines).forEach((m) => {
    const [gx, gy] = m.location
    const [mw, mh] = m.size || [2, 2]
    maxX = Math.max(maxX, gx + mw + 1)
    maxY = Math.max(maxY, gy + mh + 1)
  })

  // 检查路由点的范围
  Object.values(topology.value.waypoints).forEach((wp) => {
    const [gx, gy] = wp.location
    maxX = Math.max(maxX, gx + 1)
    maxY = Math.max(maxY, gy + 1)
  })

  // 检查禁区的范围
  topology.value.zones.forEach((z) => {
    maxX = Math.max(maxX, z.area.x + z.area.w + 1)
    maxY = Math.max(maxY, z.area.y + z.area.h + 1)
  })

  // 留一些边距
  maxX = Math.max(maxX + 1, 20)
  maxY = Math.max(maxY + 1, 14)

  view.value.gridWidth = maxX
  view.value.gridHeight = maxY

  view.value.scale =
    Math.min(
      rect.width / ((maxX + 2) * props.baseGridSize),
      rect.height / ((maxY + 2) * props.baseGridSize),
    ) * 0.9

  const contentW = (maxX + 2) * props.baseGridSize * view.value.scale
  const contentH = (maxY + 2) * props.baseGridSize * view.value.scale
  view.value.offsetX = (rect.width - contentW) / 2
  view.value.offsetY = (rect.height - contentH) / 2
}

function handleWheel(e) {
  const factor = e.deltaY > 0 ? 0.9 : 1.1
  const newScale = Math.max(0.2, Math.min(view.value.scale * factor, 6.0))
  const rect = containerRef.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  view.value.offsetX = mx - (mx - view.value.offsetX) * (newScale / view.value.scale)
  view.value.offsetY = my - (my - view.value.offsetY) * (newScale / view.value.scale)
  view.value.scale = newScale
}

function handleMouseDown(e) {
  interaction.isDragging = true
  interaction.lastX = e.clientX
  interaction.lastY = e.clientY
  containerRef.value.style.cursor = 'grabbing'
}
function handleMouseMove(e) {
  if (interaction.isDragging) {
    view.value.offsetX += e.clientX - interaction.lastX
    view.value.offsetY += e.clientY - interaction.lastY
    interaction.lastX = e.clientX
    interaction.lastY = e.clientY
  }
}
function handleMouseUp() {
  interaction.isDragging = false
  containerRef.value.style.cursor = 'default'
}
</script>

<style scoped>
@import './styles/FactoryVisualization.css';
</style>
