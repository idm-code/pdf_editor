from typing import List, Optional
import io
import pikepdf
import fitz  # PyMuPDF
from .font_manager import FontManager

class DocumentManager:
    def __init__(self):
        self._pike_doc: Optional[pikepdf.Pdf] = None
        self._fitz_doc: Optional[fitz.Document] = None
        self.path: Optional[str] = None
        self.dirty: bool = False
        self._history = None  # HistoryManager opcional
        self._font_manager: Optional[FontManager] = None

    def open(self, path: str):
        self.close()
        self._pike_doc = pikepdf.Pdf.open(path)
        self._fitz_doc = fitz.open(path)
        self.path = path
        self.dirty = False
        self._notify_history(initial=True)
        if self._font_manager:
            self._register_external_fonts()

    def is_open(self) -> bool:
        return self._pike_doc is not None

    def page_count(self) -> int:
        return 0 if not self._fitz_doc else self._fitz_doc.page_count

    def get_page_pixmap(self, index: int, zoom: float = 0.2):
        if not self._fitz_doc:
            raise ValueError("No document open")
        page = self._fitz_doc.load_page(index)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix

    def remove_page(self, index: int):
        if not self._pike_doc or not self._fitz_doc:
            return
        # Remove in pikepdf
        del self._pike_doc.pages[index]
        # Rebuild fitz doc from buffer
        buf = io.BytesIO()
        self._pike_doc.save(buf)
        buf.seek(0)
        self._fitz_doc.close()
        self._fitz_doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
        self.dirty = True
        self._notify_history()

    def insert_pdf(self, other_path: str):
        if not self._pike_doc or not self._fitz_doc:
            # If no doc open, just open the other
            self.open(other_path)
            return
        other = pikepdf.Pdf.open(other_path)
        for page in other.pages:
            self._pike_doc.pages.append(page)
        # Refresh fitz doc
        buf = io.BytesIO()
        self._pike_doc.save(buf)
        buf.seek(0)
        self._fitz_doc.close()
        self._fitz_doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
        self.dirty = True
        self._notify_history()

    def reorder_pages(self, new_order: List[int]):
        if not self._pike_doc or not self._fitz_doc:
            return
        if sorted(new_order) != list(range(self.page_count())):
            raise ValueError("Invalid new order list")
        # Rebuild with new order
        new_pdf = pikepdf.Pdf.new()
        for idx in new_order:
            new_pdf.pages.append(self._pike_doc.pages[idx])
        self._pike_doc = new_pdf
        buf = io.BytesIO()
        self._pike_doc.save(buf)
        buf.seek(0)
        self._fitz_doc.close()
        self._fitz_doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
        self.dirty = True
        self._notify_history()

    def save_as(self, path: str):
        if not self._pike_doc:
            return
        self._pike_doc.save(path)
        self.path = path
        self.dirty = False

    def save(self):
        if not self.path:
            raise ValueError("No existing path; use save_as")
        self.save_as(self.path)

    def close(self):
        try:
            if self._fitz_doc:
                self._fitz_doc.close()
        finally:
            self._fitz_doc = None
        try:
            if self._pike_doc:
                self._pike_doc.close()
        finally:
            self._pike_doc = None
        self.path = None
        self.dirty = False

    def rotate_page(self, index: int, degrees: int):
        if not self._pike_doc or not self._fitz_doc:
            return
        page = self._pike_doc.pages[index]
        current = int(page.obj.get('/Rotate', 0))
        new = (current + degrees) % 360
        page.obj['/Rotate'] = pikepdf.Number(new)
        # Rebuild fitz doc
        buf = io.BytesIO()
        self._pike_doc.save(buf)
        buf.seek(0)
        self._fitz_doc.close()
        self._fitz_doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
        self.dirty = True
        self._notify_history()

    def _rebuild_fitz(self):
        if not self._pike_doc:
            return
        buf = io.BytesIO()
        self._pike_doc.save(buf)
        buf.seek(0)
        if self._fitz_doc:
            self._fitz_doc.close()
        self._fitz_doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
        self.dirty = True
        self._notify_history()

    def insert_blank_page(self, position: int, width: int = 595, height: int = 842):
        if not self._pike_doc:
            return
        # Crear página en blanco (A4 por defecto aproximadamente 595x842 puntos)
        blank = pikepdf.Page(self._pike_doc, mediabox=(0, 0, width, height))
        if position < 0 or position > len(self._pike_doc.pages):
            position = len(self._pike_doc.pages)
        self._pike_doc.pages.insert(position, blank)
        self._rebuild_fitz()  # ya notifica

    def duplicate_page(self, index: int):
        if not self._pike_doc:
            return
        if index < 0 or index >= len(self._pike_doc.pages):
            return
        # pikepdf copia al insertar la misma página
        page = self._pike_doc.pages[index]
        self._pike_doc.pages.insert(index + 1, page)
        self._rebuild_fitz()

    def replace_page(self, index: int, other_path: str, other_page_index: int = 0):
        if not self._pike_doc:
            return
        if index < 0 or index >= len(self._pike_doc.pages):
            return
        other = pikepdf.Pdf.open(other_path)
        if other_page_index < 0 or other_page_index >= len(other.pages):
            return
        # Sustituir
        self._pike_doc.pages[index] = other.pages[other_page_index]
        self._rebuild_fitz()

    def extract_pages(self, indices: list[int], output_path: str):
        if not self._pike_doc:
            return
        indices = sorted(set(i for i in indices if 0 <= i < len(self._pike_doc.pages)))
        if not indices:
            return
        new_pdf = pikepdf.Pdf.new()
        for i in indices:
            new_pdf.pages.append(self._pike_doc.pages[i])
        new_pdf.save(output_path)

    def get_page_size(self, index: int):
        if not self._fitz_doc:
            return (0, 0)
        page = self._fitz_doc.load_page(index)
        rect = page.rect
        return (rect.width, rect.height)

    def _sync_from_fitz_bytes(self, buf: io.BytesIO):
        """Sincroniza ambos objetos desde los bytes proporcionados."""
        data = buf.getvalue()
        # Reabrir pikepdf
        self._pike_doc = pikepdf.Pdf.open(io.BytesIO(data))
        # Reabrir fitz
        if self._fitz_doc:
            try:
                self._fitz_doc.close()
            except:
                pass
        self._fitz_doc = fitz.open(stream=data, filetype="pdf")
        self.dirty = True
        if self._font_manager:
            self._register_external_fonts()

    def add_text(self, page_index: int, x: float, y: float, text: str,
                 font_size: int = 14, color=(0, 0, 0), font_family: str = "helv") -> bool:
        if not self._fitz_doc or not self._pike_doc:
            return False
        if page_index < 0 or page_index >= self.page_count():
            return False
        page = self._fitz_doc.load_page(page_index)
        page.insert_text(
            fitz.Point(x, y),
            text,
            fontsize=font_size,
            fontname=font_family,
            fill=color
        )
        buf = io.BytesIO()
        self._fitz_doc.save(buf)
        buf.seek(0)
        self._sync_from_fitz_bytes(buf)
        self._notify_history()
        return True

    def draw_filled_rect(self, page_index: int, rect, fill=(1,1,1)):
        """
        rect: (x0,y0,x1,y1) coords página. fill: tupla RGB (0..1).
        """
        if not self._fitz_doc or not self._pike_doc:
            return False
        if page_index < 0 or page_index >= self.page_count():
            return False
        x0,y0,x1,y1 = rect
        if x1 < x0: x0,x1 = x1,x0
        if y1 < y0: y0,y1 = y1,y0
        if x1 - x0 <= 0 or y1 - y0 <= 0:
            return False
        page = self._fitz_doc.load_page(page_index)
        page.draw_rect(fitz.Rect(x0,y0,x1,y1), color=None, fill=fill)
        buf = io.BytesIO()
        self._fitz_doc.save(buf)
        buf.seek(0)
        self._sync_from_fitz_bytes(buf)
        self._notify_history()
        return True

    def add_text_box(self, page_index: int, rect, text: str,
                     font_size: int = 14, color=(0,0,0), font_family: str = "helv",
                     align: int = 0, erase_background: bool = False,
                     underline: bool = False, underline_color=(0,0,0)) -> bool:
        """
        rect: (x0, y0, x1, y1) coords página.
        Devuelve True si se colocó algo de texto. Hace fallback a insert_text
        si insert_textbox no coloca nada.
        """
        if not self._fitz_doc or not self._pike_doc:
            return False
        if page_index < 0 or page_index >= self.page_count():
            return False
        x0, y0, x1, y1 = rect
        if x1 < x0: x0, x1 = x1, x0
        if y1 < y0: y0, y1 = y1, y0
        page = self._fitz_doc.load_page(page_index)
        pw, ph = page.rect.width, page.rect.height
        x0 = max(0, min(pw, x0)); x1 = max(0, min(pw, x1))
        y0 = max(0, min(ph, y0)); y1 = max(0, min(ph, y1))
        # Asegurar tamaño mínimo para que quepa al menos una línea
        min_w = max(10, font_size * 0.6)
        min_h = max(12, font_size * 1.2)
        if (x1 - x0) < min_w: x1 = x0 + min_w
        if (y1 - y0) < min_h: y1 = y0 + min_h
        if (x1 - x0) <= 0 or (y1 - y0) <= 0:
            return False
        if erase_background:
            page.draw_rect(fitz.Rect(x0,y0,x1,y1), color=None, fill=(1,1,1))

        # Preparar fontfile si es personalizada
        fontfile = None
        if not self._is_base14(font_family):
            fontfile = self._fontfile_for(font_family)
            if fontfile is None:
                font_family = 'helv'  # fallback seguro

        def _insert_box(fam, ffile):
            return page.insert_textbox(
                fitz.Rect(x0, y0, x1, y1),
                text,
                fontsize=font_size,
                fontname=fam,
                fontfile=ffile,
                fill=color,
                align=align
            )

        try:
            leftover = _insert_box(font_family, fontfile)
        except Exception:
            # fallback duro
            font_family = 'helv'
            leftover = _insert_box('helv', None)

        placed_with_box = (text.strip() != "")
        if leftover == text and text.strip():
            # El textbox no pudo colocar nada; fallback línea a línea
            lines = text.splitlines()
            cur_y = y0 + font_size
            line_gap = font_size * 1.15
            for line in lines:
                if cur_y > y1: break
                if not line and len(lines) > 1:
                    cur_y += line_gap
                    continue
                try:
                    page.insert_text(
                        fitz.Point(x0, cur_y),
                        line if line else " ",
                        fontsize=font_size,
                        fontname=font_family,
                        fontfile=fontfile if fontfile and font_family != 'helv' else None,
                        fill=color
                    )
                except Exception:
                    page.insert_text(
                        fitz.Point(x0, cur_y),
                        line if line else " ",
                        fontsize=font_size,
                        fontname='helv',
                        fill=color
                    )
                cur_y += line_gap

        if underline and text.strip():
            uy = y1 - 2
            page.draw_line(fitz.Point(x0 + 2, uy), fitz.Point(x1 - 2, uy),
                           color=underline_color, width=0.8)

        # Guardar siempre que haya borrado fondo o texto (para que se vea la acción)
        if erase_background or text.strip():
            buf = io.BytesIO()
            self._fitz_doc.save(buf)
            buf.seek(0)
            self._sync_from_fitz_bytes(buf)
            self._notify_history()
            return True
        return False

    def redact_rect(self, page_index: int, rect, fill=(1,1,1)):
        if not self._fitz_doc or not self._pike_doc:
            return False
        if page_index < 0 or page_index >= self.page_count():
            return False
        x0,y0,x1,y1 = rect
        if x1 < x0: x0,x1 = x1,x0
        if y1 < y0: y0,y1 = y1,y0
        page = self._fitz_doc.load_page(page_index)
        page.add_redact_annot(fitz.Rect(x0,y0,x1,y1), fill=fill)
        page.apply_redactions()
        buf = io.BytesIO()
        self._fitz_doc.save(buf)
        buf.seek(0)
        self._sync_from_fitz_bytes(buf)
        self._notify_history()
        return True

    def add_text_annotation(self, page_index: int, rect, text: str,
                            font_family: str = "helv", font_size: int = 14,
                            color=(0,0,0), underline=False, fill_bg=None) -> Optional[int]:
        if not self._fitz_doc or not self._pike_doc:
            return None
        if page_index < 0 or page_index >= self.page_count():
            return None
        x0,y0,x1,y1 = rect
        if x1 < x0: x0,x1 = x1,x0
        if y1 < y0: y0,y1 = y1,y0
        page = self._fitz_doc.load_page(page_index)
        annot = page.add_freetext_annot(
            fitz.Rect(x0,y0,x1,y1),
            text,
            fontsize=font_size,
            fontname=font_family,
            text_color=color,
            align=0
        )
        if fill_bg:
            annot.set_colors(stroke=None, fill=fill_bg)
        annot.update()
        # subrayado manual (línea) si se pide
        if underline:
            baseline_y = y1 - 2
            page.draw_line(fitz.Point(x0+2, baseline_y), fitz.Point(x1-2, baseline_y), color=color, width=0.8)
        buf = io.BytesIO()
        self._fitz_doc.save(buf)
        buf.seek(0)
        self._sync_from_fitz_bytes(buf)
        self._notify_history()
        return annot.xref

    def list_text_annotations(self, page_index: int):
        if not self._fitz_doc:
            return []
        page = self._fitz_doc.load_page(page_index)
        out = []
        for annot in page.annots() or []:
            if annot.type[0] == fitz.PDF_ANNOT_FREE_TEXT:
                r = annot.rect
                out.append({"xref": annot.xref, "rect": (r.x0, r.y0, r.x1, r.y1)})
        return out

    def update_text_annotation(self, page_index: int, xref: int, text: str = None,
                               rect=None, font_family=None, font_size=None,
                               color=None, fill_bg=None, underline=False):
        if not self._fitz_doc or not self._pike_doc:
            return False
        page = self._fitz_doc.load_page(page_index)
        annot = page.load_annot(xref)
        if not annot or annot.type[0] != fitz.PDF_ANNOT_FREE_TEXT:
            return False
        info_changed = False
        if rect:
            x0,y0,x1,y1 = rect
            if x1 < x0: x0,x1 = x1,x0
            if y1 < y0: y0,y1 = y1,y0
            annot.set_rect(fitz.Rect(x0,y0,x1,y1))
            info_changed = True
        if text is not None:
            annot.set_info(contents=text)
            info_changed = True
        if any(v is not None for v in (font_family,font_size,color,fill_bg)):
            # reconstruir appearance mediante update()
            pass
        if color:
            annot.set_colors(stroke=None, fill=fill_bg, text=color)
            info_changed = True
        if fill_bg:
            annot.set_colors(stroke=None, fill=fill_bg, text=color or (0,0,0))
            info_changed = True
        annot.update(fontname=font_family, fontsize=font_size)
        # underline manual si se pasa rect
        if underline and rect:
            baseline_y = y1 - 2
            page.draw_line(fitz.Point(x0+2, baseline_y), fitz.Point(x1-2, baseline_y), color=color or (0,0,0), width=0.8)
        # guardar
        buf = io.BytesIO()
        self._fitz_doc.save(buf)
        buf.seek(0)
        self._sync_from_fitz_bytes(buf)
        self._notify_history()
        return info_changed

    def delete_annotation(self, page_index: int, xref: int):
        if not self._fitz_doc or not self._pike_doc:
            return False
        page = self._fitz_doc.load_page(page_index)
        annot = page.load_annot(xref)
        if not annot:
            return False
        page.delete_annot(annot)
        buf = io.BytesIO()
        self._fitz_doc.save(buf)
        buf.seek(0)
        self._sync_from_fitz_bytes(buf)
        self._notify_history()
        return True

    def add_highlight_rect(self, page_index: int, rect, color_rgb=(255,255,0), opacity: float = 0.35) -> bool:
        """
        Crea un rectángulo de resaltado semitransparente sin borde visible.
        """
        if not self._fitz_doc or not self._pike_doc:
            return False
        if page_index < 0 or page_index >= self.page_count():
            return False
        x0,y0,x1,y1 = rect
        if x1 < x0: x0,x1 = x1,x0
        if y1 < y0: y0,y1 = y1,y0
        if (x1 - x0) <= 0 or (y1 - y0) <= 0:
            return False
        page = self._fitz_doc.load_page(page_index)
        r,g,b = (c/255.0 for c in color_rgb)
        annot = page.add_rect_annot(fitz.Rect(x0,y0,x1,y1))
        annot.set_colors(stroke=None, fill=(r,g,b))
        annot.set_opacity(max(0.05, min(1.0, opacity)))
        # Eliminar borde (width=0 y sin dash)
        try:
            annot.set_border(width=0, dashes=[])
        except:
            pass
        annot.update()
        buf = io.BytesIO()
        self._fitz_doc.save(buf)
        buf.seek(0)
        self._sync_from_fitz_bytes(buf)
        self._notify_history()
        return True

    def set_history(self, history):
        self._history = history

    def get_pdf_bytes(self) -> bytes:
        if not self._pike_doc:
            return b""
        buf = io.BytesIO()
        self._pike_doc.save(buf)
        return buf.getvalue()

    def load_from_bytes(self, data: bytes):
        """Carga estado (para undo/redo) sin registrar nuevo snapshot."""
        self.close()
        self._pike_doc = pikepdf.Pdf.open(io.BytesIO(data))
        self._fitz_doc = fitz.open(stream=data, filetype="pdf")
        self.dirty = True  # estado modificado
        if self._font_manager:
            self._register_external_fonts()

    def _notify_history(self, initial=False):
        if not self._history:
            return
        data = self.get_pdf_bytes()
        if initial and not data:
            return
        if initial and self._history:
            self._history.reset_with(data)
        else:
            self._history.push(data)

    def set_font_manager(self, font_manager: FontManager):
        """
        Asigna font manager. Si ya hay documento abierto registra las fuentes.
        """
        self._font_manager = font_manager
        if self._fitz_doc and font_manager:
            self._register_external_fonts()

    def _register_external_fonts(self):
        if not (self._fitz_doc and self._font_manager):
            return
        for f in self._font_manager.iter_fonts():
            try:
                self._fitz_doc.insert_font(fontname=f.font_name, fontfile=f.path)
            except Exception:
                pass

    def _is_base14(self, name: str) -> bool:
        return name in {
            'helv','helvb','helvi','helvbi',
            'times','timesb','timesi','timesbi',
            'cour','courb','couri','courbi',
            'symbol','zapfdingbats'
        }

    def _fontfile_for(self, internal_name: str) -> Optional[str]:
        if not self._font_manager:
            return None
        for f in self._font_manager.iter_fonts():
            if f.font_name == internal_name:
                return f.path
        return None
