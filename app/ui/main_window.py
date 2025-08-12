import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, colorchooser
from .thumbnail_panel import ThumbnailPanel
from ..core.doc_manager import DocumentManager
from .page_view import PageView
from .menus import MenusBuilder
from .tools.text_tool import TextTool
import tkinter.font as tkfont

class MainWindow(tk.Frame):
    """
    Orquesta: documento, vista de página, miniaturas, menús y herramientas.
    """
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.doc = DocumentManager()
        self.pack(fill='both', expand=True)

        # Layout principal
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.thumb_panel = ThumbnailPanel(self, on_select=self._on_select_page)
        self.thumb_panel.grid(row=0, column=0, sticky='ns')

        self.page_view = PageView(self, self._get_pixmap, self._page_count)
        self.page_view.grid(row=0, column=1, sticky='nsew')

        # Zoom scale
        self.zoom_var = tk.DoubleVar(value=self.page_view.zoom * 100)
        self.zoom_scale = tk.Scale(self, from_=10, to=400, orient='horizontal',
                                   variable=self.zoom_var, command=self._on_zoom_scale,
                                   label='Zoom (%)')
        self.zoom_scale.grid(row=1, column=0, columnspan=2, sticky='ew')

        # Barra de estilo texto
        self._build_text_style_bar()

        # Menús
        MenusBuilder(self.master).build(
            self.open_pdf, self.insert_pdf, self.save_pdf, self.save_as_pdf,
            self.delete_current_page, self.duplicate_current_page, self.insert_blank_page,
            self.replace_current_page, self.extract_current_page, self.export_current_page_image,
            lambda: self._zoom_btn(1.25), lambda: self._zoom_btn(0.8),
            self._zoom_reset, self._fit_width,
            lambda: self._rotate(90), lambda: self._rotate(-90),
            lambda: self._move_page(-1), lambda: self._move_page(1),
            self.activate_text_tool, self.deactivate_tool
        )

        # Wheel bindings
        self.page_view.canvas.bind('<MouseWheel>', self._on_wheel)
        self.page_view.canvas.bind('<Control-MouseWheel>', self._on_wheel_ctrl)

        # Estado herramienta
        self.active_tool = None

    # ---------- Construcción UI ----------
    def _build_text_style_bar(self):
        bar = tk.Frame(self)
        bar.grid(row=2, column=0, columnspan=2, sticky='ew', pady=2)
        self.font_family_var = tk.StringVar(value='Helvetica')
        self.font_size_var = tk.IntVar(value=14)
        self.bold_var = tk.BooleanVar(value=False)
        self.italic_var = tk.BooleanVar(value=False)
        self.erase_var = tk.BooleanVar(value=False)
        self.color_rgb = (0,0,0)

        tk.Label(bar, text='Fuente:').pack(side='left')
        tk.OptionMenu(bar, self.font_family_var, 'Helvetica','Times','Courier').pack(side='left')
        tk.Label(bar, text='Tam:').pack(side='left')
        tk.Spinbox(bar, from_=6, to=200, width=4, textvariable=self.font_size_var).pack(side='left')
        tk.Checkbutton(bar, text='N', variable=self.bold_var, command=self._refresh_preview).pack(side='left')
        tk.Checkbutton(bar, text='I', variable=self.italic_var, command=self._refresh_preview).pack(side='left')
        tk.Checkbutton(bar, text='Borrar fondo', variable=self.erase_var).pack(side='left')
        tk.Button(bar, text='Color', command=self._choose_color).pack(side='left')
        self.font_preview = tk.Label(bar, text='Aa')
        self.font_preview.pack(side='left', padx=6)
        self.text_bar = bar
        self._refresh_preview()
        self.text_bar.grid_remove()  # oculto hasta activar herramienta

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

    # ---------- Herramienta texto ----------
    def activate_text_tool(self):
        if self.active_tool:
            self.deactivate_tool()
        self.text_bar.grid()
        self.active_tool = TextTool(
            self.page_view,
            self.doc,
            self._collect_text_style,
            self._after_doc_change
        )
        self.page_view.set_tool(self.active_tool)

    def deactivate_tool(self):
        if self.active_tool:
            self.page_view.set_tool(None)
            self.active_tool = None
        self.text_bar.grid_remove()

    def _collect_text_style(self):
        base_map = {'Helvetica':'helv','Times':'times','Courier':'cour'}
        base = base_map.get(self.font_family_var.get(),'helv')
        bold = self.bold_var.get()
        italic = self.italic_var.get()
        style = ''
        if base == 'helv':
            if bold and italic: style='-boldoblique'
            elif bold: style='-bold'
            elif italic: style='-oblique'
        elif base == 'times':
            if bold and italic: style='-bolditalic'
            elif bold: style='-bold'
            elif italic: style='-italic'
        elif base == 'cour':
            if bold and italic: style='-boldoblique'
            elif bold: style='-bold'
            elif italic: style='-oblique'
        fontname = base + style
        return fontname, self.font_size_var.get(), self.color_rgb, self.erase_var.get()

    def _after_doc_change(self):
        self.page_view.render()
        self._refresh_thumbs()

    def _refresh_preview(self):
        f = tkfont.Font(family=self.font_family_var.get(),
                        size=self.font_size_var.get(),
                        weight='bold' if self.bold_var.get() else 'normal',
                        slant='italic' if self.italic_var.get() else 'roman')
        r,g,b = self.color_rgb
        self.font_preview.config(font=f, fg=f'#{r:02x}{g:02x}{b:02x}')

    def _choose_color(self):
        c = colorchooser.askcolor(color='#000000')
        if c and c[0]:
            r,g,b = map(int,c[0])
            self.color_rgb = (r,g,b)
            self._refresh_preview()

    # ---------- Eventos wheel ----------
    def _on_wheel(self, e):
        if self.page_view.canvas.yview() == (0.0,1.0): return
        self.page_view.scroll_wheel(-1 if e.delta>0 else 1)

    def _on_wheel_ctrl(self, e):
        self.page_view.scroll_wheel_ctrl(e.delta>0)
        self._sync_zoom_scale()

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
