# Documentación: Parámetros QMK Mouse con Teclado

## Ubicación del Código

**Archivo:** `status script\layer_status_script.py`  
**Líneas:** 79–83 (definición) y 802–819 (envío vía HID al firmware)

```python
# --- PARAMETERS MOUSE WITH KEYBOARD---
QMK_MOUSE_MAX_SPEED    = 7   # Velocidad máxima del puntero QMK
QMK_MOUSE_TIME_TO_MAX  = 30  # Rampa de aceleración
QMK_MOUSE_INTERVAL     = 18  # Refresco (~60 Hz, estándar de monitores)
QMK_MOUSE_MOVE_DELTA   = 1   # Paso mínimo posible por ciclo
```

---

## 1. ¿Qué es QMK_MOUSE_MAX_SPEED?

`QMK_MOUSE_MAX_SPEED` es un **parámetro de configuración del firmware QMK** (Quantum Mechanical Keyboard) que controla la **velocidad punta del cursor del ratón** cuando este es movido mediante combinaciones de teclas del teclado (mouse keys).

Es decir: no afecta al ratón físico externo, sino al **mouse emulado por el propio teclado** mediante atajos de teclas.

### ¿Qué hace?

| Parámetro               | Descripción                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| `QMK_MOUSE_MAX_SPEED`   | Velocidad máxima en "unidades por ciclo" que el cursor puede alcanzar.      |
| `QMK_MOUSE_TIME_TO_MAX` | Tiempo (en ciclos) que tarda en llegar a la velocidad máxima.               |
| `QMK_MOUSE_INTERVAL`    | Tiempo en ms entre cada pulso de movimiento (frecuencia de refresco).       |
| `QMK_MOUSE_MOVE_DELTA`  | Incremento mínimo por pulso al empezar a moverse (paso base).               |

### Valores configurados actualmente

| Parámetro               | Valor | Significado práctico                                          |
|-------------------------|-------|---------------------------------------------------------------|
| `QMK_MOUSE_MAX_SPEED`   | **7** | Velocidad punta **moderada** (evita que el cursor salga disparado) |
| `QMK_MOUSE_TIME_TO_MAX` | **30**| La aceleración es suave: tarda 30 ciclos en llegar al máximo. |
| `QMK_MOUSE_INTERVAL`    | **18**| ~55.5 Hz de refresco → movimiento muy progresivo y preciso.   |
| `QMK_MOUSE_MOVE_DELTA`  | **1** | El paso más fino posible (precisión milimétrica al inicio).   |

---

## 2. ¿Cómo se conecta con mi teclado QMK (Corne)?

### 2.1 Flujo de comunicación

```
┌─────────────────┐         HID Raw (USB)        ┌──────────────────────┐
│  Python Script  │ ◄──────────────────────────► │  Firmware QMK (Corne)│
│  (layer_status_ │                              │  - MCU ATmega32U4    │
│   script.py)    │                              │  - keymap.c          │
└────────┬────────┘                              └──────────┬───────────┘
         │                                                  │
         │ 1. Script envía buffer de 33 bytes               │
         │    con firma 'M' + parámetros mouse              │
         │ ─────────────────────────────────►               │
         │                                                  │
         │                   2. Firmware QMK lee los datos   │
         │                      desde el reporte HID raw     │
         │                      y ajusta mouse_keys en       │
         │                      tiempo real                  │
         │                                                  │
         │ 3. Teclado envía cambios de capa                 │
         │ ◄─────────────────────────────────               │
         │    (texto: LAYER_1, LAYER_2, etc.)               │
         │                                                  │
         ▼                                                  ▼
   ┌──────────┐                                   ┌──────────────┐
   │ Overlay  │                                   │ Movimiento   │
   │ visual   │                                   │ del cursor   │
   │ (tkinter)│                                   │ vía mouse    │
   └──────────┘                                   │ keys (F23/F24)│
                                                  └──────────────┘
```

### 2.2 Identificación del dispositivo

```python
VID, PID = 0x4653, 0x0001  # Vendor ID y Product ID del Corne
```

- `0x4653` = VID del fabricante del teclado Corne.
- `0x0001` = PID genérico para teclados QMK con raw HID.

### 2.3 Envío de parámetros al firmware

La función `enviar_calibracion_qmk(dev)` (línea 802) construye un buffer HID de 33 bytes:

```python
buf = [0] * 33
buf[0] = 0x00                     # Report ID (requerido por Windows)
buf[1] = ord("M")                 # Firma 'M' → el firmware C busca `if (data[0] == 'M')`
buf[2] = QMK_MOUSE_MAX_SPEED      # data[1] en QMK
buf[3] = QMK_MOUSE_TIME_TO_MAX    # data[2] en QMK
buf[4] = QMK_MOUSE_INTERVAL       # data[3] en QMK
# buf[5] =                        # data[4] en QMK (reservado)
# buf[6] = QMK_MOUSE_MOVE_DELTA   # data[5] en QMK (comentado, no se envía actualmente)

dev.write(buf)
```

Esto se ejecuta **una sola vez** al iniciar el script, en `main()`:

```python
enviar_calibracion_qmk(dev)  # Línea 835
```

