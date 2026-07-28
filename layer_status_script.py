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
logger.info("==========================================")
logger.info("SISTEMA REINICIADO CON DPI AWARENESS")
logger.info(f"ARCHIVO DE LOGS: {log_path}")
logger.info("==========================================")

pyautogui.FAILSAFE = False

# ===============================================================
# CONFIGURACIÓN
# ===============================================================
VID, PID = 0x4653, 0x0001

# MODO 2 (WRAP): Activación del salto por pausa y empuje
MODO_WRAP_DELAY_HABILITADO = True
WRAP_MARGEN_PORCENTAJE = 0.005   # 0.5% del tamaño de la pantalla (~10px en 1920px)
WRAP_DELAY_MS = 0.05             # 50ms - Reducido para wrap más rápido

DISTANCIA_SALTO = 450
PAUSA_ENTRE_SALTOS = 0.3
UMBRAL_CAMBIO_DIR = 15 # Reducido para mayor sensibilidad
TURBO_MARGIN = 25
WRAP_MARGIN = 5
VENTANA_GESTO_MS = 0.1  # Aumentado a 100ms
RADIO_OCULTAR = 80

# --- NUEVOS PARÁMETROS DE SUAVIDAD ---
VEL_BASE = 3.0
VEL_MAX = 42.0
ACEL_POR_FRAME = 0.65  # Incremento de velocidad por cada ciclo de 10ms
PAUSA_BORDE_S = 0.6    # Pausa al tocar el borde antes de saltar
COOLDOWN_WRAP = 0.5    # Tiempo mínimo entre saltos automáticos
TIEMPO_ANCLAJE = 0.5   # Segundos que el mouse queda bloqueado tras un salto (reducido para mayor fluidez)
pyautogui.PAUSE = 0    # Eliminar delay interno de pyautogui para máxima fluidez

# --- PARÁMETROS DE PRECISIÓN EN BORDES ---
MARGIN_ESQUINA = 100    # Píxeles desde las esquinas donde el muro es sólido (no salta)
DISTANCIA_FRENADO = 500 # Píxeles antes del borde donde empieza a frenar dinámicamente
MARGEN_BLOQUEO = 10     # Píxeles antes del borde donde el cursor choca y se detiene
UMBRAL_VIAJE_LARGO = 450 # Distancia recorrida para activar el bloqueo de esquinas
ZONA_LIBRE_BORDE = 0.25  # 25% de la pantalla para permitir paso fluido sin bloqueos

# --- PARAMETERS MOUSE WITH KEYBOARD---
QMK_MOUSE_MAX_SPEED    = 7# Camos la velocidad máxima a la mitad (ya no saldrá disparado)
QMK_MOUSE_TIME_TO_MAX  = 30 #  rampa
QMK_MOUSE_INTERVAL     = 18 # Refresco de ~60Hz (estándar de monitores), movimiento muy progresivo
QMK_MOUSE_MOVE_DELTA   = 1    # El paso mínimo posible por ciclo


# ===============================================================
# ESTADOS GLOBALES
# ===============================================================
alt_tab_menu_visible = False
INDICADOR_HABILITADO = True

tecla_horiz_down = False
tecla_vert_down = False
direccion_fijada = 0
direccion_y_fijada = 0
pos_y_referencia = 0
f15_down = False

color_actual = "#FFFFFF"
wrap_enabled = threading.Event()
wrap_enabled.set()
indicador_visible_por_capa = False


# ===============================================================
# --- UI CONFIG ---
DIAMETRO, PUNTO_MOUSE, OFFSET_MOUSE = 30, 10, 22
TAMANO_SCROLL, COLOR_SCROLL = 24, "#00FFFF"

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
# F24 / F23 – MOVIMIENTO SUAVE Y CONTROLADO
# ===============================================================

forzar_nuevo_viaje = False

def presiona_f24(e):
    global tecla_horiz_down, forzar_nuevo_viaje
    if not tecla_horiz_down:
        forzar_nuevo_viaje = True
        logger.debug("[TECLA F24 PRESIONADA] - NUEVO VIAJE FORZADO")
    tecla_horiz_down = True

def suelta_f24(e):
    global tecla_horiz_down, direccion_fijada
    tecla_horiz_down = False
    direccion_fijada = 0
    logger.debug("[TECLA F24 SOLTADA]")

