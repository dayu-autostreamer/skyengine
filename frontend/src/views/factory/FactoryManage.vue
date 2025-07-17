<template>
  <div class="outline">
    <div>
      <h3>Factory Management</h3>
    </div>

    <div>
      <div class="new-dag-font-style">Upload Config Set</div>
      <el-upload
          class="upload-demo"
          drag
          action="https://run.mocky.io/v3/9d059bf9-4660-45f2-925d-ce80ad6c4d15"
          multiple
      >
        <el-icon class="el-icon--upload">
          <upload-filled/>
        </el-icon>
        <div class="el-upload__text">
          Drop file here or <em>click to upload</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            A config set should contain 3 config files
          </div>
        </template>
      </el-upload>

      <br/>
      <br/>
      <div style="display: inline">
        <div class="new-dag-font-style">
          Factory Info
          <el-tooltip placement="right">
            <template #content>
              Both logical and physical included.
            </template>
            <el-button size="small" circle>i</el-button>
          </el-tooltip>
        </div>
      </div>

      <div>
        <ul style="list-style-type: none" class="svc-container">
          <li
              v-for="(service, index) in services"
              :key="index"
              class="svc-item"
          >
            <el-tooltip
                placement="right"
                :open-delay="500"
                enterable
            >
              <template #content>
                <div class="description">
                  {{ service.description }}
                </div>
              </template>
              <div
                  class="vue-flow__node-input"
                  :draggable="true"
                  @dragstart="onDragStart($event, '', service)"
              >
                {{ service.name }}
              </div>
            </el-tooltip>
          </li>
        </ul>
      </div>
    </div>
    <br/>

    <!--    <div>-->
    <!--      <ElRow>-->
    <!--        <ElCol :span="2">-->
    <!--          <el-button type="warning" @click="draw">Draw</el-button>-->
    <!--        </ElCol>-->
    <!--        <ElCol :span="18"></ElCol>-->
    <!--        <ElCol :span="2">-->
    <!--          <el-button-->
    <!--              type="primary"-->
    <!--              round-->
    <!--              @click="handleNewSubmit"-->
    <!--              v-if="drawing"-->
    <!--          >Add-->
    <!--          </el-button-->
    <!--          >-->
    <!--        </ElCol>-->
    <!--        <ElCol :span="2">-->
    <!--          <el-button type="primary" round @click="clearInput" v-if="drawing"-->
    <!--          >Clear-->
    <!--          </el-button-->
    <!--          >-->
    <!--        </ElCol>-->
    <!--      </ElRow>-->
    <!--    </div>-->

    <!-- 绘制区域,自动绘制 -->
    <div>
      <ElRow>
        <ElCol :span="18">
          <div
              class="draw-container"
              v-if="drawing"
              @drop="onDrop($event, flowNodes, flowNodeMap)"
          >
            <VueFlow
                class="main-flow"
                :nodes="flowNodes"
                :edges="flowEdges"
                :default-viewport="{ zoom: 1.5 }"
                :min-zoom="1"
                :max-zoom="2"
                :fit-view-on-init="false"
                @dragover="onDragOver"
                @dragleave="onDragLeave"
            >
              <div v-if="drawing" class="drag-tip">
                <el-icon class="tip-icon">
                  <MagicStick/>
                </el-icon>
                <span>Drag service nodes to build your workflow</span>
              </div>

              <Background pattern-color="#aaa" :gap="16"/>

              <MiniMap/>
              <Panel class="process-panel" position="top-right">
                <div class="layout-panel">
                  <button title="set horizontal layout" @click="layoutGraph('LR')">
                    <Icon name="horizontal"/>
                  </button>

                  <button title="set vertical layout" @click="layoutGraph('TB')">
                    <Icon name="vertical"/>
                  </button>
                </div>
              </Panel>
            </VueFlow>
          </div>
        </ElCol>
        <ElCol :span="1">

        </ElCol>
        <ElCol :span="5">
          <el-card style="max-width: 480px">
            <el-button type="warning" @click="draw">Draw</el-button>
          </el-card>
          <el-card style="max-width: 480px">
            <el-button type="warning" @click="draw">Draw</el-button>
          </el-card>
                    <el-card style="max-width: 480px">
            <el-button type="warning" @click="draw">Draw</el-button>
          </el-card>
        </ElCol>
      </ElRow>


    </div>
    <br/>
    <br/>
  </div>
