// src/scenarios/fullSystemTest.js

/**
 * 模拟完整的系统运行剧本
 * 分离的数据结构：AGV、机器、指标、事件等各自独立
 */

// ============ 1. AGV 运动轨迹 ============
const AGV_TRAJECTORIES = [
    // --- 起始点 (5, 2) ---
    { step: 0, agvs: [{ x: 5, y: 2, active: true }] },

    // --- 移动到 (5, 11) ---
    { step: 1, agvs: [{ x: 5, y: 3, active: true }] },
    { step: 2, agvs: [{ x: 5, y: 4, active: true }] },
    { step: 3, agvs: [{ x: 5, y: 5, active: true }] },
    { step: 4, agvs: [{ x: 5, y: 6, active: true }] },
    { step: 5, agvs: [{ x: 5, y: 7, active: true }] },
    { step: 6, agvs: [{ x: 5, y: 8, active: true }] },
    { step: 7, agvs: [{ x: 5, y: 9, active: true }] },
    { step: 8, agvs: [{ x: 5, y: 10, active: true }] },
    { step: 9, agvs: [{ x: 5, y: 11, active: true }] },

    // --- 移动到 (8, 11) ---
    { step: 10, agvs: [{ x: 6, y: 11, active: true }] },
    { step: 11, agvs: [{ x: 7, y: 11, active: true }] },
    { step: 12, agvs: [{ x: 8, y: 11, active: true }] },

    // --- 移动到 (8, 9) ---
    { step: 13, agvs: [{ x: 8, y: 10, active: true }] },
    { step: 14, agvs: [{ x: 8, y: 9, active: true }] },

    // --- 移动到 (8, 6) ---
    { step: 15, agvs: [{ x: 8, y: 8, active: true }] },
    { step: 16, agvs: [{ x: 8, y: 7, active: true }] },
    { step: 17, agvs: [{ x: 8, y: 6, active: true }] },

    // --- 移动到 (8, 4) ---
    { step: 18, agvs: [{ x: 8, y: 5, active: true }] },
    { step: 19, agvs: [{ x: 8, y: 4, active: true }] },

    // --- 移动到 (10, 4) ---
    { step: 20, agvs: [{ x: 9, y: 4, active: true }] },
    { step: 21, agvs: [{ x: 10, y: 4, active: true }] },

    // --- 移动到 (14, 4) ---
    { step: 22, agvs: [{ x: 11, y: 4, active: true }] },
    { step: 23, agvs: [{ x: 12, y: 4, active: true }] },
    { step: 24, agvs: [{ x: 13, y: 4, active: true }] },
    { step: 25, agvs: [{ x: 14, y: 4, active: true }] },

    // --- 移动到 (16, 4) ---
    { step: 26, agvs: [{ x: 15, y: 4, active: true }] },
    { step: 27, agvs: [{ x: 16, y: 4, active: true }] },

    // --- 掉头返回到 (14, 4) ---
    { step: 28, agvs: [{ x: 15, y: 4, active: true }] },
    { step: 29, agvs: [{ x: 14, y: 4, active: true }] },

    // --- 移动到 (14, 6) ---
    { step: 30, agvs: [{ x: 14, y: 5, active: true }] },
    { step: 31, agvs: [{ x: 14, y: 6, active: true }] },

    // --- 移动到 (14, 9) ---
    { step: 32, agvs: [{ x: 14, y: 7, active: true }] },
    { step: 33, agvs: [{ x: 14, y: 8, active: true }] },
    { step: 34, agvs: [{ x: 14, y: 9, active: true }] },

    // --- 移动到 (14, 11) ---
    { step: 35, agvs: [{ x: 14, y: 10, active: true }] },
    { step: 36, agvs: [{ x: 14, y: 11, active: true }] },

    // --- 移动到 (8, 11) ---
    { step: 37, agvs: [{ x: 13, y: 11, active: true }] },
    { step: 38, agvs: [{ x: 12, y: 11, active: true }] },
    { step: 39, agvs: [{ x: 11, y: 11, active: true }] },
    { step: 40, agvs: [{ x: 10, y: 11, active: true }] },
    { step: 41, agvs: [{ x: 9, y: 11, active: true }] },
    { step: 42, agvs: [{ x: 8, y: 11, active: true }] },

    // --- 移动到 (5, 11) ---
    { step: 43, agvs: [{ x: 7, y: 11, active: true }] },
    { step: 44, agvs: [{ x: 6, y: 11, active: true }] },
    { step: 45, agvs: [{ x: 5, y: 11, active: true }] },

    // --- 返回起点 (5, 2) ---
    { step: 46, agvs: [{ x: 5, y: 10, active: true }] },
    { step: 47, agvs: [{ x: 5, y: 9, active: true }] },
    { step: 48, agvs: [{ x: 5, y: 8, active: true }] },
    { step: 49, agvs: [{ x: 5, y: 7, active: true }] },
    { step: 50, agvs: [{ x: 5, y: 6, active: true }] },
    { step: 51, agvs: [{ x: 5, y: 5, active: true }] },
    { step: 52, agvs: [{ x: 5, y: 4, active: true }] },
    { step: 53, agvs: [{ x: 5, y: 3, active: true }] },
    { step: 54, agvs: [{ x: 5, y: 2, active: true }] }
];

