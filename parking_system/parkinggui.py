import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from core.parking_system import ParkingSystem


class ParkingGUI:
    def __init__(self, total_spots: int = 100, num_slots: int = 24):
        self.total_spots = total_spots
        self.num_slots = num_slots
        self.system = ParkingSystem(total_spots, num_slots)
        
        # 计算每个时段的时长（分钟）
        self.minutes_per_slot = 60 * 24 // self.num_slots
        
        self.selected_start: int = None
        self.selected_end: int = None
        self.next_user_id = 1
        
        # 固定行高（像素）
        self.row_height = 50
        
        self.root = tk.Tk()
        self.root.title(f"停车场预订系统 - {total_spots}车位")
        self.root.geometry("800x700")
        
        # Outlook 风格颜色
        self.colors = {
            "bg": "#f0f0f0",
            "header_bg": "#e8e8e8",
            "time_bg": "#fafafa",
            "selected_bg": "#0078d4",
            "selected_text": "#ffffff",
            "full_bg": "#ff0000",
            "full_text": "#d32f2f",
            "warning_bg": "#ffff00",
            "warning_text": "#e67e22",
            "good_bg": "#00ff00",
            "good_text": "#2e7d32",
            "normal_bg": "#ffffff",
            "normal_text": "#333333",
            "text": "#333333",
            "border": "#d0d0d0",
            "time_line": "#e0e0e0"
        }
        
        self.root.configure(bg=self.colors["bg"])
        
        self.create_widgets()
        self.update_display()
        
        # 获取当前时段编号
        self.current_slot = self.get_current_slot()
        # 每秒刷新一次显示（更新时间状态）
        self.refresh_display()

    def refresh_display(self):
        """每秒刷新显示（更新当前时段状态）"""
        self.current_slot = self.get_current_slot()
        self.update_display()
        self.root.after(1000, self.refresh_display)
    
    def get_current_slot(self) -> int:
        """获取当前时间对应的时段编号"""
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        # 计算当前处于哪个时段（时段从1开始）
        slot = current_minutes // self.minutes_per_slot + 1
        # 边界处理
        if slot < 1:
            slot = 1
        if slot > self.num_slots:
            slot = self.num_slots + 1  # 超出最后一个时段
        return slot

    def get_slot_color_and_text(self, slot: int) -> tuple:
        """根据空闲比例返回 (背景色, 文字色, 状态文字)"""
        # 检查是否已过期
        if slot < self.current_slot:
            return self.colors["bg"], self.colors["bg"], "已过", False
        
        status = self.system.get_slot_status(slot)
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
    
    def get_current_date_str(self) -> str:
        """获取当前日期时间字符串（精确到秒）"""
        now = datetime.now()
        weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return f"{now.year}年{now.month}月{now.day}日 {weekday_map[now.weekday()]} {now.hour:02d}:{now.minute:02d}:{now.second:02d}"

    def update_date(self):
        """实时更新日期时间显示（每秒刷新）"""
        self.date_label.config(text=self.get_current_date_str())
        self.root.after(1000, self.update_date)  # 每秒更新一次
    
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
        
        # 动态日期显示
        self.date_label = tk.Label(
            header_frame,
            text=self.get_current_date_str(),
            font=("Arial", 11),
            fg="#666666",
            bg=self.colors["header_bg"]
        )
        self.date_label.pack(side=tk.RIGHT, padx=20)
        
        # 每小时更新日期
        self.update_date()
        
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
        
        # 重置按钮
        reset_btn = tk.Button(
            control_frame,
            text="重置所有预订",
            font=("Arial", 10),
            bg="#d32f2f",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.reset_system
        )
        reset_btn.pack(side=tk.RIGHT)
        
        # 图例
        legend_frame = tk.Frame(self.root, bg=self.colors["bg"])
        legend_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        legends = [
            (" 充足", self.colors["good_bg"], self.colors["good_text"]),
            (" 紧张", self.colors["warning_bg"], self.colors["warning_text"]),
            (" 已满", self.colors["full_bg"], self.colors["full_text"]),
            (" 已过", self.colors["bg"], "#999999")
        ]
        
        for text, bg, fg in legends:
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
        time_col_width = self.time_column.winfo_width()
        
        # 计算总宽度
        canvas_width = self.canvas.winfo_width()
        if canvas_width < 10:
            canvas_width = 800
        
        # 绘制每条分隔线
        for slot in range(0, self.num_slots + 1):
            # 跳过第一和最后一个刻度（避免超界）
            if slot == 0 or slot == self.num_slots:
                # 绘制淡化的分隔线
                y_pos = slot * self.row_height
                line = self.canvas.create_line(
                    0, y_pos,
                    canvas_width, y_pos,
                    fill=self.colors["time_line"], 
                    width=1,
                    tags="separator"
                )
                self.separator_lines.append(line)
                continue
            
            # 绘制正常分隔线
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
        # 滚动时重绘分隔线，确保位置正确
        self.root.after(10, self.draw_separators)
    
    def on_slot_click(self, slot: int):
        """时段点击处理"""
        if self.selected_start is None:
            # 第一次点击：选择开始时段
            status = self.system.get_slot_status(slot)
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
                status = self.system.get_slot_status(s)
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
                    success, msg = self.system.book(self.next_user_id, slots)
                    if success:
                        self.next_user_id += 1
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
        # 更新当前时段（实时刷新）
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
    
    def reset_system(self):
        """重置系统"""
        if messagebox.askyesno("确认重置", "确定要重置所有预订吗？所有数据将丢失。"):
            self.system.reset()
            self.next_user_id = 1
            self.selected_start = None
            self.selected_end = None
            self.update_selection_display()
            self.update_display()
            messagebox.showinfo("重置完成", "系统已重置")
    
    def run(self):
        """运行程序"""
        self.root.mainloop()


def main():
    TOTAL_SPOTS = 2
    NUM_SLOTS = 3  # 24个时段 = 每小时1个时段
    
    app = ParkingGUI(TOTAL_SPOTS, NUM_SLOTS)
    app.run()


if __name__ == "__main__":
    main()