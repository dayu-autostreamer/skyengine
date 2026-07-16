<template>
  <div class="factory-3d-container">
    <div class="hud-header">
      <slot name="header"></slot>
    </div>
    <div ref="containerRef" class="three-wrapper"></div>
    <!-- 屏幕空间标签 -->
    <div class="labels-overlay" ref="labelsRef">
      <div
        v-for="l in screenLabels"
        :key="l.id"
        class="world-label"
        :class="[
          `label-${l.kind}`,
          {
            'label-hoverable': l.kind === 'machine' || l.kind === 'agv',
            'label-selected': isLabelSelected(l),
          },
        ]"
        :style="{ left: l.x + 'px', top: l.y + 'px', color: l.color }"
        @mouseenter="onLabelEnter(l)"
        @mouseleave="onLabelLeave(l)"
        @click.stop="selectLabel(l)"
      >
        <span class="label-hitbox" :class="{ 'label-hitbox-alert': l.alert }">
          <span class="label-main-row">
            <span class="label-name">{{ l.text }}</span>
            <span v-if="l.kind === 'machine' && l.dotClass" class="status-dot" :class="l.dotClass"></span>
          </span>
          <span v-if="l.badge" class="label-badge">{{ l.badge }}</span>
        </span>

        <!-- machine Hover 富信息 tooltip -->
        <div
          v-if="l.kind === 'machine' && l.machineId === hoveredMachineId && l.detail"
          class="machine-tooltip"
          :class="`mt-${l.detail.statusClass}`"
        >
          <div class="mt-header">
            <span class="mt-name">{{ l.text }}</span>
            <span class="mt-status-badge" :class="`tag-${l.detail.statusClass}`">
              <span class="mt-dot"></span>{{ l.detail.statusLabel }}
            </span>
          </div>

          <div class="mt-row" v-if="l.detail.op">
            <span class="mt-label">当前 Op</span>
            <span class="mt-value">Job{{ l.detail.op.job_id }} · Op{{ l.detail.op.op_id }}</span>
          </div>
          <div class="mt-row" v-else>
            <span class="mt-label">当前 Op</span>
            <span class="mt-value mt-idle">— 空闲 —</span>
          </div>
          <div class="mt-row" v-if="l.detail.repairRemaining > 0">
            <span class="mt-label">维修剩余</span>
            <span class="mt-value">{{ l.detail.repairRemaining }} 步</span>
          </div>
          <div class="mt-row" v-if="l.detail.downReason">
            <span class="mt-label">异常原因</span>
            <span class="mt-value">{{ l.detail.downReason }}</span>
          </div>

          <div class="mt-progress-block" v-if="l.detail.op">
            <div class="mt-progress-head">
              <span class="mt-label">Op 进度</span>
              <span class="mt-progress-text">{{ l.detail.op.step_done }} / {{ l.detail.op.proc_time }}</span>
            </div>
            <div class="mt-bar-wrap">
              <div class="mt-bar-fill" :style="{ width: l.detail.opPct + '%' }"></div>
            </div>
          </div>

          <div class="mt-divider"></div>

          <div class="mt-stat-row">
            <div class="mt-stat">
              <span class="mt-stat-num">{{ l.detail.queueLength }}</span>
              <span class="mt-stat-label">队列</span>
            </div>
            <div class="mt-stat">
              <span class="mt-stat-num">{{ l.detail.finishedOps }}</span>
              <span class="mt-stat-label">已完工</span>
            </div>
            <div class="mt-stat">
              <span class="mt-stat-num">{{ l.detail.op?.index_in_job + 1 ?? '-' }}/{{ l.detail.op?.total_in_job ?? '-' }}</span>
              <span class="mt-stat-label">Job 进度</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useFactoryStore } from '@/stores/factory'
import {
  BG_COLOR, GROUND_COLOR, GRID_COLOR_MAIN, GRID_COLOR_SUB,
  MACHINE_COLORS, STATUS_LIGHT,
  AGV_ACTIVE_COLOR, AGV_IDLE_COLOR,
  AGV_DOWN_COLOR, AGV_LIGHT_ACTIVE, AGV_LIGHT_IDLE, AGV_LIGHT_DOWN,
  ZONE_COLORS,
  EDGE_COLOR, WAYPOINT_DOCK_COLOR, WAYPOINT_DEFAULT_COLOR,
  HIGHLIGHT_COLOR, HIGHLIGHT_COLLISION_COLOR,
  BACKGROUND_THEMES,
  createBollard, createRack, createCabinet, createSafetyBarrier,
  createObstacleWall,
  createPerimeterWall, getDecorationLayout,
  createMachine, createAGV,
  createFactoryBackground,
} from '@/utils/assets'

// ==================== Props ====================
const props = defineProps({
  staticConfig: { type: Object, required: false, default: () => ({ machines: {}, zones: [], waypoints: {} }) },
  baseGridSize: { type: Number, default: 40 },
  defaultGridWidth: { type: Number, default: 20 },
  defaultGridHeight: { type: Number, default: 14 },
  editMode: { type: Boolean, default: false },
  backgroundTheme: { type: String, default: 'clean' },
  backgroundSize: { type: Number, default: 2 },
})

// ==================== Emits ====================
const emit = defineEmits(['asset-placed', 'asset-moved'])

// ==================== Store ====================
const store = useFactoryStore()

// ==================== Refs ====================
const containerRef = ref(null)
const labelsRef = ref(null)
const screenLabels = ref([])
const hoveredMachineId = ref(null)

function onLabelEnter(l) {
  if (l.kind === 'machine' && l.machineId != null) {
    hoveredMachineId.value = l.machineId
  }
}
function onLabelLeave(l) {
  if (l.kind === 'machine' && l.machineId === hoveredMachineId.value) {
    hoveredMachineId.value = null
  }
}

function isLabelSelected(label) {
  if (label.kind === 'machine') return store.selectedMachineKey === label.runtimeMachineKey
  if (label.kind === 'agv') return store.selectedAgvIndex === label.agvIndex
  return false
}

function runtimeKeyForMachineId(machineId) {
  const stateMachines = store.currentState?.machines || {}
  const metadataEntry = Object.entries(stateMachines).find(([, machine]) =>
    [machine?.config_id, machine?.config_key].some((value) => String(value) === String(machineId)),
  )
  if (metadataEntry) return metadataEntry[0]

  const machineIndex = Array.from(machineMeshMap.keys()).indexOf(machineId)
  return Object.keys(stateMachines)[machineIndex] || machineId
}

function selectAsset(asset) {
  if (asset?.type === 'machine') store.selectMachine(runtimeKeyForMachineId(asset.id))
  if (asset?.type === 'agv') store.selectAgv(asset.index)
}

