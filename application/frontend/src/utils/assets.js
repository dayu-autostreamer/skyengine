/**
 * 3D 数字资产定义 — 颜色、材质参数、3D 模型构建函数
 *
 * 所有 3D 可视化相关的视觉资产集中管理，
 * 组件层通过 import 引用，避免在业务代码中硬编码。
 */

import * as THREE from 'three'

// ==================== 场景 ====================
export const BG_COLOR = 0xf0f2f5
export const GROUND_COLOR = 0xe8eaed
export const GRID_COLOR_MAIN = 0xc8ccd4
export const GRID_COLOR_SUB = 0xdce0e6

// ==================== 机器 ====================
export const MACHINE_COLORS = {
  WORKING:     { body: 0x4a9eff, emissive: 0x1a5fbb },
  IDLE:        { body: 0xb0b8c8, emissive: 0x000000 },
  BROKEN:      { body: 0xff5555, emissive: 0xcc2222 },
  MAINTENANCE: { body: 0xffaa33, emissive: 0xcc8800 },
}
export const STATUS_LIGHT = {
  WORKING: 0x00e87b,
  IDLE: 0x8899aa,
  BROKEN: 0xff2d55,
  MAINTENANCE: 0xffb300,
}
export const MACHINE_PILLAR_COLOR = 0x8899aa
export const MACHINE_TOP_COLOR = 0x556677
export const MACHINE_SCREEN_COLOR = 0x223344
export const MACHINE_SCREEN_EMISSIVE = 0x112244

// ==================== AGV ====================
export const AGV_ACTIVE_COLOR = 0x3a6ea5
export const AGV_IDLE_COLOR = 0xaabbcc
export const AGV_DOWN_COLOR = 0x884455
export const AGV_FORK_COLOR = 0x667788
export const AGV_WHEEL_COLOR = 0x333333
export const AGV_ARROW_COLOR = 0x0099dd
export const AGV_LIGHT_ACTIVE = 0x00e87b
export const AGV_LIGHT_IDLE = 0x8899aa
export const AGV_LIGHT_DOWN = 0xff2d55

// ==================== 区域 ====================
export const ZONE_COLORS = {
  restricted: 0xff8800,
  workbench: 0x0088cc,
  obstacle: 0x663333,
  workarea: 0x00aa66,
  default: 0x5577aa,
}

// ==================== 围墙 ====================
export const WALL = {
  panel: { color: 0xdde4ee },
  frame: { color: 0x6688aa },
  glow: { color: 0x3399cc, emissive: 0x1166aa, emissiveIntensity: 0.6 },
  corner: { color: 0x5577aa, emissive: 0x113355 },
  baseStrip: { color: 0x4499cc, emissive: 0x1166aa, emissiveIntensity: 0.4 },
  topStrip: { color: 0x55aadd, emissive: 0x2288bb, emissiveIntensity: 0.5 },
  cornerGlow: 0x44bbff,
}

// ==================== 边 / 路径 ====================
export const EDGE_COLOR = 0x88aacc

// ==================== 路径点 ====================
export const WAYPOINT_DOCK_COLOR = 0x5588bb
export const WAYPOINT_DEFAULT_COLOR = 0x44aa77

// ==================== 装饰物 ====================
export const DECOR = {
  yellow: 0xf5c542,
  metalGray: 0x8899aa,
  darkGray: 0x556677,
  cabinet: 0x778899,
  rack: 0x99aabb,
  shelf: 0xdde4ee,
  greenBox: 0x55aa77,
  blueBox: 0x5577bb,
  black: 0x222222,
  redLight: 0xff4444,
  greenLight: 0x44ff44,
}

// ==================== 障碍物墙 ====================
export const OBSTACLE_WALL = {
  body: 0x5a5d66,
  top: 0x44474f,
  mortar: 0x6b6e77,
}

// ==================== 编辑模式高亮 ====================
export const HIGHLIGHT_COLOR = 0x667eea
export const HIGHLIGHT_COLLISION_COLOR = 0xff3355

// ==================== 工厂背景主题 ====================
export const BACKGROUND_THEMES = {
  clean: {
    name: '简洁',
    bgColor: 0xf0f2f5,
    groundColor: 0xe8eaed,
    fogNear: 60,
    fogFar: 150,
    ambientIntensity: 1.8,
    sunIntensity: 3.0,
    bgScale: 1,
  },
  factory: {
    name: '工厂车间',
    bgColor: 0x1a1d24,
    groundColor: 0x2a2d35,
    fogNear: 40,
    fogFar: 180,
    ambientIntensity: 1.2,
    sunIntensity: 2.0,
    bgScale: 2,
  },
}

/** 厂房尺寸预设 */
export const FACTORY_SIZE_PRESETS = [
  { key: 1,   label: '紧凑', spread: 1.5, ceiling: 4 },
  { key: 2,   label: '标准', spread: 3,   ceiling: 6 },
  { key: 3,   label: '宽敞', spread: 5,   ceiling: 8 },
  { key: 4,   label: '大厅', spread: 8,   ceiling: 10 },
]

