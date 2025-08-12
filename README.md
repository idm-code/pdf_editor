# PDF Editor

Editor PDF sencillo basado en Tkinter + PyMuPDF + pikepdf.

## Características actuales
- Abrir, guardar y guardar como PDF.
- Insertar otro PDF al final.
- Insertar página en blanco, duplicar, reemplazar, eliminar, reordenar (mover arriba/abajo), rotar.
- Deshacer / Rehacer (historial en memoria).
- Miniaturas navegables con selección de página.
- Zoom (manual, ajustar ancho, rueda + Ctrl, control deslizante).
- Herramienta Texto:
  - Cuadro de texto arrastrable y redimensionable (esquinas + barra superior de movimiento).
  - Fuentes estándar PDF (Helvetica / Times / Courier) más fuentes personalizadas (cargadas dinámicamente desde app/fonts/).
  - Negrita, cursiva, subrayado.
  - Cambio de color de texto y color de subrayado.
  - Opción “Borrar fondo” (pinta un rectángulo blanco antes de escribir).
  - Asegura inserción a la primera (normaliza tamaño mínimo y fallback robusto de fuente).
- Herramienta Resaltado:
  - Rectángulo de highlight semitransparente con color y opacidad configurables.
- Herramienta Imagen:
  - Carga de imagen (PNG/JPG/BMP/TIFF…).
  - Arrastrar un rectángulo y previsualización con ajuste proporcional (mantiene aspecto).
  - Redimensionar antes de confirmar (Enter) o cancelar (Esc).
- Exportar página como imagen (PNG/JPEG) con zoom adecuado.
- Extraer página a nuevo PDF.
- Rotación de página en múltiplos de 90°.
- Icono de aplicación (favicon.ico) soportado en ejecución normal y empaquetada.
- Empaquetable como ejecutable Windows (PyInstaller).

## Estructura
- Núcleo documento: [`DocumentManager`](app/core/doc_manager.py)
- Gestor historial (undo/redo): [`HistoryManager`](app/core/history.py)
- Carga de fuentes externas: [`FontManager`](app/core/font_manager.py)
- UI principal / orquestación: [`MainWindow`](app/ui/main_window.py)
- Render y eventos de página: [`PageView`](app/ui/page_view.py)
- Menús: [`MenusBuilder`](app/ui/menus.py)
- Miniaturas: [`ThumbnailPanel`](app/ui/thumbnail_panel.py)
- Herramientas:
  - Texto: [`TextTool`](app/ui/tools/text_tool.py)
  - Resaltado: [`HighlightTool`](app/ui/tools/highlight_tool.py)
  - Imagen: [`ImageTool`](app/ui/tools/image_tool.py)

## Dependencias
Listado en [requirements.txt](requirements.txt):
- pikepdf
- PyMuPDF
- Pillow

