import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, colorchooser
from .thumbnail_panel import ThumbnailPanel
from ..core.doc_manager import DocumentManager
from ..core.history import HistoryManager
from .page_view import PageView
from .menus import MenusBuilder
from .tools.text_tool import TextTool
from .tools.highlight_tool import HighlightTool
import tkinter.font as tkfont
from ..core.font_manager import FontManager
import os

class MainWindow(tk.Frame):
    """
    Orquesta: documento, vista de página, miniaturas, menús y herramientas.
    """
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.doc = DocumentManager()
        self.history = HistoryManager(limit=40)
        self.doc.set_history(self.history)
        self.pack(fill='both', expand=True)

        self.rowconfigure(1, weight=1)
        self.columnconfigure(1, weight=1)

        # Panel miniaturas y vista (fila 1)
        self.thumb_panel = ThumbnailPanel(self, on_select=self._on_select_page)
        self.thumb_panel.grid(row=1, column=0, sticky='ns')
        self.page_view = PageView(self, self._get_pixmap, self._page_count)
        self.page_view.grid(row=1, column=1, sticky='nsew')

        # Inicializar atributos de estilo (usados por ribbon)
        self.font_family_var = tk.StringVar(value='Helvetica')
        self.font_size_var = tk.IntVar(value=14)
        self.bold_var = tk.BooleanVar(value=False)
        self.italic_var = tk.BooleanVar(value=False)
        self.erase_var = tk.BooleanVar(value=False)
        self.color_rgb = (0,0,0)
        self.underline_var = tk.BooleanVar(value=False)
        self.underline_color_rgb = (0,0,0)

        # Highlight estado
        self.highlight_color_rgb = (255, 255, 0)
        self.highlight_opacity = tk.DoubleVar(value=0.35)

        # Font manager: cargar fuentes externas (directorio fonts/ si existe)
        self.font_manager = FontManager()
        fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
        if os.path.isdir(fonts_dir):
            self.font_manager.load_dir(fonts_dir)
        self.doc.set_font_manager(self.font_manager)

        # Tools
        self.text_tool = TextTool(self.page_view, self.doc,
                                  self._collect_text_style, self._after_doc_change)
        self.highlight_tool = HighlightTool(self.page_view, self.doc,
                                            self._collect_highlight_style, self._after_doc_change)
        self.active_tool_name = 'text'
        self.page_view.set_tool(self.text_tool)

        # Ribbon después de tener tools
        self._build_ribbon()

        # Zoom scale
        self.zoom_var = tk.DoubleVar(value=self.page_view.zoom * 100)
        self.zoom_scale = tk.Scale(self, from_=10, to=400, orient='horizontal',
                                   variable=self.zoom_var, command=self._on_zoom_scale,
                                   label='Zoom (%)')
        self.zoom_scale.grid(row=2, column=0, columnspan=2, sticky='ew')

        # Menús
        MenusBuilder(self.master).build(
            self.open_pdf, self.insert_pdf, self.save_pdf, self.save_as_pdf,
            self.delete_current_page, self.duplicate_current_page, self.insert_blank_page,
            self.replace_current_page, self.extract_current_page, self.export_current_page_image,
            lambda: self._zoom_btn(1.25), lambda: self._zoom_btn(0.8),
            self._zoom_reset, self._fit_width,
            lambda: self._rotate(90), lambda: self._rotate(-90),
            lambda: self._move_page(-1), lambda: self._move_page(1),
            self._undo_action, self._redo_action
        )

        # Wheel
        self.page_view.canvas.bind('<MouseWheel>', self._on_wheel)
        self.page_view.canvas.bind('<Control-MouseWheel>', self._on_wheel_ctrl)

    # ---------- Ribbon ----------
    def _build_ribbon(self):
        ribbon = tk.Frame(self, bd=1, relief='groove', bg='#f2f2f2')
        ribbon.grid(row=0, column=0, columnspan=2, sticky='ew')
        # Grupo herramientas (selector)
        grp_tools = tk.LabelFrame(ribbon, text='Herramientas', padx=4, pady=2)
        grp_tools.pack(side='left', padx=4, pady=2)
        self.tool_var = tk.StringVar(value=self.active_tool_name)
        def change_tool():
            name = self.tool_var.get()
            if name == self.active_tool_name:
                return
            # Commit texto actual antes de cambiar
            if self.active_tool_name == 'text':
                # commit implícito sólo si está editando y hay contenido
                try:
                    self.text_tool._commit_to_pdf()
                except:
                    pass
            if name == 'text':
                self.page_view.set_tool(self.text_tool)
            else:
                self.page_view.set_tool(self.highlight_tool)
            self.active_tool_name = name
        tk.Radiobutton(grp_tools, text='Texto', value='text', variable=self.tool_var,
                       command=change_tool).pack(side='left')
        tk.Radiobutton(grp_tools, text='Resaltar', value='highlight', variable=self.tool_var,
                       command=change_tool).pack(side='left')

        # Grupo texto
        group_text = tk.LabelFrame(ribbon, text='Texto', padx=4, pady=2)
        group_text.pack(side='left', padx=4, pady=2)

        def style_changed(*_):
            self._refresh_preview()
            self.text_tool.refresh_style()

        tk.Label(group_text, text='Fuente:').pack(side='left')
        font_items = ['Helvetica','Times','Courier'] + self.font_manager.list_display_names()
        self.font_family_var.set(font_items[0])
        font_menu = tk.OptionMenu(group_text, self.font_family_var, *font_items,
                                  command=lambda *_: style_changed())
        font_menu.pack(side='left')
        tk.Label(group_text, text='Tam:').pack(side='left')
        tk.Spinbox(group_text, from_=6, to=200, width=4, textvariable=self.font_size_var,
                   command=style_changed).pack(side='left')
        tk.Checkbutton(group_text, text='N', variable=self.bold_var,
                       command=style_changed).pack(side='left')
        tk.Checkbutton(group_text, text='I', variable=self.italic_var,
                       command=style_changed).pack(side='left')
        tk.Checkbutton(group_text, text='Subr', variable=self.underline_var,
                       command=style_changed).pack(side='left')
        tk.Button(group_text, text='Color', command=self._choose_color).pack(side='left')
        tk.Button(group_text, text='Color subr', command=self._choose_underline_color).pack(side='left')
        tk.Checkbutton(group_text, text='Borrar fondo', variable=self.erase_var).pack(side='left')
        self.font_preview = tk.Label(group_text, text='Aa', bd=1, relief='sunken', padx=4)
        self.font_preview.pack(side='left', padx=6)

        # Grupo resaltado
        grp_hl = tk.LabelFrame(ribbon, text='Resaltado', padx=4, pady=2)
        grp_hl.pack(side='left', padx=4, pady=2)

        def pick_hl_color():
            c = colorchooser.askcolor(color=f'#{self.highlight_color_rgb[0]:02x}{self.highlight_color_rgb[1]:02x}{self.highlight_color_rgb[2]:02x}')
            if c and c[0]:
                r,g,b = map(int,c[0])
                self.highlight_color_rgb = (r,g,b)
                hl_sample.config(bg=f'#{r:02x}{g:02x}{b:02x}')
        tk.Button(grp_hl, text='Color', command=pick_hl_color).pack(side='left')
        tk.Label(grp_hl, text='Opac:').pack(side='left')
        tk.Scale(grp_hl, from_=0.1, to=0.9, resolution=0.05, orient='horizontal',
                 variable=self.highlight_opacity, length=120).pack(side='left')
        hl_sample = tk.Label(grp_hl, width=2, relief='sunken',
                             bg=f'#{self.highlight_color_rgb[0]:02x}{self.highlight_color_rgb[1]:02x}{self.highlight_color_rgb[2]:02x}')
        hl_sample.pack(side='left', padx=4)

        self._refresh_preview()

    # ---------- Callbacks Menú / Acciones Documento ----------
    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[('PDF','*.pdf')])
        if not path: return
        try:
            self.doc.open(path)
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo abrir: {e}')
            return
        self._refresh_thumbs()

    def insert_pdf(self):
        p = filedialog.askopenfilename(filetypes=[('PDF','*.pdf')])
        if not p: return
        try:
            self.doc.insert_pdf(p)
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo insertar: {e}')
            return
        self._refresh_thumbs()

    def save_pdf(self):
        if not self.doc.is_open(): return
        try:
            if not self.doc.path: return self.save_as_pdf()
            self.doc.save()
            messagebox.showinfo('OK','Guardado')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def save_as_pdf(self):
        if not self.doc.is_open(): return
        p = filedialog.asksaveasfilename(defaultextension='.pdf')
        if not p: return
        try:
            self.doc.save_as(p)
            messagebox.showinfo('OK','Guardado')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def delete_current_page(self):
        idx = self.page_view.current_index
        if idx is None: return
        if not messagebox.askyesno('Confirmar','Eliminar página?'): return
        self.doc.remove_page(idx)
        self.page_view.set_page(None) if self.doc.page_count()==0 else self.page_view.set_page( min(idx, self.doc.page_count()-1) )
        self._refresh_thumbs()

    def insert_blank_page(self):
        idx = self.page_view.current_index
        pos = self.doc.page_count() if idx is None else idx + 1
        self.doc.insert_blank_page(pos)
        self._refresh_thumbs()
        self.page_view.set_page(pos)

    def duplicate_current_page(self):
        idx = self.page_view.current_index
        if idx is None: return
        self.doc.duplicate_page(idx)
        self._refresh_thumbs()
        self.page_view.set_page(idx+1)

    def replace_current_page(self):
        idx = self.page_view.current_index
        if idx is None: return
        p = filedialog.askopenfilename(filetypes=[('PDF','*.pdf')])
        if not p: return
        pg = simpledialog.askinteger('Página origen','Número (1..n):', minvalue=1)
        if pg is None: return
        self.doc.replace_page(idx, p, pg-1)
        self._refresh_thumbs()
        self.page_view.render()

    def extract_current_page(self):
        idx = self.page_view.current_index
        if idx is None: return
        out = filedialog.asksaveasfilename(defaultextension='.pdf')
        if not out: return
        self.doc.extract_pages([idx], out)
        messagebox.showinfo('Extraído', out)

    def export_current_page_image(self):
        idx = self.page_view.current_index
        if idx is None: return
        out = filedialog.asksaveasfilename(defaultextension='.png',
                                           filetypes=[('PNG','*.png'),('JPEG','*.jpg')])
        if not out: return
        pix = self.doc.get_page_pixmap(idx, max(self.page_view.zoom, 1.5))
        from PIL import Image
        img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        mode = 'PNG' if out.lower().endswith('.png') else 'JPEG'
        img.save(out, mode)
        messagebox.showinfo('Exportado', out)

    def _rotate(self, deg):
        idx = self.page_view.current_index
        if idx is None: return
        self.doc.rotate_page(idx, deg)
        self._refresh_thumbs()
        self.page_view.render()

    def _move_page(self, delta):
        idx = self.page_view.current_index
        if idx is None: return
        new_idx = idx + delta
        if not (0 <= new_idx < self.doc.page_count()):
            return
        order = list(range(self.doc.page_count()))
        order[idx], order[new_idx] = order[new_idx], order[idx]
        self.doc.reorder_pages(order)
        self._refresh_thumbs()
        self.page_view.set_page(new_idx)

    # ---------- Zoom ----------
    def _zoom_btn(self, factor):
        self.page_view.change_zoom_factor(factor)
        self._sync_zoom_scale()

    def _zoom_reset(self):
        self.page_view.reset_zoom()
        self._sync_zoom_scale()

    def _fit_width(self):
        self.page_view.fit_width()
        self._sync_zoom_scale()

    def _on_zoom_scale(self, _v):
        if self.page_view.current_index is None: return
        self.page_view.zoom_mode = 'custom'
        self.page_view.zoom = self.zoom_var.get()/100.0
        self.page_view.render()

    def _sync_zoom_scale(self):
        target = round(self.page_view.zoom*100,2)
        if abs(self.zoom_var.get()-target)>0.1:
            self.zoom_var.set(target)

    # ---------- Helpers internos ----------
    def _get_pixmap(self, index, zoom):
        return self.doc.get_page_pixmap(index, zoom)

    def _page_count(self):
        return self.doc.page_count()

    def _refresh_thumbs(self):
        self.thumb_panel.clear()
        if not self.doc.is_open():
            return
        for i in range(self.doc.page_count()):
            pix = self.doc.get_page_pixmap(i, zoom=0.12)
            from PIL import Image, ImageTk
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)
            self.thumb_panel.add_thumbnail(i, photo)
        if self.doc.page_count()>0:
            if self.page_view.current_index is None or self.page_view.current_index >= self.doc.page_count():
                self.page_view.set_page(0)
            self.thumb_panel.select(self.page_view.current_index)

    def _on_select_page(self, index: int):
        self.page_view.set_page(index)
        self.thumb_panel.select(index)

    # ---------- Eventos wheel ----------
    def _on_wheel(self, e):
        if self.page_view.canvas.yview() == (0.0,1.0): return
        self.page_view.scroll_wheel(-1 if e.delta>0 else 1)

    def _on_wheel_ctrl(self, e):
        self.page_view.scroll_wheel_ctrl(e.delta>0)
        self._sync_zoom_scale()

    # --- Añadir este método (faltaba) ---
    def _after_doc_change(self):
        """
        Re-renderiza la página actual tras un cambio (añadir texto, etc.)
        y refresca las miniaturas para reflejar el estado actualizado.
        """
        self.page_view.render()
        self._refresh_thumbs()

    # ---------- Text style collection ----------
    def _collect_text_style(self):
        base_map = {'Helvetica':'helv','Times':'times','Courier':'cour'}
        selected = self.font_family_var.get()
        # ¿Es fuente personalizada?
        fdef = self.font_manager.find_by_display(selected)
        if fdef:
            # Se usa tal cual el nombre interno insertado en fitz
            fontname = fdef.font_name
        else:
            base = base_map.get(selected,'helv')
            bold = self.bold_var.get()
            italic = self.italic_var.get()
            if base == 'helv':
                if bold and italic: fontname = 'helvbi'
                elif bold: fontname = 'helvb'
                elif italic: fontname = 'helvi'
                else: fontname = 'helv'
            elif base == 'times':
                if bold and italic: fontname = 'timesbi'
                elif bold: fontname = 'timesb'
                elif italic: fontname = 'timesi'
                else: fontname = 'times'
            elif base == 'cour':
                if bold and italic: fontname = 'courbi'
                elif bold: fontname = 'courb'
                elif italic: fontname = 'couri'
                else: fontname = 'cour'
            else:
                fontname = 'helv'
        return (fontname,
                self.font_size_var.get(),
                self.color_rgb,
                self.erase_var.get(),
                self.underline_var.get(),
                self.underline_color_rgb)

    def _refresh_preview(self):
        f = tkfont.Font(family=self.font_family_var.get(),
                        size=self.font_size_var.get(),
                        weight='bold' if self.bold_var.get() else 'normal',
                        slant='italic' if self.italic_var.get() else 'roman')
        r,g,b = self.color_rgb
        self.font_preview.config(font=f, fg=f'#{r:02x}{g:02x}{b:02x}')
        self.font_preview.config(underline=1 if self.underline_var.get() else 0)

    def _choose_color(self):
        c = colorchooser.askcolor(color=f'#{self.color_rgb[0]:02x}{self.color_rgb[1]:02x}{self.color_rgb[2]:02x}')
        if c and c[0]:
            r,g,b = map(int,c[0])
            self.color_rgb = (r,g,b)
            self._refresh_preview()
            if hasattr(self, 'text_tool'):
                self.text_tool.refresh_style()

    def _choose_underline_color(self):
        c = colorchooser.askcolor(color=f'#{self.underline_color_rgb[0]:02x}{self.underline_color_rgb[1]:02x}{self.underline_color_rgb[2]:02x}')
        if c and c[0]:
            r,g,b = map(int,c[0])
            self.underline_color_rgb = (r,g,b)
            # Se aplica sólo al commit final
            if hasattr(self, 'text_tool'):
                self.text_tool.refresh_style()

    def _collect_highlight_style(self):
        return (self.highlight_color_rgb, self.highlight_opacity.get())

    def _undo_action(self, event=None):
        if self.history.can_undo():
            data = self.history.undo()
            self.doc.load_from_bytes(data)
            self._after_doc_change()

    def _redo_action(self, event=None):
        if self.history.can_redo():
            data = self.history.redo()
            self.doc.load_from_bytes(data)
            self._after_doc_change()
