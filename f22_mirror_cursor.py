import tkinter as tk
import threading
import time
import keyboard
import ctypes
import logging
import os

log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f22_debug.log")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s - [MIRROR_APP] %(message)s', datefmt='%H:%M:%S', handlers=[
    logging.FileHandler(log_path, encoding='utf-8', mode='a'),
    logging.StreamHandler()
])
logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURACIÓN DEL INDICADOR DE MODO ESPEJO
# ==========================================
DISTANCIA = 25          # Distancia de la línea respecto al puntero
LADO = "derecha"        # Lado donde aparece el indicador: "izquierda" o "derecha"

# Banderas para activar/desactivar cada indicador
MOSTRAR_PRINCIPAL = False  # Muestra la línea al lado de tu puntero actual
MOSTRAR_DEST_H = True     # Muestra la línea fantasma de tu destino Horizontal
MOSTRAR_DEST_V = True     # Muestra la línea fantasma de tu destino Vertical

COLOR_PRINCIPAL = "#00FFFF" # Color del indicador principal (Ej: cyan)
COLOR_DEST_H = "#FF9900"    # Color del destino Horizontal (Ej: Naranja)
COLOR_DEST_V = "#00FF00"    # Color del destino Vertical (Ej: Verde)

GROSOR = 2              # Grosor de las líneas en píxeles
ALTURA = 20            # Altura de las líneas en píxeles

# DPI awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MirrorModeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw() # Ocultamos la ventana principal base
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Crear 3 ventanitas (indicadores) sólo si la bandera correspondiente está en True
        self.win_main = self.create_indicator_window(COLOR_PRINCIPAL) if MOSTRAR_PRINCIPAL else None
        self.win_dest_h = self.create_indicator_window(COLOR_DEST_H) if MOSTRAR_DEST_H else None
        self.win_dest_v = self.create_indicator_window(COLOR_DEST_V) if MOSTRAR_DEST_V else None
        
        # Atajos configurados por el usuario
        keyboard.on_press_key("f13", self.on_f13_press)
        keyboard.on_press_key("f14", self.on_f14_press)
        
        # Hilo que mantiene las líneas pegadas a sus posiciones constantemente
        self.update_thread = threading.Thread(target=self.track_mouse, daemon=True)
        self.update_thread.start()
        logger.info("Script f22_mirror_cursor (Subproceso) iniciado y escuchando F13/F14.")
        
    def create_indicator_window(self, color):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.config(bg="magenta")
        win.wm_attributes("-transparentcolor", "magenta")
        win.geometry(f"{GROSOR}x{ALTURA}+0+0")
        
        canvas = tk.Canvas(win, width=GROSOR, height=ALTURA, highlightthickness=0, bg="magenta")
        canvas.pack()
        canvas.create_line(GROSOR//2, 0, GROSOR//2, ALTURA, fill=color, width=GROSOR)
        return win
        
    def get_mouse_pos(self):
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
        
    def on_f13_press(self, e):
        ctrl_pressed = keyboard.is_pressed("ctrl")
        shift_pressed = keyboard.is_pressed("shift")
        logger.info(f"-----> TECLA F13 DETECTADA. Modificadores: Ctrl={ctrl_pressed}, Shift={shift_pressed}")
        # Verificar que se presionan ctrl y shift
        if ctrl_pressed and shift_pressed:
            logger.info("Ejecutando teletransporte HORIZONTAL")
            self.ejecutar_teletransporte_horizontal()

    def on_f14_press(self, e):
        ctrl_pressed = keyboard.is_pressed("ctrl")
        shift_pressed = keyboard.is_pressed("shift")
        logger.info(f"-----> TECLA F14 DETECTADA. Modificadores: Ctrl={ctrl_pressed}, Shift={shift_pressed}")
        # Verificar que se presionan ctrl y shift
        if ctrl_pressed and shift_pressed:
            logger.info("Ejecutando teletransporte VERTICAL")
            self.ejecutar_teletransporte_vertical()

    def ejecutar_teletransporte_horizontal(self):
        mx, my = self.get_mouse_pos()
        teleport_x = self.screen_width - mx
        ctypes.windll.user32.SetCursorPos(teleport_x, my)

    def ejecutar_teletransporte_vertical(self):
        mx, my = self.get_mouse_pos()
        teleport_y = self.screen_height - my
        ctypes.windll.user32.SetCursorPos(mx, teleport_y)

    def track_mouse(self):
        while True:
            try:
                mx, my = self.get_mouse_pos()
                
                # ---------------------------------------------------
                # 1. Posición del Indicador Principal (donde está el mouse)
                # ---------------------------------------------------
                if LADO.lower() == "izquierda":
                    main_x = mx - DISTANCIA - (GROSOR // 2)
                else:
                    main_x = mx + DISTANCIA - (GROSOR // 2)
                main_y = my - (ALTURA // 2)
                
                if self.win_main:
                    self.win_main.geometry(f"+{main_x}+{main_y}")
                
                # ---------------------------------------------------
                # 2. Posición del Destino Horizontal (Simetría en X)
                # ---------------------------------------------------
                if self.win_dest_h:
                    dest_x = self.screen_width - mx
                    if LADO.lower() == "izquierda":
                        ghost_h_x = dest_x - DISTANCIA - (GROSOR // 2)
                    else:
                        ghost_h_x = dest_x + DISTANCIA - (GROSOR // 2)
                        
                    self.win_dest_h.geometry(f"+{ghost_h_x}+{main_y}")
                
                # ---------------------------------------------------
                # 3. Posición del Destino Vertical (Simetría en Y)
                # ---------------------------------------------------
                if self.win_dest_v:
                    dest_y = self.screen_height - my
                    ghost_v_y = dest_y - (ALTURA // 2)
                    
                    self.win_dest_v.geometry(f"+{main_x}+{ghost_v_y}")
                
            except Exception:
                pass
            time.sleep(0.01)

if __name__ == "__main__":
    logger.info("==========================================")
    logger.info("Módulo de Modo Espejo (Subproceso) arrancando...")
    logger.info("==========================================")
    print("Módulo de Modo Espejo iniciado.")
    print(f"Indicadores activos: Principal({MOSTRAR_PRINCIPAL}), Dest Horizontal({MOSTRAR_DEST_H}), Dest Vertical({MOSTRAR_DEST_V})")
    print(" - Ctrl+Shift+F13: Espejo Horizontal")
    print(" - Ctrl+Shift+F14: Espejo Vertical")
    app = MirrorModeApp()
    app.root.mainloop()