def presiona_f23(e):
    global tecla_vert_down, forzar_nuevo_viaje
    if not tecla_vert_down:
        forzar_nuevo_viaje = True
        logger.debug("[TECLA F23 PRESIONADA] - NUEVO VIAJE FORZADO")
    tecla_vert_down = True

def suelta_f23(e):
    global tecla_vert_down, direccion_y_fijada
    tecla_vert_down = False
    direccion_y_fijada = 0
    logger.debug("[TECLA F23 SOLTADA]")

keyboard.on_press_key("f24", presiona_f24)
keyboard.on_release_key("f24", suelta_f24)
keyboard.on_press_key("f23", presiona_f23)
keyboard.on_release_key("f23", suelta_f23)

def loop_movimiento_suave():
    global direccion_fijada, direccion_y_fijada
    
    speed_x = 0
    speed_y = 0
    pause_until = 0
    distancia_recorrida = 0
    anclado_x = False
    anclado_y = False
    limite_x = 0
    limite_y = 0
    dir_anclaje_x = 0
    dir_anclaje_y = 0
    tiempo_anclaje_x = 0
    tiempo_anclaje_y = 0
    
    last_x, last_y = pyautogui.position()
    
    origen_swipe_x, origen_swipe_y = pyautogui.position()
    prev_actual_x, prev_actual_y = origen_swipe_x, origen_swipe_y
    tiempo_ultimo_movimiento_x = time.time()
    tiempo_ultimo_movimiento_y = time.time()
    
    tiempo_choque_x = 0
    tiempo_choque_y = 0
    borde_activo_x = 0
    borde_activo_y = 0
    
    while True:
        # --- OBTENER POSICIÓN REAL (Sin latencia de PyAutoGUI) ---
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        curr_x, curr_y = pt.x, pt.y
        ahora = time.time()
        
        global forzar_nuevo_viaje
        if forzar_nuevo_viaje:
            origen_swipe_x, origen_swipe_y = curr_x, curr_y
            if anclado_x:
                anclado_x = False
                logger.debug("[MURO X LIBERADO por nueva pulsación]")
            if anclado_y:
                anclado_y = False
                logger.debug("[MURO Y LIBERADO por nueva pulsación]")
            forzar_nuevo_viaje = False
            tiempo_ultimo_movimiento_x = ahora
            tiempo_ultimo_movimiento_y = ahora
        
        # --- RASTREO INDEPENDIENTE DE INACTIVIDAD (X e Y) ---
        # Reseteamos el origen si no hay movimiento en ESE eje específico por 150ms.
        # Esto evita que "deslizarse" verticalmente por el borde bloquee el reset horizontal.
        
        # Eje X
        if abs(curr_x - prev_actual_x) > 0 or tecla_horiz_down or speed_x > 0:
            tiempo_ultimo_movimiento_x = ahora
        elif ahora - tiempo_ultimo_movimiento_x > 0.15:
            if origen_swipe_x != curr_x:
                origen_swipe_x = curr_x
                if anclado_x:
                    anclado_x = False
                    logger.debug("[MURO X LIBERADO por inactividad horizontal]")
        
        # Eje Y
        if abs(curr_y - prev_actual_y) > 0 or tecla_vert_down or speed_y > 0:
            tiempo_ultimo_movimiento_y = ahora
        elif ahora - tiempo_ultimo_movimiento_y > 0.15:
            if origen_swipe_y != curr_y:
                origen_swipe_y = curr_y
                if anclado_y:
                    anclado_y = False
                    logger.debug("[MURO Y LIBERADO por inactividad vertical]")

        # 1. DETECTAR DIRECCIÓN
        if tecla_horiz_down:
            dx = curr_x - last_x
            if 2 <= abs(dx) < (pantalla_ancho // 2):
                direccion_fijada = 1 if dx > 0 else -1
        else:
            direccion_fijada = 0
            speed_x = 0
            
        if tecla_vert_down:
            dy = curr_y - last_y
            if 2 <= abs(dy) < (pantalla_alto // 2):
                direccion_y_fijada = 1 if dy > 0 else -1
        else:
            direccion_y_fijada = 0
            speed_y = 0

        # DETECTAR SALTO EXTERNO (Con Filtro de Zonas del 25% y Distancia de Viaje)
        if abs(curr_x - last_x) > (pantalla_ancho // 2) and not anclado_x:
            # Determinamos si fue un viaje largo basándonos en el origen real del swipe (universal)
            dist_viajada_x = abs(last_x - origen_swipe_x)
            es_viaje_corto = dist_viajada_x < UMBRAL_VIAJE_LARGO
            
            # Solo anclamos si NO es un viaje corto
            if not es_viaje_corto: 
                anclado_x = True
                tiempo_anclaje_x = ahora
                dir_anclaje_x = direccion_fijada if direccion_fijada != 0 else (1 if curr_x < last_x else -1)
                
                # Para que se "quede en la pared" sin pelear con programas de envoltura externos,
                # lo devolvemos 5 píxeles ANTES del borde absoluto.
                if curr_x < last_x: # Cruzó el borde derecho hacia el izquierdo
                    limite_x = pantalla_ancho - MARGEN_BLOQUEO
                else: # Cruzó el borde izquierdo hacia el derecho
                    limite_x = MARGEN_BLOQUEO
                    
                logger.debug(f"[SALTO PROTEGIDO EXT] X:{last_x}->{curr_x} | ANCLAJE EN BORDE: {limite_x} (Dist: {dist_viajada_x})")
            else:
                logger.debug(f"[SALTO LIBRE POR ZONA] X:{last_x}->{curr_x} | Viaje Corto (Dist: {dist_viajada_x})")
            
            # Tras un salto, el nuevo origen es donde aterrizamos (o donde fuimos anclados)
            if anclado_x:
                origen_swipe_x = limite_x
                last_x = limite_x
            else:
                origen_swipe_x = curr_x
                last_x = curr_x

        if abs(curr_y - last_y) > (pantalla_alto // 2) and not anclado_y:
            dist_viajada_y = abs(last_y - origen_swipe_y)
            es_viaje_corto_y = dist_viajada_y < UMBRAL_VIAJE_LARGO
                
            if not es_viaje_corto_y:
                anclado_y = True
                tiempo_anclaje_y = ahora
                dir_anclaje_y = direccion_y_fijada if direccion_y_fijada != 0 else (1 if curr_y < last_y else -1)
                
                if curr_y < last_y:
                    limite_y = pantalla_alto - MARGEN_BLOQUEO
                else:
                    limite_y = MARGEN_BLOQUEO
                    
                logger.debug(f"[SALTO PROTEGIDO EXT] Y:{last_y}->{curr_y} | ANCLAJE EN BORDE: {limite_y} (Dist: {dist_viajada_y})")
            else:
                logger.debug(f"[SALTO LIBRE POR ZONA] Y:{last_y}->{curr_y} | Viaje Corto (Dist: {dist_viajada_y})")
                
            if anclado_y:
                origen_swipe_y = limite_y
                last_y = limite_y
            else:
                origen_swipe_y = curr_y
                last_y = curr_y

        # --- APLICAR ANCLAJE (FUERZA CONSTANTE) ---
        if anclado_x:
            if ahora - tiempo_anclaje_x > TIEMPO_ANCLAJE:
                anclado_x = False
                logger.debug("[MURO X LIBERADO por tiempo]")
            elif ahora - tiempo_anclaje_x > 0.05:
                # Detectar si el usuario intenta alejarse del muro (movimiento fuerte opuesto)
                # Esperamos 50ms tras anclar para ignorar la distancia del salto inicial
                dx_manual = curr_x - last_x
                if abs(dx_manual) >= 8: # Umbral alto para ignorar jitter
                    if (1 if dx_manual > 0 else -1) == -dir_anclaje_x:
                        anclado_x = False
                        logger.debug("[MURO X LIBERADO por movimiento opuesto]")
                
            if anclado_x:
                # FORZAR POSICIÓN CONSTANTE: No dejamos que QMK lo mueva ni 1 píxel
                ctypes.windll.user32.SetCursorPos(int(limite_x), int(curr_y))
                curr_x = limite_x
                speed_x = 0

        if anclado_y:
            if ahora - tiempo_anclaje_y > TIEMPO_ANCLAJE:
                anclado_y = False
                logger.debug("[MURO Y LIBERADO por tiempo]")
            elif ahora - tiempo_anclaje_y > 0.05:
                dy_manual = curr_y - last_y
                if abs(dy_manual) >= 8:
                    if (1 if dy_manual > 0 else -1) == -dir_anclaje_y:
                        anclado_y = False
                        logger.debug("[MURO Y LIBERADO por movimiento opuesto]")
                
                if anclado_y:
                    ctypes.windll.user32.SetCursorPos(int(curr_x), int(limite_y))
                    curr_y = limite_y
                    speed_y = 0

        # 2. PROCESAR MOVIMIENTO ACELERADO
        if ahora > pause_until:
            if direccion_fijada != 0 or direccion_y_fijada != 0:
                if direccion_fijada != 0:
                    speed_x = min(VEL_MAX, (speed_x if speed_x > 0 else VEL_BASE) + ACEL_POR_FRAME)
                if direccion_y_fijada != 0:
                    speed_y = min(VEL_MAX, (speed_y if speed_y > 0 else VEL_BASE) + ACEL_POR_FRAME)
                
                step_x = speed_x * direccion_fijada
                step_y = speed_y * direccion_y_fijada
                distancia_recorrida += (abs(step_x) + abs(step_y))

                nx = curr_x + step_x
                ny = curr_y + step_y
                
                # --- LÓGICA DE FRENADO Y BORDES ---
                dist_borde_x = min(nx, pantalla_ancho - nx)
                dist_borde_y = min(ny, pantalla_alto - ny)
                
                es_viaje_corto = abs(curr_x - origen_swipe_x) < UMBRAL_VIAJE_LARGO
                es_viaje_corto_y = abs(curr_y - origen_swipe_y) < UMBRAL_VIAJE_LARGO
                
                if dist_borde_x < DISTANCIA_FRENADO and not es_viaje_corto:
                    # Frenado dinámico proporcional a la distancia al borde
                    factor_x = max(0.1, dist_borde_x / DISTANCIA_FRENADO)
                    speed_x = max(VEL_BASE, speed_x * factor_x)
                    nx = curr_x + (speed_x * direccion_fijada)

                if dist_borde_y < DISTANCIA_FRENADO and not es_viaje_corto_y:
                    factor_y = max(0.1, dist_borde_y / DISTANCIA_FRENADO)
                    speed_y = max(VEL_BASE, speed_y * factor_y)
                    ny = curr_y + (speed_y * direccion_y_fijada)
                if nx <= MARGEN_BLOQUEO and not es_viaje_corto:
                    nx = MARGEN_BLOQUEO
                    speed_x = 0 # Frena antes del borde
                elif nx >= pantalla_ancho - MARGEN_BLOQUEO and not es_viaje_corto:
                    nx = pantalla_ancho - MARGEN_BLOQUEO
                    speed_x = 0
                        
                if ny <= MARGEN_BLOQUEO and not es_viaje_corto:
                    ny = MARGEN_BLOQUEO
                    speed_y = 0
                elif ny >= pantalla_alto - MARGEN_BLOQUEO and not es_viaje_corto:
                    ny = pantalla_alto - MARGEN_BLOQUEO
                    speed_y = 0

                nx = max(0, min(pantalla_ancho - 1, nx))
                ny = max(0, min(pantalla_alto - 1, ny))
                if nx != curr_x or ny != curr_y:
                    pyautogui.moveTo(nx, ny)
                last_x, last_y = nx, ny
            else:
                # MOVIMIENTO MANUAL (Bloqueo de Posición y Freno)
                vx = curr_x - last_x
                vy = curr_y - last_y
                
                # RASTREO DE VIAJE
                es_viaje_corto_x = abs(curr_x - origen_swipe_x) < UMBRAL_VIAJE_LARGO
                es_viaje_corto_y = abs(curr_y - origen_swipe_y) < UMBRAL_VIAJE_LARGO

                # BLOQUEO DE POSICIÓN (Muro de 50px para viajes largos manuales)
                if not es_viaje_corto_x:
                    if curr_x >= pantalla_ancho - MARGEN_BLOQUEO and vx > 0:
                        ctypes.windll.user32.SetCursorPos(int(pantalla_ancho - MARGEN_BLOQUEO), int(curr_y))
                        curr_x = pantalla_ancho - MARGEN_BLOQUEO
                        vx = 0
                    elif curr_x <= MARGEN_BLOQUEO and vx < 0:
                        ctypes.windll.user32.SetCursorPos(int(MARGEN_BLOQUEO), int(curr_y))
                        curr_x = MARGEN_BLOQUEO
                        vx = 0


                if not es_viaje_corto_y:
                    if curr_y >= pantalla_alto - MARGEN_BLOQUEO and vy > 0:
                        ctypes.windll.user32.SetCursorPos(int(curr_x), int(pantalla_alto - MARGEN_BLOQUEO))
                        curr_y = pantalla_alto - MARGEN_BLOQUEO
                        vy = 0
                    elif curr_y <= MARGEN_BLOQUEO and vy < 0:
                        ctypes.windll.user32.SetCursorPos(int(curr_x), int(MARGEN_BLOQUEO))
                        curr_y = MARGEN_BLOQUEO
                        vy = 0


                if abs(vx) > 1 or abs(vy) > 1:
                    dist_borde_x = min(curr_x, pantalla_ancho - curr_x)
                    dist_borde_y = min(curr_y, pantalla_alto - curr_y)
                    
                    # Detectar si se mueve HACIA el borde
                    hacia_borde_x = (vx > 0 and curr_x > pantalla_ancho // 2) or (vx < 0 and curr_x < pantalla_ancho // 2)
                    hacia_borde_y = (vy > 0 and curr_y > pantalla_alto // 2) or (vy < 0 and curr_y < pantalla_alto // 2)
                    
                    # Detectar si estamos en zona segura (25% lateral) para desactivar el freno
                    en_zona_segura_x = curr_x < (pantalla_ancho * ZONA_LIBRE_BORDE) or curr_x > (pantalla_ancho * (1 - ZONA_LIBRE_BORDE))
                    en_zona_segura_y = curr_y < (pantalla_alto * ZONA_LIBRE_BORDE) or curr_y > (pantalla_alto * (1 - ZONA_LIBRE_BORDE))

                    # Aplicar límite de velocidad dinámico en zona de frenado SOLO si no estamos en zona segura y no es viaje corto
                    if hacia_borde_x and dist_borde_x < DISTANCIA_FRENADO and not en_zona_segura_x and not es_viaje_corto_x:
                        # Velocidad máxima permitida disminuye conforme nos acercamos al borde
                        v_permitida = max(VEL_BASE, VEL_MAX * (dist_borde_x / DISTANCIA_FRENADO))
                        if abs(vx) > v_permitida:
                            nueva_x = last_x + (v_permitida * (1 if vx > 0 else -1))
                            ctypes.windll.user32.SetCursorPos(int(nueva_x), int(curr_y))
                            curr_x = nueva_x
                            
                    if hacia_borde_y and dist_borde_y < DISTANCIA_FRENADO and not en_zona_segura_y and not es_viaje_corto_y:
                        v_permitida_y = max(VEL_BASE, VEL_MAX * (dist_borde_y / DISTANCIA_FRENADO))
                        if abs(vy) > v_permitida_y:
                            nueva_y = last_y + (v_permitida_y * (1 if vy > 0 else -1))
                            ctypes.windll.user32.SetCursorPos(int(curr_x), int(nueva_y))
                            curr_y = nueva_y
                            
                last_x, last_y = curr_x, curr_y
        else:
            last_x, last_y = curr_x, curr_y
            
        if MODO_WRAP_DELAY_HABILITADO:
            margen_x = int(pantalla_ancho * WRAP_MARGEN_PORCENTAJE)
            margen_y = int(pantalla_alto * WRAP_MARGEN_PORCENTAJE)
            
            vx_wrap = curr_x - prev_actual_x
            vy_wrap = curr_y - prev_actual_y
            
            # --- DETECCIÓN DE INTENCIÓN: el wrap se activa inmediatamente si hay movimiento
            #     en el eje correcto. Se bloquea SOLO si hay movimiento intencional en el
            #     eje perpendicular (navegación por iconos) ---
            UMBRAL_MOVIMIENTO_WRAP = 1  # Píxeles mínimos para considerar movimiento intencional
            
            # --- EVALUAR EJE X (solo si movimiento horizontal intencional) ---
            if curr_x >= pantalla_ancho - margen_x - 1:
                ctypes.windll.user32.SetCursorPos(pantalla_ancho - margen_x - 1, int(curr_y))
                curr_x = pantalla_ancho - margen_x - 1
                if vx_wrap > UMBRAL_MOVIMIENTO_WRAP and abs(vy_wrap) <= UMBRAL_MOVIMIENTO_WRAP:
                    if borde_activo_x != 1:
                        borde_activo_x = 1
                        tiempo_choque_x = ahora
                    elif ahora - tiempo_choque_x >= WRAP_DELAY_MS:
                        nuevo_x = margen_x + 5
                        ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                        curr_x = nuevo_x
                        borde_activo_x = 0
                        tiempo_choque_x = ahora + 0.5
                else:
                    borde_activo_x = 0
            elif curr_x <= margen_x:
                ctypes.windll.user32.SetCursorPos(margen_x, int(curr_y))
                curr_x = margen_x
                if vx_wrap < -UMBRAL_MOVIMIENTO_WRAP and abs(vy_wrap) <= UMBRAL_MOVIMIENTO_WRAP:
                    if borde_activo_x != -1:
                        borde_activo_x = -1
                        tiempo_choque_x = ahora
                    elif ahora - tiempo_choque_x >= WRAP_DELAY_MS:
                        nuevo_x = pantalla_ancho - margen_x - 5
                        ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                        curr_x = nuevo_x
                        borde_activo_x = 0
                        tiempo_choque_x = ahora + 0.5
                else:
                    borde_activo_x = 0
            else:
                borde_activo_x = 0
                
            # --- EVALUAR EJE Y (solo si movimiento vertical intencional) ---
            if curr_y >= pantalla_alto - margen_y - 1:
                ctypes.windll.user32.SetCursorPos(int(curr_x), pantalla_alto - margen_y - 1)
                curr_y = pantalla_alto - margen_y - 1
                if vy_wrap > UMBRAL_MOVIMIENTO_WRAP and abs(vx_wrap) <= UMBRAL_MOVIMIENTO_WRAP:
                    if borde_activo_y != 1:
                        borde_activo_y = 1
                        tiempo_choque_y = ahora
                    elif ahora - tiempo_choque_y >= WRAP_DELAY_MS:
                        nuevo_y = margen_y + 5
                        ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                        curr_y = nuevo_y
                        borde_activo_y = 0
                        tiempo_choque_y = ahora + 0.5
                else:
                    borde_activo_y = 0
            elif curr_y <= margen_y:
                ctypes.windll.user32.SetCursorPos(int(curr_x), margen_y)
                curr_y = margen_y
                if vy_wrap < -UMBRAL_MOVIMIENTO_WRAP and abs(vx_wrap) <= UMBRAL_MOVIMIENTO_WRAP:
                    if borde_activo_y != -1:
                        borde_activo_y = -1
                        tiempo_choque_y = ahora
                    elif ahora - tiempo_choque_y >= WRAP_DELAY_MS:
                        nuevo_y = pantalla_alto - margen_y - 5
                        ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                        curr_y = nuevo_y
                        borde_activo_y = 0
                        tiempo_choque_y = ahora + 0.5
                else:
                    borde_activo_y = 0
            else:
                borde_activo_y = 0
                
        prev_actual_x, prev_actual_y = curr_x, curr_y
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

def enviar_calibracion_qmk(dev):
    """Construye el buffer HID con la firma 'M' y envía las variables al Corne."""
    try:
        # Creamos un buffer de 33 bytes (1 byte para Report ID + 32 bytes de datos estándar de QMK)
        buf = [0] * 33
        buf[0] = 0x00                     # Report ID (Requerido por Windows)
        buf[1] = ord("M")                 # Firma 'M' que espera el 'if (data[0] == 'M')' en C
        buf[2] = QMK_MOUSE_MAX_SPEED     # data[1] en QMK
        buf[3] =  QMK_MOUSE_TIME_TO_MAX     # data[2] en QMK
        buf[4] =   QMK_MOUSE_INTERVAL  # data[3] en QMK

       # buf[5] =        # data[4] en QMK
       # buf[6] = QMK_MOUSE_MOVE_DELTA     # data[5] en QMK

        dev.write(buf)
        logger.info(f"[HID] Calibración enviada con éxito al Corne.")
    except Exception as e:
        logger.error(f"[HID ERROR] No se pudieron enviar los valores de calibración: {e}")

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

 # Enviamos los datos al teclado inmediatamente después de conectar
    enviar_calibracion_qmk(dev)

    threading.Thread(target=escuchar_hid, args=(dev,), daemon=True).start()
    threading.Thread(target=detectar_clic_reset_alt, args=(dev,), daemon=True).start()
    threading.Thread(target=seguimiento_mouse, daemon=True).start()
    threading.Thread(target=loop_movimiento_suave, daemon=True).start()
    # threading.Thread(target=wrap_loop, daemon=True).start()
    threading.Thread(target=ocultar_indicador_si_mouse_cerca, daemon=True).start()
    
    # Inicia la captura de Alt para OneNote 2016
    utils.onenote_nav.run_in_background()
    scroll_lock.run_in_background(lambda: scroll_lock_activo)

    print("========================================")
    print("  CORNELL READY – SALTO + WRAP INTEGRADO ")
    print("========================================")

    root.mainloop()

if __name__ == "__main__":
    main()