export const FACTORY_BG = {
  floorMarking: 0xd4a017,     // 黄色安全线
  pillar: 0x556677,           // 钢柱
  pillarBase: 0x3a3f4a,       // 柱基
  beam: 0x4a5060,             // 天花板横梁
  distantWall: 0x252830,      // 远景墙面
  overheadLight: 0xffeedd,    // 顶灯色温
  overheadLightGlow: 0xfff5e6,
}

// ==================== 3D 资产构建函数 ====================
// 每个 createXxx(U) 接收网格单元大小，返回居中原点的 THREE.Group，
// 由调用方负责定位和挂载。

/**
 * 安全警示柱
 * 黄色柱体 + 深灰顶盖 + 黑色条纹
 */
export function createBollard(U) {
  const grp = new THREE.Group()

  const yellowMat = new THREE.MeshStandardMaterial({ color: DECOR.yellow, roughness: 0.5, metalness: 0.3 })
  const darkGrayMat = new THREE.MeshStandardMaterial({ color: DECOR.darkGray, roughness: 0.6, metalness: 0.3 })
  const blackMat = new THREE.MeshStandardMaterial({ color: DECOR.black, roughness: 0.8 })

  const bollardGeom = new THREE.CylinderGeometry(U * 0.06, U * 0.06, U * 0.5, 8)
  const bollardCapGeom = new THREE.CylinderGeometry(U * 0.08, U * 0.08, U * 0.04, 8)
  const stripeGeom = new THREE.BoxGeometry(U * 0.04, U * 0.08, U * 0.14)

  // 柱体
  const post = new THREE.Mesh(bollardGeom, yellowMat)
  post.position.y = U * 0.25
  post.castShadow = true
  grp.add(post)

  // 顶盖
  const cap = new THREE.Mesh(bollardCapGeom, darkGrayMat)
  cap.position.y = U * 0.52
  grp.add(cap)

  // 黑色条纹
  const s1 = new THREE.Mesh(stripeGeom, blackMat)
  s1.position.set(0, U * 0.15, U * 0.07)
  grp.add(s1)
  const s2 = new THREE.Mesh(stripeGeom, blackMat)
  s2.position.set(0, U * 0.35, U * 0.07)
  grp.add(s2)

  return grp
}

/**
 * 储物架
 * 三层隔板 + 绿/蓝交替货箱
 */
export function createRack(U) {
  const grp = new THREE.Group()

  const rackMat = new THREE.MeshStandardMaterial({ color: DECOR.rack, roughness: 0.5, metalness: 0.4 })
  const shelfMat = new THREE.MeshStandardMaterial({ color: DECOR.shelf, roughness: 0.6, metalness: 0.1 })
  const greenBoxMat = new THREE.MeshStandardMaterial({ color: DECOR.greenBox, roughness: 0.5, metalness: 0.1 })
  const blueBoxMat = new THREE.MeshStandardMaterial({ color: DECOR.blueBox, roughness: 0.5, metalness: 0.1 })

  const rackGeom = new THREE.BoxGeometry(U * 0.8, U * 1.2, U * 0.4)
  const shelfGeom = new THREE.BoxGeometry(U * 0.75, U * 0.03, U * 0.36)

  // 框架
  const frame = new THREE.Mesh(rackGeom, rackMat)
  frame.position.y = U * 0.6
  frame.castShadow = true
  grp.add(frame)

  // 三层隔板 + 货箱
  for (let layer = 0; layer < 3; layer++) {
    const shelfY = U * (0.2 + layer * 0.35)
    const shelf = new THREE.Mesh(shelfGeom, shelfMat)
    shelf.position.y = shelfY
    grp.add(shelf)

    const boxGeom = new THREE.BoxGeometry(U * 0.25, U * 0.15, U * 0.25)
    const boxMat = layer % 2 === 0 ? greenBoxMat : blueBoxMat
    const box = new THREE.Mesh(boxGeom, boxMat)
    box.position.set(U * (layer % 2 === 0 ? -0.15 : 0.15), shelfY + U * 0.09, 0)
    box.castShadow = true
    grp.add(box)
  }

  return grp
}

/**
 * 配电箱
 * 箱体 + 门 + 红绿指示灯
 */