## Instalación rápida (entorno desarrollo)
```bash
python -m venv .venv
# Activar entorno (Windows)
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

## Uso básico
1. Archivo > Abrir para cargar un PDF.
2. Navega con miniaturas (panel izquierdo).
3. Herramientas (ribbon):
   - Texto: arrastra un rectángulo, escribe; Enter confirma, Esc cancela. Puedes mover (barra superior) o redimensionar (esquinas) antes de confirmar.
   - Resaltar: arrastra rectángulo; se crea al soltar el ratón.
   - Imagen: pulsa “Cargar imagen”, selecciona archivo; luego arrastra rectángulo donde quieras que quepa. Ajusta tamaño; Enter incrusta, Esc cancela.
4. Cambia fuente, tamaño, estilos y color antes o durante la edición activa (refresca en vivo).
5. “Borrar fondo” genera un rectángulo blanco bajo el texto (para tapar contenido anterior).
6. Subrayado: activa la casilla y (opcional) elige color de subrayado.
7. Undo / Redo: Ctrl+Z / Ctrl+Y o menú Edición.
8. Rotar página: Menú Página.
9. Insertar página en blanco / duplicar / reemplazar / eliminar: Menú Edición / Página.
10. Exportar página como imagen: Menú Edición > Exportar página como imagen.
11. Guardar / Guardar como: Menú Archivo.

## Fuentes personalizadas
Coloca archivos .ttf / .otf en `app/fonts/` antes de ejecutar. Se cargan al inicio y aparecen en el desplegable de fuentes. Se embeben automáticamente al insertar texto (PyMuPDF con `insert_font`).

## Atajos relevantes
- Ctrl+Z / Ctrl+Y: Deshacer / Rehacer.
- Rueda + Ctrl: Zoom in/out.
- Enter (en edición de texto o imagen): Confirmar.
- Esc: Cancelar edición.
- Alt + arrastrar dentro del texto: Mover (alternativa a barra superior).

## Undo / Redo
Cada operación que modifica el documento (texto, resaltar, imagen, páginas) actualiza el snapshot PDF completo vía [`HistoryManager`](app/core/history.py). El historial se guarda en memoria (ajusta límite en `HistoryManager(limit=N)`).

## Diseño / Principios
- Documento y rendering desacoplados: [`DocumentManager`](app/core/doc_manager.py) no conoce widgets; la UI traduce coordenadas.
- Herramientas intercambiables (protocol simple de métodos de eventos).
- Refresco consistente tras cada commit (`_after_doc_change` en [`MainWindow`](app/ui/main_window.py)) sincroniza vista y miniaturas.
- Inserción robusta de texto:
  - Normaliza dimensiones mínimas para evitar “no inserta a la primera”.
  - Fallback a “helv” si la fuente personalizada falla.
  - Fallback línea a línea si `insert_textbox` no colocó nada.

## Empaquetado (PyInstaller)
Archivo spec: [PDFEditor.spec](PDFEditor.spec)

Generar (modo carpeta):
```powershell
.venv\Scripts\activate
pyinstaller PDFEditor.spec --noconfirm --clean
```
Ejecutable: `dist/PDFEditor/PDFEditor.exe`

### Ejecución del .exe
El ejecutable se encuentra dentro de la carpeta `dist/PDFEditor/`.  
Al ejecutarlo por primera vez, Windows SmartScreen puede mostrar un aviso de seguridad porque no está firmado con un certificado reconocido.  
Puedes omitirlo con:
1. Más información
2. Ejecutar de todas formas
El binario se genera localmente a partir del código fuente presente, por lo que no introduce riesgo adicional siempre que confíes en este repositorio.

### Icono
Se usa `app/assets/favicon.ico` (multi‑res recomendado).

### Comprobar en máquina limpia
- Copiar carpeta `dist/PDFEditor`
- Ejecutar `PDFEditor.exe`
- Probar abrir PDF, texto, highlight, imagen, undo/redo.

### Modo One-File (opcional)
Adaptar spec (no incluido por defecto). Arranque más lento (desempaqueta en `%TEMP%`).

## Limitaciones actuales
- El texto incrustado no es editable posteriormente (no se mantiene objeto de anotación editable; se inserta en el content stream).
- Redacción simple (rectángulo blanco) no elimina objetos subyacentes complejos fuera de su área parcial.
- No hay búsqueda de texto todavía.
- No hay selección múltiple de páginas para operaciones en lote.
- No hay tema oscuro definido en la versión actual (solo estilo básico Tkinter).

## Extensiones futuras (ideas)
- Edición posterior de cuadros de texto (almacenar metadata para reabrir overlay).
- Búsqueda y resaltado de resultados.
- Exportar rango de páginas a imágenes.
- Modo dark / theming avanzado.
- Compresión / optimización de imágenes al insertar.

## Problemas comunes
| Problema | Causa | Solución |
|----------|-------|----------|
| Fuente no aparece | Archivo inválido o no OTF/TTF | Verifica fuente, reinicia app |
| Texto no se ve tras insertar | Área demasiado pequeña previa al fix | Ya se normaliza; ampliar rect si persiste |
| Imagen no se inserta | Ruta inválida / formato no soportado | Probar PNG/JPG básicos |
| Undo no revierte | Límite historial excedido | Aumentar límite en `HistoryManager` |
| Error al empaquetar | Texto extra en .spec | Usar versión limpia de [PDFEditor.spec](PDFEditor.spec) |
| Aviso SmartScreen | Ejecutable sin firma | Clic en “Más información” > “Ejecutar de todas formas” |

## Mantenimiento
- Añadir tests unitarios (pendiente carpeta tests/) centrados en:
  - Inserción de texto (varias fuentes / estilos).
  - Undo/redo secuencial y tras rotaciones.
  - Inserción y escalado de imágenes.
  - Reordenar y rotar páginas.

## Licencia
Pendiente definir (MIT recomendado si no hay restricciones).

---
Hecho con: [`DocumentManager`](app/core/doc_manager.py), [`MainWindow`](app/ui/main_window.py), [`TextTool`](app/ui/tools/text_tool.py), [`HighlightTool`](app/ui/tools/highlight_tool.py)