function selectLabel(label) {
  if (label.kind === 'machine') store.selectMachine(label.runtimeMachineKey)
  if (label.kind === 'agv') store.selectAgv(label.agvIndex)
}

// ==================== Topology ====================
const topology = computed(() => {
  const config = props.staticConfig || {}
  const topoData = config.topology || config
  // 与后端 use_io.py 的 grid_size = max(grid_width, grid_height) 对齐：
  // pogema 只支持正方形网格，非正方形地图在后端会被 max 方正化（底部补 padding 行）。
  // 前端必须同步方正化，否则 gridToWorld 的坐标系与后端仿真空间错位，
  // 非正方形地图会出现"半格偏移"且 padding 行的 AGV 会渲染错位。
  const gw = topoData.gridWidth || props.defaultGridWidth
  const gh = topoData.gridHeight || props.defaultGridHeight
  const gridSize = Math.max(gw, gh)
  return {
    zones: topoData.zones || [],
    machines: topoData.machines || {},
    waypoints: topoData.waypoints || {},
    edges: topoData.edges || [],
    gridWidth: gridSize,
    gridHeight: gridSize,
  }
})

// ==================== 坐标工具 ====================
const GRID_SIZE = 1 // 每个格子 = 1 世界单位

function gridToWorld(gx, gy) {
  const w = topology.value.gridWidth
  const h = topology.value.gridHeight
  return new THREE.Vector3((gx - w / 2 + 0.5) * GRID_SIZE, 0, (gy - h / 2 + 0.5) * GRID_SIZE)
}

// ==================== Three.js 对象 ====================
let scene, camera, renderer, controls, clock
let groundPlane, gridHelper, backgroundGroup
let ambientLight, sunLight
let machineGroup, agvGroup, zoneGroup, waypointGroup, edgeGroup, decorGroup, exceptionObstacleGroup

// 对象映射
const machineMeshMap = new Map()   // machineId → { group, bodyMat, lightMat }
const agvDataList = []             // { group, chassisMat, lightMat, targetPos: Vector3 }
const waypointPosMap = new Map()   // waypointId → { x, z } (world)
const obstacleMeshMap = new Map()   // "x,y" → Mesh

// 动画状态
let waitTimeLeft = 0
const STEP_WAIT_TIME = 800

// ==================== 编辑模式交互 ====================
const raycaster = new THREE.Raycaster()
const mouse = new THREE.Vector2()
let highlightMesh = null
let draggingAsset = null        // { type, id, group }
let isDragging = false
let selectionPointerStart = null
let dragStartMouseWorld = null
let dragStartGridX = 0
let dragStartGridY = 0
let lastDragGridX = 0           // 拖拽过程中最新的网格 X
let lastDragGridY = 0           // 拖拽过程中最新的网格 Y

function snapToGrid(worldPos) {
  const w = topology.value.gridWidth
  const h = topology.value.gridHeight
  const gx = Math.round(worldPos.x / GRID_SIZE + w / 2 - 0.5)
  const gy = Math.round(worldPos.z / GRID_SIZE + h / 2 - 0.5)
  return {
    gx: Math.max(0, Math.min(gx, w - 1)),
    gy: Math.max(0, Math.min(gy, h - 1)),
  }
}

function createHighlightMesh() {
  const geom = new THREE.BoxGeometry(GRID_SIZE * 1.1, 0.08, GRID_SIZE * 1.1)
  const mat = new THREE.MeshBasicMaterial({
    color: HIGHLIGHT_COLOR,
    transparent: true,
    opacity: 0.35,
    depthWrite: false,
  })
  highlightMesh = new THREE.Mesh(geom, mat)
  highlightMesh.visible = false
  highlightMesh.renderOrder = 999
  return highlightMesh
}

function setHighlightColor(occupied) {
  if (!highlightMesh) return
  highlightMesh.material.color.set(occupied ? HIGHLIGHT_COLLISION_COLOR : HIGHLIGHT_COLOR)
}

function updateHighlight(worldPos, isOccupied = false) {
  if (!highlightMesh) createHighlightMesh()
  if (!scene) return

  if (!scene.getObjectById(highlightMesh.id)) {
    scene.add(highlightMesh)
  }

  const { gx, gy } = snapToGrid(worldPos)
  const snapped = gridToWorld(gx, gy)
  highlightMesh.position.set(snapped.x, 0.05, snapped.z)
  setHighlightColor(isOccupied)
  highlightMesh.visible = true
}

function hideHighlight() {
  if (highlightMesh) highlightMesh.visible = false
}

function getGroundIntersection(event) {
  if (!camera || !renderer || !groundPlane) return null
  const rect = renderer.domElement.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(mouse, camera)

  const intersects = raycaster.intersectObject(groundPlane)
  return intersects.length > 0 ? intersects[0].point : null
}

function findAssetAtPoint(worldPoint) {
  // 基于网格格子的命中检测：点击资产占据的任何一格都能选中该资产
  // 不再依赖 mesh 包围盒，AGV / 路由点这种小部件也能轻松点中
  const { gx, gy } = snapToGrid(worldPoint)
  const cfg = store.currentConfig
  if (!cfg) return null

  // 1) 机器（按 size 占多格，最高优先级）
  for (const m of Object.values(topology.value.machines || {})) {
    if (!m.location) continue
    const [mx, my] = m.location
    const sw = m.size?.[0] || 1
    const sh = m.size?.[1] || 1
    if (gx >= mx && gx < mx + sw && gy >= my && gy < my + sh) {
      const data = machineMeshMap.get(m.id)
      if (data) return { type: 'machine', id: m.id, group: data.group }
    }
  }

  // 2) AGV：按 mesh 当前所在格匹配
  //    AGV 位置是动态的（仿真时由 state.grid_state.positions_xy 驱动，编辑模式下由
  //    syncAGVsFromConfig 钉在 initialLocation），所以必须按 mesh 实际位置命中，
  //    否则会出现"看得到 AGV 却点不中"。
  const agvs = cfg.agvs || []
  for (let i = 0; i < agvDataList.length; i++) {
    const ad = agvDataList[i]
    if (!ad?.group) continue
    const { gx: ax, gy: ay } = snapToGrid(ad.group.position)
    if (ax === gx && ay === gy) {
      return { type: 'agv', id: agvs[i]?.id ?? i, index: i, group: ad.group }
    }
  }

  // 3) 路由点（占 1 格）
  for (const wp of Object.values(topology.value.waypoints || {})) {
    if (!wp.location) continue
    if (wp.location[0] === gx && wp.location[1] === gy) {
      for (const child of waypointGroup.children) {
        if (child.userData.id === wp.id) {
          return { type: 'waypoint', id: wp.id, group: child }
        }
      }
    }
  }

  // 4) 区域（按 area 占多格）
  for (const z of (topology.value.zones || [])) {
    if (!z.area) continue
    const { x, y, w, h } = z.area
    if (gx >= x && gx < x + (w || 1) && gy >= y && gy < y + (h || 1)) {
      for (const child of zoneGroup.children) {
        if (child.userData.id === z.id) {
          return { type: 'zone', id: z.id, group: child }
        }
      }
    }
  }

  return null
}

