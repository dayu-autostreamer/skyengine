/**
 * 统一的 API 接口管理
 * 集中管理所有后端 API 路由和请求
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * API 路由配置
 */
export const API_ROUTES = {
  // 系统相关
  HEALTH: "/health",
  SCENARIO_STATUS: "/scenario/status",

  // 工厂配置相关 (控制连接)
  FACTORY_CONFIG_UPLOAD: "/factory/config/upload",
  FACTORY_CONTROL_RESET: "/factory/control/reset",
  FACTORY_CONTROL_PLAY: "/factory/control/play",
  FACTORY_CONTROL_SWITCH: "/factory/control/switch",

  // SSE 流相关，其中事件不同，不同工厂自行处理
  STREAM_STATE: "/stream/state",
  STREAM_METRICS: "/stream/metrics",
  STREAM_CONTROL: "/stream/control",

  // 监控相关
  MONITOR_STATUS: "/monitor/status",
  MONITOR_METRICS: "/monitor/metrics",
};

/**
 * 获取完整的 API URL
 * @param {string} route - API 路由
 * @param {Object} params - 路由参数替换
 * @returns {string} 完整的 API URL
 */
export function getApiUrl(route, params = {}) {
  let url = route;
  Object.keys(params).forEach((key) => {
    url = url.replace(`:${key}`, params[key]);
  });
  return `${API_BASE_URL}${url}`;
}

/**
 * 通用 HTTP 请求方法
 * @param {string} route - API 路由
 * @param {Object} options - 请求选项
 * @returns {Promise} 响应数据
 */
async function request(route, options = {}) {
  const {
    method = "GET",
    body = null,
    params = {},
    headers = {},
    ...otherOptions
  } = options;

  const url = getApiUrl(route, params);
  const config = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    ...otherOptions,
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = new Error(`HTTP Error: ${response.status}`);
    error.status = response.status;
    throw error;
  }

  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

/**
 * GET 请求
 */
export async function apiGet(route, options = {}) {
  return request(route, { ...options, method: "GET" });
}

/**
 * POST 请求
 */
export async function apiPost(route, body, options = {}) {
  return request(route, { ...options, method: "POST", body });
}

/**
 * PUT 请求
 */
export async function apiPut(route, body, options = {}) {
  return request(route, { ...options, method: "PUT", body });
}

/**
 * DELETE 请求
 */
export async function apiDelete(route, options = {}) {
  return request(route, { ...options, method: "DELETE" });
}

/**
 * PATCH 请求
 */
export async function apiPatch(route, body, options = {}) {
  return request(route, { ...options, method: "PATCH", body });
}
