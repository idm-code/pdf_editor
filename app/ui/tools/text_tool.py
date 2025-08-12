import tkinter as tk
from typing import Optional
from ..page_view import PageView
from ...core.doc_manager import DocumentManager

class TextTool:
    """
    Responsable sólo de: creación de áreas de texto y escritura en PDF.
    """
    def __init__(self, page_view: PageView, doc: DocumentManager,
                 get_style, notify_refresh):
        self.page_view = page_view
        self.doc = doc
        self.get_style = get_style          # callable -> (fontname, size, color_rgb, erase_bg)
        self.notify_refresh = notify_refresh
        self._drag_start = None
        self._rect_id = None
        self._pending_coords = None

    # Protocol methods
    def on_mouse_down(self, event):
        if self.page_view.current_index is None: return
        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)
        self._drag_start = (cx, cy)
        if self._rect_id:
            self.page_view.canvas.delete(self._rect_id)
        self._rect_id = self.page_view.canvas.create_rectangle(cx, cy, cx, cy,
                                                               outline='red', dash=(3,2))

    def on_mouse_move(self, event):
        if not self._drag_start or not self._rect_id: return
        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)
        x0,y0 = self._drag_start
        self.page_view.canvas.coords(self._rect_id, x0,y0,cx,cy)

    def on_mouse_up(self, event):
        if not self._drag_start or not self._rect_id: return
        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)
        x0,y0 = self._drag_start
        self._drag_start = None
        if abs(cx-x0) < 5 or abs(cy-y0) < 5:
            self.page_view.canvas.delete(self._rect_id)
            self._rect_id = None
            return
        # Guardar rect en coords canvas (no convertir aún)
        self._pending_canvas_rect = (x0, y0, cx, cy)
        self._open_editor()
        self.page_view.canvas.delete(self._rect_id)
        self._rect_id = None

    def on_page_rendered(self):
        pass

    def deactivate(self):
        if self._rect_id:
            self.page_view.canvas.delete(self._rect_id)
            self._rect_id = None
        self._drag_start = None

    # Internals
    def _open_editor(self):
        top = tk.Toplevel(self.page_view)
        top.title('Texto')
        top.geometry('420x240')
        txt = tk.Text(top, wrap='word')
        txt.pack(fill='both', expand=True)
        btn = tk.Frame(top)
        btn.pack(fill='x')
        def apply():
            content = txt.get('1.0','end').rstrip()
            top.destroy()
            if content:
                self._commit(content)
        def cancel():
            top.destroy()
        tk.Button(btn, text='Aplicar', command=apply).pack(side='left', padx=4, pady=3)
        tk.Button(btn, text='Cancelar', command=cancel).pack(side='left', padx=4, pady=3)
        txt.focus_set()
        txt.bind('<Return>', lambda e: (apply(), 'break'))
        txt.bind('<Escape>', lambda e: (cancel(), 'break'))

    def _commit(self, content: str):
        if not hasattr(self, '_pending_canvas_rect'):
            return
        x0c, y0c, x1c, y1c = self._pending_canvas_rect
        del self._pending_canvas_rect
        # Convertir AHORA usando zoom / offsets actuales (preciso tras cambios de zoom)
        px0, py0 = self.page_view.canvas_to_page(x0c, y0c)
        px1, py1 = self.page_view.canvas_to_page(x1c, y1c)
        # Normalizar
        if px1 < px0: px0, px1 = px1, px0
        if py1 < py0: py0, py1 = py1, py0
        if (px1 - px0) < 2 or (py1 - py0) < 2:
            return
        fontname, size, color_rgb, erase_bg = self.get_style()
        r,g,b = color_rgb
        if erase_bg:
            self.doc.redact_rect(self.page_view.current_index, (px0,py0,px1,py1))
        ok = self.doc.add_text_box(
            self.page_view.current_index,
            (px0,py0,px1,py1),
            content,
            font_size=size,
            color=(r/255.0,g/255.0,b/255.0),
            font_family=fontname,
            align=0,
            erase_background=erase_bg
        )
        if ok:
            self.notify_refresh()