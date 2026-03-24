/**
 * 工厂拓扑配置验证器
 * 用于验证上传的配置文件是否符合规范
 */

/**
 * 验证 AGV 对象
 */
function validateAGV(agv) {
  if (!agv || typeof agv !== 'object') {
    throw new Error('AGV must be an object')
  }
  
  if (typeof agv.id !== 'number') {
    throw new Error('AGV must have a numeric id')
  }
  
  if (!agv.name || typeof agv.name !== 'string') {
    throw new Error(`AGV ${agv.id}: must have a name`)
  }
  
  if (!Array.isArray(agv.initialLocation) || agv.initialLocation.length !== 2) {
    throw new Error(`AGV ${agv.id}: initialLocation must be [x, y]`)
  }
  
  const [x, y] = agv.initialLocation
  if (typeof x !== 'number' || typeof y !== 'number') {
    throw new Error(`AGV ${agv.id}: coordinates must be numbers`)
  }
  
  if (agv.velocity !== undefined && typeof agv.velocity !== 'number') {
    throw new Error(`AGV ${agv.id}: velocity must be a number`)
  }
  
  if (agv.capacity !== undefined && typeof agv.capacity !== 'number') {
    throw new Error(`AGV ${agv.id}: capacity must be a number`)
  }
  
  const validStatuses = ['IDLE', 'WORKING', 'LOADING', 'UNLOADING', 'BROKEN', 'MAINTENANCE']
  if (agv.status && !validStatuses.includes(agv.status)) {
    throw new Error(`AGV ${agv.id}: status must be one of ${validStatuses.join(', ')}`)
  }
  
  return true
}

/**
 * 验证 Waypoint 对象
 */
function validateWaypoint(wp) {
  if (!wp || typeof wp !== 'object') {
    throw new Error('Waypoint must be an object')
  }
  
  if (!Array.isArray(wp.location) || wp.location.length !== 2) {
    throw new Error('Waypoint location must be [x, y]')
  }
  
  const [x, y] = wp.location
  if (typeof x !== 'number' || typeof y !== 'number') {
    throw new Error('Waypoint coordinates must be numbers')
  }
  
  if (!['dock', 'route'].includes(wp.type)) {
    throw new Error(`Waypoint type must be 'dock' or 'route', got: ${wp.type}`)
  }
  
  if (!wp.name || typeof wp.name !== 'string') {
    throw new Error('Waypoint must have a name')
  }
  
  return true
}

/**
 * 验证 Machine 对象
 */
function validateMachine(machine) {
  if (!machine || typeof machine !== 'object') {
    throw new Error('Machine must be an object')
  }
  
  if (!machine.id || typeof machine.id !== 'string') {
    throw new Error('Machine must have an id')
  }
  
  if (!machine.name || typeof machine.name !== 'string') {
    throw new Error('Machine must have a name')
  }
  
  if (!Array.isArray(machine.location) || machine.location.length !== 2) {
    throw new Error(`Machine ${machine.id}: location must be [x, y]`)
  }
  
  const [x, y] = machine.location
  if (typeof x !== 'number' || typeof y !== 'number') {
    throw new Error(`Machine ${machine.id}: coordinates must be numbers`)
  }
  
  if (!Array.isArray(machine.size) || machine.size.length !== 2) {
    throw new Error(`Machine ${machine.id}: size must be [width, height]`)
  }
  
  const [w, h] = machine.size
  if (typeof w !== 'number' || typeof h !== 'number' || w <= 0 || h <= 0) {
    throw new Error(`Machine ${machine.id}: size must be positive numbers`)
  }
  
  const validStatuses = ['WORKING', 'IDLE', 'BROKEN', 'MAINTENANCE']
  if (!validStatuses.includes(machine.status)) {
    throw new Error(`Machine ${machine.id}: status must be one of ${validStatuses.join(', ')}`)
  }
  
  return true
}

/**
 * 验证 Zone 对象
 */
function validateZone(zone) {
  if (!zone || typeof zone !== 'object') {
    throw new Error('Zone must be an object')
  }
  
  if (!zone.id || typeof zone.id !== 'string') {
    throw new Error('Zone must have an id')
  }
  
  if (!zone.name || typeof zone.name !== 'string') {
    throw new Error('Zone must have a name')
  }
  
  if (!zone.area || typeof zone.area !== 'object') {
    throw new Error(`Zone ${zone.id}: must have area object`)
  }
  
  const { x, y, w, h } = zone.area
  if (typeof x !== 'number' || typeof y !== 'number') {
    throw new Error(`Zone ${zone.id}: area x,y must be numbers`)
  }
  
  if (typeof w !== 'number' || typeof h !== 'number' || w <= 0 || h <= 0) {
    throw new Error(`Zone ${zone.id}: area w,h must be positive numbers`)
  }
  
  const validTypes = ['restricted', 'workbench', 'obstacle', 'workarea']
  if (!validTypes.includes(zone.type)) {
    throw new Error(`Zone ${zone.id}: type must be one of ${validTypes.join(', ')}`)
  }
  
  if (!zone.color || typeof zone.color !== 'string') {
    throw new Error(`Zone ${zone.id}: must have color (CSS color string)`)
  }
  
  return true
}