function onCanvasPointerDown(event) {
  if (!props.editMode) {
    selectionPointerStart = { x: event.clientX, y: event.clientY }
    return
  }
  const point = getGroundIntersection(event)
  if (!point) return

  const asset = findAssetAtPoint(point)
  if (asset) {
    draggingAsset = asset
    isDragging = true
    controls.enabled = false
    // 记录起始状态：资产当前网格坐标 + 鼠标世界坐标
    const startGrid = snapToGrid(asset.group.position)
    dragStartGridX = startGrid.gx
    dragStartGridY = startGrid.gy
    dragStartMouseWorld = point.clone()
    renderer.domElement.style.cursor = 'grabbing'
  }
}

function onCanvasPointerMove(event) {
  if (!props.editMode) return
  const point = getGroundIntersection(event)
  if (!point) { hideHighlight(); return }

  if (isDragging && draggingAsset) {
    // 用鼠标相对于起始点的增量，计算网格偏移
    const dx = point.x - dragStartMouseWorld.x
    const dz = point.z - dragStartMouseWorld.z
    const gridDX = Math.round(dx / GRID_SIZE)
    const gridDZ = Math.round(dz / GRID_SIZE)

    const w = topology.value.gridWidth
    const h = topology.value.gridHeight
    const newGX = Math.max(0, Math.min(dragStartGridX + gridDX, w - 1))
    const newGY = Math.max(0, Math.min(dragStartGridY + gridDZ, h - 1))

    const snapped = gridToWorld(newGX, newGY)
    draggingAsset.group.position.set(snapped.x, 0, snapped.z)

    // 记录最新网格位置（给 pointerUp 使用）
    lastDragGridX = newGX
    lastDragGridY = newGY

    // 碰撞校验
    const occupied = store.isCellOccupied(newGX, newGY, draggingAsset.id, draggingAsset.type)
    updateHighlight(point, occupied)
    renderer.domElement.style.cursor = occupied ? 'not-allowed' : 'grabbing'
  } else {
    const asset = findAssetAtPoint(point)
    if (asset) {
      renderer.domElement.style.cursor = 'grab'
      updateHighlight(point, false)
    } else {
      renderer.domElement.style.cursor = 'crosshair'
      updateHighlight(point, false)
    }
  }
}

function onCanvasPointerUp(event) {
  if (!props.editMode) {
    const start = selectionPointerStart
    selectionPointerStart = null
    if (!start || Math.hypot(event.clientX - start.x, event.clientY - start.y) > 6) return
    const point = getGroundIntersection(event)
    if (point) selectAsset(findAssetAtPoint(point))
    return
  }

  if (isDragging && draggingAsset) {
    // 用 lastDragGridX/Y（pointerMove 已实时记录），不依赖 pointerUp 的射线检测
    const newGX = lastDragGridX
    const newGY = lastDragGridY

    const success = store.updateAssetPosition(draggingAsset.type, draggingAsset.id, newGX, newGY)

    if (success) {
      emit('asset-moved', { assetType: draggingAsset.type, assetId: draggingAsset.id, gridX: newGX, gridY: newGY })
    } else {
      // 碰撞：仅回弹被拖拽资产到起始位置，不做全量重建
      const pos = gridToWorld(dragStartGridX, dragStartGridY)
      draggingAsset.group.position.set(pos.x, 0, pos.z)
    }

    isDragging = false
    draggingAsset = null
    dragStartMouseWorld = null
    controls.enabled = true
    renderer.domElement.style.cursor = 'crosshair'
  }

  hideHighlight()
}

function setupEditModeListeners() {
  const canvas = renderer?.domElement
  if (!canvas) return
  canvas.addEventListener('pointerdown', onCanvasPointerDown)
  canvas.addEventListener('pointermove', onCanvasPointerMove)
  canvas.addEventListener('pointerup', onCanvasPointerUp)
}

function removeEditModeListeners() {
  const canvas = renderer?.domElement
  if (!canvas) return
  canvas.removeEventListener('pointerdown', onCanvasPointerDown)
  canvas.removeEventListener('pointermove', onCanvasPointerMove)
  canvas.removeEventListener('pointerup', onCanvasPointerUp)
  if (highlightMesh) {
    highlightMesh.visible = false
  }
  isDragging = false
  draggingAsset = null
  selectionPointerStart = null
  dragStartMouseWorld = null
  controls.enabled = true
  renderer.domElement.style.cursor = ''
}

// ==================== 配色常量（从 assets.js 导入） ====================

// ==================== 场景初始化 ====================
function initScene() {
  const container = containerRef.value
  if (!container) return

  // Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(container.clientWidth, container.clientHeight)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.0
  container.appendChild(renderer.domElement)

  // Scene — 根据背景主题设置
  const theme = BACKGROUND_THEMES[props.backgroundTheme] || BACKGROUND_THEMES.clean
  scene = new THREE.Scene()
  scene.background = new THREE.Color(theme.bgColor)
  scene.fog = new THREE.Fog(theme.bgColor, theme.fogNear, theme.fogFar)

  // Camera
  camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.5, 200)
  const w = topology.value.gridWidth
  const h = topology.value.gridHeight
  const dist = Math.max(w, h) * 1.1
  camera.position.set(dist * 0.55, dist * 0.65, dist * 0.55)
  camera.lookAt(0, 0, 0)

  // Lights — 根据主题调整强度
  ambientLight = new THREE.AmbientLight(0xffffff, theme.ambientIntensity)
  scene.add(ambientLight)

  sunLight = new THREE.DirectionalLight(0xffffff, theme.sunIntensity)
  sunLight.position.set(20, 35, 15)
  sunLight.castShadow = true
  sunLight.shadow.mapSize.width = 2048
  sunLight.shadow.mapSize.height = 2048
  sunLight.shadow.camera.near = 0.5
  sunLight.shadow.camera.far = 150
  sunLight.shadow.camera.left = -40
  sunLight.shadow.camera.right = 40
  sunLight.shadow.camera.top = 40
  sunLight.shadow.camera.bottom = -40
  sunLight.bias = -0.0002
  scene.add(sunLight)

  const fill = new THREE.DirectionalLight(0xffffff, 0.8)
  fill.position.set(-10, 8, -10)
  scene.add(fill)

  // Controls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.maxPolarAngle = Math.PI / 2 - 0.05
  controls.minDistance = 3
  controls.maxDistance = 100
  controls.target.set(0, 0, 0)
  controls.update()

  // Groups
  zoneGroup = new THREE.Group()
  edgeGroup = new THREE.Group()
  waypointGroup = new THREE.Group()
  decorGroup = new THREE.Group()
  machineGroup = new THREE.Group()
  agvGroup = new THREE.Group()
  exceptionObstacleGroup = new THREE.Group()
  scene.add(zoneGroup, edgeGroup, waypointGroup, decorGroup, exceptionObstacleGroup, machineGroup, agvGroup)

  // Clock
  clock = new THREE.Clock()
}

