import ctypes
import time
import threading
import logging

logger = logging.getLogger(__name__)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def run_in_background(is_mirror_active):
    t = threading.Thread(
        target=_scroll_lock_loop, args=(is_mirror_active,), daemon=True
    )
    t.start()


def _scroll_lock_loop(is_mirror_active):
    SCROLL_THRESHOLD_Y = 8
    SCROLL_THRESHOLD_X = 8
    SCROLL_DELTA = 120

    lock_x = 0
    lock_y = 0
    accum_y = 0
    accum_x = 0
    active = False

    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_HWHEEL = 0x1000

    while True:
        try:
            mirror_active = is_mirror_active()

            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            curr_x, curr_y = pt.x, pt.y

            if mirror_active:
                if not active:
                    lock_x = curr_x
                    lock_y = curr_y
                    accum_y = 0
                    accum_x = 0
                    active = True
                    logger.info(
                        "[SCROLL LOCK] Activado - cursor anclado en (%d, %d)",
                        lock_x,
                        lock_y,
                    )

                dy = lock_y - curr_y
                dx = curr_x - lock_x

                if abs(dy) >= abs(dx):
                    accum_y += dy
                if abs(dx) > abs(dy):
                    accum_x += dx

                ctypes.windll.user32.SetCursorPos(lock_x, lock_y)

                if abs(accum_y) >= SCROLL_THRESHOLD_Y:
                    steps = int(accum_y / SCROLL_THRESHOLD_Y)
                    delta = steps * SCROLL_DELTA
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
                    accum_y -= steps * SCROLL_THRESHOLD_Y
                    logger.debug(
                        "[SCROLL LOCK] Scroll vertical %s (%d pasos)",
                        "arriba" if delta > 0 else "abajo",
                        abs(steps),
                    )

                if abs(accum_x) >= SCROLL_THRESHOLD_X:
                    steps = int(accum_x / SCROLL_THRESHOLD_X)
                    delta = steps * SCROLL_DELTA
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, delta, 0)
                    accum_x -= steps * SCROLL_THRESHOLD_X
                    logger.debug(
                        "[SCROLL LOCK] Scroll horizontal %s (%d pasos)",
                        "derecha" if delta > 0 else "izquierda",
                        abs(steps),
                    )

            else:
                if active:
                    active = False
                    accum_y = 0
                    accum_x = 0
                    logger.info("[SCROLL LOCK] Desactivado")

            time.sleep(0.01)
        except Exception as e:
            logger.error("[SCROLL LOCK] Error: %s", e)
            time.sleep(0.05)
