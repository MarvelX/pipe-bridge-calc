#!/usr/bin/env python3
"""
管桥计算器 - 主程序入口
"""
import subprocess
import sys
import os


def install_requirements():
    """安装依赖"""
    print("正在安装依赖...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])


def main():
    """主函数"""
    print("=" * 50)
    print("🌉 管桥结构计算器")
    print("=" * 50)
    
    # 检查并安装依赖
    try:
        import streamlit
    except ImportError:
        install_requirements()
    
    # 启动Streamlit
    print("\n启动Web界面...")
    print("请在浏览器中打开: http://localhost:8501\n")
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run([sys.executable, "-m", "streamlit", "run", "ui/app.py", "--server.port=8501"])


if __name__ == "__main__":
    main()
