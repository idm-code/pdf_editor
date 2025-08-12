# PDF Editor

Editor PDF sencillo basado en Tkinter + PyMuPDF + pikepdf.

## Características actuales
- Abrir, guardar y guardar como PDF.
- Insertar otro PDF al final.
- Insertar página en blanco, duplicar, reemplazar, eliminar, reordenar (mover arriba/abajo), rotar.
- Extraer página a nuevo PDF.
- Exportar página como imagen (PNG/JPEG).
- Miniaturas navegables.
- Zoom (manual, ajustar ancho, rueda + Ctrl).
- Herramienta de inserción de texto (cuadro) con fuente, tamaño, negrita, cursiva, color y opción de “borrar fondo” (pinta rectángulo blanco debajo).

## Estructura
- Núcleo documento: [`DocumentManager`](app/core/doc_manager.py)
- UI principal / orquestación: [`MainWindow`](app/ui/main_window.py)
- Render y eventos de página: [`PageView`](app/ui/page_view.py)
- Menús: [`MenusBuilder`](app/ui/menus.py)
- Miniaturas: [`ThumbnailPanel`](app/ui/thumbnail_panel.py)
- Herramientas (extensibles): [`TextTool`](app/ui/tools/text_tool.py)

## Dependencias
Listado en [requirements.txt](requirements.txt):
- pikepdf
- PyMuPDF
- Pillow

## Instalación rápida
```bash
python -m venv .venv
# Activar entorno (Windows)
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

## Uso
1. Archivo > Abrir para cargar un PDF.
2. Selecciona páginas desde el panel de miniaturas.
3. Menú Edición / Página para operaciones de páginas.
4. Herramientas > Herramienta Texto para insertar texto:
   - Arrastra un rectángulo sobre la página.
   - Escribe y pulsa Enter / Aplicar.
   - Marca “Borrar fondo” si deseas cubrir contenido previo.

## Diseño / Principios
- SRP: Cada clase encapsula una responsabilidad clara.
- OCP: Nuevas herramientas solo requieren implementar una clase tipo herramienta y registrarla.
- DIP: UI depende de abstracciones (protocol Tool) y callbacks en lugar de acoplarse a implementaciones concretas.
- Separación render (PageView) vs lógica documento (`DocumentManager`).
- Sin lógica de PDF en widgets salvo traducciones de coordenadas.

## Extensión futura
- Herramienta de anotaciones movibles / edición posterior de texto.
- Deshacer / rehacer (Command pattern).
- Búsqueda de texto.
- Selección múltiple de páginas y operaciones en lote.
- Exportación rango de páginas a imágenes.
- Empaquetado (PyInstaller).

## Notas técnicas
- Render: PyMuPDF (pixmap) para mostrar.
- Escritura texto: PyMuPDF (insert_textbox); al finalizar se sincronizan bytes con pikepdf para conservar integridad estructural.
- Coordenadas: conversión canvas->página usando offsets y zoom almacenados en [`PageView`](app/ui/page_view.py).
- “Borrar fondo” dibuja un rectángulo blanco; no elimina realmente el contenido anterior (no parsing profundo).

## Limitaciones actuales
- El texto insertado no es editable después (se añade al content stream).
- No hay manejo de anotaciones FreeText movibles (plantilla ya preparada en `DocumentManager` con métodos de anotaciones).
- Sin soporte undo/redo.

## Contribuir
1. Crear rama feature/nombre.
2. Añadir tests (pendiente carpeta tests/).
3. Enviar PR describiendo cambios y arquitectura.

## Licencia
Pendiente definir.