// ==================== 构建静态元素 ====================
function buildGroundAndGrid() {
  if (groundPlane) { scene.remove(groundPlane); groundPlane.geometry?.dispose(); groundPlane.material?.dispose() }
  if (gridHelper) { scene.remove(gridHelper); gridHelper.geometry?.dispose(); gridHelper.material?.dispose() }

  const w = topology.value.gridWidth
  const h = topology.value.gridHeight
  const theme = BACKGROUND_THEMES[props.backgroundTheme] || BACKGROUND_THEMES.clean

  groundPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(w * GRID_SIZE, h * GRID_SIZE),
    new THREE.MeshStandardMaterial({ color: theme.groundColor, roughness: 0.95, metalness: 0.0 }),
  )
  groundPlane.rotation.x = -Math.PI / 2
  groundPlane.receiveShadow = true
  scene.add(groundPlane)

  gridHelper = new THREE.GridHelper(Math.max(w, h) * GRID_SIZE, Math.max(w, h), GRID_COLOR_MAIN, GRID_COLOR_SUB)
  gridHelper.position.y = 0.005
  scene.add(gridHelper)
}

// ==================== 机器构建 ====================
function buildMachines() {
  machineMeshMap.forEach(({ group, bodyMat, lightMat }) => {
    group.traverse(ch => { ch.geometry?.dispose(); ch.material?.dispose() })
    bodyMat.dispose(); lightMat.dispose()
  })
  machineMeshMap.clear()
  while (machineGroup.children.length) machineGroup.remove(machineGroup.children[0])

  const U = GRID_SIZE
  const machines = topology.value.machines
  Object.values(machines).forEach((m) => {
    const pos = gridToWorld(m.location[0], m.location[1])
    const { group, bodyMat, lightMat } = createMachine(U, m)
    group.position.set(pos.x, 0, pos.z)
    machineGroup.add(group)
    machineMeshMap.set(m.id, { group, bodyMat, lightMat })
  })
}

// ==================== 区域 / 路径点 / 边 ====================
function buildZones() {
  while (zoneGroup.children.length) {
    const c = zoneGroup.children[0]
    c.traverse(ch => { ch.geometry?.dispose(); ch.material?.dispose() })
    zoneGroup.remove(c)
  }

  const zones = topology.value.zones
  const U = GRID_SIZE
  zones.forEach((z) => {
    const area = z.area
    const cx = (area.x - topology.value.gridWidth / 2 + area.w / 2) * U
    const cz = (area.y - topology.value.gridHeight / 2 + area.h / 2) * U

    let obj
    if (z.decor) {
      // 装饰资产 → 渲染对应 3D 模型
      if (z.decor === 'bollard') obj = createBollard(U)
      else if (z.decor === 'rack') obj = createRack(U)
      else if (z.decor === 'cabinet') obj = createCabinet(U)
      else if (z.decor === 'barrier') obj = createSafetyBarrier(U)
      else obj = null

      if (obj) {
        obj.position.set(cx, 0, cz)
        obj.traverse(ch => { ch.userData = { id: z.id, name: z.name, type: z.type, decor: z.decor } })
        zoneGroup.add(obj)
      }
    }

    // 普通区域：渲染半透明底板（obstacle 除外，用 3D 墙体）
    if (!z.decor) {
      if (z.type === 'obstacle') {
        const wall = createObstacleWall(U, area.w, area.h)
        wall.position.set(cx, 0, cz)
        wall.userData = { id: z.id, name: z.name, type: z.type }
        zoneGroup.add(wall)
      } else {
        const geom = new THREE.BoxGeometry(area.w * U, 0.06, area.h * U)
        const mat = new THREE.MeshStandardMaterial({
          color: ZONE_COLORS[z.type] || ZONE_COLORS.default,
          transparent: true, opacity: 0.15, roughness: 0.9,
        })
        const mesh = new THREE.Mesh(geom, mat)
        mesh.position.set(cx, 0.03, cz)
        mesh.receiveShadow = true
        mesh.userData = { id: z.id, name: z.name, type: z.type }
        zoneGroup.add(mesh)
      }
    }
  })
}

function buildWaypoints() {
  waypointPosMap.clear()
  while (waypointGroup.children.length) {
    const c = waypointGroup.children[0]
    c.geometry?.dispose(); c.material?.dispose()
    waypointGroup.remove(c)
  }

  const wps = topology.value.waypoints
  Object.values(wps).forEach((wp) => {
    const pos = gridToWorld(wp.location[0], wp.location[1])
    waypointPosMap.set(wp.id, { x: pos.x, z: pos.z })

    let geom, mat
    if (wp.type === 'dock') {
      geom = new THREE.CylinderGeometry(GRID_SIZE * 0.3, GRID_SIZE * 0.3, GRID_SIZE * 0.06, 16)
      mat = new THREE.MeshStandardMaterial({ color: WAYPOINT_DOCK_COLOR, roughness: 0.3, metalness: 0.6 })
    } else {
      geom = new THREE.SphereGeometry(GRID_SIZE * 0.12, 8, 8)
      mat = new THREE.MeshStandardMaterial({ color: WAYPOINT_DEFAULT_COLOR, roughness: 0.4, metalness: 0.4 })
    }
    const mesh = new THREE.Mesh(geom, mat)
    mesh.position.set(pos.x, GRID_SIZE * 0.04, pos.z)
    mesh.receiveShadow = true
    mesh.userData = { id: wp.id, name: wp.name, type: wp.type }
    waypointGroup.add(mesh)
  })
}

function buildEdges() {
  while (edgeGroup.children.length) {
    const c = edgeGroup.children[0]; c.geometry?.dispose(); c.material?.dispose()
    edgeGroup.remove(c)
  }

  const edges = topology.value.edges
  if (!edges || edges.length === 0) return

  for (const edge of edges) {
    const [fromId, toId] = Array.isArray(edge) ? edge : [edge.from, edge.to]
    const from = waypointPosMap.get(fromId)
    const to = waypointPosMap.get(toId)
    if (!from || !to) continue
    const geom = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(from.x, 0.02, from.z),
      new THREE.Vector3(to.x, 0.02, to.z),
    ])
    const mat = new THREE.LineDashedMaterial({ color: EDGE_COLOR, dashSize: 0.8, gapSize: 1.0 })
    const line = new THREE.Line(geom, mat)
    line.computeLineDistances()
    edgeGroup.add(line)
  }
}

