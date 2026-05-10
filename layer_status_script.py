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

import logging
import os
import ctypes

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
TIEMPO_ANCLAJE = 2   # Segundos que el mouse queda bloqueado tras un salto
pyautogui.PAUSE = 0    # Eliminar delay interno de pyautogui para máxima fluidez

# --- PARÁMETROS DE PRECISIÓN EN BORDES ---
MARGIN_ESQUINA = 100    # Píxeles desde las esquinas donde el muro es sólido (no salta)
DISTANCIA_FRENADO = 500 # Píxeles antes del borde donde empieza a frenar dinámicamente
UMBRAL_VIAJE_LARGO = 450 # Distancia recorrida para activar el bloqueo de esquinas
ZONA_LIBRE_BORDE = 0.25  # 25% de la pantalla para permitir paso fluido sin bloqueos




# ===============================================================
# ESTADOS GLOBALES
# ===============================================================
alt_tab_menu_visible = False
INDICADOR_HABILITADO = False

tecla_horiz_down = False
tecla_vert_down = False
direccion_fijada = 0
direccion_y_fijada = 0
pos_y_referencia = 0

color_actual = "#FFFFFF"
wrap_enabled = threading.Event()
wrap_enabled.set()
indicador_visible_por_capa = False


# ===============================================================
# --- UI CONFIG ---
DIAMETRO, PUNTO_MOUSE, OFFSET_MOUSE = 30, 10, 22