// ============ 2. 机器状态变化 (自动生成 0-54 步) ============
const MACHINE_STATES = Array.from({ length: 55 }, (_, step) => {
    let m1 = { id: 'M1', status: 'IDLE', load: 0 };
    let m2 = { id: 'M2', status: 'IDLE', load: 0 };
    let m3 = { id: 'M3', status: 'IDLE', load: 0 };

    // --- 剧本逻辑 ---

    // 阶段1: 预热 (Step 5-15)
    if (step >= 5 && step < 16) {
        m1 = { id: 'M1', status: 'WORKING', load: 10 + (step - 5) * 2 }; // 负载缓慢上升
    }

    // 阶段2: 高负荷作业 (Step 16-35) - 对应 AGV 在右侧区域
    if (step >= 16 && step < 36) {
        m1 = { id: 'M1', status: 'WORKING', load: 60 + Math.floor(Math.random() * 20) };
        m2 = { id: 'M2', status: 'WORKING', load: 40 + Math.floor(Math.random() * 10) };
    }

    // 阶段3: 模拟故障 (Step 36-42)
    if (step >= 36 && step <= 42) {
        m1 = { id: 'M1', status: 'BROKEN', load: 99 }; // 故障
        m2 = { id: 'M2', status: 'IDLE', load: 0 };    // 因上游故障而待机
        m3 = { id: 'M3', status: 'WORKING', load: 20 }; // M3 尝试分流
    }

    // 阶段4: 恢复与收尾 (Step 43-54)
    if (step > 42) {
        const cooldown = Math.max(0, 50 - (step - 42) * 5);
        m1 = { id: 'M1', status: 'WORKING', load: cooldown };
        m2 = { id: 'M2', status: 'WORKING', load: cooldown / 2 };
    }

    // 结束时刻归零
    if (step === 54) {
        m1 = { id: 'M1', status: 'IDLE', load: 0 };
        m2 = { id: 'M2', status: 'IDLE', load: 0 };
    }

    return { step, machines: { 'M1': m1, 'M2': m2, 'M3': m3 } };
});
// ============ 3. 性能指标数据 (自动生成 0-54 步) ============
const METRICS_DATA = Array.from({ length: 55 }, (_, step) => {
    // 模拟数据波动
    const mLoad = MACHINE_STATES[step].machines['M1'].load; // 以M1负载为参考

    // 效率: 随负载升高，故障时下降
    let effVal = 0;
    let effType = 'info';

    if (mLoad > 0 && mLoad < 80) { effVal = 60 + Math.random() * 20; effType = 'success'; }
    else if (mLoad >= 80 && mLoad < 99) { effVal = 90; effType = 'warning'; }
    else if (mLoad === 99) { effVal = 0; effType = 'danger'; } // 故障

    // 利用率: 简单模拟
    let utilVal = Math.min(100, step * 2);
    if (step > 40) utilVal = Math.max(0, 100 - (step - 40) * 10);

    return {
        step: step,
        machine: {
            // 数据对应 [M1, M2, M3, M4, M5]
            data: [
                mLoad,
                MACHINE_STATES[step].machines['M2'].load,
                MACHINE_STATES[step].machines['M3'].load,
                Math.max(0, Math.floor(Math.random() * 10)),
                0
            ],
            labels: ['M1', 'M2', 'M3', 'M4', 'M5']
        },
        agv: {
            // 模拟 AGV 耗电和里程增加 [电量消耗, 速度, 任务数, 异常]
            data: [
                Math.min(step * 1.5, 100), // 耗电量随时间增加
                step > 0 && step < 54 ? 2 : 0, // 速度：中间动，两头停
                Math.floor(step / 10),
                step >= 36 && step <= 42 ? 1 : 0 // 故障期间显示异常
            ]
        },
        job: {
            // 模拟任务堆积
            data: [100 + step * 5, step * 2, 0, 0, 0]
        },
        keyMetrics: {
            efficiency: { value: Math.floor(effVal) + '%', type: effType },
            utilization: { value: Math.floor(utilVal) + '%', type: utilVal > 80 ? 'warning' : 'success' }
        }
    };
});
// ============ 4. 事件触发 (手动精编版) ============
const EVENTS_LOG = [
    {
        step: 0,
        title: '系统就绪',
        message: 'AGV #1 已上线，坐标 (5, 2)，等待指令',
        type: 'info'
    },
    {
        step: 10,
        title: '进入作业区',
        message: 'AGV 到达上料缓冲区 (Y=11)，M1 开始预热',
        type: 'success'
    },
    {
        step: 27,
        title: '折返点装载',
        message: 'AGV 到达最远端 (16, 4)，执行自动装载任务',
        type: 'task'
    },
    {
        step: 36,
        title: '设备告警',
        message: 'M1 主轴过载 (Load 99%)，触发安全停机',
        type: 'error'
    },
    {
        step: 43,
        title: '故障排除',
        message: 'M1 重启完成，系统恢复正常运行',
        type: 'success'
    },
    {
        step: 54,
        title: '任务完成',
        message: 'AGV 返回原点 (5, 2)，作业流程结束',
        type: 'success'
    }
];
/**
 * 驱动器：负责按时间节拍将数据推送到 Store 中
 */
