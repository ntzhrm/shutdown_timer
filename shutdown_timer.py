import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import os
import sys
import subprocess
import pystray
from PIL import Image, ImageDraw
import winreg
from datetime import datetime, timedelta

class ShutdownTimer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("定时关机助手")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # 配置文件路径
        self.config_file = os.path.join(os.path.dirname(sys.executable), "config.json")
        
        # 初始化变量
        self.shutdown_time = None
        self.timer_thread = None
        self.is_running = False
        self.remaining_time = 0
        
        # 加载配置
        self.load_config()
        
        # 创建界面
        self.create_gui()
        
        # 设置开机自启动
        self.setup_auto_start()
        
        # 系统托盘
        self.tray_icon = None
        self.create_tray_icon()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 检查并恢复定时状态
        self.restore_timer_state()
        
    def create_gui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="定时关机助手", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 时间设置区域
        time_frame = ttk.LabelFrame(main_frame, text="设置关机时间", padding="10")
        time_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # 小时
        ttk.Label(time_frame, text="小时:").grid(row=0, column=0, sticky=tk.W)
        self.hour_var = tk.StringVar(value="22")
        hour_spinbox = ttk.Spinbox(time_frame, from_=0, to=23, textvariable=self.hour_var, width=5)
        hour_spinbox.grid(row=0, column=1, padx=(5, 20))
        
        # 分钟
        ttk.Label(time_frame, text="分钟:").grid(row=0, column=2, sticky=tk.W)
        self.minute_var = tk.StringVar(value="00")
        minute_spinbox = ttk.Spinbox(time_frame, from_=0, to=59, textvariable=self.minute_var, width=5)
        minute_spinbox.grid(row=0, column=3, padx=(5, 0))
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(0, 20))
        
        self.start_button = ttk.Button(button_frame, text="开始定时", command=self.start_timer)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="停止定时", command=self.stop_timer, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(10, 0))
        
        # 状态显示
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="10")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.status_label = ttk.Label(status_frame, text="未启动定时关机", font=("Arial", 10))
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.time_label = ttk.Label(status_frame, text="", font=("Arial", 10, "bold"))
        self.time_label.grid(row=1, column=0, sticky=tk.W)
        
        # 其他选项
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        self.minimize_var = tk.BooleanVar(value=True)
        minimize_check = ttk.Checkbutton(options_frame, text="最小化到托盘", variable=self.minimize_var)
        minimize_check.grid(row=0, column=0, sticky=tk.W)
        
    def start_timer(self):
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            
            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 如果目标时间已经过了今天，则设为明天
            if target_time <= now:
                target_time += timedelta(days=1)
            
            self.shutdown_time = target_time
            self.remaining_time = int((target_time - now).total_seconds())
            
            # 保存配置
            self.save_config()
            
            # 启动计时器
            self.is_running = True
            self.timer_thread = threading.Thread(target=self.timer_worker, daemon=True)
            self.timer_thread.start()
            
            # 更新界面
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text=f"定时关机已启动，目标时间: {target_time.strftime('%Y-%m-%d %H:%M')}")
            
            # 启动状态更新
            self.update_status()
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的时间格式")
    
    def stop_timer(self):
        self.is_running = False
        self.shutdown_time = None
        self.remaining_time = 0
        
        # 更新界面
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="定时关机已停止")
        self.time_label.config(text="")
        
        # 保存配置
        self.save_config()
    
    def timer_worker(self):
        while self.is_running and self.remaining_time > 0:
            time.sleep(1)
            self.remaining_time -= 1
            
        if self.is_running and self.remaining_time <= 0:
            self.shutdown_computer()
    
    def update_status(self):
        if self.is_running and self.remaining_time > 0:
            hours = self.remaining_time // 3600
            minutes = (self.remaining_time % 3600) // 60
            seconds = self.remaining_time % 60
            
            self.time_label.config(text=f"剩余时间: {hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # 继续更新
            self.root.after(1000, self.update_status)
        elif self.is_running:
            self.time_label.config(text="正在关机...")
    
    def shutdown_computer(self):
        # 显示倒计时对话框
        result = messagebox.askokcancel("关机提醒", "计算机将在10秒后关机，点击取消可中止关机", timeout=10000)
        
        if result is not False:  # 用户点击确定或超时
            subprocess.run(["shutdown", "/s", "/t", "10"], check=False)
        
        self.stop_timer()
    
    def create_tray_icon(self):
        # 创建托盘图标
        image = Image.new('RGB', (64, 64), color='red')
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill='white')
        
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", self.show_window),
            pystray.MenuItem("退出", self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("shutdown_timer", image, "定时关机助手", menu)
        
        # 在单独线程中运行托盘图标
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def quit_app(self, icon=None, item=None):
        self.is_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
    
    def on_closing(self):
        if self.minimize_var.get():
            self.root.withdraw()  # 隐藏窗口而不是关闭
        else:
            self.quit_app()
    
    def restore_timer_state(self):
        """恢复上次的定时状态"""
        if self.is_running and self.shutdown_time:
            # 启动计时器线程
            self.timer_thread = threading.Thread(target=self.timer_worker, daemon=True)
            self.timer_thread.start()
            
            # 更新界面
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text=f"定时关机已恢复，目标时间: {self.shutdown_time.strftime('%Y-%m-%d %H:%M')}")
            
            # 启动状态更新
            self.update_status()
    
    def setup_auto_start(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Run", 
                               0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "ShutdownTimer", 0, winreg.REG_SZ, sys.executable)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"设置自启动失败: {e}")
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.hour_var = tk.StringVar(value=str(config.get('hour', 22)))
                    self.minute_var = tk.StringVar(value=str(config.get('minute', 0)))
                    
                    # 加载保存的定时状态
                    if config.get('is_running', False) and 'shutdown_time' in config:
                        shutdown_time_str = config.get('shutdown_time')
                        self.shutdown_time = datetime.fromisoformat(shutdown_time_str)
                        
                        # 检查定时时间是否仍然有效（在未来）
                        if self.shutdown_time > datetime.now():
                            self.is_running = True
                            self.remaining_time = int((self.shutdown_time - datetime.now()).total_seconds())
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def save_config(self):
        try:
            config = {
                'hour': int(self.hour_var.get()),
                'minute': int(self.minute_var.get()),
                'is_running': self.is_running
            }
            
            # 如果正在运行，保存关机时间
            if self.is_running and self.shutdown_time:
                config['shutdown_time'] = self.shutdown_time.isoformat()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ShutdownTimer()
    app.run()