export function createCabinet(U) {
  const grp = new THREE.Group()

  const cabinetMat = new THREE.MeshStandardMaterial({ color: DECOR.cabinet, roughness: 0.35, metalness: 0.5 })
  const darkGrayMat = new THREE.MeshStandardMaterial({ color: DECOR.darkGray, roughness: 0.6, metalness: 0.3 })
  const redLightMat = new THREE.MeshBasicMaterial({ color: DECOR.redLight })
  const greenLightMat = new THREE.MeshBasicMaterial({ color: DECOR.greenLight })

  const cabinetGeom = new THREE.BoxGeometry(U * 0.35, U * 0.7, U * 0.25)
  const cabinetDoorGeom = new THREE.BoxGeometry(U * 0.01, U * 0.5, U * 0.18)
  const lightDotGeom = new THREE.CircleGeometry(U * 0.025, 8)

  // 箱体
  const cab = new THREE.Mesh(cabinetGeom, cabinetMat)
  cab.position.y = U * 0.35
  cab.castShadow = true
  grp.add(cab)

  // 门
  const door = new THREE.Mesh(cabinetDoorGeom, darkGrayMat)
  door.position.set(U * 0.18, U * 0.35, 0)
  grp.add(door)

  // 指示灯
  const redLight = new THREE.Mesh(lightDotGeom, redLightMat)
  redLight.position.set(U * 0.18, U * 0.55, U * 0.06)
  redLight.rotation.y = Math.PI / 2
  grp.add(redLight)
  const greenLight = new THREE.Mesh(lightDotGeom, greenLightMat)
  greenLight.position.set(U * 0.18, U * 0.55, -U * 0.06)
  greenLight.rotation.y = Math.PI / 2
  grp.add(greenLight)

  return grp
}

/**
 * 安全隔离栏
 * 两根金属立柱 + 两道黄色横杆
 */
export function createSafetyBarrier(U) {
  const grp = new THREE.Group()

  const metalGrayMat = new THREE.MeshStandardMaterial({ color: DECOR.metalGray, roughness: 0.4, metalness: 0.6 })
  const yellowMat = new THREE.MeshStandardMaterial({ color: DECOR.yellow, roughness: 0.5, metalness: 0.3 })

  const railPostGeom = new THREE.CylinderGeometry(U * 0.03, U * 0.03, U * 0.6, 6)
  const railBarGeom = new THREE.BoxGeometry(U * 3, U * 0.04, U * 0.04)

  // 两根立柱
  const p1 = new THREE.Mesh(railPostGeom, metalGrayMat)
  p1.position.set(-U * 1.5, U * 0.3, 0)
  p1.castShadow = true
  grp.add(p1)
  const p2 = new THREE.Mesh(railPostGeom, metalGrayMat)
  p2.position.set(U * 1.5, U * 0.3, 0)
  p2.castShadow = true
  grp.add(p2)

  // 两道横杆
  const bar1 = new THREE.Mesh(railBarGeom, yellowMat)
  bar1.position.y = U * 0.45
  grp.add(bar1)
  const bar2 = new THREE.Mesh(railBarGeom, yellowMat)
  bar2.position.y = U * 0.2
  grp.add(bar2)

  return grp
}

/**
 * 障碍物墙
 * 灰色实体砖墙 + 深灰压顶 + 横向砖缝纹理
 *
 * @param {number} U      网格单元大小
 * @param {number} areaW  墙宽度（网格单位数）
 * @param {number} areaH  墙深度（网格单位数）
 * @returns {THREE.Group}
 */
export function createObstacleWall(U, areaW, areaH) {
  const grp = new THREE.Group()

  const wallH = U * 0.6
  const w = areaW * U
  const d = areaH * U

  const bodyMat = new THREE.MeshStandardMaterial({
    color: OBSTACLE_WALL.body, roughness: 0.85, metalness: 0.05,
  })
  const topMat = new THREE.MeshStandardMaterial({
    color: OBSTACLE_WALL.top, roughness: 0.6, metalness: 0.1,
  })
  const mortarMat = new THREE.MeshStandardMaterial({
    color: OBSTACLE_WALL.mortar, roughness: 0.9, metalness: 0.0,
  })

  // 1. 墙体主体
  const bodyGeom = new THREE.BoxGeometry(w, wallH, d)
  const body = new THREE.Mesh(bodyGeom, bodyMat)
  body.position.y = wallH / 2
  body.castShadow = true
  body.receiveShadow = true
  grp.add(body)

  // 2. 压顶条
  const topH = U * 0.04
  const topGeom = new THREE.BoxGeometry(w + U * 0.02, topH, d + U * 0.02)
  const topMesh = new THREE.Mesh(topGeom, topMat)
  topMesh.position.y = wallH + topH / 2
  topMesh.castShadow = true
  grp.add(topMesh)

  // 3. 砖缝纹理 — 横向细条纹
  const mortarThick = U * 0.008
  const mortarGeomH = new THREE.BoxGeometry(w - U * 0.04, mortarThick, d - U * 0.04)
  const rows = Math.max(1, Math.floor(wallH / (U * 0.12)))
  for (let i = 1; i <= rows; i++) {
    const y = (i / (rows + 1)) * wallH
    const stripe = new THREE.Mesh(mortarGeomH, mortarMat)
    stripe.position.y = y
    grp.add(stripe)
  }

  return grp
}

/**
 * 科技感围墙（整体）
 * 四面半透明面板 + 发光条 + 边框立柱 + 数据节点 + 四角发光立柱
 *
 * @param {number} U           网格单元大小
 * @param {number} gridWidth   网格列数
 * @param {number} gridHeight  网格行数
 * @returns {THREE.Group}      name='perimeter-wall'
 */