colores = {
    "ALFA": "#66BB6A",
    "MODE": "#8E24AA",
    "COMMIT": "#E53935",
    "NUMB": "#9E9E9E",
    "MOUSE_1": "#8D6E63",
    "MOVE": "#FFEB3B",
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

# --- VENTANA PARA EFECTO PULSO ELEGANTE ---
ripple_win = tk.Toplevel()
ripple_win.overrideredirect(True)
ripple_win.attributes("-topmost", True)
ripple_win.config(bg="magenta")
ripple_win.wm_attributes("-transparentcolor", "magenta")
ripple_win.geometry("120x120+0+0")
ripple_win.withdraw()

canvas_ripple = tk.Canvas(ripple_win, width=120, height=120, bg="magenta", highlightthickness=0)
canvas_ripple.pack()

def efecto_onda(x, y):
    """Muestra un pulso de diamante elegante y sutil SOLO si los indicadores están habilitados."""
    if not INDICADOR_HABILITADO:
        return
        
    ripple_win.geometry(f"120x120+{int(x-60)}+{int(y-60)}")
    ripple_win.deiconify()
    
    def animar_pulso(step):
        canvas_ripple.delete("all")
        if step < 12:
            # El radio del diamante se expande
            r = step * 4
            # El color es el de la capa actual
            color = color_actual
            
            # Dibujar un rombo (diamante) elegante que se expande
            puntos = [60, 60-r, 60+r, 60, 60, 60+r, 60-r, 60]
            canvas_ripple.create_polygon(puntos, outline=color, fill="", width=2)
            
            # Punto central fijo que se hace más pequeño
            r_centro = max(1, 4 - (step // 3))
            canvas_ripple.create_oval(60-r_centro, 60-r_centro, 60+r_centro, 60+r_centro, fill=color, outline="")
            
            ripple_win.after(15, lambda: animar_pulso(step + 1))
        else:
            ripple_win.withdraw()
            
    animar_pulso(0)

def toggle_indicadores(e=None):
    """Alterna la bandera global de visibilidad de los indicadores."""
    global INDICADOR_HABILITADO
    INDICADOR_HABILITADO = not INDICADOR_HABILITADO
    logger.info(f"Indicadores habilitados: {INDICADOR_HABILITADO}")
    
    if not INDICADOR_HABILITADO:
        root.withdraw()
        mouse_win.withdraw()
    elif indicador_visible_por_capa:
        root.deiconify()
        mouse_win.deiconify()

# Asignar F21 para alternar la visibilidad de las burbujas
keyboard.on_press_key("f21", toggle_indicadores)

def actualizar_ui(capa_msg):
    global indicador_visible_por_capa, color_actual

    clave = next((k for k in colores if k in capa_msg), None)
    if clave:
        color_actual = colores[clave]
        c = color_actual
        canvas.delete("all")
        canvas.create_oval(2, 2, DIAMETRO-2, DIAMETRO-2, fill=c, outline="")
        canvas_mouse.delete("all")
        canvas_mouse.create_oval(0, 0, PUNTO_MOUSE, PUNTO_MOUSE, fill=c, outline="")
        indicador_visible_por_capa = True
        
        if INDICADOR_HABILITADO:
            root.deiconify()
            mouse_win.deiconify()
    else:
        indicador_visible_por_capa = False
        root.withdraw()
        mouse_win.withdraw()


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
            x, y = pyautogui.position()
            mouse_win.geometry(f"+{x-PUNTO_MOUSE//2}+{y+OFFSET_MOUSE}")
        except:
            pass
        time.sleep(0.01)

# ===============================================================
# F22 / F23 – MOVIMIENTO SUAVE Y CONTROLADO
# ===============================================================

def presiona_f22(e):
    global tecla_horiz_down
    tecla_horiz_down = True
    logger.debug("[TECLA F22 PRESIONADA]")

def suelta_f22(e):
    global tecla_horiz_down, direccion_fijada
    tecla_horiz_down = False
    direccion_fijada = 0
    logger.debug("[TECLA F22 SOLTADA]")

def presiona_f23(e):
    global tecla_vert_down
    tecla_vert_down = True
    logger.debug("[TECLA F23 PRESIONADA]")

def suelta_f23(e):
    global tecla_vert_down, direccion_y_fijada
    tecla_vert_down = False
    direccion_y_fijada = 0
    logger.debug("[TECLA F23 SOLTADA]")

keyboard.on_press_key("f22", presiona_f22)
keyboard.on_release_key("f22", suelta_f22)
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
    tiempo_ultimo_movimiento = time.time()
    
    while True:
        # --- OBTENER POSICIÓN REAL (Sin latencia de PyAutoGUI) ---
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        curr_x, curr_y = pt.x, pt.y
        ahora = time.time()
        
        # --- RASTREO UNIVERSAL DE ORIGEN (Manual + Turbo) ---
        # Comparamos con la posición real anterior, no con la posición ordenada (last_x)
        if abs(curr_x - prev_actual_x) > 0 or abs(curr_y - prev_actual_y) > 0:
            tiempo_ultimo_movimiento = ahora
        elif ahora - tiempo_ultimo_movimiento > 0.15:
            # Si el ratón se detiene por 150ms, consideramos que empieza un nuevo "viaje"
            origen_swipe_x, origen_swipe_y = curr_x, curr_y

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
                
                # Para que se "quede en la pared" donde chocó, lo devolvemos al borde de la pantalla actual
                if curr_x < last_x: # Cruzó el borde derecho hacia el izquierdo
                    limite_x = pantalla_ancho - 1
                else: # Cruzó el borde izquierdo hacia el derecho
                    limite_x = 0
                    
                logger.debug(f"[SALTO PROTEGIDO EXT] X:{last_x}->{curr_x} | ANCLAJE EN BORDE: {limite_x} (Dist: {dist_viajada_x})")
            else:
                logger.debug(f"[SALTO LIBRE POR ZONA] X:{last_x}->{curr_x} | Viaje Corto (Dist: {dist_viajada_x})")
            
            # Tras un salto, el nuevo origen es donde aterrizamos
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
                    limite_y = pantalla_alto - 1
                else:
                    limite_y = 0
                    
                logger.debug(f"[SALTO PROTEGIDO EXT] Y:{last_y}->{curr_y} | ANCLAJE EN BORDE: {limite_y} (Dist: {dist_viajada_y})")
            else:
                logger.debug(f"[SALTO LIBRE POR ZONA] Y:{last_y}->{curr_y} | Viaje Corto (Dist: {dist_viajada_y})")
                
            origen_swipe_y = curr_y
            last_y = curr_y

        # --- APLICAR ANCLAJE (FUERZA CONSTANTE) ---
        if anclado_x:
            if ahora - tiempo_anclaje_x > TIEMPO_ANCLAJE:
                anclado_x = False
                logger.debug("[MURO X LIBERADO por tiempo]")
            else:
                # Detectar si el usuario intenta alejarse del muro (movimiento fuerte opuesto)
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
            else:
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
                
                if dist_borde_x < DISTANCIA_FRENADO:
                    # Frenado dinámico proporcional a la distancia al borde
                    factor_x = max(0.1, dist_borde_x / DISTANCIA_FRENADO)
                    speed_x = max(VEL_BASE, speed_x * factor_x)
                    nx = curr_x + (speed_x * direccion_fijada)

                if dist_borde_y < DISTANCIA_FRENADO:
                    factor_y = max(0.1, dist_borde_y / DISTANCIA_FRENADO)
                    speed_y = max(VEL_BASE, speed_y * factor_y)
                    ny = curr_y + (speed_y * direccion_y_fijada)

                es_viaje_corto = abs(curr_x - origen_swipe_x) < UMBRAL_VIAJE_LARGO
                hit_edge = False
                final_x, final_y = nx, ny
                
                if nx <= 0:
                    if es_viaje_corto:
                        final_x = pantalla_ancho - WRAP_MARGIN
                        hit_edge = True
                    else:
                        nx = 0
                        speed_x = 0 # Frena en seco contra la pared
                elif nx >= pantalla_ancho - 1:
                    if es_viaje_corto:
                        final_x = WRAP_MARGIN
                        hit_edge = True
                    else:
                        nx = pantalla_ancho - 1
                        speed_x = 0
                        
                if ny <= 0:
                    if es_viaje_corto:
                        final_y = pantalla_alto - WRAP_MARGIN
                        hit_edge = True
                    else:
                        ny = 0
                        speed_y = 0
                elif ny >= pantalla_alto - 1:
                    if es_viaje_corto:
                        final_y = WRAP_MARGIN
                        hit_edge = True
                    else:
                        ny = pantalla_alto - 1
                        speed_y = 0

                if hit_edge:
                    logger.debug(f"[SALTO INTERNO] nx:{nx} -> {final_x} | Viaje Corto: {es_viaje_corto} (Dist: {abs(curr_x - origen_swipe_x)})")
                    
                    # Si es un viaje corto (empezó cerca del borde), no hay pausa ni anclaje
                    if not es_viaje_corto:
                        pause_until = ahora + PAUSA_BORDE_S
                    else:
                        pause_until = ahora + 0.05 # Pausa mínima para evitar rebotes
                    
                    speed_x = VEL_BASE * 2
                    speed_y = VEL_BASE * 2
                    
                    if final_x != nx:
                        # Solo anclamos si es un viaje largo (NO viene de zona segura)
                        if not es_viaje_corto:
                            anclado_x = True
                            tiempo_anclaje_x = ahora
                            dir_anclaje_x = direccion_fijada
                            limite_x = final_x + (dir_anclaje_x * (pantalla_ancho // 4))
                    if final_y != ny:
                        if not es_viaje_corto:
                            anclado_y = True
                            tiempo_anclaje_y = ahora
                            dir_anclaje_y = direccion_y_fijada
                            limite_y = final_y + (dir_anclaje_y * (pantalla_alto // 4))

                    origen_swipe_x, origen_swipe_y = final_x, final_y
                    distancia_recorrida = 0 # Resetear tras salto
                    pyautogui.moveTo(final_x, final_y)
                    last_x, last_y = final_x, final_y
                    root.after(0, lambda: efecto_onda(final_x, final_y))
                else:
                    nx = max(0, min(pantalla_ancho - 1, nx))
                    ny = max(0, min(pantalla_alto - 1, ny))
                    if nx != curr_x or ny != curr_y:
                        pyautogui.moveTo(nx, ny)
                    last_x, last_y = nx, ny
            else:
                # --- FRENO DE EMERGENCIA GLOBAL (Para teclas normales QMK) ---
                vx = curr_x - last_x
                vy = curr_y - last_y
                
                # Solo actuar si hay movimiento real (ignorar jitter)
                if abs(vx) > 1 or abs(vy) > 1:
                    dist_borde_x = min(curr_x, pantalla_ancho - curr_x)
                    dist_borde_y = min(curr_y, pantalla_alto - curr_y)
                    
                    # Detectar si se mueve HACIA el borde
                    hacia_borde_x = (vx > 0 and curr_x > pantalla_ancho // 2) or (vx < 0 and curr_x < pantalla_ancho // 2)
                    hacia_borde_y = (vy > 0 and curr_y > pantalla_alto // 2) or (vy < 0 and curr_y < pantalla_alto // 2)
                    
                    # Detectar si estamos en zona segura (25% lateral) para desactivar el freno
                    en_zona_segura_x = curr_x < (pantalla_ancho * ZONA_LIBRE_BORDE) or curr_x > (pantalla_ancho * (1 - ZONA_LIBRE_BORDE))
                    en_zona_segura_y = curr_y < (pantalla_alto * ZONA_LIBRE_BORDE) or curr_y > (pantalla_alto * (1 - ZONA_LIBRE_BORDE))

                    # Aplicar límite de velocidad dinámico en zona de frenado SOLO si no estamos en zona segura
                    if hacia_borde_x and dist_borde_x < DISTANCIA_FRENADO and not en_zona_segura_x:
                        # Velocidad máxima permitida disminuye conforme nos acercamos al borde
                        v_permitida = max(VEL_BASE, VEL_MAX * (dist_borde_x / DISTANCIA_FRENADO))
                        if abs(vx) > v_permitida:
                            nueva_x = last_x + (v_permitida * (1 if vx > 0 else -1))
                            ctypes.windll.user32.SetCursorPos(int(nueva_x), int(curr_y))
                            curr_x = nueva_x
                            
                    if hacia_borde_y and dist_borde_y < DISTANCIA_FRENADO and not en_zona_segura_y:
                        v_permitida_y = max(VEL_BASE, VEL_MAX * (dist_borde_y / DISTANCIA_FRENADO))
                        if abs(vy) > v_permitida_y:
                            nueva_y = last_y + (v_permitida_y * (1 if vy > 0 else -1))
                            ctypes.windll.user32.SetCursorPos(int(curr_x), int(nueva_y))
                            curr_y = nueva_y
                            
                last_x, last_y = curr_x, curr_y
        else:
            last_x, last_y = curr_x, curr_y
            
        prev_actual_x, prev_actual_y = curr_x, curr_y
        time.sleep(0.01)

# ===============================================================
# WRAP AROUND (PROTEGIDO)
# ===============================================================

def wrap_loop():
    def click_izquierdo_activo():
        return ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000 != 0

    ultimo_wrap = 0
    last_x_wrap, last_y_wrap = pyautogui.position()
    while True:
        ahora = time.time()
        
        try:
            x, y = pyautogui.position()
            vx = x - last_x_wrap
            vy = y - last_y_wrap
            
            # Solo actuar si no estamos en turbo (F22/F23) y ha pasado el cooldown
            if not tecla_horiz_down and not tecla_vert_down and (ahora - ultimo_wrap > COOLDOWN_WRAP):
                if not mouse.is_pressed("left") and not click_izquierdo_activo():
                    cambio = False
                    nx, ny = x, y

                    # Solo salta si el usuario empuja el ratón FÍSICAMENTE hacia el borde (vx > 1, etc.)
                    # Evita que salte solo por estar quieto en el borde tras un viaje largo.
                    if x <= 0 and vx < 0:
                        nx = pantalla_ancho - WRAP_MARGIN
                        cambio = True
                    elif x >= pantalla_ancho - 1 and vx > 0:
                        nx = WRAP_MARGIN
                        cambio = True

                    if y <= 0 and vy < 0:
                        ny = pantalla_alto - WRAP_MARGIN
                        cambio = True
                    elif y >= pantalla_alto - 1 and vy > 0:
                        ny = WRAP_MARGIN
                        cambio = True

                    if cambio:
                        # Reducido el delay para que sea instantáneo en zona segura
                        time.sleep(0.02)
                        pyautogui.moveTo(nx, ny)
                        ultimo_wrap = time.time()
                        
                        # DISPARAR EFECTO VISUAL
                        root.after(0, lambda: efecto_onda(nx, ny))
                        
            last_x_wrap, last_y_wrap = x, y
        except:
            pass
            
        time.sleep(0.01)


# ===============================================================
# ocultar indicador
# ===============================================================
def ocultar_indicador_si_mouse_cerca():
    while True:
        try:
            if not indicador_visible_por_capa:
                time.sleep(0.05)
                continue

            mx, my = pyautogui.position()

            # Centro del indicador superior
            cx = pantalla_ancho // 2
            cy = 5 + DIAMETRO // 2

            dx = mx - cx
            dy = my - cy
            distancia = (dx*dx + dy*dy) ** 0.5

            if distancia < RADIO_OCULTAR:
                root.withdraw()
            else:
                root.deiconify()

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

    threading.Thread(target=escuchar_hid, args=(dev,), daemon=True).start()
    threading.Thread(target=detectar_clic_reset_alt, args=(dev,), daemon=True).start()
    threading.Thread(target=seguimiento_mouse, daemon=True).start()
    threading.Thread(target=loop_movimiento_suave, daemon=True).start()
    threading.Thread(target=wrap_loop, daemon=True).start()
    threading.Thread(target=ocultar_indicador_si_mouse_cerca, daemon=True).start()
    
    # Inicia la captura de Alt para OneNote 2016
    utils.onenote_nav.run_in_background()

    print("========================================")
    print("  CORNELL READY – SALTO + WRAP INTEGRADO ")
    print("========================================")

    root.mainloop()

if __name__ == "__main__":
    main()
