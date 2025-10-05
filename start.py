import subprocess
import sys



def run_command(cmd, cwd=None):
    """启动一个子进程，并保持输出实时打印"""
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr
    )

def main():
    print("=" * 40)
    print(" 🚀 SkyEngine 项目启动中...")
    print("=" * 40)

    # 启动后端
    print("\n[1/2] 启动后端服务...")
    print(sys.executable)
    backend_process = run_command(f'"{sys.executable}" main.py', cwd="backend")

    # 启动前端
    print("\n[2/2] 启动前端服务...")
    frontend_process = run_command("npm run dev", cwd="frontend")

    print("\n✅ 前后端已启动，按 Ctrl+C 可退出。")
    print("=" * 40)

    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n⏹ 收到退出信号，正在关闭进程...")
        backend_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    main()