</template>

<script>
import {ElButton, ElCol, ElInput, ElMessage, ElRow, ElTable, ElTableColumn, ElTag, ElTooltip,} from "element-plus";
import {nextTick, ref} from "vue";
import {MarkerType, Panel, useVueFlow, VueFlow} from "@vue-flow/core";
import {ControlButton, Controls} from "@vue-flow/controls";
import {Background} from "@vue-flow/background";
import {MiniMap} from "@vue-flow/minimap";
import useDragAndDrop from "./useDnD";
import Icon from "./Icon.vue";
import {useLayout} from "./useLayout";
import {Connection, Link, MagicStick, Right} from '@element-plus/icons-vue';
import {UploadFilled} from '@element-plus/icons-vue'

export default {
  name: "DagManage",
  components: {
    nextTick,
    ElTable,
    ElTableColumn,
    ElTooltip,
    ElTag,
    ElInput,
    ElButton,
    ElCol,
    ElRow,
    ElMessage,
    VueFlow,
    Background,
    MarkerType,
    MiniMap,
    ControlButton,
    Controls,
    Icon,
    Panel,

    Connection,
    Link,
    Right,
    MagicStick,
    UploadFilled
  },
  setup() {
    const {onInit, onNodeDragStop, onConnect, fitView} = useVueFlow();

    const {onDragOver, onDrop, onDragLeave, isDragOver, onDragStart} =
        useDragAndDrop();

    const layoutMethods = useLayout();


    const flowNodes = ref([])
    const flowEdges = ref([])
    const flowNodeMap = ref({})

    const layoutGraph = async (direction) => {
      try {
        const layoutNodes = layout(
            [...flowNodes.value],
            [...flowEdges.value],
            direction
        )
        flowNodes.value = layoutNodes
        await nextTick()
        fitView()
      } catch (e) {
        console.error("Layout failed:", e)
        ElMessage.error("DAG layout error")
      }
    }

    // life cycle callback
    onInit((vueFlowInstance) => {
      vueFlowInstance.fitView();
    });
    onNodeDragStop(({event, nodes, node}) => {
    });
    onConnect((connection) => {
      const line = {
        id: connection.source + "-" + connection.target,
        source: connection.source,
        target: connection.target,
        label: "",
        markerEnd: MarkerType.ArrowClosed,
      };
      flowEdges.value.push(line);
      flowNodeMap.value[connection.source].data.succ.push(connection.target);
      flowNodeMap.value[connection.target].data.prev.push(connection.source);
    });

    return {
      onDragOver,
      onDrop,
      onDragLeave,
      isDragOver,
      onDragStart,
      layoutGraph,
      flowNodes,
      flowEdges,
      flowNodeMap,
      ...layoutMethods,
    };
  },

  data() {
    return {
      services: [],
      editInput: "",
      newInputName: "",
      newInputDag: "",
      newInputDagId: "",
      editDisabled: true,
      editingIndex: -1,
      editingRow: null,

      // drawing flag
      drawing: false,
      dagList: [],

      activeDag: null,
      hoverPosition: {x: 0, y: 0},
    };
  },

  methods: {
    flushDrawData() {
      this.flowNodes = [];
      this.flowEdges = [];
      this.flowNodeMap = {};
    },
    draw() {
      this.drawing = !this.drawing;
    },
    clearInput() {
      this.newInputName = "";
      this.newInputDag = "";
      this.newInputDagId = "";
      this.flushDrawData();
    },
    // delete dag
    deleteWorkflow(index, dag_id) {
      this.dagList.splice(index, 1);
      const content = {
        dag_id: dag_id,
      };
      fetch("/api/dag_workflow", {
        method: "DELETE",
        body: JSON.stringify(content),
      })
          .then((response) => response.json())
          .then((data) => {
            const state = data["state"];
            let msg = data["msg"];
            msg += ". Refreshing..";
            this.showMsg(state, msg);
            setTimeout(() => {
              location.reload();
            }, 500);
          })
          .catch((error) => {
            ElMessage.error("Network error");
            console.error(error);
          });
    },

    handleNewSubmit() {
      if (this.newInputName === "" || this.newInputName === null) {
        ElMessage.error("Please fill the dag name");
        return;
      }
      if (this.flowNodes === undefined || this.flowNodes.length === 0) {
        ElMessage.error("Please choose services");
        return;
      }

      // get graph
      const constructDagGraph = () => {
        const graph = {_start: []};
        for (const flowNode of this.flowNodes) {

          const serviceId = flowNode.id;
          if (graph[serviceId]) {
            throw new Error(`Duplicate service_id: ${serviceId}`);
          }
          const prev = flowNode.data?.prev ? [...flowNode.data.prev] : [];
          const succ = flowNode.data?.succ ? [...flowNode.data.succ] : [];
          graph[serviceId] = {service_id: serviceId, prev, succ};
          graph[serviceId] = {
            id: serviceId,
            prev: prev,
            succ: flowNode.data?.succ ?? [],
          };

          if (prev.length === 0) {
            graph._start.push(serviceId);
          }
        }

        return graph;
      };
      const graph = constructDagGraph();
      const newData = {
        dag_name: this.newInputName,
        dag: graph,
      };
      // update all Daglist
      this.updateDagList(newData);
    },
    // get dag from backen
    getDagList() {
      fetch("/api/dag_workflow")
          .then((response) => response.json())
          .then((data) => {
            this.dagList = data.map(dag => {
              const nodeList = this.parseDag(dag.dag);
              const lineList = this.generateEdges(dag.dag);

              const layoutNodes = this.layout(
                  nodeList,
                  lineList,
                  "LR"
              );

              return {
                ...dag,
                nodeList: layoutNodes,  // 添加布局后的节点
                lineList               // 添加边数据
              };
            });
          })
          .catch((error) => {
            console.error('Error fetching data:', error);
            // console.error("Error fetching data");
          });
    },
    fetchData() {
      this.getDagList();
    },
    showMsg(state, msg) {
      if (state === "success") {
        ElMessage({
          message: msg,
          showClose: true,
          type: "success",
          duration: 3000,
        });
      } else {
        ElMessage({
          message: msg,
          showClose: true,
          type: "error",
          duration: 3000,
        });
      }
    },
    // update dag to backen
    updateDagList(data) {
      fetch("/api/dag_workflow", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      })
          .then((response) => response.json())
          .then((data) => {
            const state = data["state"];
            const msg = data["msg"];
            this.showMsg(state, msg);
            if (state === "success") {
              this.getDagList();
              location.reload();
              this.clearInput()
            }
          })
          .catch((error) => {
            console.error("Error sending data:", error);
          });
    },
    async getServiceList() {
      const response = await fetch("/api/service");
      this.services = await response.json();
    },


    async layoutGraph(direction) {
      try {
        const layoutNodes = this.layout(
            [...this.flowNodes],
            [...this.flowEdges],
            direction
        )

        this.flowNodes = [...layoutNodes]

      } catch (e) {
        console.error("Layout failed:", e);
        ElMessage.error("DAG layout error");
      }
    },

    /*methods for dag view*/
    async showDagDetail(row, event) {
      if (!row || !event) {
        console.warn('Invalid parameters');
        return;
      }

      try {
        this.activeDag = row.dag_id;

        const baseX = event.clientX || 0;
        const baseY = event.clientY || 0;

        const SAFE_MARGIN = 20;
        const cardWidth = 400;
        const cardHeight = 300;

        let posX = baseX + 20;
        let posY = baseY - 50;

        if (posX + cardWidth > window.innerWidth) {
          posX = window.innerWidth - cardWidth - SAFE_MARGIN;
        }

        if (posY + cardHeight > window.innerHeight) {
          posY = window.innerHeight - cardHeight - SAFE_MARGIN;
        }

        this.hoverPosition = {x: posX, y: posY};


        if (!row.nodeList) {
          const nodeList = this.parseDag(row.dag);
          const lineList = this.generateEdges(row.dag);


          const layoutNodes = this.layout(
              nodeList.map(n => ({
                ...n,
                dimensions: {width: 160, height: 40}
              })),
              lineList,
              'LR'
          )

          Object.assign(row, {
            nodeList: layoutNodes,
            lineList
          });
        }
      } catch (error) {
        console.error('DAG detail error:', error);
        this.activeDag = null;
      }
    },

    hideDagDetail() {
      this.activeDag = null;
    },
    countEdges(dag) {
      let count = 0
      for (const node of Object.values(dag)) {
        if (node.succ && Array.isArray(node.succ)) {
          count += node.succ.length
        }
      }
      return count
    },

    randomColor() {
      const colors = [
        "#F0F4F8", "#E3F2FD", "#E8F5E9", "#F3E5F5",
        "#FFF3E0", "#FBE9E7", "#E0F7FA", "#F1F8E9",
        "#FCE4EC", "#EDE7F6", "#E8F5E6", "#FFEBEE",
        "#E0F2F1", "#F5F5F5", "#FFF8E1", "#EFEBE9"
      ];
      return colors[Math.floor(Math.random() * colors.length)];
    },


    parseDag(dag) {
      return Object.keys(dag)
          .filter(k => k !== '_start')
          .map(key => ({
            id: key,
            data: {label: key},
            dimensions: {width: 200, height: 50},
            style: {
              backgroundColor: this.randomColor(),
              border: '1px solid #e2e8f0'
            }
          }));
    },


    generateEdges(dag) {
      const edges = []
      for (const [source, node] of Object.entries(dag)) {
        if (node.succ) {
          node.succ.forEach(target => {
            edges.push({
              id: `${source}-${target}`,
              source,
              target,
              markerEnd: MarkerType.ArrowClosed
            })
          })
        }
      }
      return edges
    },
  }
  ,
  mounted() {
    // init dag data list
    this.fetchData();

    const getServiceInterval = () => {
      let timer;
      if (timer !== undefined) {
        clearInterval(timer);
      }
      timer = setInterval(() => {
        this.fetchData();
      }, 5000);
    };
    getServiceInterval();

    this.getServiceList();

    // this.$nextTick(() => {
    //   if (this.flowNodes.length > 0) {
    //     this.layoutGraph('LR')
    //   }
    // })
  }
  ,
}
;
</script>

