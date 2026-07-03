import win32gui
import win32con
import win32api

import whitelist

ID_LIST = 101
ID_BTN_ADD = 102
ID_BTN_CLOSE = 103

ID_EDIT_TITLE = 201
ID_EDIT_EXE = 202
ID_EDIT_CLASS = 203
ID_BTN_OK = 204
ID_BTN_CANCEL = 205

STATS_CLASS = 'Close360AdStatsDlg'
WL_CLASS = 'Close360AdWlDlg'

_stats_dlg_map = {}
_wl_dlg_map = {}


def _pump():
    win32gui.PumpMessages()


def _stats_wndproc(hwnd, msg, wparam, lparam):
    dlg = _stats_dlg_map.get(hwnd)

    if msg == win32con.WM_COMMAND:
        if wparam == ID_BTN_CLOSE:
            win32gui.DestroyWindow(hwnd)
        elif wparam == ID_BTN_ADD and dlg:
            dlg._on_add()
        elif wparam == ID_LIST:
            hi = (wparam >> 16) & 0xFFFF
            if hi == win32con.LBN_DBLCLK and dlg:
                dlg._on_add()
    elif msg == win32con.WM_SIZE and dlg:
        dlg._on_size()
    elif msg == win32con.WM_CLOSE:
        win32gui.DestroyWindow(hwnd)
    elif msg == win32con.WM_DESTROY:
        _stats_dlg_map.pop(hwnd, None)
        win32gui.PostQuitMessage(0)

    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


class StatsDialog:
    def __init__(self, entries):
        self.entries = entries
        self.hwnd = 0
        self.listbox = 0
        self.btn_add = 0
        self.btn_close = 0

    def run(self):
        self._register()
        hinst = win32api.GetModuleHandle(None)

        self.hwnd = win32gui.CreateWindow(
            STATS_CLASS, 'Close360Ad - \u5173\u95ed\u8bb0\u5f55',
            win32con.WS_OVERLAPPEDWINDOW & ~0x00030000,
            200, 200, 720, 460,
            0, 0, hinst, None,
        )
        _stats_dlg_map[self.hwnd] = self
        self._create_controls()
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        _pump()

    def _register(self):
        try:
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = _stats_wndproc
            wc.hInstance = win32api.GetModuleHandle(None)
            wc.hbrBackground = win32con.COLOR_BTNFACE + 1
            wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
            wc.lpszClassName = STATS_CLASS
            win32gui.RegisterClass(wc)
        except win32gui.error:
            pass

    def _create_controls(self):
        rect = win32gui.GetClientRect(self.hwnd)
        cw, ch = rect[2], rect[3]

        self.listbox = win32gui.CreateWindowEx(
            0, 'LISTBOX', '',
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_VSCROLL |
            win32con.WS_BORDER | win32con.LBS_NOTIFY,
            10, 10, cw - 20, ch - 50,
            self.hwnd, ID_LIST, win32api.GetModuleHandle(None), None,
        )

        font = win32gui.SendMessage(self.hwnd, win32con.WM_GETFONT, 0, 0)
        if font:
            win32gui.SendMessage(self.listbox, win32con.WM_SETFONT, font, 1)

        if self.entries:
            for i, (t, title, cls, exe) in enumerate(self.entries):
                text = f'[{t}] {title or "(\u65e0\u6807\u9898)"}  |  {cls}  |  {exe}'
                win32gui.SendMessage(self.listbox, win32con.LB_ADDSTRING, 0, text)
                win32gui.SendMessage(self.listbox, win32con.LB_SETITEMDATA, i, i)
        else:
            win32gui.SendMessage(
                self.listbox, win32con.LB_ADDSTRING, 0,
                '\u8fd8\u6ca1\u6709\u5173\u95ed\u8fc7\u5e7f\u544a\u7a97\u53e3',
            )

        self.btn_add = win32gui.CreateWindowEx(
            0, 'BUTTON', '\u52a0\u5165\u767d\u540d\u5355',
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
            cw - 190, ch - 35, 85, 25,
            self.hwnd, ID_BTN_ADD, win32api.GetModuleHandle(None), None,
        )

        self.btn_close = win32gui.CreateWindowEx(
            0, 'BUTTON', '\u5173\u95ed',
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
            cw - 95, ch - 35, 85, 25,
            self.hwnd, ID_BTN_CLOSE, win32api.GetModuleHandle(None), None,
        )

    def _on_size(self):
        if not win32gui.IsWindow(self.listbox):
            return
        rect = win32gui.GetClientRect(self.hwnd)
        cw, ch = rect[2], rect[3]
        win32gui.SetWindowPos(
            self.listbox, 0, 10, 10, cw - 20, ch - 50,
            win32con.SWP_NOZORDER,
        )
        win32gui.SetWindowPos(
            self.btn_add, 0, cw - 190, ch - 35, 85, 25,
            win32con.SWP_NOZORDER,
        )
        win32gui.SetWindowPos(
            self.btn_close, 0, cw - 95, ch - 35, 85, 25,
            win32con.SWP_NOZORDER,
        )

    def _get_selected_entry(self):
        idx = win32gui.SendMessage(self.listbox, win32con.LB_GETCURSEL, 0, 0)
        if idx == win32con.LB_ERR:
            return None
        if not self.entries:
            return None
        data = win32gui.SendMessage(self.listbox, win32con.LB_GETITEMDATA, idx, 0)
        if data == win32con.LB_ERR:
            return None
        if 0 <= data < len(self.entries):
            return self.entries[data]
        return None

    def _on_add(self):
        entry = self._get_selected_entry()
        if not entry:
            win32gui.MessageBox(
                self.hwnd,
                '\u8bf7\u5148\u5728\u5217\u8868\u4e2d\u9009\u62e9\u4e00\u6761\u8bb0\u5f55',
                '\u63d0\u793a',
                win32con.MB_OK | win32con.MB_ICONINFORMATION,
            )
            return
        win32gui.EnableWindow(self.hwnd, False)
        self._show_sub_dialog(entry)
        win32gui.EnableWindow(self.hwnd, True)
        win32gui.SetFocus(self.hwnd)

    def _show_sub_dialog(self, entry):
        dlg = SubDialog(entry, self.hwnd)
        dlg.run()


