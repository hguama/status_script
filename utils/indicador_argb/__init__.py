"""
indicador_argb — Círculo de color con fondo realmente transparente en X11/XWayland.

Tk no puede crear ventanas con canal alfa y el recorte con la extensión Shape
no se respeta bajo XWayland (queda el cuadrado de fondo). Se usa una ventana X11
propia de 32 bits (ARGB): el compositor mezcla los píxeles transparentes con lo
que hay detrás, así solo se ve el círculo.

Todas las llamadas deben hacerse desde el mismo hilo (el de Tk): python-xlib
no es thread-safe.

Uso:
    c = CirculoARGB(30, x=945, y=5)
    c.set_color("#66BB6A")
    c.show(); c.move(100, 100); c.hide()
"""

import logging

from Xlib import X, display
from Xlib.ext import shape

logger = logging.getLogger(__name__)

_d = display.Display()
_scr = _d.screen()
_vis = next(
    (v for dep in _scr.allowed_depths if dep.depth == 32
     for v in dep.visuals if v.visual_class == X.TrueColor),
    None,
)
if _vis is None:
    raise RuntimeError("No hay visual ARGB de 32 bits disponible")
_cmap = _scr.root.create_colormap(_vis.visual_id, X.AllocNone)


class CirculoARGB:
    def __init__(self, size, x=0, y=0, color="#FFFFFF"):
        self.size = size
        self._color = color
        self._visible = False
        self._win = _scr.root.create_window(
            x, y, size, size, 0, 32, X.InputOutput, _vis.visual_id,
            background_pixel=0, border_pixel=0, colormap=_cmap,
            override_redirect=True,
        )
        try:
            # Sin región de entrada: los clics atraviesan el indicador.
            self._win.shape_rectangles(shape.ShapeSet, shape.ShapeInput, X.Unsorted, 0, 0, [])
        except Exception as e:
            logger.debug("[ARGB] no se pudo hacer transparente a los clics: %s", e)
        _d.sync()

    def _dibujar(self):
        r, g, b = (int(self._color[i:i + 2], 16) for i in (1, 3, 5))
        gc = self._win.create_gc(foreground=0xFF000000 | (r << 16) | (g << 8) | b)
        self._win.clear_area(0, 0, self.size, self.size)
        self._win.fill_arc(gc, 0, 0, self.size, self.size, 0, 360 * 64)
        gc.free()
        _d.flush()

    def set_color(self, color):
        self._color = color
        if self._visible:
            self._dibujar()

    def show(self):
        self._win.map()
        self._win.configure(stack_mode=X.Above)
        self._visible = True
        self._dibujar()

    def hide(self):
        self._win.unmap()
        self._visible = False
        _d.flush()

    def move(self, x, y):
        self._win.configure(x=x, y=y)
        _d.flush()
