import hid
import tkinter as tk
import threading
import pyautogui
import time
import mouse
import keyboard
import ctypes # Añade esto al inicio de tu archivo

from datetime import datetime
import utils.onenote_nav  # Integración OneNote Nav
import utils.scroll_lock as scroll_lock
import utils.qmk_calibracion as qmk_cal

import logging
import os
import ctypes
import subprocess

# Hacer el proceso consciente de los DPI para que las coordenadas de pantalla coincidan
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

# Configuración de logs con ruta absoluta
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f22_debug.log")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s - %(message)s', datefmt='%H:%M:%S', handlers=[
    logging.FileHandler(log_path, encoding='utf-8', mode='a'),
    logging.StreamHandler()
])
logger = logging.getLogger(__name__)
logger.info("=" * 55)
logger.info("  SISTEMA INICIADO — DPI AWARENESS ACTIVO")
logger.info(f"  LOGS → {log_path}")
logger.info("=" * 55)

pyautogui.FAILSAFE = False

# ===============================================================
# CONFIGURACIÓN
# ===============================================================
VID, PID = 0x4653, 0x0001

RADIO_OCULTAR = 80
pyautogui.PAUSE = 0    # Eliminar delay interno de pyautogui para máxima fluidez

# --- WRAP-AROUND (salto de borde a borde) ---
MODO_WRAP_DELAY_HABILITADO = True
WRAP_MARGEN_PORCENTAJE = 0.005   # 0.5% del tamaño de la pantalla (~10px en 1920px)
WRAP_DELAY_MS = 0.05             # 50ms de pausa en el borde antes de saltar
COOLDOWN_WRAP = 0.5              # Tiempo mínimo entre saltos automáticos

# --- PARAMETERS MOUSE WITH KEYBOARD ---
# Estos valores ahora se manejan en utils/qmk_calibracion/__init__.py
# Importarlos desde allí permite activar/desactivar el envío con la bandera HABILITADA


# ===============================================================
# ESTADOS GLOBALES
# ===============================================================
alt_tab_menu_visible = False
INDICADOR_HABILITADO = True
f15_down = False

color_actual = "#FFFFFF"
indicador_visible_por_capa = False


# ===============================================================
# --- UI CONFIG ---
DIAMETRO, PUNTO_MOUSE, OFFSET_MOUSE = 30, 10, 22
TAMANO_SCROLL, COLOR_SCROLL = 18, "#2982F0"

colores = {
    "ALFA": "#66BB6A",    # Verde claro / Menta (Material Green 400)
    "MODE": "#8E24AA",    # Púrpura / Morado (Material Purple 600)
    "FAST": "#E53935",    # Rojo intenso / Carmesí (Material Red 600)
    "NUMB": "#9E9E9E",    # Gris neutro / Medio (Material Grey 500)
    "SCROLL": "#24A4F2",  # Azul celeste / Vivo
    "MOVE": "#FFEB3B",    # Amarillo brillante (Material Yellow 500)
}

root = tk.Tk()
root.withdraw()

pantalla_ancho = root.winfo_screenwidth()
pantalla_alto = root.winfo_screenheight()

root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg="magenta")
root.wm_attributes("-transparentcolor", "magenta")
root.geometry(f"{DIAMETRO}x{DIAMETRO}+{(pantalla_ancho-DIAMETRO)//2}+5")

canvas = tk.Canvas(root, width=DIAMETRO, height=DIAMETRO,
                   highlightthickness=0, bg="magenta")
canvas.pack()

mouse_win = tk.Toplevel()
mouse_win.overrideredirect(True)
mouse_win.attributes("-topmost", True)
mouse_win.config(bg="magenta")
mouse_win.wm_attributes("-transparentcolor", "magenta")
mouse_win.geometry(f"{PUNTO_MOUSE}x{PUNTO_MOUSE}+0+0")

canvas_mouse = tk.Canvas(mouse_win, width=PUNTO_MOUSE, height=PUNTO_MOUSE,
                         highlightthickness=0, bg="magenta")
canvas_mouse.pack()

scroll_lock_win = tk.Toplevel()
scroll_lock_win.overrideredirect(True)
scroll_lock_win.attributes("-topmost", True)
scroll_lock_win.config(bg="magenta")
scroll_lock_win.wm_attributes("-transparentcolor", "magenta")
scroll_lock_win.geometry(f"{TAMANO_SCROLL}x{TAMANO_SCROLL}+{(pantalla_ancho-DIAMETRO)//2 + DIAMETRO + 4}+5")

canvas_scroll = tk.Canvas(scroll_lock_win, width=TAMANO_SCROLL, height=TAMANO_SCROLL,
                          highlightthickness=0, bg="magenta")
canvas_scroll.pack()

