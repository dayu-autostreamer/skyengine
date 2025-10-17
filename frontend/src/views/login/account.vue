<template>
  <div class="account-login">
    <h2 class="login-title">系统登录</h2>
    <el-form :model="loginForm" @submit.prevent="handleLogin">
      <el-form-item>
        <el-input v-model="loginForm.username" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item>
        <el-input type="password" v-model="loginForm.password" placeholder="请输入密码" />
      </el-form-item>
      <el-button type="primary" class="login-btn" @click="handleLogin">登录</el-button>
    </el-form>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

const loginForm = reactive({ username: '', password: '' })

const handleLogin = () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  // 登录逻辑
}
</script>

<style scoped>
.account-login {
  display: flex;
  flex-direction: column;
}

.login-title {
  text-align: center;
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 25px;
}

.login-btn {
  width: 100%;
  margin-top: 10px;
}
</style>
