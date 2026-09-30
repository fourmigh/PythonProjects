import threading
import tkinter as tk
from tkinter import ttk

import single_instance
from gui_input import InputPage
from gui_editor import EditorPage
from aligner import warmup

APP_TITLE = '翻译对照工具'


class TranslateApp(tk.Tk):
    def __init__(self, fixed_engine=None):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('1000x720')
        self.minsize(760, 520)
        threading.Thread(target=warmup, daemon=True).start()
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True)
        self.frames = {}
        for Page, engine in ((InputPage, fixed_engine), (EditorPage, None)):
            f = Page(container, self, engine) if engine is not None \
                else Page(container, self)
            self.frames[Page] = f
            f.grid(row=0, column=0, sticky='nsew')
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.show(InputPage)
        self.after(50, self._close_splash)

    def _close_splash(self):
        try:
            import pyi_splash
            pyi_splash.close()
        except Exception:
            pass

    def show(self, page):
        self.frames[page].tkraise()
        on_show = getattr(self.frames[page], 'on_show', None)
        if on_show:
            on_show()

    def show_input(self):
        self.show(InputPage)

    def open_editor(self, src_lines, tgt_lines):
        self.frames[EditorPage].set_content(src_lines, tgt_lines)
        self.show(EditorPage)


def main():
    if not single_instance.ensure_single(APP_TITLE):
        return
    app = TranslateApp()
    app.mainloop()


if __name__ == '__main__':
    main()
