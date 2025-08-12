import tkinter as tk
from typing import Optional, Protocol, Tuple, Callable
from PIL import Image, ImageTk

class Tool(Protocol):
    def on_mouse_down(self, event): ...
    def on_mouse_move(self, event): ...
    def on_mouse_up(self, event): ...
    def on_page_rendered(self): ...
    def deactivate(self): ...

class PageView(tk.Frame):
    """
    Responsabilidad: mostrar la página PDF, gestionar zoom, scroll y delegar eventos al Tool activo.
    """
    def __init__(self, master, get_page_pixmap: Callable, get_page_count: Callable):
        super().__init__(master, bg='gray')
        self.get_page_pixmap = get_page_pixmap
        self.get_page_count = get_page_count
        self.canvas = tk.Canvas(self, bg='gray')
        self.v_scroll = tk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.h_scroll = tk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.v_scroll.grid(row=0, column=1, sticky='ns')
        self.h_scroll.grid(row=1, column=0, sticky='ew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.current_index: Optional[int] = None
        self.zoom_mode = 'custom'  # custom | fit_width
        self.zoom = 0.8
        self._tool: Optional[Tool] = None
        self._photo = None
        self.last_offsets: Tuple[float,float] = (0,0)
        self.last_zoom_used = self.zoom

        self.canvas.bind('<Button-1>', self._on_down)
        self.canvas.bind('<B1-Motion>', self._on_move)
        self.canvas.bind('<ButtonRelease-1>', self._on_up)
        self.canvas.bind('<Configure>', lambda e: self._maybe_refit())

    # Public API
    def set_page(self, index: int):
        self.current_index = index
        self.render()

    def set_tool(self, tool: Optional[Tool]):
        if self._tool:
            self._tool.deactivate()
        self._tool = tool
        if self._tool:
            self._tool.on_page_rendered()

    def change_zoom_factor(self, factor: float):
        if self.current_index is None: return
        self.zoom_mode = 'custom'
        self.zoom = max(0.1, min(self.zoom * factor, 5.0))
        self.render()

    def reset_zoom(self):
        if self.current_index is None: return
        self.zoom_mode = 'custom'
        self.zoom = 1.0
        self.render()

    def fit_width(self):
        if self.current_index is None: return
        self.zoom_mode = 'fit_width'
        self.render()

    def scroll_wheel(self, delta_units: int):
        self.canvas.yview_scroll(delta_units, 'units')

    def scroll_wheel_ctrl(self, zoom_in: bool):
        self.change_zoom_factor(1.1 if zoom_in else 0.9)

    # Rendering
    def render(self):
        if self.current_index is None:
            return
        if self.zoom_mode == 'fit_width':
            probe = self.get_page_pixmap(self.current_index, 0.1)
            target_w = max(50, self.canvas.winfo_width())
            if probe.width > 0:
                self.zoom = max(0.1, min(target_w / probe.width * 0.1, 5.0))
        pix = self.get_page_pixmap(self.current_index, self.zoom)
        img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete('all')
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x_off = (cw - pix.width)/2 if cw > pix.width else 0
        y_off = (ch - pix.height)/2 if ch > pix.height else 0
        self.canvas.create_image(x_off, y_off, image=self._photo, anchor='nw')
        self.canvas.config(scrollregion=(0,0,max(cw,pix.width), max(ch,pix.height)))
        self.last_offsets = (x_off, y_off)
        self.last_zoom_used = self.zoom
        if self._tool:
            self._tool.on_page_rendered()

    # Helpers
    def canvas_to_page(self, cx, cy):
        ox, oy = self.last_offsets
        return (cx - ox)/self.last_zoom_used, (cy - oy)/self.last_zoom_used

    def page_to_canvas(self, px, py):
        """
        Convierte coords de página -> canvas usando último render.
        """
        ox, oy = self.last_offsets
        return px * self.last_zoom_used + ox, py * self.last_zoom_used + oy

    def _maybe_refit(self):
        if self.zoom_mode == 'fit_width' and self.current_index is not None:
            self.render()

    # Event delegation
    def _on_down(self, e):
        if self._tool: self._tool.on_mouse_down(e)
    def _on_move(self, e):
        if self._tool: self._tool.on_mouse_move(e)
    def _on_up(self, e):
        if self._tool: self._tool.on_mouse_up(e)