# --- VENTANA PARA EFECTO PULSO ELEGANTE (DESACTIVADO) ---
# ripple_win = tk.Toplevel() ...

scroll_lock_activo = False

def activar_scroll_lock():
    global scroll_lock_activo
    if not scroll_lock_activo:
        scroll_lock_activo = True
        logger.info("===> [SCROLL LOCK] Activado por Ctrl+Shift+F15.")
        root.after(0, actualizar_scroll_lock_ui)


def desactivar_scroll_lock():
    global scroll_lock_activo
    if scroll_lock_activo:
        scroll_lock_activo = False
        logger.info("===> [SCROLL LOCK] Desactivado.")
        root.after(0, actualizar_scroll_lock_ui)


def on_f15_press(e):
    global f15_down
    if not f15_down and keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
        f15_down = True
        logger.info("Ctrl+Shift+F15: activando funcionalidad SCROLL LOCK.")
        activar_scroll_lock()


def on_f15_release(e):
    global f15_down
    if f15_down:
        f15_down = False
        desactivar_scroll_lock()


keyboard.on_press_key("f15", on_f15_press)
keyboard.on_release_key("f15", on_f15_release)


def efecto_onda(x, y):
    """Efecto desactivado a petición del usuario."""
    pass
    
# def animar_pulso(step):
#    ... (resto de la función comentada lógicamente)

def toggle_indicadores(e=None):
    """Alterna la bandera global de visibilidad de los indicadores."""
    global INDICADOR_HABILITADO
    INDICADOR_HABILITADO = not INDICADOR_HABILITADO
    logger.info(f"Indicadores habilitados: {INDICADOR_HABILITADO}")
    
    if not INDICADOR_HABILITADO:
        root.withdraw()
        mouse_win.withdraw()
        scroll_lock_win.withdraw()
    elif indicador_visible_por_capa:
        root.deiconify()
        mouse_win.deiconify()
    
    root.after(0, actualizar_scroll_lock_ui)

# Asignar F21 para alternar la visibilidad de las burbujas
keyboard.on_press_key("f21", toggle_indicadores)

def actualizar_ui(capa_msg):
    global indicador_visible_por_capa, color_actual, scroll_lock_activo

    clave = next((k for k in colores if k in capa_msg), None)

    if clave:
        color_actual = colores[clave]
        c = color_actual
        canvas.delete("all")
        canvas.create_oval(2, 2, DIAMETRO-2, DIAMETRO-2, fill=c, outline="")
        canvas_mouse.delete("all")
        canvas_mouse.create_oval(0, 0, PUNTO_MOUSE, PUNTO_MOUSE, fill=c, outline="")
        indicador_visible_por_capa = True
        logger.debug(f"[UI] Capa detectada: {clave} - Indicadores: {'ON' if INDICADOR_HABILITADO else 'OFF'}")
        
        if INDICADOR_HABILITADO:
            root.deiconify()
            mouse_win.deiconify()
    else:
        indicador_visible_por_capa = False
        root.withdraw()
        mouse_win.withdraw()

    actualizar_scroll_lock_ui()


def actualizar_scroll_lock_ui():
    global scroll_lock_activo
    if scroll_lock_activo and INDICADOR_HABILITADO:
        canvas_scroll.delete("all")
        canvas_scroll.create_rectangle(2, 2, TAMANO_SCROLL-2, TAMANO_SCROLL-2, fill=COLOR_SCROLL, outline="")
        scroll_lock_win.deiconify()
    else:
        canvas_scroll.delete("all")
        scroll_lock_win.withdraw()


# ===============================================================
# HID
# ===============================================================
def escuchar_hid(dev):
    global alt_tab_menu_visible
    capa_actual = None
    print("[HID] Escuchando...")

    while True:
        try:
            data = dev.read(32, timeout_ms=500)
            if not data:
                continue

            msg = "".join(chr(b) for b in data if 31 < b < 127).strip()

            if "AT_ON" in msg:
                alt_tab_menu_visible = True
            elif "AT_OFF" in msg:
                alt_tab_menu_visible = False

            nombres = list(colores.keys()) + ["LAYER_BASE"]
            nueva = next((n for n in nombres if n in msg), None)

            if nueva and nueva != capa_actual:
                logger.info(f"======> [HID] CAMBIO DE CAPA DETECTADO: '{capa_actual}' -> '{nueva}'")
                capa_actual = nueva
                root.after(0, lambda c=capa_actual: actualizar_ui(c))

        except Exception as e:
            print("[HID ERROR]", e)
            break

# ===============================================================
# ALT-TAB RESET
# ===============================================================
def detectar_clic_reset_alt(dev):
    global alt_tab_menu_visible
    while True:
        if alt_tab_menu_visible and mouse.is_pressed("left"):
            while mouse.is_pressed("left"):
                time.sleep(0.01)
            keyboard.release("alt")
            try:
                buf = [0]*33
                buf[1] = ord("R")
                dev.write(buf)
            except:
                pass
            alt_tab_menu_visible = False
        time.sleep(0.01)