export function runFullSystemTest(factoryStore, monitorStore, onFinish) {
    let frameIndex = 0;
    const TOTAL_STEPS = 55; // 0-54 共 55 步

    // 1. 初始化
    factoryStore.reset();
    monitorStore.clear();
    factoryStore.isPlaying = true; // 开启播放状态，让 Store 知道我们在进行实时更新

    // 2. 启动定时器 (模拟时间流逝)
    const timer = setInterval(() => {
        // 结束条件
        if (frameIndex >= TOTAL_STEPS) {
            clearInterval(timer);
            factoryStore.isPlaying = false;
            if (onFinish) onFinish();
            return;
        }

        const step = frameIndex;

        // ==================== A. 推送 AGV 环境 ====================
        // 如果超出基础轨迹范围，使用最后一个状态
        const agvFrame = AGV_TRAJECTORIES[Math.min(step, AGV_TRAJECTORIES.length - 1)];
        const machineFrame = MACHINE_STATES[step];

        if (agvFrame && machineFrame) {
            const snapshot = {
                timestamp: `T+${step}s`,
                grid_state: {
                    positions_xy: agvFrame.agvs.map(a => [a.x, a.y]),
                    is_active: agvFrame.agvs.map(a => a.active)
                },
                // 【关键】推送动态机器状态到 Store
                machines: machineFrame.machines,
                active_transfers: []
            };

            // 【关键】推送工厂环境快照
            factoryStore.pushSnapshot(snapshot);
        }

        // ==================== B. 推送性能指标 ====================
        // 防止数组越界：如果 METRICS_DATA 不足，使用最后一个或生成默认值
        let metricsFrame = METRICS_DATA[step];
        if (!metricsFrame && step < TOTAL_STEPS) {
            // 如果没有预生成的数据，自动补充默认值
            metricsFrame = {
                step: step,
                machine: { data: [0, 0, 0, 0, 0], labels: ['M1', 'M2', 'M3', 'M4', 'M5'] },
                agv: { data: [0, 0, 0, 0] },
                job: { data: [0, 0, 0, 0, 0] },
                keyMetrics: {
                    efficiency: { value: '0%', type: 'info' },
                    utilization: { value: '0%', type: 'info' }
                }
            };
        }

        if (metricsFrame) {
            const metricsPayload = {
                machine: metricsFrame.machine,
                agv: metricsFrame.agv,
                job: metricsFrame.job,
                keyMetrics: metricsFrame.keyMetrics
            };

            // 【关键】推送监控指标
            monitorStore.pushMetrics(metricsPayload);
        }

        // ==================== C. 推送事件 ====================
        const eventFrame = EVENTS_LOG.find(e => e.step === step);
        if (eventFrame) {
            // 【关键】推送事件
            monitorStore.pushEvent({
                title: eventFrame.title,
                message: eventFrame.message,
                type: eventFrame.type,
                idx: step
            });
        }

        frameIndex++;
    }, 1500); // 模拟每 1.5 秒产生一个新时间步

    // 返回停止句柄
    return () => clearInterval(timer);
}