import tkinter as tk
from typing import Optional, Tuple
from PIL import Image, ImageTk
from ..page_view import PageView
from ...core.doc_manager import DocumentManager
import os

_HANDLE_SIZE = 6

class ImageTool:
    """
    Inserción de imagen:
    1. Cargar imagen (método load_image_path)
    2. Arrastrar rectángulo
    3. Redimensionar con esquinas
    4. Enter: incrusta. Esc: cancela.
    """
    def __init__(self, page_view: PageView, doc: DocumentManager, notify_refresh):
        self.page_view = page_view
        self.doc = doc
        self.notify_refresh = notify_refresh

        # Estado imagen
        self._image_path: Optional[str] = None
        self._pil: Optional[Image.Image] = None
        self._tk: Optional[ImageTk.PhotoImage] = None

        # Creación rect
        self._drag_start_canvas: Optional[Tuple[float,float]] = None
        self._creating_rect_id: Optional[int] = None

        # Overlay
        self._rect_id: Optional[int] = None
        self._handle_ids = []
        self._img_item: Optional[int] = None
        self._page_rect: Optional[Tuple[float,float,float,float]] = None
        self._resizing_handle_index: Optional[int] = None

    # API externa
    def load_image_path(self, path: str):
        if not path or not os.path.isfile(path):
            return False
        try:
            self._pil = Image.open(path).convert('RGBA')
            self._tk = ImageTk.PhotoImage(self._pil)
            self._image_path = path
            return True
        except Exception:
            self._pil = None
            self._tk = None
            self._image_path = None
            return False

    # Protocol
    def on_mouse_down(self, event):
        if self.page_view.current_index is None:
            return
        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)

        # Si hay overlay y clic sobre handle
        if self._rect_id and self._page_rect:
            h = self._hit_handle(cx, cy)
            if h is not None:
                self._resizing_handle_index = h
                return
            if self._hit_inside_rect(cx, cy):
                # No movimiento (opcional) por simplicidad
                return
            # Clic fuera => descartar overlay actual
            self._destroy_overlay()

        # Requiere imagen cargada
        if not self._image_path:
            # Ignorar hasta que usuario cargue imagen
            return

        self._drag_start_canvas = (cx, cy)
        if self._creating_rect_id:
            self.page_view.canvas.delete(self._creating_rect_id)
        self._creating_rect_id = self.page_view.canvas.create_rectangle(
            cx, cy, cx, cy, outline='#0077ff', dash=(3,2)
        )

    def on_mouse_move(self, event):
        cx = self.page_view.canvas.canvasx(event.x)
        cy = self.page_view.canvas.canvasy(event.y)
        if self._drag_start_canvas and self._creating_rect_id:
            x0,y0 = self._drag_start_canvas
            self.page_view.canvas.coords(self._creating_rect_id, x0,y0,cx,cy)
            return
        if self._page_rect and self._resizing_handle_index is not None:
            x0,y0,x1,y1 = self._page_rect
            px, py = self.page_view.canvas_to_page(cx, cy)
            if self._resizing_handle_index == 0:
                x0,y0 = px,py
            elif self._resizing_handle_index == 1:
                x1,y0 = px,py
            elif self._resizing_handle_index == 2:
                x1,y1 = px,py
            elif self._resizing_handle_index == 3:
                x0,y1 = px,py
            self._page_rect = (x0,y0,x1,y1)
            self._reposition_overlay()

    def on_mouse_up(self, event):
        if self._drag_start_canvas and self._creating_rect_id:
            cx = self.page_view.canvas.canvasx(event.x)
            cy = self.page_view.canvas.canvasy(event.y)
            x0,y0 = self._drag_start_canvas
            self._drag_start_canvas = None
            if abs(cx-x0) < 5 or abs(cy-y0) < 5:
                self.page_view.canvas.delete(self._creating_rect_id)
                self._creating_rect_id = None
                return
            px0,py0 = self.page_view.canvas_to_page(x0,y0)
            px1,py1 = self.page_view.canvas_to_page(cx,cy)
            if px1 < px0: px0,px1 = px1,px0
            if py1 < py0: py0,py1 = py1,py0
            self._page_rect = (px0,py0,px1,py1)
            self.page_view.canvas.delete(self._creating_rect_id)
            self._creating_rect_id = None
            self._create_overlay()
        if self._resizing_handle_index is not None:
            self._resizing_handle_index = None

    def on_page_rendered(self):
        if self._page_rect and self._rect_id:
            self._reposition_overlay()

    def deactivate(self):
        self._destroy_overlay()
        self._drag_start_canvas = None
        self._creating_rect_id = None

    # Teclas
    def on_key(self, event):
        if event.keysym == 'Return':
            self._commit()
            return "break"
        if event.keysym == 'Escape':
            self._destroy_overlay()
            return "break"

    # Overlay
    def _create_overlay(self):
        if not (self._page_rect and self._tk):
            return
        cvs = self.page_view.canvas
        self._rect_id = cvs.create_rectangle(0,0,0,0, outline='#0077ff', width=2)
        self._handle_ids = []
        for _ in range(4):
            hid = cvs.create_rectangle(0,0,0,0, outline='#0077ff', fill='#0077ff')
            self._handle_ids.append(hid)
        self._img_item = cvs.create_image(0,0, image=self._tk, anchor='nw')
        self._reposition_overlay()

    def _reposition_overlay(self):
        if not (self._page_rect and self._rect_id and self._tk and self._pil):
            return
        x0,y0,x1,y1 = self._page_rect
        c0x,c0y = self.page_view.page_to_canvas(x0,y0)
        c1x,c1y = self.page_view.page_to_canvas(x1,y1)
        cvs = self.page_view.canvas
        cvs.coords(self._rect_id, c0x,c0y,c1x,c1y)
        # Handles
        hs = _HANDLE_SIZE
        corners = [
            (c0x-hs, c0y-hs, c0x+hs, c0y+hs),
            (c1x-hs, c0y-hs, c1x+hs, c0y+hs),
            (c1x-hs, c1y-hs, c1x+hs, c1y+hs),
            (c0x-hs, c1y-hs, c0x+hs, c1y+hs),
        ]
        for hid, coords in zip(self._handle_ids, corners):
            cvs.coords(hid, *coords)
        # Escalado mantener aspecto dentro del rect
        bw = c1x - c0x
        bh = c1y - c0y
        iw, ih = self._pil.size
        if iw == 0 or ih == 0: return
        scale = min(bw/iw, bh/ih) if bw>0 and bh>0 else 1
        dw = max(1, int(iw * scale))
        dh = max(1, int(ih * scale))
        # Crear versión redimensionada para preview
        preview = self._pil.resize((dw, dh), Image.LANCZOS)
        self._tk = ImageTk.PhotoImage(preview)
        offset_x = c0x + (bw - dw)/2
        offset_y = c0y + (bh - dh)/2
        cvs.itemconfig(self._img_item, image=self._tk)
        cvs.coords(self._img_item, offset_x, offset_y)

    def _destroy_overlay(self):
        cvs = self.page_view.canvas
        if self._rect_id:
            cvs.delete(self._rect_id)
            self._rect_id = None
        for hid in self._handle_ids:
            cvs.delete(hid)
        self._handle_ids.clear()
        if self._img_item:
            cvs.delete(self._img_item)
            self._img_item = None
        self._page_rect = None
        self._resizing_handle_index = None

    # Hit tests
    def _hit_handle(self, cx, cy):
        for idx, hid in enumerate(self._handle_ids):
            x0,y0,x1,y1 = self.page_view.canvas.coords(hid)
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                return idx
        return None

    def _hit_inside_rect(self, cx, cy):
        if not self._rect_id: return False
        coords = self.page_view.canvas.coords(self._rect_id)
        if len(coords) != 4: return False
        x0,y0,x1,y1 = coords
        return x0 <= cx <= x1 and y0 <= cy <= y1

    def _commit(self):
        if not (self._page_rect and self._image_path):
            return
        ok = self.doc.add_image(self.page_view.current_index, self._page_rect, self._image_path)
        self._destroy_overlay()
        if ok:
            self.notify_refresh()