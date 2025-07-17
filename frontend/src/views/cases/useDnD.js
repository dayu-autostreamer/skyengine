import { useVueFlow } from "@vue-flow/core";
import { ref, watch } from "vue";

const state = {
  serviceData: ref(null),
  draggedType: ref(null),
  isDragOver: ref(false),
  isDragging: ref(false),
};

export default function useDragAndDrop() {
  const { draggedType, isDragOver, isDragging, serviceData } = state;

  const { screenToFlowCoordinate, onNodesInitialized, updateNode } =
    useVueFlow();

  watch(isDragging, (dragging) => {
    document.body.style.userSelect = dragging ? "none" : "";
  });

  function onDragStart(event, type, service) {
    if (event.dataTransfer) {
      event.dataTransfer.setData("application/vueflow", type);
      event.dataTransfer.effectAllowed = "move";
    }

    draggedType.value = type;
    isDragging.value = true;
    serviceData.value = service;

    document.addEventListener("drop", onDragEnd);
  }

  function onDragOver(event) {
    event.preventDefault();

    if (draggedType.value) {
      isDragOver.value = true;

      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = "move";
      }
    }
  }

  function onDragLeave() {
    isDragOver.value = false;
  }

  function onDragEnd() {
    isDragging.value = false;
    isDragOver.value = false;
    draggedType.value = null;
    serviceData.value = null;
    document.removeEventListener("drop", onDragEnd);
  }

  function randomColor() {
    const colors = [
    "#F0F4F8", // 极浅灰蓝
    "#E3F2FD", // 柔和的天蓝
    "#E8F5E9", // 薄荷绿
    "#F3E5F5", // 浅紫丁香
    "#FFF3E0", // 杏仁白
    "#FBE9E7", // 浅珊瑚
    "#E0F7FA", // 冰蓝
    "#F1F8E9", // 嫩绿
    "#FCE4EC", // 浅粉红
    "#EDE7F6", // 薰衣草紫
    "#E8F5E6", // 青苹果
    "#FFEBEE", // 淡玫瑰
    "#E0F2F1", // 浅水蓝
    "#F5F5F5", // 浅灰白
    "#FFF8E1", // 香槟黄
    "#EFEBE9", // 浅米色
    ];
    const randomIndex = Math.floor(Math.random() * colors.length);
    return colors[randomIndex];
  }
  function onDrop(event, nodeList, nodeMap) {
    const position = screenToFlowCoordinate({
      x: event.clientX,
      y: event.clientY,
    });

    const nodeId = serviceData.value.id;
    const nodeName = serviceData.value.name;
    const nodeData = {
      label: nodeName,
      prev: [],
      succ: [],
      service_id: serviceData.value.name,
    };
    const newNode = {
      id: nodeId,
      type: draggedType.value,
      position: position,
      style: {
        backgroundColor: randomColor(),
        class: "vue-flow__node-input2",
        width: "auto",
        height: "auto",
      },
      data: nodeData,
      sourcePosition: 'right',
      targetPosition: 'left'
    };

    const { off } = onNodesInitialized(() => {
      updateNode(nodeId, (node) => ({
        position: {
          // x: node.position.x - node.dimensions.width / 2,
          // y: node.position.y - node.dimensions.height / 2,
           x: node.position.x,
          y: node.position.y,
        },
      }));

      off();
    });

    nodeMap[nodeId] = newNode;
    nodeList.push(newNode);
  }

  return {
    draggedType,
    isDragOver,
    isDragging,
    onDragStart,
    onDragLeave,
    onDragOver,
    onDrop,
  };
}
