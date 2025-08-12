import tkinter as tk
from typing import Optional, Tuple
from ..page_view import PageView
from ...core.doc_manager import DocumentManager

class HighlightTool:
    """
    Herramienta de resaltado: arrastrar para crear un rectángulo translúcido.
    """
    def __init__(self, page_view: PageView, doc: DocumentManager,
                 get_color, notify_refresh):
        self.page_view = page_view
        self.doc = doc
        self.get_color = get_color          # -> (rgb_tuple, opacity)
        self.notify_refresh = notify_refresh
        self._start_canvas: Optional[Tuple[float,float]] = None
        self._preview_id: Optional[int] = None

    def on_mouse_down(self, event):
        if self.page_view.current_index is None:
            return
        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)
        self._start_canvas = (cx, cy)
        if self._preview_id:
            self.page_view.canvas.delete(self._preview_id)
        # previsualización (solo borde)
        self._preview_id = self.page_view.canvas.create_rectangle(
            cx, cy, cx, cy, outline='#ff0', width=2, dash=(4,2)
        )

    def on_mouse_move(self, event):
        if not (self._start_canvas and self._preview_id):
            return
        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)
        x0,y0 = self._start_canvas
        self.page_view.canvas.coords(self._preview_id, x0,y0,cx,cy)

    def on_mouse_up(self, event):
        if not (self._start_canvas and self._preview_id):
            return
        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)
        x0,y0 = self._start_canvas
        self._start_canvas = None
        if abs(cx-x0) < 4 or abs(cy-y0) < 4:
            self.page_view.canvas.delete(self._preview_id)
            self._preview_id = None
            return
        # Convertir a coords página
        px0, py0 = self.page_view.canvas_to_page(x0,y0)
        px1, py1 = self.page_view.canvas_to_page(cx,cy)
        color, opacity = self.get_color()
        self.doc.add_highlight_rect(self.page_view.current_index,
                                    (px0,py0,px1,py1),
                                    color_rgb=color,
                                    opacity=opacity)
        self.page_view.canvas.delete(self._preview_id)
        self._preview_id = None
        self.notify_refresh()

    def on_page_rendered(self):
        # Nada que reubicar (no persiste overlay)
        pass

    def deactivate(self):
        if self._preview_id:
            self.page_view.canvas.delete(self._preview_id)
            self._preview_id = None
        self._start_canvas = None