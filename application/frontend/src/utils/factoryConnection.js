/**
 * 工厂多连接管理器 工厂mounted时创建连接 ，unmounted时断开连接
 * 用于管理工厂的多个 SSE 连接（控制、状态、指标）
 */

import { sseManager } from "./sse";
import { apiGet, apiPost, API_ROUTES, getApiUrl } from "./api";

export class FactoryConnectionManager {
  constructor(factoryId) {
    this.factoryId = factoryId;
    this.connections = {
      control: null, // 控制连接
      state: null, // 状态连接
      metrics: null, // 指标连接
    };
    this.handlers = {
      onStateUpdate: null,
      onMetricsUpdate: null,
      onControlError: null,
    };
    this.eventConfig = {
      state: ['message'], // 默认监听 message 事件
      metrics: ['message'],
      control: ['message'],
    };
    this.eventHandlers = {
      state: {},   // 状态流的事件处理器映射
      metrics: {}, // 指标流的事件处理器映射
      control: {}, // 控制流的事件处理器映射
    };
    this.isScenarioConnected = false;
    console.log(`[Factory] 创建工厂连接管理器, 工厂ID: ${factoryId}`);
  }

  /**
   * 初始化所有连接
   * @param {Object} handlers - 事件处理器
   * @param {Function} handlers.onStateUpdate - 状态更新回调（通用）
   * @param {Function} handlers.onMetricsUpdate - 指标更新回调（通用）
   * @param {Function} handlers.onControlError - 控制错误回调
   * @param {Object} eventTypes - 可选：自定义要监听的事件类型
   * @param {Array} eventTypes.state - 状态流监听的事件类型
   * @param {Array} eventTypes.metrics - 指标流监听的事件类型
   * @param {Array} eventTypes.control - 控制流监听的事件类型
   * @param {Object} eventHandlers - 可选：为特定事件类型指定专属处理器
   * @param {Object} eventHandlers.state - 状态流事件处理器 { eventType: handler }
   * @param {Object} eventHandlers.metrics - 指标流事件处理器 { eventType: handler }
   * @param {Object} eventHandlers.control - 控制流事件处理器 { eventType: handler }
   */
  async init(handlers = {}, eventTypes = null, eventHandlers = null) {
    this.handlers = { ...this.handlers, ...handlers };

    // 如果提供了自定义事件类型，使用它们
    if (eventTypes) {
      if (eventTypes.state) this.eventConfig.state = eventTypes.state;
      if (eventTypes.metrics) this.eventConfig.metrics = eventTypes.metrics;
      if (eventTypes.control) this.eventConfig.control = eventTypes.control;
    }

    // 如果提供了自定义事件处理器，使用它们
    if (eventHandlers) {
      if (eventHandlers.state) this.eventHandlers.state = eventHandlers.state;
      if (eventHandlers.metrics) this.eventHandlers.metrics = eventHandlers.metrics;
      if (eventHandlers.control) this.eventHandlers.control = eventHandlers.control;
    }

    try {
      // 检查是否连接到真实场景
      const scenarioStatus = await this.checkScenarioConnection();
      this.isScenarioConnected = scenarioStatus;

      console.log(`[Factory] 工厂 ${this.factoryId} 初始化`);
      console.log(
        `[Factory] 真实场景连接状态: ${this.isScenarioConnected ? "已连接" : "未连接"}`,
      );

      // 建立状态连接
      this.connectState();

      // 如果连接到真实场景，建立控制和指标连接
      if (this.isScenarioConnected) {
        this.connectControl();
        this.connectMetrics();
      }
    } catch (error) {
      console.error("[Factory] 初始化失败:", error);
      if (this.handlers.onControlError) {
        this.handlers.onControlError(error);
      }
    }
  }

  /**
   * 检查是否连接到真实场景
   */
  async checkScenarioConnection() {
    try {
      const response = await apiGet(API_ROUTES.SCENARIO_STATUS);
      return response?.connected || false;
    } catch (error) {
      console.warn("[Factory] 场景连接检查失败:", error);
      return false;
    }
  }

  /**
   * 连接到控制流
   * 用于: 上传配置、发送控制命令（播放、重置）、传送状态
   */
  connectControl() {
    if (!this.isScenarioConnected) {
      console.warn("[Factory] 未连接到真实场景，不建立控制连接");
      return;
    }

    const endpoint = getApiUrl(API_ROUTES.STREAM_CONTROL);
    const eventTypes = this.eventConfig.control;
    const eventHandlers = this.eventHandlers.control;

    this.connections.control = sseManager.connect(endpoint, {
      eventTypes,
      eventHandlers, // 传入专属事件处理器
      onMessage: (data, eventType) => {
        const message = typeof data === "string" ? JSON.parse(data) : data;
        console.log(`[Control-Stream][${eventType}]`, message);
        // 如果没有专属处理器，这里会被调用
      },
      onError: (error) => {
        console.error("[Control-Stream] 错误:", error);
        if (this.handlers.onControlError) {
          this.handlers.onControlError(error);
        }
      },
    });
    console.log(`[Factory] 控制连接已建立 (事件: ${eventTypes.join(', ')})`);
  }