export function createPerimeterWall(U, gridWidth, gridHeight) {
  const halfW = (gridWidth * U) / 2
  const halfH = (gridHeight * U) / 2
  const wallH = U * 0.55
  const offset = U * 0.6

  const wallGroup = new THREE.Group()
  wallGroup.name = 'perimeter-wall'

  // --- 材质 ---
  const panelMat = new THREE.MeshStandardMaterial({
    color: WALL.panel.color, transparent: true, opacity: 0.35,
    roughness: 0.1, metalness: 0.8, side: THREE.DoubleSide,
  })
  const frameMat = new THREE.MeshStandardMaterial({
    color: WALL.frame.color, roughness: 0.25, metalness: 0.8,
  })
  const glowMat = new THREE.MeshStandardMaterial({
    color: WALL.glow.color, emissive: WALL.glow.emissive, emissiveIntensity: WALL.glow.emissiveIntensity,
    roughness: 0.1, metalness: 0.9,
  })
  const cornerMat = new THREE.MeshStandardMaterial({
    color: WALL.corner.color, emissive: WALL.corner.emissive, roughness: 0.2, metalness: 0.7,
  })
  const baseStripMat = new THREE.MeshStandardMaterial({
    color: WALL.baseStrip.color, emissive: WALL.baseStrip.emissive, emissiveIntensity: WALL.baseStrip.emissiveIntensity,
    roughness: 0.15, metalness: 0.85,
  })
  const topStripMat = new THREE.MeshStandardMaterial({
    color: WALL.topStrip.color, emissive: WALL.topStrip.emissive, emissiveIntensity: WALL.topStrip.emissiveIntensity,
    roughness: 0.1, metalness: 0.9,
  })

  // --- 每面墙的生成 ---
  function createWallSegment(length, position, rotationY) {
    const seg = new THREE.Group()

    // 1. 半透明面板
    const panelGeom = new THREE.PlaneGeometry(length, wallH)
    const panel = new THREE.Mesh(panelGeom, panelMat)
    panel.position.y = wallH / 2 + U * 0.02
    seg.add(panel)

    // 2. 边框立柱 — 每隔 2 个单位一根
    const postGeom = new THREE.BoxGeometry(U * 0.06, wallH + U * 0.04, U * 0.06)
    const postCount = Math.max(2, Math.floor(length / (U * 2)) + 1)
    for (let i = 0; i < postCount; i++) {
      const t = postCount === 1 ? 0 : (i / (postCount - 1) - 0.5) * length
      const post = new THREE.Mesh(postGeom, frameMat)
      post.position.set(t, wallH / 2, 0)
      post.castShadow = true
      seg.add(post)
    }

    // 3. 底部发光条
    const baseGeom = new THREE.BoxGeometry(length, U * 0.04, U * 0.03)
    const base = new THREE.Mesh(baseGeom, baseStripMat)
    base.position.y = U * 0.02
    seg.add(base)

    // 4. 顶部发光条
    const topGeom = new THREE.BoxGeometry(length, U * 0.03, U * 0.03)
    const top = new THREE.Mesh(topGeom, topStripMat)
    top.position.y = wallH + U * 0.01
    seg.add(top)

    // 5. 数据节点 — 每段中间小方块（模拟数据接口）
    const nodeGeom = new THREE.BoxGeometry(U * 0.12, U * 0.08, U * 0.05)
    const nodeCount = Math.max(1, Math.floor(length / (U * 4)))
    for (let i = 0; i < nodeCount; i++) {
      const t = nodeCount === 1 ? 0 : ((i + 0.5) / nodeCount - 0.5) * length
      const node = new THREE.Mesh(nodeGeom, glowMat)
      node.position.set(t, wallH * 0.4, U * 0.01)
      seg.add(node)
    }

    seg.position.copy(position)
    seg.rotation.y = rotationY
    wallGroup.add(seg)
  }

  // --- 四面墙 ---
  createWallSegment(gridWidth * U, new THREE.Vector3(0, 0, halfH + offset), 0)
  createWallSegment(gridWidth * U, new THREE.Vector3(0, 0, -halfH - offset), 0)
  createWallSegment(gridHeight * U, new THREE.Vector3(-halfW - offset, 0, 0), Math.PI / 2)
  createWallSegment(gridHeight * U, new THREE.Vector3(halfW + offset, 0, 0), Math.PI / 2)

  // --- 四角立柱 ---
  const cornerGeom = new THREE.CylinderGeometry(U * 0.1, U * 0.12, wallH + U * 0.2, 8)
  const cornerTopGeom = new THREE.CylinderGeometry(U * 0.13, U * 0.1, U * 0.06, 8)
  const cornerGlowGeom = new THREE.SphereGeometry(U * 0.06, 8, 8)
  const cornerGlowMat = new THREE.MeshBasicMaterial({ color: WALL.cornerGlow })

  const cornerPositions = [
    [-halfW - offset, -halfH - offset],
    [ halfW + offset, -halfH - offset],
    [-halfW - offset,  halfH + offset],
    [ halfW + offset,  halfH + offset],
  ]
  cornerPositions.forEach(([x, z]) => {
    const grp = new THREE.Group()
    const pillar = new THREE.Mesh(cornerGeom, cornerMat)
    pillar.position.y = (wallH + U * 0.2) / 2
    pillar.castShadow = true
    grp.add(pillar)
    const cap = new THREE.Mesh(cornerTopGeom, frameMat)
    cap.position.y = wallH + U * 0.2
    grp.add(cap)
    const glow = new THREE.Mesh(cornerGlowGeom, cornerGlowMat)
    glow.position.y = wallH + U * 0.28
    grp.add(glow)
    grp.position.set(x, 0, z)
    wallGroup.add(grp)
  })

  return wallGroup
}