// ==================== 工厂背景层 ====================
function buildBackground() {
  // 清理旧背景
  if (backgroundGroup) {
    backgroundGroup.traverse(ch => { ch.geometry?.dispose(); ch.material?.dispose() })
    scene.remove(backgroundGroup)
    backgroundGroup = null
  }

  // 仅 factory 主题才构建背景层
  if (props.backgroundTheme !== 'factory') return

  const w = topology.value.gridWidth
  const h = topology.value.gridHeight
  backgroundGroup = createFactoryBackground(GRID_SIZE, w, h, props.backgroundSize)
  scene.add(backgroundGroup)
}

// ==================== 科技感围墙 ====================
function buildPerimeterWall() {
  const existingWall = scene.getObjectByName('perimeter-wall')
  if (existingWall) {
    existingWall.traverse(ch => { ch.geometry?.dispose(); ch.material?.dispose() })
    scene.remove(existingWall)
  }

  const w = topology.value.gridWidth
  const h = topology.value.gridHeight
  const wallGroup = createPerimeterWall(GRID_SIZE, w, h)
  scene.add(wallGroup)
}


// ==================== 装饰物构建 ====================
// function buildDecorations() {
//   while (decorGroup.children.length) {
//     const c = decorGroup.children[0]
//     c.traverse(ch => { ch.geometry?.dispose(); ch.material?.dispose() })
//     decorGroup.remove(c)
//   }

//   const w = topology.value.gridWidth
//   const h = topology.value.gridHeight
//   const U = GRID_SIZE
//   const layout = getDecorationLayout(w, h)

//   // 1. 安全警示柱
//   layout.bollards.forEach(([gx, gy]) => {
//     const pos = gridToWorld(gx, gy)
//     const grp = createBollard(U)
//     grp.position.set(pos.x, 0, pos.z)
//     decorGroup.add(grp)
//   })

//   // 2. 储物架
//   layout.racks.forEach(([gx, gy]) => {
//     const pos = gridToWorld(gx, gy)
//     const grp = createRack(U)
//     grp.position.set(pos.x, 0, pos.z)
//     decorGroup.add(grp)
//   })

//   // 3. 配电箱
//   layout.cabinets.forEach(([gx, gy]) => {
//     const pos = gridToWorld(gx, gy)
//     const grp = createCabinet(U)
//     grp.position.set(pos.x, 0, pos.z)
//     decorGroup.add(grp)
//   })

//   // 4. 安全隔离栏
//   layout.barriers.forEach(([gx, gyOffset]) => {
//     const fenceX = gridToWorld(gx, 0).x
//     const fenceZ = gridToWorld(0, 0).z + gyOffset * U
//     const grp = createSafetyBarrier(U)
//     grp.position.set(fenceX, 0, fenceZ)
//     decorGroup.add(grp)
//   })
// }

function buildStaticElements() {
  buildBackground()
  buildGroundAndGrid()
  buildPerimeterWall()
  buildZones()
  buildEdges()
  buildWaypoints()
  // buildDecorations()
  buildMachines()
}


// ==================== AGV 构建 ====================
function rebuildAGVs(count) {
  agvDataList.forEach(d => {
    d.group?.traverse(ch => { ch.geometry?.dispose(); ch.material?.dispose() })
    d.chassisMat?.dispose(); d.lightMat?.dispose()
  })
  agvDataList.length = 0
  while (agvGroup.children.length) agvGroup.remove(agvGroup.children[0])

  const U = GRID_SIZE
  for (let i = 0; i < count; i++) {
    const { group, chassisMat, lightMat } = createAGV(U, i)
    group.position.set(0, 0, 0)
    agvGroup.add(group)
    agvDataList.push({ group, chassisMat, lightMat, targetPos: new THREE.Vector3() })
  }
}

// ==================== 动态更新 ====================
/**
 * 编辑模式（或无仿真状态）下，把 AGV mesh 同步到 cfg.agvs[i].initialLocation。
 * 用于：1) 编辑模式下让 AGV 可见并可拖；2) 拖拽完成后保持 mesh 位置与 store 一致。
 * 正在拖拽的那个 AGV 跳过，避免覆盖 pointerMove 实时设置的 mesh 位置。
 */
function syncAGVsFromConfig() {
  const cfg = store.currentConfig
  if (!cfg?.agvs) return
  if (agvDataList.length !== cfg.agvs.length) rebuildAGVs(cfg.agvs.length)
  cfg.agvs.forEach((a, i) => {
    const ad = agvDataList[i]
    if (!ad || !a.initialLocation) return
    if (isDragging && draggingAsset?.type === 'agv' && draggingAsset.group === ad.group) return
    const target = gridToWorld(a.initialLocation[0], a.initialLocation[1])
    ad.group.position.set(target.x, 0, target.z)
  })
}

function updateFromStore() {
  const state = store.currentState
  // 没有真实仿真数据（historyBuffer 为空 → currentState 是 EMPTY_GRID_STATE）
  // 时直接 return，避免每帧 rebuildAGVs(0) 把 AGV mesh 销毁重建、覆盖拖拽。
  if (store.totalSteps === 0) return
  const targets = state.grid_state?.positions_xy || []
  const isActive = state.grid_state?.is_active || []
  const agvStatus = state.grid_state?.agv_status || []
  const agvRepairRemaining = state.grid_state?.agv_repair_remaining || []

  // AGV 数量同步
  if (agvDataList.length !== targets.length) rebuildAGVs(targets.length)

  // AGV 位置插值
  let allArrived = true
  targets.forEach(([gx, gy], i) => {
    const agvData = agvDataList[i]
    if (!agvData) return
    const target = gridToWorld(gx, gy)
    agvData.targetPos.copy(target)

    const grp = agvData.group
    const dx = target.x - grp.position.x
    const dz = target.z - grp.position.z
    const dist = Math.sqrt(dx * dx + dz * dz)

    const speed = store.isPlaying ? 0.12 : 0.45
    if (dist > 0.02) {
      grp.position.x += dx * speed
      grp.position.z += dz * speed
      allArrived = false
    } else {
      grp.position.x = target.x
      grp.position.z = target.z
    }

    // 活跃状态 → 底盘材质
    const down = agvStatus[i] === 'DOWN'
    const active = isActive[i] !== false
    agvData.group.userData.status = down ? 'DOWN' : (active ? 'ACTIVE' : 'IDLE')
    agvData.group.userData.repairRemaining = agvRepairRemaining[i] || 0
    agvData.chassisMat.color.set(down ? AGV_DOWN_COLOR : (active ? AGV_ACTIVE_COLOR : AGV_IDLE_COLOR))
    agvData.chassisMat.needsUpdate = true
    agvData.lightMat.color.set(down ? AGV_LIGHT_DOWN : (active ? AGV_LIGHT_ACTIVE : AGV_LIGHT_IDLE))
  })

  // 机器状态更新
  updateMachineStates(state.machines || {})
  updateExceptionObstacles(state.blocked_cells || [])

  // 自动步进
  const dt = clock.getDelta()
  if (store.isPlaying && allArrived) {
    waitTimeLeft -= dt * 1000
    if (waitTimeLeft <= 0) {
      if (store.nextStep()) waitTimeLeft = STEP_WAIT_TIME
    }
  } else if (!store.isPlaying) {
    waitTimeLeft = 0
  }

  updateScreenLabels()
}

