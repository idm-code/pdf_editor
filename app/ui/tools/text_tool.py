import tkinter as tk
import tkinter.font as tkfont
from typing import Optional, Tuple
from ..page_view import PageView
from ...core.doc_manager import DocumentManager

_HANDLE_SIZE = 6

class TextTool:
    """
    Edición de texto en vivo:
    - Arrastrar para crear rect.
    - Texto editable sobre canvas (tk.Text).
    - Mover arrastrando interior.
    - Redimensionar arrastrando esquinas.
    - Enter / Ctrl+Enter: commit a PDF.
    - Esc: cancelar.
    """
    def __init__(self, page_view: PageView, doc: DocumentManager,
                 get_style, notify_refresh):
        self.page_view = page_view
        self.doc = doc
        self.get_style = get_style          # -> (fontname, size, color_rgb, erase_bg)
        self.notify_refresh = notify_refresh

        # Estados
        self._drag_start_canvas: Optional[Tuple[float,float]] = None  # creación inicial
        self._creating_rect_id: Optional[int] = None

        self._editing = False
        self._page_rect: Optional[Tuple[float,float,float,float]] = None  # (x0,y0,x1,y1) coords PDF
        self._rect_id: Optional[int] = None
        self._handle_ids = []
        self._text_widget: Optional[tk.Text] = None
        self._text_window_id: Optional[int] = None

        # Movimiento / resize
        self._move_start_canvas: Optional[Tuple[float,float]] = None
        self._resizing_handle_index: Optional[int] = None  # 0..3 (esquinas)

    # Protocol methods
    def on_mouse_down(self, event):
        if self.page_view.current_index is None:
            return

        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)

        if self._editing and self._page_rect:
            # ¿clic sobre handle?
            h_index = self._hit_handle(cx, cy)
            if h_index is not None:
                self._resizing_handle_index = h_index
                return
            # ¿clic dentro del rect actual?
            if self._hit_inside_rect(cx, cy):
                self._move_start_canvas = (cx, cy)
                return
            # Clic fuera -> commit existente antes de crear otro
            self._commit_to_pdf()

        # Comenzar creación nuevo rect
        self._editing = False
        self._destroy_overlay()
        self._drag_start_canvas = (cx, cy)
        if self._creating_rect_id:
            self.page_view.canvas.delete(self._creating_rect_id)
        self._creating_rect_id = self.page_view.canvas.create_rectangle(
            cx, cy, cx, cy, outline='red', dash=(3,2)
        )

    def on_mouse_move(self, event):
        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)

        # Creando rectángulo inicial
        if self._drag_start_canvas and self._creating_rect_id:
            x0, y0 = self._drag_start_canvas
            self.page_view.canvas.coords(self._creating_rect_id, x0, y0, cx, cy)
            return

        # Moviendo rect editando
        if self._editing and self._page_rect and self._move_start_canvas:
            dx = (cx - self._move_start_canvas[0]) / self.page_view.last_zoom_used
            dy = (cy - self._move_start_canvas[1]) / self.page_view.last_zoom_used
            x0,y0,x1,y1 = self._page_rect
            self._page_rect = (x0+dx, y0+dy, x1+dx, y1+dy)
            self._move_start_canvas = (cx, cy)
            self._reposition_overlay()
            return

        # Redimensionando
        if self._editing and self._page_rect and self._resizing_handle_index is not None:
            x0,y0,x1,y1 = self._page_rect
            # Convertir puntero a coords página
            px, py = self.page_view.canvas_to_page(cx, cy)
            # Handles: 0=TL,1=TR,2=BR,3=BL
            if self._resizing_handle_index == 0:  # TL
                x0, y0 = px, py
            elif self._resizing_handle_index == 1:  # TR
                x1, y0 = px, py
            elif self._resizing_handle_index == 2:  # BR
                x1, y1 = px, py
            elif self._resizing_handle_index == 3:  # BL
                x0, y1 = px, py
            self._page_rect = (x0, y0, x1, y1)
            self._reposition_overlay()
            return

    def on_mouse_up(self, event):
        # Fin creación
        if self._drag_start_canvas and self._creating_rect_id:
            cx = self.page_view.canvas.canvasx(event.x)
            cy = self.page_view.canvas.canvasy(event.y)
            x0,y0 = self._drag_start_canvas
            self._drag_start_canvas = None
            if abs(cx - x0) < 5 or abs(cy - y0) < 5:
                self.page_view.canvas.delete(self._creating_rect_id)
                self._creating_rect_id = None
                return
            # Convertir a coords página
            px0, py0 = self.page_view.canvas_to_page(x0, y0)
            px1, py1 = self.page_view.canvas_to_page(cx, cy)
            if px1 < px0: px0, px1 = px1, px0
            if py1 < py0: py0, py1 = py1, py0
            self._page_rect = (px0, py0, px1, py1)
            # Crear overlay de edición
            self.page_view.canvas.delete(self._creating_rect_id)
            self._creating_rect_id = None
            self._create_overlay()
            return

        # Fin movimiento
        if self._move_start_canvas:
            self._move_start_canvas = None

        # Fin redimensionado
        if self._resizing_handle_index is not None:
            self._resizing_handle_index = None

    def on_page_rendered(self):
        # Reposicionar overlay si se está editando
        if self._editing and self._page_rect:
            self._reposition_overlay()

    def deactivate(self):
        # Commit implícito? Mejor no. Solo limpiar.
        self._destroy_overlay()
        self._drag_start_canvas = None
        self._creating_rect_id = None

    # ----- Overlay -----
    def _create_overlay(self):
        if not self._page_rect:
            return
        self._editing = True
        # Crear rectángulo principal y handles + text widget
        self._rect_id = self.page_view.canvas.create_rectangle(0,0,0,0,
                                                               outline='orange', width=2)
        self._handle_ids = []
        for _ in range(4):
            hid = self.page_view.canvas.create_rectangle(0,0,0,0,
                                                         outline='orange', fill='orange')
            self._handle_ids.append(hid)
        # Text widget
        fontname, size, color_rgb, _erase = self.get_style()
        # Para preview usamos familia base (Tk no entiende sufijos PDF exactos)
        tk_family = 'Helvetica'
        if fontname.startswith('times'): tk_family = 'Times'
        elif fontname.startswith('cour'): tk_family = 'Courier'
        weight = 'bold' if 'bold' in fontname else 'normal'
        slant = 'italic' if 'italic' in fontname or 'oblique' in fontname else 'roman'
        tkfont_obj = tkfont.Font(family=tk_family, size=size, weight=weight, slant=slant)

        self._text_widget = tk.Text(self.page_view.canvas, wrap='word',
                                    font=tkfont_obj,
                                    bd=0, highlightthickness=0)
        r,g,b = color_rgb
        self._text_widget.configure(fg=f'#{r:02x}{g:02x}{b:02x}')
        self._text_window_id = self.page_view.canvas.create_window(0,0,
                                                                   anchor='nw',
                                                                   window=self._text_widget)
        # Bindings de texto
        self._text_widget.bind('<Return>', self._on_commit_key)
        self._text_widget.bind('<Control-Return>', self._on_commit_key)
        self._text_widget.bind('<Escape>', self._on_cancel_key)

        self._reposition_overlay()
        self._text_widget.focus_set()

    def _reposition_overlay(self):
        if not self._page_rect or not self._rect_id:
            return
        x0,y0,x1,y1 = self._page_rect
        # Normalizar
        if x1 < x0: x0,x1 = x1,x0
        if y1 < y0: y0,y1 = y1,y0
        # Convertir a canvas
        c0x, c0y = self.page_view.page_to_canvas(x0, y0)
        c1x, c1y = self.page_view.page_to_canvas(x1, y1)
        self.page_view.canvas.coords(self._rect_id, c0x, c0y, c1x, c1y)
        # Handles (TL, TR, BR, BL)
        hs = _HANDLE_SIZE
        handles_pos = [
            (c0x-hs, c0y-hs, c0x+hs, c0y+hs),
            (c1x-hs, c0y-hs, c1x+hs, c0y+hs),
            (c1x-hs, c1y-hs, c1x+hs, c1y+hs),
            (c0x-hs, c1y-hs, c0x+hs, c1y+hs),
        ]
        for hid, pos in zip(self._handle_ids, handles_pos):
            self.page_view.canvas.coords(hid, *pos)
        # Text widget ajustado al interior con padding
        pad = 4
        self.page_view.canvas.coords(self._text_window_id, c0x+pad, c0y+pad)
        width_px = max(10, (c1x - c0x) - 2*pad)
        height_px = max(10, (c1y - c0y) - 2*pad)
        # Ajustar tamaño widget (usar place geometry vs config no directo, truco: width/height en chars/lines)
        # Para mantener proporcional: estimar chars = width_px / (font_size*0.6)
        if self._text_widget:
            font_size = self._text_widget['font']
            # Ajuste aproximado: chars y líneas
            chars = max(5, int(width_px / 7))
            lines = max(1, int(height_px / 18))
            self._text_widget.config(width=chars, height=lines)

    def _destroy_overlay(self):
        if self._rect_id:
            self.page_view.canvas.delete(self._rect_id)
            self._rect_id = None
        for hid in self._handle_ids:
            self.page_view.canvas.delete(hid)
        self._handle_ids.clear()
        if self._text_window_id:
            self.page_view.canvas.delete(self._text_window_id)
            self._text_window_id = None
        if self._text_widget:
            self._text_widget.destroy()
            self._text_widget = None
        self._editing = False
        self._page_rect = None

    # ----- Interacciones -----
    def _hit_handle(self, cx, cy):
        for idx, hid in enumerate(self._handle_ids):
            x0,y0,x1,y1 = self.page_view.canvas.coords(hid)
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                return idx
        return None

    def _hit_inside_rect(self, cx, cy):
        if not self._rect_id:
            return False
        x0,y0,x1,y1 = self.page_view.canvas.coords(self._rect_id)
        return x0 <= cx <= x1 and y0 <= cy <= y1

    # ----- Commit / Cancel -----
    def _on_commit_key(self, event):
        self._commit_to_pdf()
        return "break"

    def _on_cancel_key(self, event):
        self._destroy_overlay()
        return "break"

    def _commit_to_pdf(self):
        if not (self._editing and self._page_rect and self._text_widget):
            return
        content = self._text_widget.get('1.0', 'end').rstrip()
        if not content:
            self._destroy_overlay()
            return
        fontname, size, color_rgb, erase_bg = self.get_style()
        r,g,b = color_rgb
        x0,y0,x1,y1 = self._page_rect
        self.doc.add_text_box(
            self.page_view.current_index,
            (x0,y0,x1,y1),
            content,
            font_size=size,
            color=(r/255.0,g/255.0,b/255.0),
            font_family=fontname,
            align=0,
            erase_background=erase_bg
        )
        self._destroy_overlay()
        self.notify_refresh()