/**
 * 装饰物布局配置生成器
 * 根据网格尺寸计算各装饰物的网格坐标列表
 *
 * @param {number} w 网格列数
 * @param {number} h 网格行数
 * @returns {{ bollards: [number,number][], racks: [number,number][], cabinets: [number,number][] }}
 */
export function getDecorationLayout(w, h) {
  const bollards = []
  // 顶边和底边
  for (let gx = 1; gx < w; gx += 3) {
    bollards.push([gx, 0])
    bollards.push([gx, h - 1])
  }
  // 左边和右边
  for (let gy = 1; gy < h; gy += 3) {
    bollards.push([0, gy])
    bollards.push([w - 1, gy])
  }

  const racks = [
    [1, 1], [w - 2, 1], [1, h - 2], [w - 2, h - 2],
  ]

  const cabinets = [
    [Math.floor(w / 2), 0],
    [Math.floor(w / 2), h - 1],
    [0, Math.floor(h / 2)],
    [w - 1, Math.floor(h / 2)],
  ]

  // 安全隔离栏 — 底部外侧两段
  const barriers = []
  if (w > 6) {
    for (let i = 0; i < 2; i++) {
      barriers.push([Math.floor(w / 4) + i * Math.floor(w / 2), -1.5])
    }
  }

  return { bollards, racks, cabinets, barriers }
}

// ==================== 机器构建 ====================

/**
 * 加工机器复合体
 * 主体 + 四根立柱 + 顶部控制面板 + 前面板屏幕 + 状态指示灯
 *
 * @param {number} U                 网格单元大小
 * @param {{ id, name, status }} opts 机器元信息
 * @returns {{ group: THREE.Group, bodyMat, lightMat }}
 */
export function createMachine(U, opts = {}) {
  const group = new THREE.Group()
  const status = opts.status || 'IDLE'
  const mc = MACHINE_COLORS[status] || MACHINE_COLORS.IDLE

  // 共享几何体（单次创建）
  const bodyGeom    = new THREE.BoxGeometry(U * 1.2, U * 0.5, U * 0.9)
  const pillarGeom  = new THREE.CylinderGeometry(U * 0.035, U * 0.035, U * 0.5, 6)
  const topGeom     = new THREE.BoxGeometry(U * 0.55, U * 0.07, U * 0.35)
  const screenGeom  = new THREE.BoxGeometry(U * 0.3, U * 0.15, U * 0.02)
  const lightGeom   = new THREE.SphereGeometry(U * 0.07, 8, 8)

  // 1. 主体
  const bodyMat = new THREE.MeshStandardMaterial({ color: mc.body, emissive: mc.emissive, roughness: 0.35, metalness: 0.5 })
  const body = new THREE.Mesh(bodyGeom, bodyMat)
  body.position.y = U * 0.28
  body.castShadow = true
  body.receiveShadow = true
  group.add(body)

  // 2. 四根立柱
  const pillarMat = new THREE.MeshStandardMaterial({ color: MACHINE_PILLAR_COLOR, roughness: 0.4, metalness: 0.6 })
  const corners = [[-U*0.5, U*0.28, -U*0.35], [U*0.5, U*0.28, -U*0.35], [-U*0.5, U*0.28, U*0.35], [U*0.5, U*0.28, U*0.35]]
  corners.forEach(([x, y, z]) => {
    const p = new THREE.Mesh(pillarGeom, pillarMat)
    p.position.set(x, y, z)
    p.castShadow = true
    group.add(p)
  })

  // 3. 顶部控制面板
  const topMat = new THREE.MeshStandardMaterial({ color: MACHINE_TOP_COLOR, roughness: 0.25, metalness: 0.7 })
  const top = new THREE.Mesh(topGeom, topMat)
  top.position.set(0, U * 0.57, -U * 0.1)
  top.castShadow = true
  group.add(top)

  // 4. 前面板（小屏幕）
  const screenMat = new THREE.MeshStandardMaterial({ color: MACHINE_SCREEN_COLOR, emissive: MACHINE_SCREEN_EMISSIVE, roughness: 0.1, metalness: 0.3 })
  const screen = new THREE.Mesh(screenGeom, screenMat)
  screen.position.set(0, U * 0.32, U * 0.46)
  group.add(screen)

  // 5. 状态指示灯
  const lightMat = new THREE.MeshBasicMaterial({ color: STATUS_LIGHT[status] || STATUS_LIGHT.IDLE })
  const light = new THREE.Mesh(lightGeom, lightMat)
  light.position.set(0, U * 0.62, -U * 0.1)
  group.add(light)

  group.userData = { id: opts.id, name: opts.name, status, load: 0 }
  return { group, bodyMat, lightMat }
}