function updateExceptionObstacles(blockedCells) {
  if (!exceptionObstacleGroup) return
  const activeKeys = new Set()
  ;(blockedCells || []).forEach((cell) => {
    if (!Array.isArray(cell) || cell.length < 2) return
    const [gx, gy] = cell
    const key = `${gx},${gy}`
    activeKeys.add(key)
    if (obstacleMeshMap.has(key)) return

    const pos = gridToWorld(gx, gy)
    const geom = new THREE.BoxGeometry(GRID_SIZE * 0.9, GRID_SIZE * 0.16, GRID_SIZE * 0.9)
    const mat = new THREE.MeshStandardMaterial({
      color: 0xff4d4f,
      emissive: 0x661111,
      transparent: true,
      opacity: 0.62,
      roughness: 0.45,
      metalness: 0.15,
    })
    const mesh = new THREE.Mesh(geom, mat)
    mesh.position.set(pos.x, GRID_SIZE * 0.08, pos.z)
    mesh.castShadow = true
    mesh.receiveShadow = true
    exceptionObstacleGroup.add(mesh)
    obstacleMeshMap.set(key, mesh)
  })

  obstacleMeshMap.forEach((mesh, key) => {
    if (activeKeys.has(key)) return
    mesh.geometry?.dispose()
    mesh.material?.dispose()
    exceptionObstacleGroup.remove(mesh)
    obstacleMeshMap.delete(key)
  })
}

function updateMachineStates(machineStates) {
  // 兜底：当 key 对不上时按 mesh 迭代顺序做 index 对齐（StaticFactory 用 M1/M2/M3，
  // config 用 MACHINE_1_1 之类的 id）
  const stateList = Object.values(machineStates || {})
  let idx = 0
  machineMeshMap.forEach(({ group, bodyMat, lightMat }, machineId) => {
    const curIdx = idx++
    const dyn = machineStates[machineId]
      || machineStates[`M${machineId}`]
      || stateList[curIdx]
      || {}
    const newStatus = dyn.status || null
    if (newStatus && group.userData.status !== newStatus) {
      group.userData.status = newStatus
      const mc = MACHINE_COLORS[newStatus] || MACHINE_COLORS.IDLE
      bodyMat.color.set(mc.body)
      bodyMat.emissive.set(mc.emissive)
      bodyMat.needsUpdate = true
      lightMat.color.set(STATUS_LIGHT[newStatus] || STATUS_LIGHT.IDLE)
    }
  })
}

// ==================== 屏幕标签 ====================
function updateScreenLabels() {
  if (!renderer || !labelsRef.value) return
  const cw = renderer.domElement.clientWidth
  const ch = renderer.domElement.clientHeight
  const rect = renderer.domElement.getBoundingClientRect()
  const containerRect = containerRef.value?.getBoundingClientRect()
  const labels = []

  // 当前机器动态状态 (来自 store 快照)
  const machineStatesDict = store.currentState?.machines || {}
  // 兜底：StaticFactory 用 "M1"/"M2"/"M3" 作 key，但 mesh 用 config 的 id (如 MACHINE_1_1)
  // → 当 key 对不上时，按 mesh 迭代顺序做 index 对齐
  const machineStateList = Object.values(machineStatesDict)
  const machineStateKeys = Object.keys(machineStatesDict)

  // 统计每台机器已完工 Op 数（来自 jobs 反查）
  const jobs = store.currentState?.jobs || []
  const machineIdToInt = (v) => {
    if (v == null) return null
    if (typeof v === 'number') return v
    const m = String(v).match(/(\d+)/)
    return m ? Number(m[1]) : null
  }
  // mesh id (config 的字符串) → int 编号（按 mesh 迭代顺序）
  const meshIntIds = []
  machineMeshMap.forEach((_, id) => { meshIntIds.push({ id, intId: machineIdToInt(id) }) })

  const finishedOpsByMachine = {}
  jobs.forEach((job) => {
    ;(job.ops || []).forEach((op) => {
      if (op.status !== 'FINISHED' || op.assigned_machine == null) return
      const key = `M${op.assigned_machine}`
      finishedOpsByMachine[key] = (finishedOpsByMachine[key] || 0) + 1
    })
  })

  // 机器标签 + Hover 富信息 tooltip
  let meshIndex = 0
  machineMeshMap.forEach(({ group }, id) => {
    const vec = group.position.clone()
    vec.y += GRID_SIZE * 0.7
    vec.project(camera)
    const curIndex = meshIndex++

    if (vec.z > 1) return

    // 三级兜底：精确 id → "M"+id → 按索引对齐
    const dyn = machineStatesDict[id]
      || machineStatesDict[`M${id}`]
      || machineStateList[curIndex]
      || {}

    let detail = null
    let dotClass = null
    let badge = null
    let alert = false
    if (dyn && Object.keys(dyn).length > 0) {
      const op = dyn.current_op
      const status = dyn.status || (op ? 'WORKING' : 'IDLE')
      const statusClass = String(status).toLowerCase()
      const repairRemaining = dyn.repair_remaining || 0
      const opPct = op && op.proc_time > 0
        ? Math.min(100, Math.round(((op.step_done ?? 0) / op.proc_time) * 100))
        : 0

      // 找本机已完工 Op 数：优先用 dyn.id 反推，否则按 curIndex+1 当作 machine 编号
      const dynIdInt = machineIdToInt(dyn.id ?? id)
      const mKey = dynIdInt != null ? `M${dynIdInt}` : `M${curIndex + 1}`
      const finishedOps = finishedOpsByMachine[mKey] || 0

      detail = {
        statusLabel: status,
        statusClass,
        op: op
          ? {
              job_id: op.job_id,
              op_id: op.op_id,
              step_done: op.step_done ?? 0,
              proc_time: op.proc_time ?? 0,
              index_in_job: op.index_in_job,
              total_in_job: op.total_in_job,
            }
          : null,
        opPct,
        queueLength: dyn.queue_length || 0,
        finishedOps,
        repairRemaining,
        downReason: dyn.down_reason || '',
      }
      dotClass = `dot-${statusClass}`
      if (status === 'BROKEN') {
        alert = true
        badge = repairRemaining > 0 ? `机器故障 · 剩余 ${repairRemaining} 步` : '机器故障'
      }
    }

    labels.push({
      id: `machine-${id}`,
      kind: 'machine',
      machineId: id,
      runtimeMachineKey: machineStateKeys[curIndex] || id,
      x: (vec.x * 0.5 + 0.5) * cw + rect.left - (containerRect?.left || 0),
      y: (-vec.y * 0.5 + 0.5) * ch + rect.top - (containerRect?.top || 0),
      text: group.userData.name || id,
      color: '#f4f8ff',
      detail,
      dotClass,
      badge,
      alert,
    })
  })

  // AGV 标签
  agvDataList.forEach(({ group }, i) => {
    const vec = group.position.clone()
    vec.y += GRID_SIZE * 0.2
    vec.project(camera)
    if (vec.z > 1) return
    const status = group.userData.status || 'IDLE'
    const repairRemaining = group.userData.repairRemaining || 0
    const down = status === 'DOWN'
    labels.push({
      id: `agv-${i}`,
      kind: 'agv',
      agvIndex: i,
      x: (vec.x * 0.5 + 0.5) * cw + rect.left - (containerRect?.left || 0),
      y: (-vec.y * 0.5 + 0.5) * ch + rect.top - (containerRect?.top || 0),
      text: `A${i + 1}`,
      badge: down ? `AGV故障 · 剩余 ${repairRemaining} 步` : null,
      color: down ? '#ffd6d6' : '#e7fbff',
      alert: down,
    })
  })

  // 临时障碍标签
  ;(store.currentState?.blocked_cells || []).forEach((cell, idx) => {
    if (!Array.isArray(cell) || cell.length < 2) return
    const [gx, gy] = cell
    const pos = gridToWorld(gx, gy)
    const vec = new THREE.Vector3(pos.x, GRID_SIZE * 0.38, pos.z)
    vec.project(camera)
    if (vec.z > 1) return

    labels.push({
      id: `exception-obstacle-${gx}-${gy}-${idx}`,
      kind: 'exception-obstacle',
      x: (vec.x * 0.5 + 0.5) * cw + rect.left - (containerRect?.left || 0),
      y: (-vec.y * 0.5 + 0.5) * ch + rect.top - (containerRect?.top || 0),
      text: '临时障碍',
      color: '#fff4f4',
    })
  })

  screenLabels.value = labels
}

