import hid
import tkinter as tk
import threading

# Colores por capa
colores = {
    "MOVE": "#66BB6A",
    "MOUSE": "#E53935",
    "NUM": "#9E9E9E",
}

# Crear ventana principal
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.9)  # Visible cuando se activa

# Tamaño y posición
ANCHO, ALTO = 100, 25
pantalla_ancho = root.winfo_screenwidth()
pos_x = (pantalla_ancho - ANCHO) // 2
pos_y = 5
root.geometry(f"{ANCHO}x{ALTO}+{pos_x}+{pos_y}")

# Contenedor sin texto
frame = tk.Frame(root, width=ANCHO, height=ALTO, bg="black")
frame.pack_propagate(False)
frame.pack()

def actualizar_color(capa):
    if capa in colores:
        color = colores[capa]
        frame.configure(bg=color)
        root.deiconify()             # Mostrar
        root.attributes("-alpha", 0.9)
    else:
        root.withdraw()              # Ocultar (capa base)

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
    except Exception as e:
        print("❌ Error:", e)

def main():
    threading.Thread(target=escuchar_hid, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()

