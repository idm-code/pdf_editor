import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class FontDef:
    display_name: str   # Nombre que ve el usuario
    font_name: str      # Nombre interno que usaremos en PyMuPDF
    path: str           # Ruta absoluta al fichero

class FontManager:
    """
    Gestiona fuentes externas (TTF/OTF). Se registran en el documento fitz al abrir.
    """
    def __init__(self):
        self._fonts: List[FontDef] = []

    def load_dir(self, directory: str):
        exts = {'.ttf', '.otf'}
        for fname in sorted(os.listdir(directory)):
            base, ext = os.path.splitext(fname)
            if ext.lower() not in exts:
                continue
            path = os.path.join(directory, fname)
            # Nombre interno sin espacios
            internal = base.replace(' ', '_')
            # Evitar colisiones
            if any(f.font_name == internal for f in self._fonts):
                i = 2
                new_internal = f"{internal}_{i}"
                while any(f.font_name == new_internal for f in self._fonts):
                    i += 1
                    new_internal = f"{internal}_{i}"
                internal = new_internal
            self._fonts.append(FontDef(display_name=base, font_name=internal, path=path))

    def list_display_names(self):
        return [f.display_name for f in self._fonts]

    def find_by_display(self, display_name: str) -> Optional[FontDef]:
        for f in self._fonts:
            if f.display_name == display_name:
                return f
        return None

    def iter_fonts(self):
        return iter(self._fonts)