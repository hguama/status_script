import hid
import tkinter as tk
import threading
import pyautogui
import time
import ctypes

# Colores por capa
colores = {
    "ALFA": "#66BB6A",       # verde
    "MODE": "#8E24AA",       # morado
    "COMMIT": "#E53935",     # rojo
    "NUMB": "#9E9E9E",       # gris
    "MOUSE_1": "#FFEB3B",    # amarillo
    "MOUSE_2": "#64B5F6",    # azul claro
}

# Tamaño del botón redondo
DIAMETRO = 40

# Crear ventana transparente
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.0)
root.config(bg="magenta")
root.wm_attributes("-transparentcolor", "magenta")

# Centrar en parte superior
pantalla_ancho = root.winfo_screenwidth()
pos_x = (pantalla_ancho - DIAMETRO) // 2
pos_y = 5
root.geometry(f"{DIAMETRO}x{DIAMETRO}+{pos_x}+{pos_y}")
root.withdraw()

# Canvas circular
canvas = tk.Canvas(root, width=DIAMETRO, height=DIAMETRO, highlightthickness=0, bg="magenta")
canvas.pack()

def dibujar_boton(color):
    canvas.delete("all")
    MARGEN = 2
    canvas.create_oval(MARGEN, MARGEN, DIAMETRO - MARGEN, DIAMETRO - MARGEN, fill=color, outline="")

def actualizar_color(capa_activa):
    if capa_activa in colores:
        dibujar_boton(colores[capa_activa])
        root.deiconify()
        root.attributes("-alpha", 0.9)
    else:
        root.withdraw()

# --- WRAP AROUND DEL MOUSE ---

user32 = ctypes.windll.user32
screen_width = user32.GetSystemMetrics(0)
screen_height = user32.GetSystemMetrics(1)
margin = 1
wrap_enabled = threading.Event()  # control de activación

def wrap_mouse_loop():
    """Teletransporta el cursor entre los 4 bordes de la pantalla, con recuperación automática."""
    print("🖱️ Hilo de wrap-around iniciado correctamente.")
    while True:
        try:
            if wrap_enabled.is_set():
                x, y = pyautogui.position()

                # Envolver horizontalmente
                if x >= screen_width - margin:
                    pyautogui.moveTo(margin, y)
                elif x <= 0:
                    pyautogui.moveTo(screen_width - margin, y)

                # Envolver verticalmente
                if y >= screen_height - margin:
                    pyautogui.moveTo(x, margin)
                elif y <= 0:
                    pyautogui.moveTo(x, screen_height - margin)

            # Breve pausa (suaviza movimiento y evita alta carga)
            time.sleep(0.01)

        except Exception as e:
            print(f"⚠️ Error en wrap-around: {e}")
            # Pausa corta antes de intentar recuperar
            time.sleep(0.5)
            continue


# --- ESCUCHA HID ---
def escuchar_hid():
    dispositivo = next((d['path'] for d in hid.enumerate()
                        if d['vendor_id'] == 0x4653 and d['product_id'] == 0x0001 and d['usage_page'] != 1), None)
    if not dispositivo:
        print("❌ Dispositivo no encontrado.")
        return

    try:
        dev = hid.device()
        dev.open_path(dispositivo)
        print("✅ Escuchando RAW HID...")

        capa_actual = None
        while True:
            data = dev.read(32, timeout_ms=500)
            if data:
                mensaje = bytes(data).decode('utf-8', errors='ignore').strip('\x00')
                print("Mensaje recibido:", mensaje)
                nueva_capa = next((c for c in colores if c in mensaje), None)
                if nueva_capa != capa_actual:
                    capa_actual = nueva_capa
                    root.after(0, actualizar_color, nueva_capa)

                    # Activar o desactivar wrap-around según capa
                    if capa_actual == "MOUSE_2":
                        wrap_enabled.set()
                        print("🌀 Wrap-around ACTIVADO (MOUSE_2)")
                    else:
                        wrap_enabled.clear()
                        print("🛑 Wrap-around DESACTIVADO")

    except Exception as e:
        print("❌ Error:", e)

# --- MAIN ---
def main():
    threading.Thread(target=escuchar_hid, daemon=True).start()
    threading.Thread(target=wrap_mouse_loop, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()
