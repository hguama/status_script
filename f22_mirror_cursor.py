import tkinter as tk
import threading
import time
import keyboard
import ctypes

# ==========================================
# CONFIGURACIÓN DEL INDICADOR DE MODO ESPEJO
# ==========================================
DISTANCIA = 25          # Distancia de la línea respecto al puntero
LADO = "derecha"        # Lado donde aparece el indicador: "izquierda" o "derecha"
COLOR = "#00FFFF"       # Color del indicador (Ej: cyan)
GROSOR = 2             # Grosor de la línea en píxeles
ALTURA = 20            # Altura de la línea en píxeles

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
        self.root.title("Mirror Indicator")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg="magenta")
        self.root.wm_attributes("-transparentcolor", "magenta")
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        self.width = GROSOR
        self.height = ALTURA
        
        self.root.geometry(f"{self.width}x{self.height}+0+0")
        
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, highlightthickness=0, bg="magenta")
        self.canvas.pack()
        
        # Dibujar la línea indicadora
        self.canvas.create_line(self.width//2, 0, self.width//2, self.height, fill=COLOR, width=GROSOR)
        
        # Atajos configurados por el usuario
        keyboard.on_press_key("f13", self.on_f13_press)
        keyboard.on_press_key("f14", self.on_f14_press)
        
        # Hilo que mantiene la línea pegada al cursor constantemente
        self.update_thread = threading.Thread(target=self.track_mouse, daemon=True)
        self.update_thread.start()
        
    def get_mouse_pos(self):
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
        
    def on_f13_press(self, e):
        # Verificar que se presionan ctrl y shift
        if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
            self.ejecutar_teletransporte_horizontal()

    def on_f14_press(self, e):
        # Verificar que se presionan ctrl y shift
        if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
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
                
                # Calcular posición constante al lado del puntero
                if LADO.lower() == "izquierda":
                    win_x = mx - DISTANCIA - (self.width // 2)
                else:
                    win_x = mx + DISTANCIA - (self.width // 2)
                    
                win_y = my - (self.height // 2)
                
                self.root.geometry(f"+{win_x}+{win_y}")
            except Exception:
                pass
            time.sleep(0.01)

if __name__ == "__main__":
    print("Módulo de Modo Espejo (Subproceso) iniciado.")
    print(" - Ctrl+Shift+F13: Espejo Horizontal")
    print(" - Ctrl+Shift+F14: Espejo Vertical")
    app = MirrorModeApp()
    app.root.mainloop()