# ===============================================================
# SEGUIMIENTO VISUAL DEL MOUSE
# ===============================================================
def seguimiento_mouse():
    while True:
        try:
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            x, y = pt.x, pt.y
            mouse_win.geometry(f"+{x-PUNTO_MOUSE//2}+{y+OFFSET_MOUSE}")
            
        except:
            pass
        time.sleep(0.01)

# ===============================================================
# WRAP-AROUND — Salto de borde a borde de pantalla
# ===============================================================

def wrap_loop():
    """
    Detecta cuando el cursor llega al borde de la pantalla y lo
    transporta automáticamente al borde opuesto (wrap-around).
    Funciona con cualquier fuente de movimiento (QMK nativo, ratón físico, etc.).
    """
    logger.info("🖱️  WRAP-AROUND: Hilo iniciado.")

    borde_activo_x = 0
    borde_activo_y = 0
    tiempo_choque_x = 0
    tiempo_choque_y = 0
    prev_x, prev_y = 0, 0

    while True:
        try:
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            curr_x, curr_y = pt.x, pt.y
            ahora = time.time()

            if MODO_WRAP_DELAY_HABILITADO:
                margen_x = int(pantalla_ancho * WRAP_MARGEN_PORCENTAJE)
                margen_y = int(pantalla_alto * WRAP_MARGEN_PORCENTAJE)

                vx = curr_x - prev_x
                vy = curr_y - prev_y
                UMBRAL_MOV = 1  # Píxeles mínimos para considerar movimiento intencional

                # ── EJE X ──
                if curr_x >= pantalla_ancho - margen_x - 1:
                    ctypes.windll.user32.SetCursorPos(pantalla_ancho - margen_x - 1, int(curr_y))
                    curr_x = pantalla_ancho - margen_x - 1
                    if vx > UMBRAL_MOV and abs(vy) <= UMBRAL_MOV:
                        if borde_activo_x != 1:
                            borde_activo_x = 1
                            tiempo_choque_x = ahora
                        elif ahora - tiempo_choque_x >= WRAP_DELAY_MS:
                            nuevo_x = margen_x + 5
                            ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                            curr_x = nuevo_x
                            borde_activo_x = 0
                            tiempo_choque_x = ahora + COOLDOWN_WRAP
                    else:
                        borde_activo_x = 0
                elif curr_x <= margen_x:
                    ctypes.windll.user32.SetCursorPos(margen_x, int(curr_y))
                    curr_x = margen_x
                    if vx < -UMBRAL_MOV and abs(vy) <= UMBRAL_MOV:
                        if borde_activo_x != -1:
                            borde_activo_x = -1
                            tiempo_choque_x = ahora
                        elif ahora - tiempo_choque_x >= WRAP_DELAY_MS:
                            nuevo_x = pantalla_ancho - margen_x - 5
                            ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                            curr_x = nuevo_x
                            borde_activo_x = 0
                            tiempo_choque_x = ahora + COOLDOWN_WRAP
                    else:
                        borde_activo_x = 0
                else:
                    borde_activo_x = 0

                # ── EJE Y ──
                if curr_y >= pantalla_alto - margen_y - 1:
                    ctypes.windll.user32.SetCursorPos(int(curr_x), pantalla_alto - margen_y - 1)
                    curr_y = pantalla_alto - margen_y - 1
                    if vy > UMBRAL_MOV and abs(vx) <= UMBRAL_MOV:
                        if borde_activo_y != 1:
                            borde_activo_y = 1
                            tiempo_choque_y = ahora
                        elif ahora - tiempo_choque_y >= WRAP_DELAY_MS:
                            nuevo_y = margen_y + 5
                            ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                            curr_y = nuevo_y
                            borde_activo_y = 0
                            tiempo_choque_y = ahora + COOLDOWN_WRAP
                    else:
                        borde_activo_y = 0
                elif curr_y <= margen_y:
                    ctypes.windll.user32.SetCursorPos(int(curr_x), margen_y)
                    curr_y = margen_y
                    if vy < -UMBRAL_MOV and abs(vx) <= UMBRAL_MOV:
                        if borde_activo_y != -1:
                            borde_activo_y = -1
                            tiempo_choque_y = ahora
                        elif ahora - tiempo_choque_y >= WRAP_DELAY_MS:
                            nuevo_y = pantalla_alto - margen_y - 5
                            ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                            curr_y = nuevo_y
                            borde_activo_y = 0
                            tiempo_choque_y = ahora + COOLDOWN_WRAP
                    else:
                        borde_activo_y = 0
                else:
                    borde_activo_y = 0

            prev_x, prev_y = curr_x, curr_y

        except Exception as e:
            logger.debug(f"[WRAP ERROR] {e}")

        time.sleep(0.01)


