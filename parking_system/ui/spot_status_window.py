import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.system_proxy import system_proxy
from ui.shared_utils import COLORS, get_spot_status_legends


class SpotStatusWindow:
    """车位状态显示窗口"""
    
    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        
        self.window = tk.Toplevel(parent)
        self.window.title("车位状态查看 - 时间模拟")
        self.window.geometry("1000x700")
        self.window.configure(bg=COLORS["bg"])
        
        system_proxy.register_refresh_callback(self.refresh_display)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.create_widgets()
        self.refresh_display()
    
    def on_close(self):
        system_proxy.unregister_refresh_callback(self.refresh_display)
        self.window.destroy()
    
    def get_time_info_text(self) -> str:
        total_points = system_proxy.total_time_points
        time_point = system_proxy.time_point
        
        if total_points == 0:
            return f"[时间] 时间点: {time_point} / ?\n时段数量未设置"
        
        progress = time_point / total_points * 100 if total_points > 0 else 0
        return f"[时间] 时间点: {time_point} / {total_points}  ({progress:.0f}%)\n{system_proxy.get_time_point_description()}"
    
    def create_widgets(self):
        # 标题栏
        title_frame = tk.Frame(self.window, bg=COLORS["header_bg"])
        title_frame.pack(fill=tk.X, padx=0, pady=0)
        
        title_label = tk.Label(
            title_frame,
            text="车位占用状态 - 时间模拟",
            font=("Arial", 14, "bold"),
            bg=COLORS["header_bg"],
            fg=COLORS["text"]
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        button_frame = tk.Frame(title_frame, bg=COLORS["header_bg"])
        button_frame.pack(side=tk.RIGHT, padx=20)
        
        self.advance_btn = tk.Button(
            button_frame,
            text="前进时间",
            font=("Arial", 11, "bold"),
            bg="#0078d4",
            fg="white",
            padx=20,
            pady=5,
            cursor="hand2",
            command=self.advance_time
        )
        self.advance_btn.pack(side=tk.LEFT, padx=5)
        
        self.auto_advance = False
        self.auto_btn = tk.Button(
            button_frame,
            text="自动前进",
            font=("Arial", 10),
            bg="#28a745",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.toggle_auto_advance
        )
        self.auto_btn.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = tk.Button(
            button_frame,
            text="刷新",
            font=("Arial", 10),
            bg="#ffc107",
            fg="#333333",
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.refresh_display
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        process_overtime_btn = tk.Button(
            button_frame,
            text="处理超时",
            font=("Arial", 10),
            bg="#fd7e14",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.process_all_overtime_users
        )
        process_overtime_btn.pack(side=tk.LEFT, padx=5)
        
        main_frame = tk.Frame(self.window, bg=COLORS["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = tk.Frame(main_frame, bg=COLORS["bg"])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        left_label = tk.Label(
            left_frame,
            text="车位占用情况",
            font=("Arial", 11, "bold"),
            bg=COLORS["bg"]
        )
        left_label.pack(anchor="w", pady=(0, 5))
        
        canvas_frame = tk.Frame(left_frame, bg=COLORS["bg"])
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS["bg"])
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=self.canvas.winfo_width())
        
        def on_canvas_configure(event):
            self.canvas.itemconfig(1, width=event.width - 10)
        
        self.canvas.bind("<Configure>", on_canvas_configure)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        self.spot_buttons = {}
        
        right_frame = tk.Frame(main_frame, bg=COLORS["bg"], width=280)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        right_frame.pack_propagate(False)
        
        time_info_frame = tk.Frame(right_frame, bg=COLORS["selected_bg"], height=60)
        time_info_frame.pack(fill=tk.X, pady=(0, 10))
        time_info_frame.pack_propagate(False)
        
        self.time_info_label = tk.Label(
            time_info_frame,
            text=self.get_time_info_text(),
            font=("Arial", 10, "bold"),
            bg=COLORS["selected_bg"],
            fg="white",
            justify=tk.CENTER
        )
        self.time_info_label.pack(expand=True)
        
        overtime_label = tk.Label(
            right_frame,
            text="超时用户",
            font=("Arial", 11, "bold"),
            bg=COLORS["bg"]
        )
        overtime_label.pack(anchor="w", pady=(10, 5))
        
        overtime_frame = tk.Frame(right_frame, bg="white", relief=tk.SUNKEN, bd=1, height=150)
        overtime_frame.pack(fill=tk.X, pady=(0, 10))
        overtime_frame.pack_propagate(False)
        
        overtime_columns = ("用户ID", "车位", "超时时段", "操作")
        self.overtime_tree = ttk.Treeview(overtime_frame, columns=overtime_columns, show="headings", height=5)
        
        self.overtime_tree.heading("用户ID", text="用户ID")
        self.overtime_tree.heading("车位", text="车位")
        self.overtime_tree.heading("超时时段", text="超时时段")
        self.overtime_tree.heading("操作", text="操作")
        
        self.overtime_tree.column("用户ID", width=60, anchor="center")
        self.overtime_tree.column("车位", width=50, anchor="center")
        self.overtime_tree.column("超时时段", width=100, anchor="center")
        self.overtime_tree.column("操作", width=50, anchor="center")
        
        def on_overtime_click(event):
            item = self.overtime_tree.selection()[0] if self.overtime_tree.selection() else None
            if item:
                values = self.overtime_tree.item(item, 'values')
                if len(values) >= 4:
                    region = self.overtime_tree.identify_region(event.x, event.y)
                    if region == "cell":
                        col = self.overtime_tree.identify_column(event.x)
                        if col == "#4":
                            user_id = int(values[0])
                            self.force_depart_user(user_id)
        
        self.overtime_tree.bind("<ButtonRelease-1>", on_overtime_click)
        
        scrollbar_overtime = ttk.Scrollbar(overtime_frame, orient=tk.VERTICAL, command=self.overtime_tree.yview)
        self.overtime_tree.configure(yscrollcommand=scrollbar_overtime.set)
        
        self.overtime_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_overtime.pack(side=tk.RIGHT, fill=tk.Y)
        
        right_label = tk.Label(
            right_frame,
            text="等待分配用户",
            font=("Arial", 11, "bold"),
            bg=COLORS["bg"]
        )
        right_label.pack(anchor="w", pady=(0, 5))
        
        waiting_frame = tk.Frame(right_frame, bg="white", relief=tk.SUNKEN, bd=1)
        waiting_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("用户ID", "预订时段", "时长")
        self.waiting_tree = ttk.Treeview(waiting_frame, columns=columns, show="headings", height=20)
        
        self.waiting_tree.heading("用户ID", text="用户ID")
        self.waiting_tree.heading("预订时段", text="预订时段")
        self.waiting_tree.heading("时长", text="时长")
        
        self.waiting_tree.column("用户ID", width=70, anchor="center")
        self.waiting_tree.column("预订时段", width=120, anchor="center")
        self.waiting_tree.column("时长", width=50, anchor="center")
        
        scrollbar_tree = ttk.Scrollbar(waiting_frame, orient=tk.VERTICAL, command=self.waiting_tree.yview)
        self.waiting_tree.configure(yscrollcommand=scrollbar_tree.set)
        
        self.waiting_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_tree.pack(side=tk.RIGHT, fill=tk.Y)
        
        legend_frame = tk.Frame(self.window, bg=COLORS["bg"])
        legend_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        for text, bg, fg in get_spot_status_legends():
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
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def process_all_overtime_users(self):
        overtime_users = self.get_overtime_users()
        
        if not overtime_users:
            messagebox.showinfo("提示", "没有超时用户")
            return
        
        msg = f"发现 {len(overtime_users)} 个超时用户：\n\n"
        for user in overtime_users:
            overtime_duration = system_proxy.time_point // 2 - user.slots[-1]
            msg += f"  * 用户 {user.id}: 车位 {user.spot_assigned}, 已超时 {overtime_duration} 段\n"
        msg += "\n是否强制让所有超时用户离开？"
        
        if messagebox.askyesno("处理超时用户", msg):
            for user in overtime_users:
                success, msg2 = system_proxy.depart(user.id, system_proxy.time_point // 2, False)
                if success:
                    print(f"用户 {user.id} 强制离开")
                else:
                    print(f"用户 {user.id} 离开失败: {msg2}")
            self.refresh_display()
            messagebox.showinfo("完成", f"已处理 {len(overtime_users)} 个超时用户")
    
    def get_overtime_users(self):
        overtime_users = []
        current_slot = system_proxy.time_point // 2
        
        for user in system_proxy.users.values():
            if user.checked_in and not user.checked_out and user.spot_assigned:
                if user.overtime:
                    overtime_users.append(user)
                elif user.slots[-1] < current_slot:
                    overtime_users.append(user)
        
        return overtime_users
    
    def force_depart_user(self, user_id: int):
        user = system_proxy.users.get(user_id)
        if not user:
            messagebox.showwarning("错误", f"用户 {user_id} 不存在")
            return
        
        if not user.checked_in:
            messagebox.showwarning("错误", f"用户 {user_id} 尚未到达")
            return
        
        if user.checked_out:
            messagebox.showwarning("错误", f"用户 {user_id} 已经离开")
            return
        
        confirm = messagebox.askyesno(
            "确认强制离开",
            f"确定要强制用户 {user_id} 离开吗？\n"
            f"车位: {user.spot_assigned}\n"
            f"预订时段: {user.slots[0]}-{user.slots[-1]}\n"
            f"超时状态: {'是' if user.overtime else '否'}"
        )
        
        if confirm:
            current_slot = system_proxy.time_point // 2
            success, msg = system_proxy.depart(user_id, current_slot, False)
            if success:
                messagebox.showinfo("成功", f"用户 {user_id} 已强制离开")
                self.refresh_display()
            else:
                messagebox.showerror("失败", f"用户 {user_id} 离开失败: {msg}")
    
    def advance_time(self):
        total_points = system_proxy.total_time_points
        time_point = system_proxy.time_point
        
        if total_points == 0:
            messagebox.showerror("错误", "时段数量未设置，无法前进时间！")
            return False
        
        if time_point >= total_points:
            messagebox.showinfo("提示", "所有时间点已处理完毕！")
            if self.auto_advance:
                self.toggle_auto_advance()
            return False
        
        slot_index = time_point // 2
        is_start = (time_point % 2 == 0)
        
        if is_start:
            self.process_time_start(slot_index)
        else:
            self.process_time_end(slot_index)
        
        system_proxy.advance_time(time_point + 1)
        
        self.refresh_display()
        
        if system_proxy.time_point >= total_points:
            self.advance_btn.config(text="已完成", state=tk.DISABLED)
            if self.auto_advance:
                self.toggle_auto_advance()
            messagebox.showinfo("完成", "所有时间点已处理完毕！")
        
        return True
    
    def process_time_start(self, time_slot: int):
        arriving_users = []
        for user in system_proxy.get_all_users():
            if not user.checked_in and not user.checked_out:
                if time_slot + 1 == user.slots[0]:
                    arriving_users.append(user)
        
        if arriving_users:
            msg = f"[时段开始] 时段 {time_slot + 1} ({system_proxy.get_time_range(time_slot)}) 开始\n\n"
            msg += f"需要分配车位的用户（共 {len(arriving_users)} 人）：\n"
            for user in arriving_users:
                msg += f"  * 用户 {user.id}: 预订时段 {user.slots[0]}-{user.slots[-1]}\n"
            msg += f"\n是否继续分配车位？"
            
            result = messagebox.askyesno("到达用户", msg)
            
            if result:
                for user in arriving_users:
                    success, msg2 = system_proxy.arrive_smart(user.id, time_slot)
                    if success:
                        print(f"用户 {user.id} 到达，{msg2}")
                    else:
                        print(f"用户 {user.id} 分配失败: {msg2}")
                        messagebox.showwarning("分配失败", f"用户 {user.id} 无法分配车位: {msg2}")
    
    def process_time_end(self, time_slot: int):
        leaving_users = []
        for user in system_proxy.get_all_users():
            if user.checked_in and not user.checked_out:
                if time_slot + 1 == user.slots[-1]:
                    leaving_users.append(user)
        
        if leaving_users:
            msg = f"[时段结束] 时段 {time_slot + 1} ({system_proxy.get_time_range(time_slot)}) 结束\n\n"
            msg += f"需要处理的用户（共 {len(leaving_users)} 人）：\n"
            for user in leaving_users:
                spot_display = str(user.spot_assigned) if user.spot_assigned is not None else "未分配"
                msg += f"  * 用户 {user.id} (车位 {spot_display}) - 预订结束\n"
            msg += f"\n是否让这些用户离开？\n(选择'否'表示让用户超时继续停车)"
            
            result = messagebox.askyesno("离开用户", msg)
            
            for user in leaving_users:
                if user.spot_assigned is None:
                    continue
                overtime_choice = not result
                success, msg2 = system_proxy.depart(user.id, time_slot, overtime_choice)
                if success:
                    if overtime_choice:
                        print(f"用户 {user.id} 选择继续停车（超时）")
                        messagebox.showinfo("超时", f"用户 {user.id} 将继续停车（超时状态）")
                    else:
                        print(f"用户 {user.id} 离开")
                else:
                    print(f"用户 {user.id} 处理失败: {msg2}")
    
    def toggle_auto_advance(self):
        self.auto_advance = not self.auto_advance
        if self.auto_advance:
            self.auto_btn.config(text="暂停", bg="#dc3545")
            self.auto_advance_step()
        else:
            self.auto_btn.config(text="自动前进", bg="#28a745")
    
    def auto_advance_step(self):
        if self.auto_advance and system_proxy.time_point < system_proxy.total_time_points:
            self.advance_time()
            self.window.after(1000, self.auto_advance_step)
    
    def refresh_display(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.spot_buttons.clear()
        self.time_info_label.config(text=self.get_time_info_text())
        
        users = system_proxy.users
        total_spots = system_proxy.total_spots
        
        occupied_spots = {}
        for user in users.values():
            if user.checked_in and not user.checked_out and user.spot_assigned:
                spot = user.spot_assigned
                if spot not in occupied_spots:
                    occupied_spots[spot] = []
                
                if user.overtime and hasattr(user, 'actual_end_slot') and user.actual_end_slot is not None:
                    slot_range = f"{user.slots[0]}-{user.actual_end_slot}"
                else:
                    slot_range = f"{user.slots[0]}-{user.slots[-1]}"
                
                occupied_spots[spot].append({
                    'id': user.id,
                    'range': slot_range,
                    'overtime': user.overtime
                })
        
        self.scrollable_frame.update_idletasks()
        available_width = self.canvas.winfo_width() - 20
        if available_width < 100:
            available_width = 800
        
        btn_width = 85
        cols_per_row = max(1, available_width // btn_width)
        cols_per_row = min(cols_per_row, 15)
        
        for i in range(0, total_spots, cols_per_row):
            row_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg"])
            row_frame.pack(pady=2, fill=tk.X)
            
            for j in range(cols_per_row):
                spot_num = i + j + 1
                if spot_num > total_spots:
                    break
                
                if spot_num in occupied_spots:
                    has_overtime = any(occ['overtime'] for occ in occupied_spots[spot_num])
                    
                    if has_overtime:
                        bg_color = "#ff0000"
                        fg_color = "#ffffff"
                    else:
                        bg_color = "#ffff00"
                        fg_color = "#333333"
                    
                    occupiers = occupied_spots[spot_num]
                    if len(occupiers) == 1:
                        occ = occupiers[0]
                        text = f"{spot_num}\n用户{occ['id']}\n{occ['range']}"
                    else:
                        ids = ','.join(str(occ['id']) for occ in occupiers[:2])
                        text = f"{spot_num}\n用户{ids}"
                        if len(occupiers) > 2:
                            text += f"等{len(occupiers)}人"
                else:
                    bg_color = "#00ff00"
                    fg_color = "#333333"
                    text = f"{spot_num}\n空闲"
                
                btn = tk.Button(
                    row_frame,
                    text=text,
                    width=10,
                    height=2,
                    font=("Arial", 8),
                    bg=bg_color,
                    fg=fg_color,
                    cursor="hand2",
                    command=lambda s=spot_num: self.show_spot_detail(s)
                )
                btn.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)
                self.spot_buttons[spot_num] = btn
        
        self.refresh_waiting_users()
        self.refresh_overtime_users()
    
    def refresh_waiting_users(self):
        for item in self.waiting_tree.get_children():
            self.waiting_tree.delete(item)
        
        users = system_proxy.users
        current_slot = system_proxy.time_point // 2
        
        waiting_users = []
        for user in users.values():
            if user.checked_in and not user.spot_assigned:
                waiting_users.append(user)
            elif not user.checked_in and not user.checked_out:
                if user.slots[0] > current_slot:
                    waiting_users.append(user)
        
        waiting_users.sort(key=lambda u: u.slots[0])
        
        for user in waiting_users:
            status = "已到达" if user.checked_in else "待到达"
            duration = len(user.slots)
            slots_str = f"{user.slots[0]}-{user.slots[-1]}"
            
            self.waiting_tree.insert("", "end", values=(
                f"{user.id}({status})",
                slots_str,
                f"{duration}段"
            ))
        
        if not waiting_users:
            self.waiting_tree.insert("", "end", values=("无", "无", "无"))
    
    def refresh_overtime_users(self):
        for item in self.overtime_tree.get_children():
            self.overtime_tree.delete(item)
        
        current_slot = system_proxy.time_point // 2
        overtime_users = []
        
        for user in system_proxy.users.values():
            if user.checked_in and not user.checked_out and user.spot_assigned:
                if user.overtime:
                    overtime_duration = current_slot - (user.overtime_start if user.overtime_start else user.slots[-1])
                    overtime_users.append((user, overtime_duration))
                elif user.slots[-1] < current_slot:
                    overtime_duration = current_slot - user.slots[-1]
                    overtime_users.append((user, overtime_duration))
        
        for user, duration in overtime_users:
            self.overtime_tree.insert("", "end", values=(
                user.id,
                user.spot_assigned,
                f"{duration}段",
                "离开"
            ))
        
        if not overtime_users:
            self.overtime_tree.insert("", "end", values=("无", "无", "无", ""))
    
    def show_spot_detail(self, spot: int):
        detail_window = tk.Toplevel(self.window)
        detail_window.title(f"车位 {spot} 详细信息")
        detail_window.geometry("450x400")
        detail_window.configure(bg=COLORS["bg"])
        
        occupants = []
        for user in system_proxy.users.values():
            if user.checked_in and not user.checked_out and user.spot_assigned == spot:
                occupants.append(user)
        
        title_label = tk.Label(
            detail_window,
            text=f"车位 {spot} 占用详情",
            font=("Arial", 14, "bold"),
            bg=COLORS["bg"]
        )
        title_label.pack(pady=10)
        
        if occupants:
            list_frame = tk.Frame(detail_window, bg=COLORS["bg"])
            list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            for user in occupants:
                info_frame = tk.Frame(list_frame, bg="white", relief=tk.RIDGE, bd=1)
                info_frame.pack(fill=tk.X, pady=5)
                
                if user.overtime:
                    end_slot = user.actual_end_slot if hasattr(user, 'actual_end_slot') and user.actual_end_slot else user.slots[-1]
                    slot_range = f"{user.slots[0]}-{end_slot} (超时)"
                    status_text = "超时"
                else:
                    slot_range = f"{user.slots[0]}-{user.slots[-1]}"
                    status_text = "正常"
                
                info_text = f"用户 {user.id}\n占用时段: {slot_range}\n状态: {status_text}"
                info_label = tk.Label(
                    info_frame,
                    text=info_text,
                    font=("Arial", 10),
                    bg="white",
                    justify=tk.LEFT
                )
                info_label.pack(padx=10, pady=10, side=tk.LEFT)
                
                depart_btn = tk.Button(
                    info_frame,
                    text="强制离开",
                    font=("Arial", 9),
                    bg="#d32f2f",
                    fg="white",
                    padx=10,
                    pady=5,
                    cursor="hand2",
                    command=lambda u=user: self.force_depart_from_detail(u.id, detail_window)
                )
                depart_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        else:
            empty_label = tk.Label(
                detail_window,
                text="该车位当前空闲",
                font=("Arial", 12),
                bg=COLORS["bg"],
                fg="#666666"
            )
            empty_label.pack(expand=True)
        
        close_btn = tk.Button(
            detail_window,
            text="关闭",
            font=("Arial", 10),
            bg=COLORS["selected_bg"],
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2",
            command=detail_window.destroy
        )
        close_btn.pack(pady=10)
    
    def force_depart_from_detail(self, user_id: int, detail_window):
        user = system_proxy.users.get(user_id)
        if not user:
            messagebox.showwarning("错误", f"用户 {user_id} 不存在")
            return
        
        confirm = messagebox.askyesno(
            "确认强制离开",
            f"确定要强制用户 {user_id} 离开吗？\n"
            f"车位: {user.spot_assigned}\n"
            f"预订时段: {user.slots[0]}-{user.slots[-1]}"
        )
        
        if confirm:
            current_slot = system_proxy.time_point // 2
            success, msg = system_proxy.depart(user_id, current_slot, False)
            if success:
                messagebox.showinfo("成功", f"用户 {user_id} 已强制离开")
                detail_window.destroy()
                self.refresh_display()
            else:
                messagebox.showerror("失败", f"用户 {user_id} 离开失败: {msg}")