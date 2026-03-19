# Guía de Remapeo de Teclas para Aplicaciones Específicas en Windows

Esta guía documenta la lógica, los conceptos ocultos y el flujo de los scripts en Python que interceptan el teclado a bajo nivel, especialmente si quieres automatizar otras aplicaciones trabajando junto a un teclado que emita macros rápidas (`QMK`/`VIA`).

## ¿Por qué usar la API `ctypes` (Bajo nivel)?
En Python existen maravillosas librerías como `keyboard` o `pynput`, pero a menudo carecen de "filtro dinámico condicional" rápido. Por ejemplo, capturar `Alt+Izquierda` usando `.add_hotkey('alt+left', suppress=True)` bloquearía el uso de `Alt+Izquierda` en **toda la computadora**. 

El uso del `WH_KEYBOARD_LL` de la API de Windows nos permite atrapar las teclas al vuelo y decir "si tengo *este programa abierto*, bloquear la tecla. De lo contrario, dejarla pasar nativamente". 

---

## 1. Patrón Fundamental del Código

En proyectos recientes, el archivo `onenote_nav.py` ilustra un patrón que podrás reciclar para cualquier aplicación futura:

1. **Definir tu Hook (Gancho) y el Bucle Principal (Message Loop):**
   Tu rutina requiere una función interceptora (`hook_proc`) que evaluará cada evento y un bucle de mensajes (que atrapa Windows usando el thread original). Se definen códigos clásicos de Windows (e.g., `WM_KEYDOWN = 0x0100`). **(No olvides la prevención del Error 126)**.

2. **La Variable de "Consumo" (`consumed_alt`):**
   Cuando inyectas comandos, puedes entrar en problemas de estados de teclado residuales. Si el teclado emite `Alt -> Letra`, se marca la letra como interceptada, y devolvemos un bloqueador: `return 1` para engañar a Windows diciendo que esa letra nunca existió. 

---

## 2. El Problema Modificador QMK y el "Foco Ribbon" 🚨
Casi siempre que manipules interceptaciones con atajos basados en **`Alt`** (como `LALT(kc)` o `A(kc)` en teclados con QMK), sufrirás del comportamiento inherente de Microsoft:

> **El Menú Superior:** Si presionar la tecla `Alt` y se suelta por sí sola —o un robot "ocultó" la tecla del medio que las separaba—, Microsoft asume que quieres abrir la Cinta de Opciones (Ribbon Menu). Cuando el Ribbon se abre, la aplicación cambiará la regla de sus atajos de la pantalla al menú. Ahi es donde por ejemplo los Page Up saltarán pestañas (Sections) en lugar de saltar tus hojas/vistas regulares.

### La Solución ("La Técnica del Dummy o Máscara")
Si bloqueaste el evento central `Left`, Windows ya no sabrá qué escribiste y registrará sólo `Alt Abajo` y `Alt Arriba` consecutivos:
- Para que Windows olvide el Ribbon, inyecta `Ctrl` Down (simular el registro `Ctrl`).
- Ahora es seguro enviar tu `.release("alt")` nativo. 
- Dispara rudimentariamente todos los `.press('mi_nueva_tecla')` seguido de sus `release('mi_nueva_tecla')` explícitos.
- Finalmente libera el `Ctrl`.

> **Lección de oro:** *Evita comandos "inteligentes" como `.send("mi_tecla")` de la librería `keyboard` si hay modificadores presionados dinámicamente, porque estos scripts eliminan momentáneamente el modificador (en este caso limpiando el Ctrl engañosamente).* Siempre haz `press` y `release` rudimentarios de tu propia mano manual.

---

## 3. Ejemplo Práctico: Adaptar el Script

Supón que quieres que al estar en Excel (`EXCEL.EXE`), presionar `Shift Derecho + Enter` (vía QMK) emule enviar `Tab` para otra tarea diferente:

```python
# 1. Agregas las constantes
VK_RSHIFT = 0xA1
VK_RETURN = 0x0D

# 2. Definis la validación de ventana
def is_excel_active():
    return get_active_process_name().lower() == "excel.exe"

# 3. Función independiente de acción
def enviar_hacia_excel():
    time.sleep(0.01) # Deja vaciar eventos QMK rápidos
    
    # Inyéctalo puro sin modifiers ocultos
    keyboard.press("tab") 
    time.sleep(0.005)
    keyboard.release("tab")

# 4. Monitorea dentro de hook_proc()
# if vk == VK_RSHIFT: ...
#    if wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN:
#        track_shift = True
#        consumed_shift = False
# ... etc, aplicas la condición si track_shift y la app es Excel: envías el Thread(enviar_hacia_excel).
```

## Resumen para Depuraciones Futuras
1. Asegúrate siempre de definir la estructura `restype` para `SetWindowsHookExW` a 64 bits para evitar el Error 126.
2. Todo QMK dispara los eventos `Tap` en tiempos asincrónicamente instantáneos (`<1ms`). Si fallan las pulsaciones, da retrasos rudimentarios (10-15ms) a los Hilos de inyección antes de enviarle pulsaciones a la App. 
3. Asegura y bloquea el estado nativo de `is_injected = (flags & 0x10) != 0` para prevenir que tu propio código sea atrapado dos veces en bucle infinito.