// ==================== 渲染循环 ====================
let animationId

function animate() {
  animationId = requestAnimationFrame(animate)
  if (!renderer || !scene || !camera) return

  updateFromStore()
  controls.update()
  renderer.render(scene, camera)
}

// ==================== 大小适配 ====================
function onResize() {
  const container = containerRef.value
  if (!container || !renderer || !camera) return
  const w = container.clientWidth
  const h = container.clientHeight
  if (w === 0 || h === 0) return
  renderer.setSize(w, h)
  camera.aspect = w / h
  camera.updateProjectionMatrix()
}

// ==================== 生命周期 ====================
let resizeObserver = null

onMounted(async () => {
  await nextTick()
  if (!containerRef.value) return

  initScene()
  buildStaticElements()
  rebuildAGVs(0)
  animate()

  resizeObserver = new ResizeObserver(onResize)
  resizeObserver.observe(containerRef.value)

  // 选择与编辑共用同一套画布事件；具体行为由 editMode 决定。
  setupEditModeListeners()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId)
  resizeObserver?.disconnect()
  removeEditModeListeners()
  controls?.dispose()

  // 遍历并清理所有 mesh
  const disposeMesh = (obj) => {
    obj.traverse?.(child => {
      child.geometry?.dispose()
      if (child.material) {
        if (Array.isArray(child.material)) child.material.forEach(m => m.dispose())
        else child.material.dispose()
      }
    })
  }
  if (scene) { disposeMesh(scene); scene.clear() }

  renderer?.dispose()
  renderer?.domElement?.remove()
})

// ==================== 监听拓扑变化 ====================
watch(() => props.staticConfig, (newVal, oldVal) => {
  // 配置引用变化（加载新配置）→ 全量重建
  if (newVal !== oldVal) {
    machineMeshMap.forEach(({ bodyMat, lightMat }) => {
      bodyMat?.dispose(); lightMat?.dispose()
    })
    machineMeshMap.clear()
    while (machineGroup?.children.length) machineGroup.remove(machineGroup.children[0])
    while (agvGroup?.children.length) agvGroup.remove(agvGroup.children[0])
    agvDataList.length = 0

    nextTick(() => {
      buildStaticElements()
      rebuildAGVs(0)
      // 新配置加载后，按 cfg.agvs.initialLocation 把 AGV 摆好
      if (props.editMode) syncAGVsFromConfig()
    })
    return
  }

  // 同一引用的深度变更（增删资产）→ 根据 hint 精准重建
  const hint = store.rebuildHint

  // 消费完 hint 后延迟清除，防止残留影响后续操作
  if (hint) {
    nextTick(() => { store.rebuildHint = null })
  }

  if (hint === 'zone') {
    buildZones()
  } else if (hint === 'machine') {
    machineMeshMap.forEach(({ bodyMat, lightMat }) => {
      bodyMat?.dispose(); lightMat?.dispose()
    })
    machineMeshMap.clear()
    while (machineGroup?.children.length) machineGroup.remove(machineGroup.children[0])
    buildMachines()
  } else if (hint === 'waypoint') {
    buildWaypoints()
    buildEdges()
  } else if (hint === 'agv') {
    // AGV 增删/重命名：重建 mesh 数量并按 initialLocation 重新摆位
    syncAGVsFromConfig()
  } else if (!hint) {
    // 无 hint（纯数据修正等场景）→ 仅同步重建静态元素
    buildStaticElements()
  }
}, { deep: true })

// ==================== 监听编辑模式切换 ====================
watch(() => props.editMode, (val) => {
  if (val) {
    // 进入编辑模式：把 AGV 摆到 cfg.agvs.initialLocation（无仿真时 mesh 默认停在 0,0）
    syncAGVsFromConfig()
  } else {
    hideHighlight()
    selectionPointerStart = null
  }
})

// ==================== 监听背景主题/尺寸切换 ====================
watch([() => props.backgroundTheme, () => props.backgroundSize], () => {
  if (!scene) return
  const theme = BACKGROUND_THEMES[props.backgroundTheme] || BACKGROUND_THEMES.clean
  scene.background = new THREE.Color(theme.bgColor)
  scene.fog.color.set(theme.bgColor)
  scene.fog.near = theme.fogNear
  scene.fog.far = theme.fogFar
  if (ambientLight) ambientLight.intensity = theme.ambientIntensity
  if (sunLight) sunLight.intensity = theme.sunIntensity
  buildBackground()
  buildGroundAndGrid()
})

