"""
cursor_texto — Posición en pantalla del cursor de texto de Konsole.

En un terminal el puntero del mouse se oculta al escribir, así que el punto chico
que lo sigue no se ve. Konsole expone el terminal por accesibilidad (AT-SPI) como
un widget ``Text``: de ahí salen el offset del cursor y el rectángulo de su celda,
relativo al widget. Bajo Wayland no hay posición global, así que se suma la
geometría de la ventana activa que envía KWin (``cursor_kwin.ventana()``) más el
origen del widget dentro de la ventana.

Claude Code deja el cursor nativo del terminal en el punto de escritura, así que
el dato también vale para él.

Requiere accesibilidad activa en Konsole (``QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1`` al
arrancarlo, ver DOCs/README_LINUX.md). Sin ella el árbol de AT-SPI no trae a Konsole
y ``get()`` devuelve None, con un aviso en el log.

Uso:
    from utils import cursor_texto
    cursor_texto.iniciar()
    pos = cursor_texto.get()   # (x_centro, y_base) de la celda del cursor, o None
"""

import logging
import threading
import time

from utils import cursor_kwin

logger = logging.getLogger(__name__)

HABILITADA = True

APPS = ("konsole",)          # fragmentos de la clase de la ventana (en minúsculas)
INTERVALO = 0.033            # s entre consultas (~30 por segundo)
TITULO_SSD = 29              # px de la barra de título de KWin sobre el área de cliente
MARGEN_X = 4                 # px entre el borde del widget y la 1ª columna (AT-SPI no lo incluye)
CADUCIDAD = 0.5              # s tras los que una posición sin refrescar deja de valer
CABECERA_PANEL = 22          # px de la barra de título que Konsole pone a cada panel dividido
REBUSCAR = 1.0               # s mínimos entre recorridos del árbol de AT-SPI (~60 ms cada uno)

_pos = None                  # (x_centro, y_base, t) o None
_atspi = None


def log_configuracion():
    estado = "ACTIVO" if HABILITADA else "INACTIVO"
    logger.info("├─ CURSOR-TEXTO  [%s]", estado)
    logger.info("│  apps = %s  |  %.0f consultas/s vía AT-SPI", ", ".join(APPS), 1 / INTERVALO)


def get():
    """(x_centro, y_base) de la celda del cursor de texto de la ventana activa, o None."""
    p = _pos
    if p is None or time.monotonic() - p[2] > CADUCIDAD:
        return None
    return p[0], p[1]


def _buscar_terminales():
    """[(ventana, terminal)] de todas las ventanas de Konsole (pestañas y paneles, visibles o no).

    Puede haber varios procesos Konsole (``--separate``); cada ventana es un grupo aparte
    para poder contar los paneles de una sola.
    """
    terminales = []

    def recorrer(n, ventana, prof=0):
        rol = n.get_role_name()
        if rol == "terminal":
            terminales.append((ventana, n))
        elif prof <= 12 and rol not in ("menu bar", "tool bar"):
            for i in range(n.get_child_count()):
                hijo = n.get_child_at_index(i)
                if hijo:
                    recorrer(hijo, ventana, prof + 1)

    desktop = _atspi.get_desktop(0)
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if not app or (app.get_name() or "").lower() not in APPS:
            continue
        for j in range(app.get_child_count()):
            marco = app.get_child_at_index(j)
            if marco:
                recorrer(marco, (i, j))
    return terminales


def _elegir(terminales):
    """(terminal con foco o None, cuántos paneles hay a la vista en su ventana).

    Consulta barata (solo estados), así que se hace en cada ciclo: el foco puede pasar de
    un panel a otro sin que cambie nada más. Solo la ventana activa tiene un terminal con foco.
    """
    Atspi = _atspi
    foco, ventana_foco, visibles = None, None, {}
    for ventana, t in terminales:
        estados = t.get_state_set()
        if not estados.contains(Atspi.StateType.SHOWING):
            continue
        visibles[ventana] = visibles.get(ventana, 0) + 1
        if estados.contains(Atspi.StateType.FOCUSED):
            foco, ventana_foco = t, ventana
    return foco, visibles.get(ventana_foco, 0)


def _leer(terminal, ventana, dividido):
    """(x_centro, y_base) en pantalla del cursor, o None si no está a la vista."""
    Atspi = _atspi
    w = Atspi.Component.get_extents(terminal, Atspi.CoordType.WINDOW)
    off = Atspi.Text.get_caret_offset(terminal)
    c = Atspi.Text.get_character_extents(terminal, off, Atspi.CoordType.WINDOW)
    if c.width <= 0 or c.height <= 0 or c.y < 0 or c.y + c.height > w.height:
        return None          # sin geometría o fuera de la vista (scroll en el historial)
    _, vx, vy, _, _ = ventana
    # El rectángulo del carácter viene relativo al widget; el widget, a la ventana. Con
    # paneles divididos cada uno lleva una barra de título que AT-SPI no descuenta.
    cabecera = CABECERA_PANEL if dividido else 0
    return (vx + w.x + MARGEN_X + c.x + c.width // 2,
            vy + TITULO_SSD + w.y + cabecera + c.y + c.height)


def _bucle():
    global _pos, _atspi
    import gi
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi
    _atspi = Atspi
    Atspi.init()
    terminales, t_busqueda, avisado = [], 0.0, False
    while True:
        time.sleep(INTERVALO)
        try:
            ventana = cursor_kwin.ventana()
            if not ventana or not any(a in ventana[0].lower() for a in APPS):
                _pos = None
                continue
            foco, visibles = _elegir(terminales)
            ahora = time.monotonic()
            if foco is None and ahora - t_busqueda >= REBUSCAR:
                # Nada con foco: hay un panel, pestaña o ventana nuevos, o aún no se conocían.
                t_busqueda = ahora
                terminales = _buscar_terminales()
                if not terminales:
                    if not avisado:
                        logger.info("[CURSOR-TEXTO] Konsole no aparece en AT-SPI: arrancarlo con "
                                    "QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1 (ver DOCs/README_LINUX.md)")
                        avisado = True
                    _pos = None
                    continue
                avisado = False
                logger.debug("[CURSOR-TEXTO] %d terminales en AT-SPI", len(terminales))
                foco, visibles = _elegir(terminales)
            if foco is None:         # p. ej. el foco está en la barra de búsqueda
                _pos = None
                continue
            xy = _leer(foco, ventana, visibles > 1)
            _pos = (xy[0], xy[1], time.monotonic()) if xy else None
        except Exception as e:
            # Un widget desapareció (panel, pestaña o ventana cerrada): se vuelve a buscar.
            logger.debug("[CURSOR-TEXTO] consulta fallida (%s); se vuelve a buscar", e)
            terminales, _pos, t_busqueda = [], None, 0.0


def iniciar():
    if not HABILITADA:
        logger.info("[CURSOR-TEXTO] Módulo desactivado.")
        return
    threading.Thread(target=_bucle, daemon=True).start()