/**
 * 验证完整的 Topology 配置
 */
export function validateTopologyConfig(topology) {
  if (!topology || typeof topology !== 'object') {
    throw new Error('Topology must be an object')
  }
  
  // 验证 zones
  if (!Array.isArray(topology.zones)) {
    throw new Error('Topology zones must be an array')
  }
  
  topology.zones.forEach((zone, idx) => {
    try {
      validateZone(zone)
    } catch (error) {
      throw new Error(`Zone[${idx}]: ${error.message}`)
    }
  })
  
  // 验证 machines
  if (!topology.machines || typeof topology.machines !== 'object') {
    throw new Error('Topology machines must be an object')
  }
  
  Object.entries(topology.machines).forEach(([key, machine]) => {
    try {
      validateMachine(machine)
    } catch (error) {
      throw new Error(`Machine "${key}": ${error.message}`)
    }
  })
  
  // 验证 waypoints
  if (!topology.waypoints || typeof topology.waypoints !== 'object') {
    throw new Error('Topology waypoints must be an object')
  }
  
  Object.entries(topology.waypoints).forEach(([key, wp]) => {
    try {
      validateWaypoint(wp)
    } catch (error) {
      throw new Error(`Waypoint "${key}": ${error.message}`)
    }
  })
  
  return true
}

/**
 * 验证完整的工厂配置文件
 */
export function validateFactoryConfig(config) {
  if (!config || typeof config !== 'object') {
    throw new Error('Config must be an object')
  }
  
  // 必需字段
  if (!config.id || typeof config.id !== 'string') {
    throw new Error('Config must have an id (string)')
  }
  
  if (!config.name || typeof config.name !== 'string') {
    throw new Error('Config must have a name (string)')
  }
  
  // 验证 topology
  if (!config.topology) {
    throw new Error('Config must have topology')
  }
  
  validateTopologyConfig(config.topology)
  
  // 可选字段验证
  if (config.version && typeof config.version !== 'string') {
    throw new Error('Version must be a string if provided')
  }
  
  if (config.description && typeof config.description !== 'string') {
    throw new Error('Description must be a string if provided')
  }
  
  // renderConfig 是可选的，但如果提供必须是对象
  if (config.renderConfig && typeof config.renderConfig !== 'object') {
    throw new Error('renderConfig must be an object if provided')
  }
    // 验证 AGVs（可选）
  if (config.agvs) {
    if (!Array.isArray(config.agvs)) {
      throw new Error('AGVs must be an array')
    }
    
    config.agvs.forEach((agv, idx) => {
      try {
        validateAGV(agv)
      } catch (error) {
        throw new Error(`AGV[${idx}]: ${error.message}`)
      }
    })
  }
    return true
}

/**
 * 规范化配置 (填充默认值)
 */
export function normalizeConfig(config) {
  return {
    id: config.id,
    name: config.name,
    version: config.version || '1.0.0',
    createdAt: config.createdAt || new Date().toISOString().split('T')[0],
    description: config.description || '',

    topology: {
      zones: config.topology?.zones || [],
      machines: config.topology?.machines || {},
      waypoints: config.topology?.waypoints || {},
      gridWidth: config.topology?.gridWidth || 20,
      gridHeight: config.topology?.gridHeight || 14
    },

    agvs: (config.agvs || []).map(agv => ({
      id: agv.id,
      name: agv.name || `AGV-${agv.id}`,
      initialLocation: agv.initialLocation || [0, 0],
      velocity: agv.velocity || 1.0,
      capacity: agv.capacity || 100,
      status: agv.status || 'IDLE'
    })),

    // 保留 jobs 配置
    jobs: config.jobs || { job_list: [] },

    renderConfig: {
      baseGridSize: config.renderConfig?.baseGridSize || 40,
      gridWidth: config.renderConfig?.gridWidth || config.topology?.gridWidth || 20,
      gridHeight: config.renderConfig?.gridHeight || config.topology?.gridHeight || 14,
      colors: {
        background: '#ECEFF1',
        grid: '#CFD8DC',
        dock: '#1565C0',
        route: '#4CAF50',
        agv: '#FF5722',
        machine_working: '#42A5F5',
        machine_idle: '#A5D6A7',
        ...config.renderConfig?.colors
      }
    }
  }
}

/**
 * 一体化验证 & 规范化
 */
export function validateAndNormalizeConfig(config) {
  validateFactoryConfig(config)
  return normalizeConfig(config)
}

/**
 * 从 JSON 字符串加载配置
 */
export function loadConfigFromJSON(jsonString) {
  try {
    const config = JSON.parse(jsonString)
    validateAndNormalizeConfig(config)
    return config
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error(`JSON 格式错误: ${error.message}`)
    }
    throw error
  }
}

export default {
  validateTopologyConfig,
  validateFactoryConfig,
  normalizeConfig,
  validateAndNormalizeConfig,
  loadConfigFromJSON
}
