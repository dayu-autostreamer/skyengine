<template>
  <div class="outline">
    <div>
      <h3>Statistic Infomation</h3>
    </div>
    <div>
      <div class="new-dag-font-style">Upload Config Set</div>
      <div class="upload-config-box">
        <ElRow>
          <ElCol :span="1"></ElCol>

          <ElCol :span="10">
            <ElCard>
              <template #header>
                <div class="card-header">
                  <el-tag>Config Set Operation</el-tag>
                </div>
              </template>
              <v-chart class="chart" :option="option"/>
            </ElCard>
          </ElCol>
          <ElCol :span="2"></ElCol>

          <ElCol :span="10">
            <ElCard>
              <template #header>
                <div class="card-header">
                  <el-tag @click="test">Config Set Operation</el-tag>
                </div>
              </template>
              <v-chart class="chart" :option="option"/>
            </ElCard>
          </ElCol>
          <ElCol :span="1"></ElCol>

        </ElRow>


      </div>
    </div>

  </div>
  <br/>
</template>

<script setup>
import {ElButton, ElCol, ElInput, ElRow, ElTag, ElTooltip} from "element-plus";

import {use} from "echarts/core";
import {CanvasRenderer} from "echarts/renderers";
import {PieChart} from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import VChart, {THEME_KEY} from "vue-echarts";
import {ref, provide} from "vue";

use([
  CanvasRenderer,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
]);

const options_dict = ref({
  machine_load_bar: {},
  agv_load_bar: {},
  job_finish_time: {},
})

const option = ref({
  title: {
    text: "Traffic Sources",
    left: "center",
  },
  tooltip: {
    trigger: "item",
    formatter: "{a} <br/>{b} : {c} ({d}%)",
  },
  legend: {
    orient: "vertical",
    left: "left",
    data: ["Direct", "Email", "Ad Networks", "Video Ads", "Search Engines"],
  },
  series: [
    {
      name: "Traffic Sources",
      type: "pie",
      radius: "55%",
      center: ["50%", "60%"],
      data: [
        {value: 335, name: "Direct"},
        {value: 310, name: "Email"},
        {value: 234, name: "Ad Networks"},
        {value: 135, name: "Video Ads"},
        {value: 1548, name: "Search Engines"},
      ],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: "rgba(0, 0, 0, 0.5)",
        },
      },
    },
  ],
});


</script>


<style scoped lang="scss">
.outline {
  /* max-width: 600px; */
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  /* box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); */
}


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

.new-dag-font-style {
  font-size: 16px;
  margin-bottom: 15px;
  font-weight: bold;
}

.upload-config-box {

  padding: 20px;
  background-color: #f0f8ff; /* 浅蓝背景 */
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin: 0 auto;
}

.el-card__body {
  width: 100px;
  height: 100px;
}

.echarts.chart {
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 300px; /* 最小高度，避免为 0 */
}
</style>