### 2.4 Del lado del firmware QMK (keymap.c)

El firmware del Corne debe tener un handler en C que intercepte el reporte HID raw con firma `'M'` y aplique los valores a las variables internas de QMK. Algo así:

```c
// Dentro de raw_hid_receive() en keymap.c
void raw_hid_receive(uint8_t *data, uint8_t length) {
    if (data[0] == 'M') {
        // Aplicar parámetros recibidos del script Python
        // data[1] = QMK_MOUSE_MAX_SPEED
        // data[2] = QMK_MOUSE_TIME_TO_MAX
        // data[3] = QMK_MOUSE_INTERVAL
        // data[4] = reservado
        // data[5] = QMK_MOUSE_MOVE_DELTA
    }
}
```

Los parámetros se inyectan en las variables internas del sistema de mouse keys de QMK, que controlan:
- La curva de aceleración del cursor.
- La velocidad máxima alcanzable.
- El intervalo de refresco (cada cuántos ms se envía un `MOUSEKEY` report).

---

## 3. Relación con el movimiento del cursor en el script

Estos parámetros **NO** controlan directamente el movimiento desde Python (eso lo hace `loop_movimiento_suave()` con `VEL_BASE`, `VEL_MAX`, `ACEL_POR_FRAME`). Los parámetros QMK controlan **el comportamiento del teclado mismo** cuando el usuario mueve el ratón con las teclas asignadas a mouse keys en el firmware.

### Parámetros del script Python (para comparar)

| Parámetro Python    | Valor | Rol                                                         |
|---------------------|-------|-------------------------------------------------------------|
| `VEL_BASE`          | 3.0   | Velocidad inicial en píxeles/ciclo para movimiento suave.   |
| `VEL_MAX`           | 42.0  | Velocidad máxima en píxeles/ciclo (aceleración del script). |
| `ACEL_POR_FRAME`    | 0.65  | Incremento de velocidad por cada frame (~10ms).             |
| `MARGEN_BLOQUEO`    | 10    | Píxeles de bloqueo en los bordes de la pantalla.            |
| `DISTANCIA_FRENADO` | 500   | Distancia antes del borde donde empieza a frenar.           |

### ¿Por qué hay dos juegos de parámetros?

- **Parámetros QMK** → controlan cómo el **firmware del teclado** emite eventos de ratón al SO (más "bajo nivel").
- **Parámetros Python** → controlan cómo el **script en la PC** mueve el cursor mediante `pyautogui`/`ctypes` (más "alto nivel", con lógica de bordes, wrap-around, etc.).

Ambos coexisten porque el sistema usa **dos modos de movimiento**:
1. **Mouse keys nativas de QMK** (controladas por los parámetros QMK).
2. **Movimiento suave por software** (controlado por el script, activado con F23/F24).

---

## 4. Resumen visual de los valores configurados

```
         Velocidad
            ▲
            │
      7 ────┼─────────────────────────● ● ● ● ●  (QMK_MOUSE_MAX_SPEED = 7)
            │                    ╱
            │                 ╱
            │              ╱
            │           ╱
            │        ╱
      1 ────┼───●───╱                            (QMK_MOUSE_MOVE_DELTA = 1)
            │  ╱
            │ ╱
            │╱
            └──────────────────────────────────► Tiempo (ciclos)
            0                              30
                                    (QMK_MOUSE_TIME_TO_MAX)

   Cada pulso ocurre cada 18 ms (~55.5 Hz → QMK_MOUSE_INTERVAL)
```

---

## 5. Cómo modificar estos valores

### Desde el script Python

Editar las constantes en `layer_status_script.py`, líneas 80–83:

```python
QMK_MOUSE_MAX_SPEED    = 10   # Aumentar para cursor más rápido
QMK_MOUSE_TIME_TO_MAX  = 20   # Reducir para aceleración más agresiva
QMK_MOUSE_INTERVAL     = 10   # Reducir para más fluidez (~100 Hz)
QMK_MOUSE_MOVE_DELTA   = 2    # Aumentar paso mínimo
```

Al reiniciar el script, los nuevos valores se envían automáticamente al teclado.

### Desde el firmware QMK

Si prefieres valores fijos sin depender del script, puedes configurarlos directamente en `config.h` del firmware:

```c
#define MOUSEKEY_MAX_SPEED      7
#define MOUSEKEY_TIME_TO_MAX    30
#define MOUSEKEY_INTERVAL       18
#define MOUSEKEY_MOVE_DELTA     1
```

Esto es lo que recomienda la [documentación oficial de QMK](https://docs.qmk.fm/#/feature_mouse_keys) para mouse keys.

---

## 6. Notas adicionales

- El parámetro `QMK_MOUSE_MOVE_DELTA` está definido en el script pero **comentado** en el buffer de envío (`# buf[6] = QMK_MOUSE_MOVE_DELTA`). Actualmente no se transmite al firmware.
- Los valores fueron elegidos para un **Corne keyboard** con **pantalla de 1920×1080**.
- La configuración prioriza **precisión sobre velocidad** para evitar que el cursor "salga disparado" al usar las teclas de navegación.
