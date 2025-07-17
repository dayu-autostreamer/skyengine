<template>
  <!-- <SvcInstall/>
  <SvcQuery/>  -->
  <div class="home-container layout-pd">
    <el-row :gutter="15" class="home-card-two mb15">
      <el-col :xs="24">
        <div class="home-card-item">
          <div style="height: 100%">
            <div class="flex-margin flex w100">
              <div class="flex-auto">
                <FactoryManage/>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

  </div>
</template>

<script>
import FactoryManage from "/@/views/factory/FactoryManage.vue";


export default {
  components: {
    FactoryManage,
  },
  data() {
    return {
    }
  },
}

</script>

<style scoped lang="scss">
$homeNavLengh: 8;


.home-container {
  overflow: hidden;

  .home-card-one,
  .home-card-two,
  .home-card-three {
    .home-card-item {
      width: 100%;
      height: 150px;
      border-radius: 2px;
      transition: all ease 0.3s;
      padding: 5px;
      overflow: hidden;
      background: var(--el-color-white);
      color: var(--el-text-color-primary);
      border: 1px solid var(--next-border-color-light);

      &:hover {
        box-shadow: 0 2px 12px var(--next-color-dark-hover);
        transition: all ease 0.3s;
      }

      &-icon {
        width: 70px;
        height: 70px;
        border-radius: 100%;
        flex-shrink: 1;

        i {
          color: var(--el-text-color-placeholder);
        }
      }

      &-title {
        font-size: 15px;
        font-weight: bold;
        height: 30px;
      }
    }
  }

  .home-card-one {
    @for $i from 0 through 3 {
      .home-one-animation#{$i} {
        opacity: 0;
        animation-name: error-num;
        animation-duration: 0.5s;
        animation-fill-mode: forwards;
        animation-delay: calc($i/4) + s;
      }
    }
  }

  .home-card-two,
  .home-card-three {
    .home-card-item {
      height: 90vh;
      width: 100%;
      overflow: scroll;

      .home-monitor {
        height: 100%;

        .flex-warp-item {
          width: 25%;
          height: 111px;
          display: flex;

          .flex-warp-item-box {
            margin: auto;
            text-align: center;
            color: var(--el-text-color-primary);
            display: flex;
            border-radius: 5px;
            background: var(--next-bg-color);
            cursor: pointer;
            transition: all 0.3s ease;

            &:hover {
              background: var(--el-color-primary-light-9);
              transition: all 0.3s ease;
            }
          }

          @for $i from 0 through $homeNavLengh {
            .home-animation#{$i} {
              opacity: 0;
              animation-name: error-num;
              animation-duration: 0.5s;
              animation-fill-mode: forwards;
              animation-delay: calc($i/10) + s;
            }
          }
        }
      }
    }

  }



  .dag-manage {
    .home-card-item {
      height: 100vh;
      width: 100%;
      overflow: scroll;
    }
  }
}
</style>