<style scoped>
body {
  font-family: Arial, sans-serif;
  background-color: #f9f9f9;
  margin: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

form {
  max-width: 600px;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  /* box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); */
}

h3 {
  font-size: 24px;
  color: #333;
  margin-bottom: 20px;
}

input[type="text"],
input[type="file"] {
  width: calc(100% - 20px);
  padding: 10px;
  margin-bottom: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 16px;
}

input[type="file"] {
  cursor: pointer;
}

.draw-container {
  width: 100%;
  height: 500px;

  display: flex;
  align-items: flex-start;
  justify-content: center;
  margin-top: 15px;
  border: 1px solid #ccc;
}

.compact-container {
  width: 100%;
  height: 100px;
}

.el-button {
  font-size: 16px;
  margin-right: 10px;
}

.el-button:first-child {
  margin-left: 0;
}

.outline {
  /* max-width: 600px; */
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  /* box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); */
}

.new-dag-font-style {
  font-size: 16px;
  margin-bottom: 15px;
  font-weight: bold;
}

.svc-container {
  margin-top: -20px;
  display: flex;
  flex-wrap: wrap;
  padding: 10px;
  list-style-type: none;
}


.svc-item {
  display: inline-block;
  margin: 2px;
  padding: 2px;
  border-radius: 12px;
}

.vue-flow__node-input {
  border: 1px solid #e2e8f0; /* 柔和的蓝灰色 */
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  width: auto;
  padding: 10px;
  font-size: 18px;
}

.vue-flow__node-input:hover {
  border-color: #94a3b8; /* 悬停时稍深的颜色 */
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.vue-flow__node-input2 {
  width: auto;
  padding: 5px;
  font-size: 20px;
}

.description {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.el-button {
  font-size: 16px;
  margin-right: 10px;
}

.el-button:first-child {
  margin-left: 0;
}

.process-panel,
.layout-panel {
  display: flex;
  gap: 10px;
}

.process-panel {
  background-color: #2d3748;
  padding: 10px;
  border-radius: 8px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

.process-panel button {
  border: none;
  cursor: pointer;
  background-color: #4a5568;
  border-radius: 8px;
  color: white;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
}

.process-panel button {
  font-size: 16px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.checkbox-panel {
  display: flex;
  align-items: center;
  gap: 10px;
}

.process-panel button:hover,
.layout-panel button:hover {
  background-color: #2563eb;
  transition: background-color 0.2s;
}

.process-panel label {
  color: white;
  font-size: 12px;
}

.drag-tip {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 16px;
  border-radius: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 8px;
  backdrop-filter: blur(4px);
  border: 1px solid #ebeef5;
  animation: float 3s ease-in-out infinite;
}

.tip-icon {
  color: #409eff;
  font-size: 18px;
}

.drag-tip span {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 14px;
  color: #606266;
  font-weight: 500;
  letter-spacing: 0.3px;
}

@keyframes float {
  0%, 100% {
    transform: translateX(-50%) translateY(0);
  }
  50% {
    transform: translateX(-50%) translateY(-4px);
  }
}


.dag-preview {
  position: relative;
  padding: 8px;
  border-radius: 8px;
  background: #f8fafc;
  transition: all 0.3s;
}

.mini-dag {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;

  .node {
    padding: 2px 8px;
    background: #e2e8f0;
    border-radius: 4px;
    font-size: 12px;
  }

  .edges {
    color: #94a3b8;
    display: flex;
    gap: 2px;
  }
}

.stats {
  display: flex;
  gap: 8px;

  .el-tag {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}


.dag-detail-card {
  position: fixed;
  z-index: 99999 !important;
  pointer-events: none;
  width: 400px;
  height: 300px;
  right: 120px;
  left: auto !important;
  top: 40% !important;
  transform: translate(-20px, -50%) !important;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  padding: 16px;
  animation: slide-in 0.3s ease;
  max-width: 90vw;
  max-height: 80vh;
  overflow: auto;
  transition: all 0.3s ease;

  .dag-title {
    font-weight: 600;
    margin-bottom: 12px;
    color: #2d3748;
  }


}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dag-detail-card .vue-flow__node {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.dag-detail-card .vue-flow__edge-path {
  stroke: #64748b;
  stroke-width: 2;
}

.mini-dag .node {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edges {
  .no-edges {
    color: #999;
    font-size: 12px;
  }

  .el-icon {
    &:nth-child(n+4) {
      display: none;
    }
  }
}

.el-table__body tr.hover-row > td {
  z-index: auto !important;
}

.first-service {
  background: #e2e8f0;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.main-flow .vue-flow__node {
}

.preview-flow {
  z-index: 100000;
  pointer-events: none;
}

.preview-flow .vue-flow__node {
  transform: scale(0.8);
  cursor: default !important;
}

</style>
