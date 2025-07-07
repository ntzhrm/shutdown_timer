import os
import sys
import subprocess

def build_executable():
    """打包Python程序为可执行文件"""
    
    # 确保安装了pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("正在安装PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # 构建命令
    build_cmd = [
        "pyinstaller",
        "--onefile",  # 打包成单个exe文件
        "--windowed",  # 不显示控制台窗口
        "--name=定时关机助手",  # 设置exe文件名
        "--icon=icon.ico",  # 图标文件(可选)
        "shutdown_timer.py"
    ]
    
    print("开始打包...")
    try:
        subprocess.run(build_cmd, check=True)
        print("打包完成！可执行文件位于 dist/ 目录下")
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
    except FileNotFoundError:
        print("PyInstaller未找到，请确保已正确安装")

if __name__ == "__main__":
    build_executable()