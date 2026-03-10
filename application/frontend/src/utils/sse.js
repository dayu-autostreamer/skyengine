/**
 * SSE (Server-Sent Events) 通信管理
 * 用于实时数据推送和事件流处理
 */

/**
 * SSE 事件管理器类
 */
export class SSEManager {
  constructor() {
    this.eventSources = new Map()
    this.listeners = new Map()
  }

  /**
   * 连接到 SSE 端点
   * @param {string} endpoint - SSE 端点 URL
   * @param {Object} options - 配置选项
   * @param {Array|string} options.eventTypes - 要监听的事件类型（可以是字符串或数组）
   * @param {Object} options.eventHandlers - 事件处理器映射 { eventType: handler }
   * @param {Function} options.onMessage - 默认消息回调（用于所有事件类型）
   * @param {Function} options.onError - 错误回调
   * @param {Function} options.onOpen - 连接打开回调
   * @returns {string} 连接 ID
   */
  connect(endpoint, options = {}) {
    const { eventTypes = ['message'], eventHandlers = {}, onMessage, onError, onOpen } = options
    const connectionId = `${endpoint}_${Date.now()}_${Math.random()}`

    try {
      const eventSource = new EventSource(endpoint)

      eventSource.addEventListener('open', () => {
        console.log(`[SSE] Connected to ${endpoint}`)
        onOpen && onOpen()
      })

      // 支持多种事件类型监听
      const typesToListen = Array.isArray(eventTypes) ? eventTypes : [eventTypes]
      
      typesToListen.forEach(eventType => {
        eventSource.addEventListener(eventType, (event) => {
          try {
            const data = JSON.parse(event.data)
            // 优先使用特定事件处理器，否则使用默认的 onMessage
            const handler = eventHandlers[eventType] || onMessage
            if (handler) {
              handler(data, eventType)
            }
          } catch (e) {
            // 如果解析失败，传递原始数据
            const handler = eventHandlers[eventType] || onMessage
            if (handler) {
              handler(event.data, eventType)
            }
          }
        })
      })

      eventSource.addEventListener('error', (error) => {
        console.error(`[SSE] Error on ${endpoint}:`, error)
        onError && onError(error)
        if (eventSource.readyState === EventSource.CLOSED) {
          this.eventSources.delete(connectionId)
        }
      })

      this.eventSources.set(connectionId, eventSource)
      return connectionId
    } catch (error) {
      console.error(`[SSE] Failed to connect to ${endpoint}:`, error)
      onError && onError(error)
      throw error
    }
  }

  /**
   * 订阅特定事件类型
   * @param {string} endpoint - SSE 端点
   * @param {string} eventType - 事件类型
   * @param {Function} callback - 回调函数
   * @returns {string} 订阅 ID
   */
  subscribe(endpoint, eventType, callback) {
    const subscriptionId = `${endpoint}_${eventType}_${Date.now()}`

    if (!this.listeners.has(endpoint)) {
      this.listeners.set(endpoint, new Map())
    }

    const endpointListeners = this.listeners.get(endpoint)
    if (!endpointListeners.has(eventType)) {
      endpointListeners.set(eventType, [])
    }

    endpointListeners.get(eventType).push({
      id: subscriptionId,
      callback,
    })

    return subscriptionId
  }

  /**
   * 取消订阅
   * @param {string} endpoint - SSE 端点
   * @param {string} eventType - 事件类型
   * @param {string} subscriptionId - 订阅 ID
   */
  unsubscribe(endpoint, eventType, subscriptionId) {
    const endpointListeners = this.listeners.get(endpoint)
    if (!endpointListeners) return

    const listeners = endpointListeners.get(eventType)
    if (!listeners) return

    const index = listeners.findIndex((item) => item.id === subscriptionId)
    if (index > -1) {
      listeners.splice(index, 1)
    }
  }

  /**
   * 断开连接
   * @param {string} connectionId - 连接 ID（可选，不提供则断开所有连接）
   */
  disconnect(connectionId) {
    if (connectionId) {
      const eventSource = this.eventSources.get(connectionId)
      if (eventSource) {
        eventSource.close()
        this.eventSources.delete(connectionId)
      }
    } else {
      this.eventSources.forEach((eventSource) => {
        eventSource.close()
      })
      this.eventSources.clear()
    }
  }

  /**
   * 获取连接状态
   * @param {string} connectionId - 连接 ID
   * @returns {number} 连接状态 (CONNECTING=0, OPEN=1, CLOSED=2)
   */
  getStatus(connectionId) {
    const eventSource = this.eventSources.get(connectionId)
    return eventSource ? eventSource.readyState : -1
  }

  /**
   * 获取所有活动连接
   * @returns {Array} 连接 ID 数组
   */
  getConnections() {
    return Array.from(this.eventSources.keys())
  }
}

// 创建全局 SSE 管理器实例
export const sseManager = new SSEManager()

/**
 * 监控工厂实时数据
 * @param {string} factoryId - 工厂 ID
 * @param {Function} onData - 数据回调
 * @returns {string} 连接 ID
 */
export function monitorFactoryData(factoryId, onData) {
  const endpoint = `/api/factory/${factoryId}/stream`
  return sseManager.connect(endpoint, {
    onMessage: onData,
    onError: (error) => console.error('Factory monitor error:', error),
  })
}
