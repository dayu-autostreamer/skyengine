

// 我说的"更换数据源" — 是打算接入 SSE 形式.
import { sseManager } from '../utils/sse.js';
import { API_ROUTES, getApiUrl } from '../utils/api.js';
import { apiPost } from '../utils/api.js';

/**
 * 后端系统测试 - 通过 SSE 与后端交互
 * @param {Object} factoryStore - 工厂状态 Store
 * @param {Object} monitorStore - 监控 Store
 * @param {Object} data - 配置数据 { algorithm }
 * @param {Function} onFinish - 完成回调
 * @returns {Function} 清理函数，用于停止测试和断开 SSE 连接
 */
export async function backendSystemTest(factoryStore, monitorStore, data, onFinish) {
    // 保存 SSE 连接 ID
    let connectionId = null;

    // 清理函数 - 断开 SSE 连接
    const cleanup = () => {
        if (connectionId) {
            console.log('[backendSystemTest] 断开 SSE 连接:', connectionId);
            sseManager.disconnect(connectionId);
            connectionId = null;
        }
        factoryStore.isPlaying = false;
    };

    // 后端发送请求,构造数据 - 必须顺序执行，避免竞态条件
    try {
        // 1. 设定策略
        console.log("[backendSystemTest] Step 1: 设定策略...", data);
        await apiPost(API_ROUTES.FACTORY_ALGORITHM_SET, data, { timeout: 15000 });
        console.log("[backendSystemTest] 策略设定完成");

        // 2. 重置环境
        console.log("[backendSystemTest] Step 2: 重置环境...");
        await apiPost(API_ROUTES.FACTORY_CONTROL_RESET, null, { timeout: 15000 });
        console.log("[backendSystemTest] 环境RESET完成");

        // 3. 启动仿真
        console.log("[backendSystemTest] Step 3: 启动仿真...");
        await apiPost(API_ROUTES.FACTORY_CONTROL_PLAY, null, { timeout: 15000 });
        console.log("[backendSystemTest] 仿真启动完成");
    } catch (error) {
        console.error("[backendSystemTest] API调用失败:", error);
        cleanup();
        if (onFinish) onFinish();
        return cleanup;
    }
    // 通过SSE监听数据流，更新store

    // 1. 初始化
    factoryStore.reset();
    monitorStore.clear();
    factoryStore.isPlaying = true; // 开启播放状态，让 Store 知道我们在进行实时更新

    let cnt = 0;

    // 通过SSE获得agvFrame和machineFrame
    const stateUrl = getApiUrl(API_ROUTES.STREAM_STATE);
    connectionId = sseManager.connect(stateUrl, {
        eventTypes: ['state'],  // 监听的事件类型
        eventHandlers: {
            // 处理快照事件 - 添加到缓冲队列

            state: (data) => {
                console.log('[SSE] Received state:', data);


                // 检查是否是有效状态（不是 idle/no_factory/error）
                if (data.status === 'idle' || data.status === 'no_factory' || data.status === 'error') {
                    console.log('[SSE] 跳过无效状态:', data.status);
                    cnt += 1;
                    return;
                }
                // 检查是否完成
                if (cnt >= 5 || data.status === 'finished' || data.status === 'stopped') {
                    // 运行完成，断开连接
                    console.log('[backendSystemTest] 仿真完成');
                    cleanup();
                    if (onFinish) onFinish();
                    return;
                }
                // 添加到缓冲队列（带去重）
                factoryStore.pushSnapshot(data.frame);

            },
        },

        onError: (error) => {
            console.error('SSE error:', error);
            cleanup();
            if (onFinish) onFinish();
        }
    });

    // 返回清理函数，供外部调用
    return cleanup;
}