// ==================== AGV 构建 ====================

/**
 * AGV 复合体
 * 底盘 + 四轮 + 货叉 + 方向箭头 + 状态灯
 *
 * @param {number} U      网格单元大小
 * @param {number} index  AGV 编号（从 0 开始）
 * @returns {{ group: THREE.Group, chassisMat, lightMat }}
 */
export function createAGV(U, index) {
  const group = new THREE.Group()

  // 共享几何体
  const chassisGeom = new THREE.BoxGeometry(U * 0.55, U * 0.06, U * 0.38)
  const wheelGeom   = new THREE.CylinderGeometry(U * 0.055, U * 0.055, U * 0.05, 8)
  const forkGeom    = new THREE.BoxGeometry(U * 0.04, U * 0.025, U * 0.18)
  const arrowGeom   = new THREE.ConeGeometry(U * 0.04, U * 0.08, 4)
  const lightGeom   = new THREE.SphereGeometry(U * 0.04, 6, 6)

  // 1. 底盘
  const chassisMat = new THREE.MeshStandardMaterial({ color: AGV_ACTIVE_COLOR, roughness: 0.25, metalness: 0.6 })
  const chassis = new THREE.Mesh(chassisGeom, chassisMat)
  chassis.position.y = U * 0.07
  chassis.castShadow = true
  chassis.receiveShadow = true
  group.add(chassis)

  // 2. 四个轮子
  const wheelMat = new THREE.MeshStandardMaterial({ color: AGV_WHEEL_COLOR, roughness: 0.8, metalness: 0.1 })
  const wheelPos = [[-U*0.22, U*0.035, -U*0.18], [U*0.22, U*0.035, -U*0.18], [-U*0.22, U*0.035, U*0.18], [U*0.22, U*0.035, U*0.18]]
  wheelPos.forEach(([x, y, z]) => {
    const wheel = new THREE.Mesh(wheelGeom, wheelMat)
    wheel.position.set(x, y, z)
    wheel.rotation.x = Math.PI / 2
    group.add(wheel)
  })

  // 3. 货叉（两根平行臂）
  const forkMat = new THREE.MeshStandardMaterial({ color: AGV_FORK_COLOR, roughness: 0.4, metalness: 0.6 })
  const fork1 = new THREE.Mesh(forkGeom, forkMat)
  fork1.position.set(-U * 0.1, U * 0.1, U * 0.28)
  group.add(fork1)
  const fork2 = new THREE.Mesh(forkGeom, forkMat)
  fork2.position.set(U * 0.1, U * 0.1, U * 0.28)
  group.add(fork2)

  // 4. 方向指示（小箭头）
  const arrowMat = new THREE.MeshBasicMaterial({ color: AGV_ARROW_COLOR })
  const arrow = new THREE.Mesh(arrowGeom, arrowMat)
  arrow.position.set(0, U * 0.12, U * 0.22)
  arrow.rotation.x = -Math.PI / 2
  group.add(arrow)

  // 5. 状态指示灯
  const lightMat = new THREE.MeshBasicMaterial({ color: AGV_LIGHT_ACTIVE })
  const light = new THREE.Mesh(lightGeom, lightMat)
  light.position.set(0, U * 0.12, 0)
  group.add(light)

  group.userData = { id: `AGV-${index + 1}` }
  return { group, chassisMat, lightMat }
}

// ==================== 工厂背景构建 ====================

/**
 * 工厂背景层 — 营造工业车间氛围
 * 包含：地坪安全标线、钢结构立柱、天花板横梁、远景墙面、顶部照明灯
 *
 * @param {number} U           网格单元大小
 * @param {number} gridWidth   网格列数
 * @param {number} gridHeight  网格行数
 * @param {number} sizePreset  厂房尺寸预设 (1=紧凑 2=标准 3=宽敞 4=大厅)
 * @returns {THREE.Group}      name='factory-background'
 */