def _wl_wndproc(hwnd, msg, wparam, lparam):
    dlg = _wl_dlg_map.get(hwnd)

    if msg == win32con.WM_COMMAND:
        if wparam == ID_BTN_OK and dlg:
            new_title = win32gui.GetWindowText(dlg.edit_title)
            new_exe = win32gui.GetWindowText(dlg.edit_exe)
            new_cls = win32gui.GetWindowText(dlg.edit_cls)
            whitelist.add_rule(new_title, new_exe, new_cls)
            win32gui.MessageBox(
                hwnd,
                '\u767d\u540d\u5355\u89c4\u5219\u5df2\u4fdd\u5b58',
                '\u63d0\u793a',
                win32con.MB_OK | win32con.MB_ICONINFORMATION,
            )
            win32gui.DestroyWindow(hwnd)
        elif wparam == ID_BTN_CANCEL:
            win32gui.DestroyWindow(hwnd)
    elif msg == win32con.WM_CLOSE:
        win32gui.DestroyWindow(hwnd)
    elif msg == win32con.WM_DESTROY:
        _wl_dlg_map.pop(hwnd, None)
        win32gui.PostQuitMessage(0)

    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


class SubDialog:
    def __init__(self, entry, parent):
        self.entry = entry
        self.parent = parent
        self.hwnd = 0
        self.edit_title = 0
        self.edit_exe = 0
        self.edit_cls = 0

    def run(self):
        try:
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = _wl_wndproc
            wc.hInstance = win32api.GetModuleHandle(None)
            wc.hbrBackground = win32con.COLOR_BTNFACE + 1
            wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
            wc.lpszClassName = WL_CLASS
            win32gui.RegisterClass(wc)
        except win32gui.error:
            pass

        self.hwnd = win32gui.CreateWindow(
            WL_CLASS, '\u52a0\u5165\u767d\u540d\u5355',
            win32con.WS_OVERLAPPEDWINDOW & ~0x00070000,
            300, 300, 430, 240,
            self.parent, 0, win32api.GetModuleHandle(None), None,
        )
        _wl_dlg_map[self.hwnd] = self
        self._create_controls()
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        _pump()

    def _create_controls(self):
        _t, title, cls, exe = self.entry
        labels = ['\u6807\u9898\u5173\u952e\u8bcd:', '\u7a0b\u5e8f\u540d\u79f0:', '\u7a97\u53e3\u7c7b\u540d:']
        defaults = [title or '', exe or '', cls or '']
        cids = [ID_EDIT_TITLE, ID_EDIT_EXE, ID_EDIT_CLASS]
        edits = []

        for i, (label, default, cid) in enumerate(zip(labels, defaults, cids)):
            y = 20 + i * 35
            win32gui.CreateWindowEx(
                0, 'STATIC', label,
                win32con.WS_CHILD | win32con.WS_VISIBLE,
                15, y + 3, 80, 20,
                self.hwnd, 0, win32api.GetModuleHandle(None), None,
            )
            edit = win32gui.CreateWindowEx(
                0, 'EDIT', default,
                win32con.WS_CHILD | win32con.WS_VISIBLE |
                win32con.WS_BORDER | win32con.ES_AUTOHSCROLL,
                100, y, 300, 22,
                self.hwnd, cid, win32api.GetModuleHandle(None), None,
            )
            edits.append(edit)

        self.edit_title, self.edit_exe, self.edit_cls = edits

        win32gui.CreateWindowEx(
            0, 'STATIC', '\u7559\u7a7a\u7684\u5b57\u6bb5\u4e0d\u53c2\u4e0e\u767d\u540d\u5355\u5339\u914d',
            win32con.WS_CHILD | win32con.WS_VISIBLE,
            15, 130, 300, 20,
            self.hwnd, 0, win32api.GetModuleHandle(None), None,
        )

        win32gui.CreateWindowEx(
            0, 'BUTTON', '\u786e\u8ba4',
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
            245, 155, 75, 25,
            self.hwnd, ID_BTN_OK, win32api.GetModuleHandle(None), None,
        )

        win32gui.CreateWindowEx(
            0, 'BUTTON', '\u53d6\u6d88',
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
            330, 155, 75, 25,
            self.hwnd, ID_BTN_CANCEL, win32api.GetModuleHandle(None), None,
        )


def show_stats(entries):
    dlg = StatsDialog(entries)
    dlg.run()
