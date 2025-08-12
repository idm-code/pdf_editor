import tkinter as tk

class ThumbnailPanel(tk.Frame):
    def __init__(self, master, on_select):
        super().__init__(master, width=160)
        self.on_select = on_select
        self.canvas = tk.Canvas(self, width=150)
        self.scrollbar = tk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas)
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0,0), window=self.inner, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side='left', fill='y')
        self.scrollbar.pack(side='right', fill='y')
        self.thumbs = []
        self.selected_index = None

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()
        self.thumbs.clear()

    def add_thumbnail(self, index, photo):
        btn = tk.Button(self.inner, image=photo, command=lambda i=index: self._select_and_call(i))
        btn.image = photo  # keep ref
        btn.pack(pady=4)
        self.thumbs.append(btn)

    def _select_and_call(self, index):
        self.select(index)
        self.on_select(index)

    def select(self, index):
        self.selected_index = index
        for i, btn in enumerate(self.thumbs):
            if i == index:
                btn.config(relief='sunken', borderwidth=3)
            else:
                btn.config(relief='raised', borderwidth=1)