// ==================== 暴露方法 ====================
defineExpose({
  /** 获取当前可用的背景主题列表 */
  getBackgroundThemes() {
    return Object.entries(BACKGROUND_THEMES).map(([key, val]) => ({ key, name: val.name }))
  },
})
</script>

<style scoped>
.factory-3d-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: #0a0e1c;
}

.hud-header {
  position: absolute;
  top: 16px;
  left: 16px;
  right: 16px;
  z-index: 10;
  pointer-events: none;
}

.hud-header :deep(*) {
  pointer-events: auto;
}

.three-wrapper {
  width: 100%;
  height: 100%;
}

.labels-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 5;
}

.world-label {
  position: absolute;
  font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 13px;
  font-weight: 800;
  transform: translate(-50%, -50%);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.85), 0 0 10px rgba(0, 0, 0, 0.55);
  white-space: nowrap;
  pointer-events: none;
  letter-spacing: 0;
}

.label-name {
  line-height: 1;
}

.label-main-row {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.label-badge {
  display: block;
  margin-top: 3px;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(255, 70, 70, 0.92);
  color: #fff8f0;
  font-size: 12px;
  font-weight: 900;
  line-height: 1.15;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.65);
}

/* Hover 命中区：扩大点击范围 */
.label-hoverable {
  pointer-events: auto;
  cursor: pointer;
}
.label-hitbox {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 5px 8px;
  margin: -5px -8px;
  border-radius: 4px;
  background: rgba(11, 18, 28, 0.58);
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
  transition: background 0.15s;
}
.label-hitbox-alert {
  background: rgba(132, 18, 26, 0.88);
  border-color: rgba(255, 215, 140, 0.75);
  box-shadow: 0 0 0 1px rgba(255, 95, 95, 0.35), 0 4px 14px rgba(90, 0, 0, 0.38);
}
.label-hoverable:hover .label-hitbox {
  background: rgba(100, 180, 255, 0.12);
}
.label-hoverable:hover .label-hitbox-alert {
  background: rgba(158, 28, 38, 0.96);
}
.label-selected .label-hitbox {
  background: rgba(70, 145, 220, 0.32);
  border-color: rgba(148, 215, 255, 0.95);
  box-shadow: 0 0 0 2px rgba(100, 181, 255, 0.35), 0 4px 14px rgba(0, 0, 0, 0.32);
}

.label-machine .label-hitbox {
  background: rgba(20, 32, 48, 0.72);
}

.label-machine .label-hitbox-alert {
  background: rgba(128, 18, 28, 0.9);
}

.label-agv .label-hitbox {
  background: rgba(0, 73, 92, 0.76);
  border-color: rgba(151, 232, 255, 0.45);
}

.label-agv .label-hitbox-alert {
  background: rgba(152, 24, 32, 0.94);
  border-color: rgba(255, 225, 150, 0.82);
}

.label-agv .label-hitbox-alert .label-badge {
  background: #ff2f3f;
  color: #fff;
}

.label-exception-obstacle .label-hitbox {
  background: rgba(178, 28, 36, 0.82);
  border-color: rgba(255, 222, 160, 0.75);
  color: #fff4f4;
}

/* 状态色点 */
.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #888;
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.5);
}
.status-dot.dot-working { background: #64b5ff; box-shadow: 0 0 6px rgba(100, 181, 255, 0.7); }
.status-dot.dot-idle    { background: #888; }
.status-dot.dot-broken  { background: #ff6464; box-shadow: 0 0 6px rgba(255, 100, 100, 0.7); animation: pulse 1.2s infinite; }
.status-dot.dot-blocked { background: #ffb450; box-shadow: 0 0 6px rgba(255, 180, 80, 0.7); }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Hover 富信息 tooltip */
.machine-tooltip {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translate(-50%, 8px);
  min-width: 200px;
  padding: 10px 12px;
  background: linear-gradient(180deg, rgba(20, 26, 48, 0.95), rgba(10, 14, 28, 0.95));
  border: 1px solid rgba(100, 180, 255, 0.3);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(100, 180, 255, 0.05);
  backdrop-filter: blur(10px);
  color: rgba(220, 230, 245, 0.9);
  font-family: "Inter", "PingFang SC", sans-serif;
  font-size: 11px;
  font-weight: 400;
  text-shadow: none;
  white-space: normal;
  pointer-events: none;
  z-index: 100;
  animation: mtFadeIn 0.12s ease-out;
}
.machine-tooltip.mt-broken { border-color: rgba(255, 100, 100, 0.5); box-shadow: 0 8px 24px rgba(0,0,0,0.5), 0 0 0 1px rgba(255, 100, 100, 0.1); }
.machine-tooltip.mt-blocked { border-color: rgba(255, 180, 80, 0.5); }

@keyframes mtFadeIn {
  from { opacity: 0; transform: translate(-50%, 4px); }
  to   { opacity: 1; transform: translate(-50%, 8px); }
}

.mt-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.mt-name {
  font-size: 13px;
  font-weight: 700;
  color: rgba(240, 245, 255, 1);
}
.mt-status-badge {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(200, 220, 255, 0.7);
}
.mt-status-badge .mt-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}
.mt-status-badge.tag-working { background: rgba(100, 181, 255, 0.22); color: #64b5ff; }
.mt-status-badge.tag-idle    { background: rgba(160, 160, 160, 0.18); color: #a0a0a0; }
.mt-status-badge.tag-broken  { background: rgba(255, 100, 100, 0.22); color: #ff6464; }
.mt-status-badge.tag-blocked { background: rgba(255, 180, 80, 0.22); color: #ffb450; }

.mt-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 4px 0;
}
.mt-label {
  font-size: 10px;
  color: rgba(160, 190, 230, 0.55);
}
.mt-value {
  font-size: 11px;
  color: rgba(220, 230, 245, 0.9);
  font-variant-numeric: tabular-nums;
}
.mt-value.mt-idle {
  color: rgba(160, 190, 230, 0.4);
  font-style: italic;
}

.mt-progress-block {
  margin: 6px 0 4px;
}
.mt-progress-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.mt-progress-text {
  font-size: 10px;
  color: #64b5ff;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.mt-bar-wrap {
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}
.mt-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #64b5ff, #4a90e2);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.mt-divider {
  height: 1px;
  background: rgba(100, 180, 255, 0.1);
  margin: 8px 0 6px;
}

.mt-stat-row {
  display: flex;
  gap: 8px;
}
.mt-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 0;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
}
.mt-stat-num {
  font-size: 14px;
  font-weight: 700;
  color: rgba(240, 245, 255, 0.95);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.mt-stat-label {
  font-size: 9px;
  color: rgba(160, 190, 230, 0.5);
  margin-top: 2px;
}
</style>
