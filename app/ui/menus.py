import tkinter as tk

class MenusBuilder:
    """
    Construye menús y conecta callbacks (sin menú de herramientas ahora).
    """
    def __init__(self, master: tk.Tk):
        self.master = master

    def build(self,
              on_open, on_insert_pdf, on_save, on_save_as,
              on_delete_page, on_duplicate, on_insert_blank,
              on_replace_page, on_extract_page, on_export_img,
              on_zoom_in, on_zoom_out, on_zoom_reset, on_fit_width,
              on_rotate_cw, on_rotate_ccw, on_move_up, on_move_down,
              on_undo, on_redo):
        menubar = tk.Menu(self.master)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Abrir', command=on_open)
        file_menu.add_command(label='Insertar PDF...', command=on_insert_pdf)
        file_menu.add_separator()
        file_menu.add_command(label='Guardar', command=on_save)
        file_menu.add_command(label='Guardar como...', command=on_save_as)
        file_menu.add_separator()
        file_menu.add_command(label='Salir', command=self.master.destroy)
        menubar.add_cascade(label='Archivo', menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label='Deshacer', command=on_undo, accelerator='Ctrl+Z')
        edit_menu.add_command(label='Rehacer', command=on_redo, accelerator='Ctrl+Y')
        edit_menu.add_separator()
        edit_menu.add_command(label='Eliminar página', command=on_delete_page)
        edit_menu.add_command(label='Duplicar página', command=on_duplicate)
        edit_menu.add_command(label='Insertar página en blanco', command=on_insert_blank)
        edit_menu.add_command(label='Reemplazar página...', command=on_replace_page)
        edit_menu.add_separator()
        edit_menu.add_command(label='Extraer página...', command=on_extract_page)
        edit_menu.add_command(label='Exportar página como imagen...', command=on_export_img)
        menubar.add_cascade(label='Edición', menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label='Zoom +', command=on_zoom_in)
        view_menu.add_command(label='Zoom -', command=on_zoom_out)
        view_menu.add_separator()
        view_menu.add_command(label='100%', command=on_zoom_reset)
        view_menu.add_command(label='Ajustar ancho', command=on_fit_width)
        menubar.add_cascade(label='Ver', menu=view_menu)

        page_menu = tk.Menu(menubar, tearoff=0)
        page_menu.add_command(label='Rotar 90° ↻', command=on_rotate_cw)
        page_menu.add_command(label='Rotar 90° ↺', command=on_rotate_ccw)
        page_menu.add_separator()
        page_menu.add_command(label='Subir página', command=on_move_up)
        page_menu.add_command(label='Bajar página', command=on_move_down)
        menubar.add_cascade(label='Página', menu=page_menu)

        self.master.bind_all('<Control-z>', lambda e: on_undo())
        self.master.bind_all('<Control-y>', lambda e: on_redo())
        self.master.config(menu=menubar)