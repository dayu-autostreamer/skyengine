/**
 * 统一的 API 接口管理
 * 集中管理所有后端 API 路由和请求
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

/**
 * API 路由配置
 */
export const API_ROUTES = {
  // 系统相关
  HEALTH: "/health",
  SCENARIO_STATUS: "/scenario/status",
  ALGO: "/algo",

  // 工厂配置相关 (控制连接)
  FACTORY_CONFIG_UPLOAD: "/factory/config/upload",
  FACTORY_CONTROL_RESET: "/factory/control/reset",
  FACTORY_CONTROL_PLAY: "/factory/control/play",
  FACTORY_CONTROL_PAUSE: "/factory/control/pause",
  FACTORY_CONTROL_SWITCH: "/factory/control/switch",
  FACTORY_CONTROL_DISCONNECT: "/factory/control/disconnect",
  FACTORY_CONTROL_INSERT_JOBS: "/factory/control/insert_jobs",
  FACTORY_EXCEPTION_INJECT: "/factory/exception/inject",
  FACTORY_EXCEPTION_CLEAR: "/factory/exception/clear",

  // 调度算法相关
  FACTORY_ALGORITHM_SET: "/factory/algorithm/set",
  FACTORY_ALGORITHM_GET: "/factory/algorithm/get",

  // SSE 流相关，其中事件不同，不同工厂自行处理
  STREAM_STATE: "/stream/state",
  STREAM_METRICS: "/stream/metrics",
  STREAM_CONTROL: "/stream/control",
  STREAM_EVENTS: "/stream/events",

  // 监控相关
  MONITOR_STATUS: "/monitor/status",
  MONITOR_METRICS: "/monitor/metrics",

  // 数据集相关
  DATASET_LIST: "/dataset/list",
  DATASET_GENERATE: "/dataset/generate",

  // 历史记录
  HISTORY_RUNS: "/history/runs",
  HISTORY_RUN_DETAIL: "/history/run/:run_id",
  HISTORY_RUN_LOGS: "/history/run/:run_id/logs",
  HISTORY_COMPARE: "/history/compare",
  HISTORY_STATS: "/history/stats",
  HISTORY_RUN_COMPLETE: "/history/run/:run_id/complete",

  // 离线分析 — 服务端下载接口（StaticFactory mock 版：POST JSON 回吐带 attachment 头）
  ANALYSIS_EXPORT: "/analysis/export",

  // 离线分析 — Run 持久化仓库（dataset/run/，工厂无关）
  ANALYSIS_RUNS: "/analysis/runs",
  ANALYSIS_RUN_DETAIL: "/analysis/runs/:run_id",

  // 批处理实验 — DockerProxy 专用（实验 compose + run.py）
  // POST /batch/start          body = {experiments: [...], base_env?}
  // POST /batch/cancel
  // GET  /batch/status
  // GET  /batch/stream         SSE: batch_progress/batch_log/batch_metric/batch_done/batch_error
  // POST /batch/upload_instance  multipart: file + kind=fjsp|mapf
  BATCH_START: "/batch/start",
  BATCH_CANCEL: "/batch/cancel",
  BATCH_STATUS: "/batch/status",
  BATCH_STREAM: "/batch/stream",
  BATCH_UPLOAD_INSTANCE: "/batch/upload_instance",
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
 * @param {number} options.timeout - 超时时间（毫秒），默认 10000ms
 * @returns {Promise} 响应数据
 */
async function request(route, options = {}) {
  const {
    method = "GET",
    body = null,
    params = {},
    headers = {},
    timeout = 10000, // 默认 10 秒超时
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

  // 创建超时控制器
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  config.signal = controller.signal;

  try {
    const response = await fetch(url, config);
    clearTimeout(timeoutId);

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
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      const timeoutError = new Error(`请求超时 (${timeout}ms)`);
      timeoutError.isTimeout = true;
      throw timeoutError;
    }
    throw error;
  }
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
