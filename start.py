# 启动指令: python start.py --server_type grid --backend_port 9000 --frontend_port 3000 --dev_mode 0

import subprocess
import sys
import argparse
import os


def run_command(cmd, cwd=None, env=None):
    """启动一个子进程，并保持输出实时打印"""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=merged_env
    )


def main():
    # -------------------------------
    # 解析命令行参数
    # -------------------------------
    parser = argparse.ArgumentParser(description="启动 SkyEngine 前后端服务")
    parser.add_argument("--server_type", type=str, default="grid",
                        help="后端服务类型: [packet,grid]")
    parser.add_argument("--backend_port", type=int, default=8000, help="后端端口号")
    parser.add_argument("--frontend_port", type=int, default=5173, help="前端端口号")
    parser.add_argument("--dev_mode", type=int, default=1, choices=[0, 1],
                        help="是否启用开发模式: 1=开发, 0=生产")
    args = parser.parse_args()

    print("=" * 40)
    print(" 🚀 SkyEngine 项目启动中...")
    print("=" * 40)
    print(f"🌐 当前配置:")
    print(f"  server_type   = {args.server_type}")
    print(f"  backend_port  = {args.backend_port}")
    print(f"  frontend_port = {args.frontend_port}")
    print(f"  dev_mode      = {args.dev_mode}")

    # -------------------------------
    # 后端环境变量
    # -------------------------------
    backend_env = {
        "SERVER_TYPE": args.server_type,
        "GUNICORN_PORT": str(args.backend_port),
        "DEV_MODE": str(args.dev_mode)
    }

    # 启动后端
    print("\n[1/2] 启动后端服务...")
    backend_process = run_command(f'"{sys.executable}" -m backend.main', cwd=".", env=backend_env)

    # -------------------------------
    # 前端环境变量
    # -------------------------------

    # 启动前端
    print("\n[2/2] 启动前端服务...")
    frontend_process = run_command("npm run dev", cwd="frontend")

    print("\n✅ 前后端已启动，按 Ctrl+C 可退出。")
    print("=" * 40)

    # -------------------------------
    # 等待进程结束
    # -------------------------------
    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n⏹ 收到退出信号，正在关闭进程...")
        backend_process.terminate()
        frontend_process.terminate()


if __name__ == "__main__":
    main()
