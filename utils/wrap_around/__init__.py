"""
wrap_around — Módulo independiente para salto de borde a borde de pantalla.

Detecta cuando el cursor llega al borde de la pantalla y lo transporta
automáticamente al borde opuesto (wrap-around). Funciona con cualquier
fuente de movimiento: QMK nativo, ratón físico, etc.

Uso:
    from utils.wrap_around import HABILITADA, wrap_loop, log_configuracion

    if HABILITADA:
        threading.Thread(
            target=wrap_loop,
            args=(pantalla_ancho, pantalla_alto),
            daemon=True,
        ).start()
"""

import ctypes
import logging
import time

logger = logging.getLogger(__name__)

HABILITADA = True

MARGEN_PORCENTAJE = 0.005
DELAY_MS         = 0.05
COOLDOWN         = 0.5


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def log_configuracion():
    estado = "ACTIVO" if HABILITADA else "INACTIVO"
    logger.info("├─ WRAP-AROUND  [%s]", estado)
    logger.info("│  margen      = %.1f%% del borde", MARGEN_PORCENTAJE * 100)
    logger.info("│  delay       = %d ms", int(DELAY_MS * 1000))
    logger.info("│  cooldown    = %.2f s", COOLDOWN)


def wrap_loop(ancho_pantalla: int, alto_pantalla: int):
    if not HABILITADA:
        logger.info("[WRAP] Módulo desactivado.")
        return

    logger.info(
        "🖱️  WRAP-AROUND: Hilo iniciado [margen=%.1f%%, delay=%d ms, cooldown=%.1f s]",
        MARGEN_PORCENTAJE * 100, int(DELAY_MS * 1000), COOLDOWN,
    )

    UMBRAL_MOV = 1

    borde_x = 0             # 1=der, -1=izq, 0=libre
    borde_y = 0             # 1=abajo, -1=arriba, 0=libre
    t_choque_x = 0.0
    t_choque_y = 0.0
    prev_x, prev_y = 0, 0

    while True:
        try:
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            curr_x, curr_y = pt.x, pt.y
            ahora = time.time()

            margen_x = int(ancho_pantalla * MARGEN_PORCENTAJE)
            margen_y = int(alto_pantalla * MARGEN_PORCENTAJE)

            vx = curr_x - prev_x
            vy = curr_y - prev_y

            abs_vx = abs(vx)
            abs_vy = abs(vy)

            # ═══════════════════════════════════════════════════════
            # EJE X — BORDE DERECHO
            # ═══════════════════════════════════════════════════════
            if curr_x >= ancho_pantalla - margen_x - 1:
                ctypes.windll.user32.SetCursorPos(ancho_pantalla - margen_x - 1, int(curr_y))
                curr_x = ancho_pantalla - margen_x - 1

                empuja_derecha  = vx > UMBRAL_MOV
                navega_vertical = abs_vy > UMBRAL_MOV and abs_vy >= abs_vx  # vertical domina

                if navega_vertical:
                    if borde_x != 0:
                        logger.debug("[WRAP] ↕ Navegación vertical — timer cancelado")
                    borde_x = 0
                elif empuja_derecha:
                    if borde_x != 1:
                        borde_x = 1
                        t_choque_x = ahora
                        logger.debug("[WRAP] ▶ Borde derecho — esperando %.0f ms...", DELAY_MS * 1000)
                    elif ahora - t_choque_x >= DELAY_MS:
                        logger.debug("[WRAP] ⚡ SALTO: derecha → izquierda  (espera=%.0f ms)",
                                     (ahora - t_choque_x) * 1000)
                        nuevo_x = margen_x + 5
                        ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                        curr_x = nuevo_x
                        borde_x = 0
                        t_choque_x = ahora + COOLDOWN
                # else: sin movimiento claro → mantener estado

            # ═══════════════════════════════════════════════════════
            # EJE X — BORDE IZQUIERDO
            # ═══════════════════════════════════════════════════════
            elif curr_x <= margen_x:
                ctypes.windll.user32.SetCursorPos(margen_x, int(curr_y))
                curr_x = margen_x

                empuja_izquierda = vx < -UMBRAL_MOV
                navega_vertical  = abs_vy > UMBRAL_MOV and abs_vy >= abs_vx

                if navega_vertical:
                    if borde_x != 0:
                        logger.debug("[WRAP] ↕ Navegación vertical — timer cancelado")
                    borde_x = 0
                elif empuja_izquierda:
                    if borde_x != -1:
                        borde_x = -1
                        t_choque_x = ahora
                        logger.debug("[WRAP] ◀ Borde izquierdo — esperando %.0f ms...", DELAY_MS * 1000)
                    elif ahora - t_choque_x >= DELAY_MS:
                        logger.debug("[WRAP] ⚡ SALTO: izquierda → derecha  (espera=%.0f ms)",
                                     (ahora - t_choque_x) * 1000)
                        nuevo_x = ancho_pantalla - margen_x - 5
                        ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                        curr_x = nuevo_x
                        borde_x = 0
                        t_choque_x = ahora + COOLDOWN

            else:
                borde_x = 0

            # ═══════════════════════════════════════════════════════
            # EJE Y — BORDE INFERIOR
            # ═══════════════════════════════════════════════════════
            if curr_y >= alto_pantalla - margen_y - 1:
                ctypes.windll.user32.SetCursorPos(int(curr_x), alto_pantalla - margen_y - 1)
                curr_y = alto_pantalla - margen_y - 1

                empuja_abajo      = vy > UMBRAL_MOV
                navega_horizontal = abs_vx > UMBRAL_MOV and abs_vx >= abs_vy

                if navega_horizontal:
                    if borde_y != 0:
                        logger.debug("[WRAP] ↔ Navegación horizontal — timer cancelado")
                    borde_y = 0
                elif empuja_abajo:
                    if borde_y != 1:
                        borde_y = 1
                        t_choque_y = ahora
                        logger.debug("[WRAP] ▼ Borde inferior — esperando %.0f ms...", DELAY_MS * 1000)
                    elif ahora - t_choque_y >= DELAY_MS:
                        logger.debug("[WRAP] ⚡ SALTO: abajo → arriba  (espera=%.0f ms)",
                                     (ahora - t_choque_y) * 1000)
                        nuevo_y = margen_y + 5
                        ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                        curr_y = nuevo_y
                        borde_y = 0
                        t_choque_y = ahora + COOLDOWN

            # ═══════════════════════════════════════════════════════
            # EJE Y — BORDE SUPERIOR
            # ═══════════════════════════════════════════════════════
            elif curr_y <= margen_y:
                ctypes.windll.user32.SetCursorPos(int(curr_x), margen_y)
                curr_y = margen_y

                empuja_arriba     = vy < -UMBRAL_MOV
                navega_horizontal = abs_vx > UMBRAL_MOV and abs_vx >= abs_vy

                if navega_horizontal:
                    if borde_y != 0:
                        logger.debug("[WRAP] ↔ Navegación horizontal — timer cancelado")
                    borde_y = 0
                elif empuja_arriba:
                    if borde_y != -1:
                        borde_y = -1
                        t_choque_y = ahora
                        logger.debug("[WRAP] ▲ Borde superior — esperando %.0f ms...", DELAY_MS * 1000)
                    elif ahora - t_choque_y >= DELAY_MS:
                        logger.debug("[WRAP] ⚡ SALTO: arriba → abajo  (espera=%.0f ms)",
                                     (ahora - t_choque_y) * 1000)
                        nuevo_y = alto_pantalla - margen_y - 5
                        ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                        curr_y = nuevo_y
                        borde_y = 0
                        t_choque_y = ahora + COOLDOWN

            else:
                borde_y = 0

            prev_x, prev_y = curr_x, curr_y

        except Exception as e:
            logger.debug("[WRAP ERROR] %s", e)

        time.sleep(0.01)