# ===============================================================
# ocultar indicador
# ===============================================================
def ocultar_indicador_si_mouse_cerca():
    while True:
        try:
            if not indicador_visible_por_capa and not scroll_lock_activo:
                time.sleep(0.05)
                continue

            mx, my = pyautogui.position()

            cx = pantalla_ancho // 2
            cy = 5 + DIAMETRO // 2
            dx = mx - cx
            dy = my - cy
            distancia = (dx*dx + dy*dy) ** 0.5

            cx_scroll = (pantalla_ancho - DIAMETRO)//2 + DIAMETRO + TAMANO_SCROLL//2
            cy_scroll = 5 + TAMANO_SCROLL//2
            dxs = mx - cx_scroll
            dys = my - cy_scroll
            distancia_scroll = (dxs*dxs + dys*dys) ** 0.5

            ocultar = distancia < RADIO_OCULTAR or distancia_scroll < RADIO_OCULTAR

            if ocultar:
                root.withdraw()
                scroll_lock_win.withdraw()
            else:
                if INDICADOR_HABILITADO and indicador_visible_por_capa:
                    root.deiconify()
                root.after(0, actualizar_scroll_lock_ui)

        except:
            pass

        time.sleep(0.03)

# ===============================================================
# MAIN
# ===============================================================

# Global reference to avoid Garbage Collection of the mutex
_mutex_ref = None

def check_single_instance():
    global _mutex_ref
    kernel32 = ctypes.windll.kernel32
    mutex_name = "LAYER_STATUS_SCRIPT_UNIQUE_MUTEX_123"
    _mutex_ref = kernel32.CreateMutexW(None, False, mutex_name)
    if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        print("❌ Ya hay una instancia de este script ejecutándose. Saliendo para evitar conflictos...")
        import sys
        sys.exit(0)

def log_configuracion():
    """Vuelca todos los parámetros de configuración al log para diagnóstico."""
    sep = "─" * 55
    logger.info(sep)
    logger.info("📋 CONFIGURACIÓN DEL SISTEMA")
    logger.info(sep)

    # ── Identificación del teclado ──
    logger.info("┌─ TECLADO")
    logger.info(f"│  VID = 0x{VID:04X}  |  PID = 0x{PID:04X}")

    # ── QMK Mouse (→ módulo independiente) ──
    qmk_cal.log_configuracion()

    # ── Wrap-around ──
    logger.info("├─ WRAP-AROUND")
    logger.info(f"│  MODO_WRAP        = {'ACTIVO' if MODO_WRAP_DELAY_HABILITADO else 'INACTIVO'}")
    logger.info(f"│  WRAP_MARGEN      = {int(WRAP_MARGEN_PORCENTAJE * 10000) / 100:.1f}%")
    logger.info(f"│  WRAP_DELAY       = {WRAP_DELAY_MS * 1000:.0f} ms")
    logger.info(f"│  COOLDOWN_WRAP    = {COOLDOWN_WRAP:.2f} s")

    # ── Otros ──
    logger.info("├─ OTROS")
    logger.info(f"│  RADIO_OCULTAR    = {RADIO_OCULTAR} px")
    logger.info(sep)


def main():
    check_single_instance()
    
    path = next((d["path"] for d in hid.enumerate()
                if d["vendor_id"] == VID and d["product_id"] == PID), None)
    if not path:
        print("❌ Teclado no encontrado")
        return

    dev = hid.device()
    dev.open_path(path)
    dev.set_nonblocking(True)

    # ── Volcar toda la configuración al log ──
    log_configuracion()

    # ── Enviar calibración de mouse keys al firmware (solo si HABILITADA = True) ──
    qmk_cal.enviar_calibracion(dev)

    threading.Thread(target=escuchar_hid, args=(dev,), daemon=True).start()
    threading.Thread(target=detectar_clic_reset_alt, args=(dev,), daemon=True).start()
    threading.Thread(target=seguimiento_mouse, daemon=True).start()
    threading.Thread(target=wrap_loop, daemon=True).start()
    threading.Thread(target=ocultar_indicador_si_mouse_cerca, daemon=True).start()
    
    # Inicia la captura de Alt para OneNote 2016
    utils.onenote_nav.run_in_background()
    scroll_lock.run_in_background(lambda: scroll_lock_activo)

    logger.info("=" * 55)
    logger.info("  🎯 CORNELL READY — SALTO + WRAP INTEGRADO")
    logger.info("=" * 55)
    print("=" * 40)
    print("  CORNELL READY")
    print("=" * 40)

    root.mainloop()

if __name__ == "__main__":
    main()
