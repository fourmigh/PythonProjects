
"""共享的工具函数、颜色配置和UI组件"""
import tkinter as tk
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import User


# ========== 颜色配置 ==========
COLORS = {
    "bg": "#f0f0f0",
    "header_bg": "#e8e8e8",
    "time_bg": "#fafafa",
    "selected_bg": "#0078d4",
    "selected_text": "#ffffff",
    "full_bg": "#ff0000",
    "full_text": "#ffffff",
    "warning_bg": "#ffff00",
    "warning_text": "#333333",
    "good_bg": "#00ff00",
    "good_text": "#ffffff",
    "normal_bg": "#ffffff",
    "normal_text": "#333333",
    "text": "#333333",
    "border": "#d0d0d0",
    "time_line": "#e0e0e0"
}


# ========== 图例配置 ==========
def get_legends():
    """获取图例列表"""
    return [
        (" 充足", COLORS["good_bg"], COLORS["good_text"]),
        (" 紧张", COLORS["warning_bg"], COLORS["warning_text"]),
        (" 已满", COLORS["full_bg"], COLORS["full_text"]),
        (" 已过", COLORS["bg"], "#999999")
    ]


def get_spot_status_legends():
    """获取车位状态窗口的图例"""
    return [
        ("🟢 空闲", "#00ff00", "#333333"),
        ("🟡 正常占用", "#ffff00", "#333333"),
        ("🔴 超时占用", "#ff0000", "#ffffff"),
        ("⚪ 已过期", "#e0e0e0", "#999999")
    ]


# ========== 时间工具函数 ==========
def get_current_date_str() -> str:
    """获取当前日期时间字符串（精确到秒）"""
    now = datetime.now()
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return f"{now.year}年{now.month}月{now.day}日 {weekday_map[now.weekday()]} {now.hour:02d}:{now.minute:02d}:{now.second:02d}"


def format_time_range(minutes_per_slot: int, slot: int) -> str:
    """将时段转换为时间范围显示"""
    start_minutes = (slot - 1) * minutes_per_slot
    end_minutes = slot * minutes_per_slot
    
    start_hour = start_minutes // 60
    start_min = start_minutes % 60
    end_hour = end_minutes // 60
    end_min = end_minutes % 60
    
    if end_hour == 24 and end_min == 0:
        end_display = "24:00"
    else:
        end_display = f"{end_hour:02d}:{end_min:02d}"
    
    return f"{start_hour:02d}:{start_min:02d}-{end_display}"


# ========== UI组件工厂函数 ==========
def create_legend_frame(parent, legends):
    """创建图例框架"""
    legend_frame = tk.Frame(parent, bg=COLORS["bg"])
    
    for text, bg, fg in legends:
        legend_item = tk.Frame(legend_frame, bg=COLORS["bg"])
        legend_item.pack(side=tk.LEFT, padx=10)
        
        color_box = tk.Label(
            legend_item,
            text="    ",
            bg=bg,
            relief=tk.SUNKEN,
            bd=1
        )
        color_box.pack(side=tk.LEFT)
        
        legend_label = tk.Label(
            legend_item,
            text=text,
            font=("Arial", 9),
            fg=fg,
            bg=COLORS["bg"]
        )
        legend_label.pack(side=tk.LEFT, padx=5)
    
    return legend_frame


def create_header(parent, title: str, show_date: bool = True):
    """创建标题栏"""
    header_frame = tk.Frame(parent, bg=COLORS["header_bg"])
    header_frame.pack(fill=tk.X, padx=0, pady=0)
    
    title_label = tk.Label(
        header_frame,
        text=title,
        font=("Arial", 16, "bold"),
        fg=COLORS["text"],
        bg=COLORS["header_bg"]
    )
    title_label.pack(side=tk.LEFT, padx=20, pady=10)
    
    date_label = None
    if show_date:
        date_label = tk.Label(
            header_frame,
            text=get_current_date_str(),
            font=("Arial", 11),
            fg="#666666",
            bg=COLORS["header_bg"]
        )
        date_label.pack(side=tk.RIGHT, padx=20)
    
    return header_frame, date_label


def create_scrollable_area(parent, bg_color):
    """创建可滚动区域"""
    canvas_frame = tk.Frame(parent, bg=bg_color)
    canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    canvas = tk.Canvas(canvas_frame, bg=bg_color, highlightthickness=0)
    scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
    
    scrollable_frame = tk.Frame(canvas, bg=bg_color)
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
    
    def on_canvas_configure(event):
        canvas.itemconfig(1, width=event.width)
    
    canvas.bind("<Configure>", on_canvas_configure)
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 鼠标滚轮绑定
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind("<MouseWheel>", on_mousewheel)
    
    return canvas, scrollable_frame


# 为了避免循环导入，在函数内部导入tkinter
import tkinter as tk