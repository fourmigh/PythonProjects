import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.system_proxy import system_proxy
from ui.shared_utils import COLORS, get_legends
from ui.spot_status_window import SpotStatusWindow


class ParkingGUI:
    def __init__(self, total_spots: int = 100, num_slots: int = 24):
        self.total_spots = total_spots
        self.num_slots = num_slots
        
        # 初始化系统代理
        system_proxy.init_system(total_spots, num_slots)
        system_proxy.register_refresh_callback(self.update_display)
        
        # 计算每个时段的时长（分钟）
        self.minutes_per_slot = system_proxy.minutes_per_slot
        
        self.selected_start: int = None
        self.selected_end: int = None
        
        # 固定行高（像素）
        self.row_height = 50
        
        self.root = tk.Tk()
        self.root.title(f"停车场预订系统 - {total_spots}车位 - {num_slots}时段")
        self.root.geometry("800x700")
        
        # 使用共享颜色配置
        self.colors = COLORS
        
        self.root.configure(bg=self.colors["bg"])
        
        self.create_widgets()
        self.update_display()
        
        # 获取当前时段编号（基于模拟时间）
        self.current_slot = self.get_current_slot()
        # 每秒刷新一次显示
        self.refresh_display()

    def refresh_display(self):
        """每秒刷新显示"""
        self.current_slot = self.get_current_slot()
        self.update_display()
        self.update_time_display()  # 更新时间显示
        self.root.after(1000, self.refresh_display)
    
    def get_current_slot(self) -> int:
        """获取当前模拟时间对应的时段编号"""
        current_minutes = system_proxy.time_point * (self.minutes_per_slot // 2) if system_proxy.time_point > 0 else 0
        slot = current_minutes // self.minutes_per_slot + 1
        if slot < 1:
            slot = 1
        if slot > self.num_slots:
            slot = self.num_slots + 1
        return slot
    
    def get_simulated_time_str(self) -> str:
        """获取模拟时间字符串"""
        total_points = self.num_slots * 2
        time_point = system_proxy.time_point
        
        if time_point >= total_points:
            return "模拟时间: 已结束"
        
        slot_index = time_point // 2
        is_start = (time_point % 2 == 0)
        
        # 计算当前时间
        minutes = slot_index * self.minutes_per_slot
        if not is_start:
            minutes += self.minutes_per_slot
        
        hour = minutes // 60
        minute = minutes % 60
        
        if is_start:
            phase = "开始前"
        else:
            phase = "结束后"
        
        return f"模拟时间: {hour:02d}:{minute:02d} (时段{slot_index + 1}{phase})"
    
    def get_slot_color_and_text(self, slot: int) -> tuple:
        """根据空闲比例返回 (背景色, 文字色, 状态文字, 是否可用)"""
        # 检查是否已过期（基于模拟时间）
        if slot < self.current_slot:
            return self.colors["bg"], "#999999", "已过", False
        
        status = system_proxy.get_slot_status(slot)
        free_count = status.capacity - status.booked_count
        
        if free_count == 0:
            return self.colors["full_bg"], self.colors["full_text"], "已满", False
        elif free_count < 2 or free_count / status.capacity < 0.5:
            return self.colors["warning_bg"], self.colors["warning_text"], "紧张", True
        else:
            return self.colors["good_bg"], self.colors["good_text"], "充足", True
    
    def get_time_marker(self, slot: int) -> str:
        """获取时段起始点的时间标记"""
        if slot == 0 or slot > self.num_slots:
            return ""
        
        minutes = (slot - 1) * self.minutes_per_slot
        hour = minutes // 60
        minute = minutes % 60
        
        # 显示所有时间点
        if minute == 0:
            return f"{hour:02d}:00"
        elif minute == 30:
            return f"{hour:02d}:30"
        elif minute % 15 == 0:
            return f"{hour:02d}:{minute:02d}"
        else:
            return ""
    
    def update_time_display(self):
        """更新时间显示"""
        self.time_label.config(text=self.get_simulated_time_str())
    
    def create_widgets(self):
        """创建界面组件"""
        
        # 顶部标题栏
        header_frame = tk.Frame(self.root, bg=self.colors["header_bg"])
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        
        title_label = tk.Label(
            header_frame,
            text="停车场预订系统",
            font=("Arial", 16, "bold"),
            fg=self.colors["text"],
            bg=self.colors["header_bg"]
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        # 模拟时间显示（替换原来的日期）
        self.time_label = tk.Label(
            header_frame,
            text=self.get_simulated_time_str(),
            font=("Arial", 11),
            fg="#666666",
            bg=self.colors["header_bg"]
        )
        self.time_label.pack(side=tk.RIGHT, padx=20)
        
        # 创建滚动区域
        canvas_frame = tk.Frame(self.root, bg=self.colors["bg"])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建画布和滚动条
        self.canvas = tk.Canvas(canvas_frame, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        # 创建内容框架
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["bg"])
        
        # 绑定配置事件
        def on_frame_configure(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # 将框架放入画布
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=self.canvas.winfo_width())
        
        # 当画布大小变化时，调整内部框架宽度
        def on_canvas_configure(event):
            self.canvas.itemconfig(1, width=event.width)
        
        self.canvas.bind("<Configure>", on_canvas_configure)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 鼠标滚轮绑定
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # 创建左右两列的容器
        content_frame = tk.Frame(self.scrollable_frame, bg=self.colors["bg"])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧时间列（用于占位）
        self.time_column = tk.Frame(content_frame, bg=self.colors["bg"], width=100)
        self.time_column.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.time_column.pack_propagate(False)
        
        # 右侧时段列
        self.slot_column = tk.Frame(content_frame, bg=self.colors["bg"])
        self.slot_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 存储按钮引用
        self.slot_buttons = {}
        self.status_labels = {}
        self.time_marker_frames = {}
        
        # 创建所有行
        for slot in range(1, self.num_slots + 1):
            # 左侧：时间标记行
            time_row = tk.Frame(self.time_column, bg=self.colors["time_bg"], height=self.row_height)
            time_row.pack(fill=tk.X, pady=0)
            time_row.pack_propagate(False)
            
            # 时间文字（显示在顶部，对齐分隔线）
            time_text = self.get_time_marker(slot)
            if time_text:
                time_label = tk.Label(
                    time_row,
                    text=time_text,
                    font=("Arial", 9),
                    fg="#666666",
                    bg=self.colors["time_bg"],
                    anchor="e"
                )
                time_label.pack(side=tk.TOP, fill=tk.X, padx=5)
            else:
                # 空白占位
                empty_label = tk.Label(
                    time_row,
                    text="",
                    bg=self.colors["time_bg"]
                )
                empty_label.pack(side=tk.TOP, fill=tk.X)
            
            # 右侧：时段按钮行
            slot_row = tk.Frame(self.slot_column, bg=self.colors["bg"], height=self.row_height)
            slot_row.pack(fill=tk.X, pady=0)
            slot_row.pack_propagate(False)
            
            # 时段按钮
            btn = tk.Button(
                slot_row,
                text=f"时段 {slot}",
                font=("Arial", 9),
                cursor="hand2",
                command=lambda s=slot: self.on_slot_click(s)
            )
            btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            # 状态标签
            status_label = tk.Label(
                slot_row,
                text="",
                width=8,
                font=("Arial", 9),
                bg=self.colors["bg"],
                anchor="center"
            )
            status_label.pack(side=tk.RIGHT, padx=(0, 10))
            
            self.slot_buttons[slot] = btn
            self.status_labels[slot] = status_label
            self.time_marker_frames[slot] = time_row
        
        # 在Canvas上绘制分隔线（覆盖在左右两列上）
        self.draw_separators()
        
        # 绑定滚动时重绘分隔线
        self.canvas.bind("<Configure>", lambda e: self.draw_separators())
        self.scrollable_frame.bind("<Configure>", lambda e: self.draw_separators())
        
        # ========== 底部控制区域 ==========
        control_frame = tk.Frame(self.root, bg=self.colors["bg"])
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 选择信息
        self.selection_label = tk.Label(
            control_frame,
            text="未选择时段",
            font=("Arial", 10),
            fg=self.colors["text"],
            bg=self.colors["bg"]
        )
        self.selection_label.pack(side=tk.LEFT)
        
        # 按钮容器
        button_frame = tk.Frame(control_frame, bg=self.colors["bg"])
        button_frame.pack(side=tk.RIGHT)
        
        # 车位状态按钮
        spot_status_btn = tk.Button(
            button_frame,
            text="车位状态",
            font=("Arial", 10),
            bg=self.colors["selected_bg"],
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.show_spot_status
        )
        spot_status_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 重置按钮
        reset_btn = tk.Button(
            button_frame,
            text="重置系统",
            font=("Arial", 10),
            bg="#d32f2f",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.reset_system
        )
        reset_btn.pack(side=tk.LEFT)
        
        # 图例
        legend_frame = tk.Frame(self.root, bg=self.colors["bg"])
        legend_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        for text, bg, fg in get_legends():
            legend_item = tk.Frame(legend_frame, bg=self.colors["bg"])
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
                bg=self.colors["bg"]
            )
            legend_label.pack(side=tk.LEFT, padx=5)
        
        # 操作说明
        info_label = tk.Label(
            legend_frame,
            text="  点击时段选择开始，再次点击选择结束（连续时段）",
            font=("Arial", 9),
            fg="#888888",
            bg=self.colors["bg"]
        )
        info_label.pack(side=tk.RIGHT)
    
    def draw_separators(self):
        """绘制分隔线"""
        # 清除之前的分隔线
        if hasattr(self, 'separator_lines'):
            for line in self.separator_lines:
                self.canvas.delete(line)
        
        self.separator_lines = []
        
        # 获取时间列的实际宽度
        self.time_column.update_idletasks()
        
        # 计算总宽度
        canvas_width = self.canvas.winfo_width()
        if canvas_width < 10:
            canvas_width = 800
        
        # 绘制每条分隔线
        for slot in range(0, self.num_slots + 1):
            y_pos = slot * self.row_height
            line = self.canvas.create_line(
                0, y_pos,
                canvas_width, y_pos,
                fill=self.colors["time_line"], 
                width=1,
                tags="separator"
            )
            self.separator_lines.append(line)
    
    def _on_mousewheel(self, event):
        """鼠标滚轮滚动"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.root.after(10, self.draw_separators)
    
    def on_slot_click(self, slot: int):
        """时段点击处理"""
        if self.selected_start is None:
            # 第一次点击：选择开始时段
            status = system_proxy.get_slot_status(slot)
            if status.booked_count >= self.total_spots:
                messagebox.showwarning("无法预订", f"时段 {slot} 已满")
                return
            self.selected_start = slot
            self.selected_end = None
            self.update_selection_display()
            self.update_display()
        else:
            # 第二次点击：选择结束时段
            self.selected_end = slot
            
            start = min(self.selected_start, self.selected_end)
            end = max(self.selected_start, self.selected_end)
            slots = list(range(start, end + 1))
            
            # 检查是否有已满时段
            full_slots = []
            for s in slots:
                status = system_proxy.get_slot_status(s)
                if status.booked_count >= self.total_spots:
                    full_slots.append(s)
            
            if full_slots:
                messagebox.showerror("预订失败", f"时段 {full_slots} 已满，无法预订")
            else:
                total_minutes = len(slots) * self.minutes_per_slot
                hours = total_minutes // 60
                minutes = total_minutes % 60
                
                if hours > 0 and minutes > 0:
                    duration_str = f"{hours}小时{minutes}分钟"
                elif hours > 0:
                    duration_str = f"{hours}小时"
                else:
                    duration_str = f"{minutes}分钟"
                
                confirm = messagebox.askyesno(
                    "确认预订",
                    f"确认预订时段 {start} 到 {end}\n"
                    f"共 {len(slots)} 个连续时段（{duration_str}）"
                )
                
                if confirm:
                    next_id = system_proxy.next_user_id
                    success, msg = system_proxy.book(next_id, slots)
                    if success:
                        messagebox.showinfo("预订成功", msg)
                    else:
                        messagebox.showerror("预订失败", msg)
            
            # 清除选择状态
            self.selected_start = None
            self.selected_end = None
            self.update_selection_display()
            self.update_display()
    
    def update_selection_display(self):
        """更新选择状态显示"""
        if self.selected_start is not None:
            self.selection_label.config(
                text=f"已选择开始: 时段 {self.selected_start}，请点击结束时段",
                fg=self.colors["selected_bg"]
            )
        else:
            self.selection_label.config(text="未选择时段", fg=self.colors["text"])
    
    def update_display(self):
        """更新所有时段按钮的颜色"""
        # 更新当前时段（基于模拟时间）
        self.current_slot = self.get_current_slot()
        
        for slot, btn in self.slot_buttons.items():
            bg_color, text_color, status_text, enabled = self.get_slot_color_and_text(slot)
            
            # 检查是否被选中
            is_selected = (self.selected_start == slot)
            
            if is_selected:
                btn.config(
                    bg=self.colors["selected_bg"],
                    fg=self.colors["selected_text"],
                    text=f"时段 {slot} ✓"
                )
            else:
                btn.config(
                    bg=bg_color,
                    fg=text_color,
                    text=f"时段 {slot}"
                )
            
            # 更新状态标签
            if slot in self.status_labels:
                self.status_labels[slot].config(text=status_text, fg=text_color)
            
            # 设置按钮状态
            if not enabled or status_text == "已满":
                btn.config(state=tk.DISABLED, cursor="arrow")
            else:
                btn.config(state=tk.NORMAL, cursor="hand2")
        
        self.root.update_idletasks()
    
    def show_spot_status(self):
        """显示车位状态窗口"""
        spot_window = SpotStatusWindow(self.root, self)
    
    def reset_system(self):
        """重置系统"""
        from tkinter import simpledialog
        
        dialog = tk.Toplevel(self.root)
        dialog.title("重置系统")
        dialog.geometry("400x250")
        dialog.configure(bg=self.colors["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 250) // 2
        dialog.geometry(f"+{x}+{y}")
        
        title_label = tk.Label(
            dialog,
            text="重置系统设置",
            font=("Arial", 14, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"]
        )
        title_label.pack(pady=(20, 10))
        
        info_label = tk.Label(
            dialog,
            text="重置将清除所有预订数据，请输入新配置：",
            font=("Arial", 10),
            bg=self.colors["bg"],
            fg="#666666"
        )
        info_label.pack(pady=(0, 15))
        
        spots_frame = tk.Frame(dialog, bg=self.colors["bg"])
        spots_frame.pack(pady=5)
        
        spots_label = tk.Label(
            spots_frame,
            text="总车位数：",
            font=("Arial", 10),
            bg=self.colors["bg"],
            width=10,
            anchor="e"
        )
        spots_label.pack(side=tk.LEFT)
        
        spots_var = tk.IntVar(value=self.total_spots)
        spots_entry = tk.Entry(
            spots_frame,
            textvariable=spots_var,
            font=("Arial", 10),
            width=15
        )
        spots_entry.pack(side=tk.LEFT, padx=5)
        
        spots_info = tk.Label(
            spots_frame,
            text="(1-1000)",
            font=("Arial", 9),
            bg=self.colors["bg"],
            fg="#888888"
        )
        spots_info.pack(side=tk.LEFT)
        
        slots_frame = tk.Frame(dialog, bg=self.colors["bg"])
        slots_frame.pack(pady=10)
        
        slots_label = tk.Label(
            slots_frame,
            text="时段个数：",
            font=("Arial", 10),
            bg=self.colors["bg"],
            width=10,
            anchor="e"
        )
        slots_label.pack(side=tk.LEFT)
        
        slots_var = tk.IntVar(value=self.num_slots)
        slots_entry = tk.Entry(
            slots_frame,
            textvariable=slots_var,
            font=("Arial", 10),
            width=15
        )
        slots_entry.pack(side=tk.LEFT, padx=5)
        
        slots_info = tk.Label(
            slots_frame,
            text="(1-96)",
            font=("Arial", 9),
            bg=self.colors["bg"],
            fg="#888888"
        )
        slots_info.pack(side=tk.LEFT)
        
        warning_label = tk.Label(
            dialog,
            text="⚠ 警告：重置将清除所有预订数据！",
            font=("Arial", 9),
            bg=self.colors["bg"],
            fg="#d32f2f"
        )
        warning_label.pack(pady=(15, 10))
        
        button_frame = tk.Frame(dialog, bg=self.colors["bg"])
        button_frame.pack(pady=10)
        
        result = [False, None, None]
        
        def on_confirm():
            try:
                new_spots = spots_var.get()
                new_slots = slots_var.get()
                
                if new_spots < 1:
                    messagebox.showwarning("输入错误", "车位数必须大于0")
                    return
                if new_spots > 1000:
                    messagebox.showwarning("输入错误", "车位数不能超过1000")
                    return
                if new_slots < 1:
                    messagebox.showwarning("输入错误", "时段数必须大于0")
                    return
                if new_slots > 96:
                    messagebox.showwarning("输入错误", "时段数不能超过96")
                    return
                
                result[0] = True
                result[1] = new_spots
                result[2] = new_slots
                dialog.destroy()
            except ValueError:
                messagebox.showwarning("输入错误", "请输入有效的数字")
        
        def on_cancel():
            result[0] = False
            dialog.destroy()
        
        confirm_btn = tk.Button(
            button_frame,
            text="确认重置",
            font=("Arial", 10),
            bg="#d32f2f",
            fg="white",
            padx=20,
            pady=5,
            cursor="hand2",
            command=on_confirm
        )
        confirm_btn.pack(side=tk.LEFT, padx=10)
        
        cancel_btn = tk.Button(
            button_frame,
            text="取消",
            font=("Arial", 10),
            bg="#666666",
            fg="white",
            padx=20,
            pady=5,
            cursor="hand2",
            command=on_cancel
        )
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        spots_entry.bind("<Return>", lambda e: slots_entry.focus())
        slots_entry.bind("<Return>", lambda e: on_confirm())
        
        self.root.wait_window(dialog)
        
        if result[0]:
            new_total_spots = result[1]
            new_num_slots = result[2]
            
            # 更新实例变量
            self.total_spots = new_total_spots
            self.num_slots = new_num_slots
            
            # 重新初始化系统代理（这会创建新的 ParkingSystem）
            system_proxy.init_system(new_total_spots, new_num_slots)
            
            # 重新注册刷新回调（因为 init_system 可能清空了回调）
            system_proxy.register_refresh_callback(self.update_display)
            
            # 更新分钟数
            self.minutes_per_slot = system_proxy.minutes_per_slot
            
            # 清除选择状态
            self.selected_start = None
            self.selected_end = None
            
            # 更新窗口标题
            self.root.title(f"停车场预订系统 - {new_total_spots}车位 - {new_num_slots}时段")
            
            # 重建界面
            self.rebuild_ui()
            
            # 更新当前时段和显示
            self.current_slot = self.get_current_slot()
            self.update_time_display()
            self.update_display()
            
            messagebox.showinfo("重置完成", f"系统已重置为：\n  车位数: {new_total_spots}\n  时段数: {new_num_slots}")
    
    def rebuild_ui(self):
        """重建界面（当车位数或时段数改变时）"""
        # 清除整个滚动区域的所有内容
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # 重新创建左右两列的容器
        content_frame = tk.Frame(self.scrollable_frame, bg=self.colors["bg"])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧时间列
        self.time_column = tk.Frame(content_frame, bg=self.colors["bg"], width=100)
        self.time_column.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.time_column.pack_propagate(False)
        
        # 右侧时段列
        self.slot_column = tk.Frame(content_frame, bg=self.colors["bg"])
        self.slot_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 清空按钮引用
        self.slot_buttons = {}
        self.status_labels = {}
        self.time_marker_frames = {}
        
        # 创建所有行（使用新的 num_slots）
        for slot in range(1, self.num_slots + 1):
            # 左侧：时间标记行
            time_row = tk.Frame(self.time_column, bg=self.colors["time_bg"], height=self.row_height)
            time_row.pack(fill=tk.X, pady=0)
            time_row.pack_propagate(False)
            
            # 时间文字
            time_text = self.get_time_marker(slot)
            if time_text:
                time_label = tk.Label(
                    time_row,
                    text=time_text,
                    font=("Arial", 9),
                    fg="#666666",
                    bg=self.colors["time_bg"],
                    anchor="e"
                )
                time_label.pack(side=tk.TOP, fill=tk.X, padx=5)
            else:
                empty_label = tk.Label(
                    time_row,
                    text="",
                    bg=self.colors["time_bg"]
                )
                empty_label.pack(side=tk.TOP, fill=tk.X)
            
            # 右侧：时段按钮行
            slot_row = tk.Frame(self.slot_column, bg=self.colors["bg"], height=self.row_height)
            slot_row.pack(fill=tk.X, pady=0)
            slot_row.pack_propagate(False)
            
            # 时段按钮
            btn = tk.Button(
                slot_row,
                text=f"时段 {slot}",
                font=("Arial", 9),
                cursor="hand2",
                command=lambda s=slot: self.on_slot_click(s)
            )
            btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            # 状态标签
            status_label = tk.Label(
                slot_row,
                text="",
                width=8,
                font=("Arial", 9),
                bg=self.colors["bg"],
                anchor="center"
            )
            status_label.pack(side=tk.RIGHT, padx=(0, 10))
            
            self.slot_buttons[slot] = btn
            self.status_labels[slot] = status_label
            self.time_marker_frames[slot] = time_row
        
        # 重新绘制分隔线
        self.draw_separators()
        
        # 重新绑定事件（移除旧的绑定，添加新的）
        # 注意：不需要重新绑定 canvas 的配置事件，因为 canvas 本身没有改变
        
        # 强制更新画布的滚动区域
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 更新显示
        self.update_display()
        
        # 刷新一下画布
        self.canvas.update_idletasks()
    
    def run(self):
        """运行程序"""
        self.root.mainloop()


def main():
    TOTAL_SPOTS = 100
    NUM_SLOTS = 24
    
    app = ParkingGUI(TOTAL_SPOTS, NUM_SLOTS)
    app.run()


if __name__ == "__main__":
    main()