  /**
   * 连接到状态流
   * 用于: 传输实时状态数据（AGV位置、机器状态等）
   */
  connectState() {
    const endpoint = getApiUrl(API_ROUTES.STREAM_STATE);
    const eventTypes = this.eventConfig.state;
    const eventHandlers = this.eventHandlers.state;

    this.connections.state = sseManager.connect(endpoint, {
      eventTypes,
      eventHandlers, // 传入专属事件处理器
      onMessage: (data, eventType) => {
        const message = typeof data === "string" ? JSON.parse(data) : data;
        console.log(`[State-Stream][${eventType}]`, message);
        // 如果有通用处理器且该事件没有专属处理器，调用通用处理器
        if (this.handlers.onStateUpdate) {
          this.handlers.onStateUpdate(message, eventType);
        }
      },
      onError: (error) => {
        console.error("[State-Stream] 错误:", error);
      },
    });
    console.log(`[Factory] 状态连接已建立 (事件: ${eventTypes.join(', ')})`);
  }

  /**
   * 连接到指标流
   * 用于: 传输后端记录的指标数据（效率、吞吐量等）
   */
  connectMetrics() {
    if (!this.isScenarioConnected) {
      console.warn("[Factory] 未连接到真实场景，不建立指标连接");
      return;
    }

    const endpoint = getApiUrl(API_ROUTES.STREAM_METRICS);
    const eventTypes = this.eventConfig.metrics;
    const eventHandlers = this.eventHandlers.metrics;

    this.connections.metrics = sseManager.connect(endpoint, {
      eventTypes,
      eventHandlers, // 传入专属事件处理器
      onMessage: (data, eventType) => {
        const message = typeof data === "string" ? JSON.parse(data) : data;
        console.log(`[Metrics-Stream][${eventType}]`, message);
        // 如果有通用处理器且该事件没有专属处理器，调用通用处理器
        if (this.handlers.onMetricsUpdate) {
          this.handlers.onMetricsUpdate(message, eventType);
        }
      },
      onError: (error) => {
        console.error("[Metrics-Stream] 错误:", error);
      },
    });
    console.log(`[Factory] 指标连接已建立 (事件: ${eventTypes.join(', ')})`);
  }

  /**
   * 执行控制命令（仅在连接真实场景时有效）
   */
  async executeControl(command, data = {}) {
    if (!this.isScenarioConnected) {
      throw new Error("未连接到真实场景，无法执行控制命令");
    }

    try {
      let route;
      switch (command) {
        case "play":
          route = API_ROUTES.FACTORY_CONTROL_PLAY;
          break;
        case "reset":
          route = API_ROUTES.FACTORY_CONTROL_RESET;
          break;
        default:
          throw new Error(`未知的控制命令: ${command}`);
      }

      const response = await apiPost(route, data, {
        params: { id: this.factoryId },
      });
      console.log(`[Factory] 控制命令 '${command}' 已发送`, response);
      return response;
    } catch (error) {
      console.error(`[Factory] 控制命令失败:`, error);
      throw error;
    }
  }

  /**
   * 发送状态更新到后端
   */
  async sendState(stateData) {
    try {
      const response = await apiPost(
        API_ROUTES.FACTORY_CONTROL_STATE,
        stateData,
        {
          params: { id: this.factoryId },
        },
      );
      return response;
    } catch (error) {
      console.error("[Factory] 状态发送失败:", error);
      throw error;
    }
  }

  /**
   * 断开所有连接
   */
  disconnect() {
    Object.values(this.connections).forEach((connectionId) => {
      if (connectionId) {
        sseManager.disconnect(connectionId);
      }
    });
    this.connections = {
      control: null,
      state: null,
      metrics: null,
    };
    console.log(`[Factory] 工厂 ${this.factoryId} 所有连接已断开`);
  }

  /**
   * 获取连接状态
   */
  getStatus() {
    return {
      control: this.connections.control ? "已连接" : "未连接",
      state: this.connections.state ? "已连接" : "未连接",
      metrics: this.connections.metrics ? "已连接" : "未连接",
      scenario: this.isScenarioConnected ? "已连接" : "未连接",
    };
  }
}

/**
 * 创建工厂连接管理器实例
 * @param {string} factoryId - 工厂ID
 */
export function createFactoryConnectionManager(factoryId) {
  return new FactoryConnectionManager(factoryId);
}