export function createFactoryBackground(U, gridWidth, gridHeight, sizePreset = 2) {
  const bgGroup = new THREE.Group()
  bgGroup.name = 'factory-background'

  const halfW = (gridWidth * U) / 2
  const halfH = (gridHeight * U) / 2

  const preset = FACTORY_SIZE_PRESETS.find(p => p.key === sizePreset) || FACTORY_SIZE_PRESETS[1]
  const ceilingH = U * preset.ceiling
  const spread = U * preset.spread

  // ---------- 材质 ----------
  const markingMat = new THREE.MeshStandardMaterial({
    color: FACTORY_BG.floorMarking, roughness: 0.6, metalness: 0.1,
  })
  const pillarMat = new THREE.MeshStandardMaterial({
    color: FACTORY_BG.pillar, roughness: 0.3, metalness: 0.7,
  })
  const pillarBaseMat = new THREE.MeshStandardMaterial({
    color: FACTORY_BG.pillarBase, roughness: 0.5, metalness: 0.4,
  })
  const beamMat = new THREE.MeshStandardMaterial({
    color: FACTORY_BG.beam, roughness: 0.35, metalness: 0.6,
  })
  const wallMat = new THREE.MeshStandardMaterial({
    color: FACTORY_BG.distantWall, roughness: 0.8, metalness: 0.1, side: THREE.DoubleSide,
  })
  const lightBoxMat = new THREE.MeshStandardMaterial({
    color: FACTORY_BG.overheadLight, emissive: FACTORY_BG.overheadLightGlow,
    emissiveIntensity: 0.5, roughness: 0.2, metalness: 0.3,
  })

  // ---------- 1. 地坪安全标线 (黄色) ----------
  // 沿工厂区域外围画一圈虚线框
  const lineW = U * 0.06
  const lineY = 0.008
  const offset = U * 0.8   // 标线离围墙的距离

  // 上下两条长线
  const hLineGeom = new THREE.BoxGeometry(gridWidth * U + offset * 2, 0.01, lineW)
  const topLine = new THREE.Mesh(hLineGeom, markingMat)
  topLine.position.set(0, lineY, halfH + offset)
  bgGroup.add(topLine)
  const bottomLine = new THREE.Mesh(hLineGeom, markingMat)
  bottomLine.position.set(0, lineY, -halfH - offset)
  bgGroup.add(bottomLine)

  // 左右两条宽线
  const vLineGeom = new THREE.BoxGeometry(lineW, 0.01, gridHeight * U + offset * 2)
  const leftLine = new THREE.Mesh(vLineGeom, markingMat)
  leftLine.position.set(-halfW - offset, lineY, 0)
  bgGroup.add(leftLine)
  const rightLine = new THREE.Mesh(vLineGeom, markingMat)
  rightLine.position.set(halfW + offset, lineY, 0)
  bgGroup.add(rightLine)

  // 四角 L 形标记
  const cornerLen = U * 1.5
  const cornerLineH = new THREE.BoxGeometry(cornerLen, 0.01, lineW)
  const cornerLineV = new THREE.BoxGeometry(lineW, 0.01, cornerLen)
  const corners = [
    [-halfW - offset, -halfH - offset],
    [ halfW + offset, -halfH - offset],
    [-halfW - offset,  halfH + offset],
    [ halfW + offset,  halfH + offset],
  ]
  corners.forEach(([cx, cz]) => {
    const h = new THREE.Mesh(cornerLineH, markingMat)
    h.position.set(cx, lineY, cz)
    bgGroup.add(h)
    const v = new THREE.Mesh(cornerLineV, markingMat)
    v.position.set(cx, lineY, cz)
    bgGroup.add(v)
  })

  // ---------- 2. 钢结构立柱 ----------
  // 在工厂外围间隔放置 H 型钢柱
  const pillarSpacing = Math.max(4, Math.floor(Math.max(gridWidth, gridHeight) / 4))
  const pillarH = ceilingH
  const pillarR = U * 0.12
  const baseW = U * 0.35
  const baseH = U * 0.15

  const pillarGeom = new THREE.BoxGeometry(pillarR * 2, pillarH, pillarR)
  const baseGeom = new THREE.BoxGeometry(baseW, baseH, baseW)

  function addPillar(x, z) {
    const grp = new THREE.Group()
    const p = new THREE.Mesh(pillarGeom, pillarMat)
    p.position.y = pillarH / 2
    p.castShadow = true
    grp.add(p)
    const b = new THREE.Mesh(baseGeom, pillarBaseMat)
    b.position.y = baseH / 2
    grp.add(b)
    grp.position.set(x, 0, z)
    bgGroup.add(grp)
  }

  // 上下两侧
  for (let i = 0; i <= gridWidth; i += pillarSpacing) {
    const x = (i - gridWidth / 2) * U
    addPillar(x, halfH + spread)
    addPillar(x, -halfH - spread)
  }
  // 左右两侧（避免与角落重复）
  for (let i = pillarSpacing; i < gridHeight; i += pillarSpacing) {
    const z = (i - gridHeight / 2) * U
    addPillar(-halfW - spread, z)
    addPillar(halfW + spread, z)
  }

  // ---------- 3. 天花板横梁 ----------
  const beamW = U * 0.15
  const beamH = U * 0.25
  const totalSpanX = gridWidth * U + spread * 2 + U * 2
  const totalSpanZ = gridHeight * U + spread * 2 + U * 2

  const mainBeamGeom = new THREE.BoxGeometry(totalSpanX, beamH, beamW)
  const crossBeamGeom = new THREE.BoxGeometry(beamW, beamH, totalSpanZ)

  // 主横梁 (沿 X 方向)
  for (let i = 0; i <= gridHeight; i += pillarSpacing) {
    const z = (i - gridHeight / 2) * U
    const beam = new THREE.Mesh(mainBeamGeom, beamMat)
    beam.position.set(0, ceilingH, z)
    bgGroup.add(beam)
  }
  // 纵梁 (沿 Z 方向, 两根)
  const crossZ1 = new THREE.Mesh(crossBeamGeom, beamMat)
  crossZ1.position.set(-halfW - spread * 0.5, ceilingH, 0)
  bgGroup.add(crossZ1)
  const crossZ2 = new THREE.Mesh(crossBeamGeom, beamMat)
  crossZ2.position.set(halfW + spread * 0.5, ceilingH, 0)
  bgGroup.add(crossZ2)

  // ---------- 4. 远景墙面 ----------
  const wallDist = spread + U * 2
  const wallH = ceilingH + U
  const hWallLen = gridWidth * U + wallDist * 2
  const vWallLen = gridHeight * U + wallDist * 2

  // 上下墙
  const hWallGeom = new THREE.PlaneGeometry(hWallLen, wallH)
  const topWall = new THREE.Mesh(hWallGeom, wallMat)
  topWall.position.set(0, wallH / 2, halfH + wallDist)
  bgGroup.add(topWall)
  const bottomWall = new THREE.Mesh(hWallGeom, wallMat)
  bottomWall.position.set(0, wallH / 2, -halfH - wallDist)
  bgGroup.add(bottomWall)

  // 左右墙
  const vWallGeom = new THREE.PlaneGeometry(vWallLen, wallH)
  const leftWall = new THREE.Mesh(vWallGeom, wallMat)
  leftWall.position.set(-halfW - wallDist, wallH / 2, 0)
  leftWall.rotation.y = Math.PI / 2
  bgGroup.add(leftWall)
  const rightWall = new THREE.Mesh(vWallGeom, wallMat)
  rightWall.position.set(halfW + wallDist, wallH / 2, 0)
  rightWall.rotation.y = Math.PI / 2
  bgGroup.add(rightWall)

  // ---------- 5. 顶部工业照明灯 ----------
  const lightBoxW = U * 1.2
  const lightBoxH = U * 0.1
  const lightBoxD = U * 0.5
  const lightBoxGeom = new THREE.BoxGeometry(lightBoxW, lightBoxH, lightBoxD)
  const lightSpotGeom = new THREE.PlaneGeometry(lightBoxW * 0.8, lightBoxD * 0.8)

  const lightMat = new THREE.MeshBasicMaterial({
    color: FACTORY_BG.overheadLightGlow,
  })

  const lightSpacingX = Math.max(3, Math.floor(gridWidth / 3))
  const lightSpacingZ = Math.max(3, Math.floor(gridHeight / 3))

  for (let ix = lightSpacingX; ix < gridWidth; ix += lightSpacingX) {
    for (let iz = lightSpacingZ; iz < gridHeight; iz += lightSpacingZ) {
      const x = (ix - gridWidth / 2) * U
      const z = (iz - gridHeight / 2) * U
      const grp = new THREE.Group()

      // 灯壳
      const box = new THREE.Mesh(lightBoxGeom, beamMat)
      grp.add(box)

      // 发光面 (朝下)
      const glow = new THREE.Mesh(lightSpotGeom, lightMat)
      glow.position.y = -lightBoxH / 2 + 0.005
      glow.rotation.x = Math.PI / 2
      grp.add(glow)

      // 吊杆
      const rodGeom = new THREE.CylinderGeometry(U * 0.015, U * 0.015, ceilingH - U * 1.5, 4)
      const rod = new THREE.Mesh(rodGeom, beamMat)
      rod.position.y = (ceilingH - U * 1.5) / 2 + lightBoxH
      grp.add(rod)

      grp.position.set(x, ceilingH - U * 1.5, z)
      bgGroup.add(grp)
    }
  }

  // ---------- 6. 扩展地面 (工厂区域外围) ----------
  const extGroundW = gridWidth * U + (spread + U * 3) * 2
  const extGroundH = gridHeight * U + (spread + U * 3) * 2
  const extGroundGeom = new THREE.PlaneGeometry(extGroundW, extGroundH)
  const extGroundMat = new THREE.MeshStandardMaterial({
    color: 0x22252d, roughness: 0.95, metalness: 0.0,
  })
  const extGround = new THREE.Mesh(extGroundGeom, extGroundMat)
  extGround.rotation.x = -Math.PI / 2
  extGround.position.y = -0.01
  extGround.receiveShadow = true
  bgGroup.add(extGround)

  return bgGroup
}
