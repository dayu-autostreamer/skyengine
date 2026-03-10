/**
 * Factory Animation Composable
 * 处理 SSE 通信、Game Loop 和平滑动画
 */

import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

export function useFactoryAnimation(apiUrl = '/api/stream-state') {
  // ============ 状态管理 ============
  
  // 逻辑状态：来自后端的实际数据（整数坐标）
  const logicalState = ref({
    grid_state: {
      positions_xy: [],
      finishes_xy: [],
      is_active: []
    },
    machines: [],
    active_transfers: [],
    env_timeline: 0
  });

  // 渲染状态：用于绘制的插值坐标（浮点数）
  const renderState = ref({
    agvPositions: [], // 插值后的 AGV 位置
    machineBreathings: {}, // 机器呼吸效果的透明度/缩放
  });

  // 动画配置
  const animationConfig = {
    lerpFactor: 0.1, // 插值因子（0-1），越小越平滑
    breathingSpeed: 0.05, // 呼吸效果速度
    breathingAmplitude: 0.15 // 呼吸振幅（±15%）
  };

  // ============ 帧计数与时间跟踪 ============
  let frameCount = 0;
  let lastFrameTime = 0;
  let eventSource = null;
  let animationFrameId = null;

  // ============ Lerp 函数 ============
  /**
   * 线性插值
   * @param {number} current - 当前值
   * @param {number} target - 目标值
   * @param {number} factor - 插值因子 (0-1)
   * @returns {number} 插值后的值
   */
  function lerp(current, target, factor) {
    return current + (target - current) * factor;
  }

  /**
   * 二维点插值
   */
  function lerpPoint(currentPoint, targetPoint, factor) {
    if (!currentPoint || !targetPoint) return targetPoint;
    return [
      lerp(currentPoint[0], targetPoint[0], factor),
      lerp(currentPoint[1], targetPoint[1], factor)
    ];
  }

  // SSE 连接状态
  let sseConnected = false;
  let sseConnectionAttempts = 0;
  const maxSSERetries = 3;

  // ============ SSE 通信 ============
  /**
   * 建立 SSE 连接并监听实时数据
   */
  function initializeSSE() {
    // 如果已经尝试过多次，不再尝试
    if (sseConnectionAttempts >= maxSSERetries) {
      console.warn(`SSE connection failed after ${maxSSERetries} attempts. Falling back to manual update mode.`);
      sseConnected = false;
      return;
    }

    try {
      sseConnectionAttempts++;
      console.log(`[SSE] Attempting connection... (attempt ${sseConnectionAttempts}/${maxSSERetries})`);
      
      eventSource = new EventSource(apiUrl);

      eventSource.onopen = () => {
        console.log('[SSE] ✓ Connection established successfully');
        sseConnected = true;
        sseConnectionAttempts = 0; // 重置重试计数
      };

      eventSource.onmessage = (event) => {
        try {
          const newLogicalState = JSON.parse(event.data);
          updateLogicalState(newLogicalState);
        } catch (error) {
          console.error('[SSE] Failed to parse message:', error);
        }
      };

      eventSource.onerror = (error) => {
        sseConnected = false;
        
        if (eventSource.readyState === EventSource.CLOSED) {
          console.warn('[SSE] ✗ Connection closed');
          eventSource = null;
          
          // 自动重试（仅在重试次数未超限时）
          if (sseConnectionAttempts < maxSSERetries) {
            console.log(`[SSE] Retrying in 3 seconds...`);
            setTimeout(() => {
              initializeSSE();
            }, 3000);
          }
        } else if (eventSource.readyState === EventSource.CONNECTING) {
          console.warn('[SSE] ✗ Connection failed, trying to reconnect...');
        }
      };

    } catch (error) {
      sseConnected = false;
      console.warn(`[SSE] ✗ Failed to initialize: ${error.message}`);
      console.warn('[SSE] → Falling back to manual update mode');
      console.warn(`[SSE] → Make sure the server endpoint is available at: ${apiUrl}`);
    }
  }

  /**
   * 获取 SSE 连接状态
   */
  function isSSEConnected() {
    return sseConnected;
  }

  /**
   * 更新逻辑状态
   */
  function updateLogicalState(newState) {
    logicalState.value = {
      grid_state: newState.grid_state || logicalState.value.grid_state,
      machines: newState.machines || logicalState.value.machines,
      active_transfers: newState.active_transfers || logicalState.value.active_transfers,
      env_timeline: newState.env_timeline ?? logicalState.value.env_timeline
    };

    // 初始化或更新 AGV 渲染位置
    const positions = logicalState.value.grid_state.positions_xy || [];
    if (renderState.value.agvPositions.length === 0) {
      // 首次初始化，直接设置位置
      renderState.value.agvPositions = positions.map(pos => [...pos]);
    } else if (positions.length > renderState.value.agvPositions.length) {
      // 如果 AGV 数量增加，添加新的位置
      for (let i = renderState.value.agvPositions.length; i < positions.length; i++) {
        renderState.value.agvPositions.push([...positions[i]]);
      }
    }
  }

  // ============ 游戏循环与动画更新 ============
  /**
   * 更新渲染状态（平滑插值）
   */
  function updateRenderState(deltaTime) {
    const { lerpFactor, breathingSpeed } = animationConfig;
    const positions = logicalState.value.grid_state.positions_xy || [];

    // 更新 AGV 位置插值
    if (renderState.value.agvPositions.length === 0) {
      renderState.value.agvPositions = positions.map(pos => [...pos]);
    }

    // 对每个 AGV 进行 Lerp 插值
    positions.forEach((targetPos, index) => {
      if (index < renderState.value.agvPositions.length) {
        renderState.value.agvPositions[index] = lerpPoint(
          renderState.value.agvPositions[index],
          targetPos,
          lerpFactor
        );
      } else {
        renderState.value.agvPositions.push([...targetPos]);
      }
    });

    // 更新机器呼吸效果
    const machines = logicalState.value.machines || [];
    const machineList = Array.isArray(machines) ? machines : Object.values(machines);

    if (!renderState.value.machineBreathings) {
      renderState.value.machineBreathings = {};
    }

    machineList.forEach((machine, index) => {
      const machineId = machine.id || index;
      if (!renderState.value.machineBreathings[machineId]) {
        renderState.value.machineBreathings[machineId] = 0;
      }

      // 如果机器处于 WORKING 状态，计算呼吸效果
      if (machine.status === 'WORKING') {
        // 使用正弦波产生呼吸效果
        renderState.value.machineBreathings[machineId] = 
          Math.sin(frameCount * breathingSpeed) * animationConfig.breathingAmplitude;
      } else {
        // 缓慢回归到 0
        renderState.value.machineBreathings[machineId] *= 0.9;
      }
    });

    frameCount++;
  }

  /**
   * 游戏循环主函数
   */
  function gameLoop(timestamp) {
    const deltaTime = timestamp - lastFrameTime;
    lastFrameTime = timestamp;

    // 更新渲染状态
    updateRenderState(deltaTime);

    // 继续请求下一帧
    animationFrameId = requestAnimationFrame(gameLoop);
  }

  /**
   * 启动游戏循环
   */
  function startGameLoop() {
    lastFrameTime = performance.now();
    animationFrameId = requestAnimationFrame(gameLoop);
  }

  /**
   * 停止游戏循环
   */
  function stopGameLoop() {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }
  }

  // ============ 清理资源 ============
  function closeSSE() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  // ============ 导出接口 ============
  return {
    // 状态
    logicalState,
    renderState,
    animationConfig,

    // 方法
    initializeSSE,
    updateLogicalState,
    startGameLoop,
    stopGameLoop,
    closeSSE,
    isSSEConnected,

    // 工具函数
    lerp,
    lerpPoint
  };
}
