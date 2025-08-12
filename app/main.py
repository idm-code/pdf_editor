import tkinter as tk
import sys, os

def _enable_dpi_awareness():
    if sys.platform.startswith("win"):
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

def resource_path(rel_path: str):
    """
    Devuelve ruta válida tanto en ejecución normal como congelada (PyInstaller).
    """
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS  # type: ignore
    else:
        base = os.path.abspath(".")
    return os.path.join(base, rel_path)

# Llamar antes de crear la ventana
_enable_dpi_awareness()

from app.ui.main_window import MainWindow  # después de helper

def main():
    root = tk.Tk()
    root.title('PDF Editor')
    # Establecer icono ventana (ignora si falta)
    try:
        ico_path = resource_path('assets/favicon.ico')
        if os.path.isfile(ico_path):
            root.iconbitmap(ico_path)
    except Exception:
        pass
    root.geometry('1024x768')
    MainWindow(root)
    root.mainloop()

if __name__ == '__main__':
    main()
