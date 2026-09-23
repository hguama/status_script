> **Documentación de la versión Windows (rama `main`).** En Linux (rama `linux-port`) varias de estas funciones están deshabilitadas: ver [`README_LINUX.md`](README_LINUX.md).

# QMK Calibración — Mouse Keys vía HID Raw

> **Archivo:** `utils/qmk_calibracion/__init__.py`  
> **Propósito:** Enviar parámetros de mouse keys al firmware QMK durante la fase
> de pruebas, sin necesidad de reflashear el teclado.

---

## 🎯 ¿Qué hace?

El teclado Corne (firmware QMK) puede mover el cursor del ratón usando
teclas mapeadas como `KC_MS_UP`, `KC_MS_DOWN`, etc. La velocidad y
comportamiento de ese movimiento lo controlan 4 parámetros internos del
firmware.

Este módulo **inyecta esos parámetros en tiempo real** vía USB HID raw,
permitiendo ajustar la sensibilidad sin tocar el código C del teclado.

```
┌─────────────────────┐     HID Raw (USB, 33 bytes)     ┌──────────────────────┐
│  Python (este módulo)│ ──────────────────────────────► │  Firmware QMK (Corne)│
│                     │   firma 'M' + 4 parámetros      │  raw_hid_receive()   │
│  qmk_calibracion/   │                                 │  ajusta mouse keys   │
└─────────────────────┘                                 └──────────────────────┘
```

---

## 🎛️ Parámetros

Todos los valores se configuran en `utils/qmk_calibracion/__init__.py`:

```python
HABILITADA      = True   # ← Bandera maestra. False = no se envía nada.

MK_DELAY        = 5      # Retardo inicial antes de empezar a mover (ms)
MK_MAX_SPEED    = 22     # Velocidad máxima estable (1-255)
MK_TIME_TO_MAX  = 10     # Eventos para alcanzar velocidad máxima (1-255)
MK_INTERVAL     = 6      # Intervalo entre eventos de movimiento (ms)
```

### Mapeo en el buffer HID

| Posición Python (`buf`) | Posición QMK (`data`) | Variable | Significado |
|---|---|---|---|
| `buf[1]` | `data[0]` | `'M'` | Firma de comando |
| `buf[2]` | `data[1]` | `MK_DELAY` | Retardo inicial (ms) |
| `buf[3]` | `data[2]` | `MK_MAX_SPEED` | Velocidad máxima |
| `buf[4]` | `data[3]` | `MK_TIME_TO_MAX` | Rampa de aceleración |
| `buf[5]` | `data[4]` | `MK_INTERVAL` | Intervalo entre eventos (ms) |

> **Nota:** `buf[0] = 0x00` es el Report ID que Windows requiere pero que
> el driver HID elimina antes de entregar los datos a QMK. Por eso en el
> firmware `data[0]` = `'M'`, no `0x00`.

---

## 🧪 Guía de ajuste

### ¿Cómo sé qué perilla mover?

| Síntoma | Solución |
|---|---|
| El cursor **no se mueve** al presionar la tecla | ¿Está `HABILITADA = True`? ¿Aparece `✅ CALIBRACIÓN QMK ENVIADA` en el log? |
| Se siente **muy lento** en general | ↑ `MK_MAX_SPEED`, ↓ `MK_INTERVAL` |
| **Arranca muy lento** (tarda en responder) | ↓ `MK_DELAY` |
| Tarda mucho en **alcanzar velocidad punta** | ↓ `MK_TIME_TO_MAX` |
| Se siente **muy brusco / saltarín** | ↓ `MK_MAX_SPEED`, ↑ `MK_INTERVAL`, ↑ `MK_TIME_TO_MAX` |
| Se mueve **a tirones** (no fluido) | ↓ `MK_INTERVAL` (más eventos por segundo) |

### Relación entre parámetros

```
         Velocidad
            ▲
  MK_MAX   ─┼─────────────────────● ● ● ● ●
   _SPEED   │                ╱
            │             ╱
            │          ╱
            │       ╱
            │    ╱
            │ ╱
            └──────────────────────────────► Tiempo (eventos)
            0                    MK_TIME_TO_MAX
            │                    │
            └─ MK_DELAY          └─ Se alcanza velocidad punta

   Cada pulso: MK_INTERVAL ms
```

---

## 🚦 Bandera de activación

```python
# utils/qmk_calibracion/__init__.py — línea 30
HABILITADA = True
```

| Estado | Comportamiento |
|---|---|
| `True` | Al iniciar el script, envía los 4 parámetros al Corne. |
| `False` | No envía nada. Los valores deben estar hardcodeados en `config.h` de QMK. |

### Flujo recomendado

1. **Fase de pruebas:** `HABILITADA = True` → ajustas valores en Python, reinicias el script, pruebas al instante.
2. **Fase final:** copias los 4 valores definitivos a `config.h` del firmware QMK:
   ```c
   #define MOUSEKEY_DELAY       5
   #define MOUSEKEY_MAX_SPEED   22
   #define MOUSEKEY_TIME_TO_MAX 10
   #define MOUSEKEY_INTERVAL    6
   ```
3. **Apagas el módulo:** `HABILITADA = False` → el script ya no depende de este envío.

---

## 📋 Log de ejemplo

```
12:05:23 INFO - ───────────────────────────────────────────────────────
12:05:23 INFO - 📋 CONFIGURACIÓN DEL SISTEMA
12:05:23 INFO - ───────────────────────────────────────────────────────
12:05:23 INFO - ┌─ TECLADO
12:05:23 INFO - │  VID = 0x4653  |  PID = 0x0001
12:05:23 INFO - ├─ QMK MOUSE (→ firmware vía HID raw)  [ACTIVO]
12:05:23 INFO - │  mk_delay       =   5 ms   (retardo inicial)
12:05:23 INFO - │  mk_max_speed   =  22       (velocidad máxima)
12:05:23 INFO - │  mk_time_to_max =  10       (eventos hasta vel. máx.)
12:05:23 INFO - │  mk_interval    =   6 ms   (intervalo entre eventos)
12:05:23 INFO - =======================================================
12:05:23 INFO -   ✅ CALIBRACIÓN QMK ENVIADA AL CORNE
12:05:23 INFO -   mk_delay       = 5 ms
12:05:23 INFO -   mk_max_speed   = 22
12:05:23 INFO -   mk_time_to_max = 10
12:05:23 INFO -   mk_interval    = 6 ms
12:05:23 INFO - =======================================================
```

---

## 🔗 Dependencias

- **Python:** `hid` (para comunicación HID raw con el teclado)
- **Firmware QMK:** El `keymap.c` del Corne debe tener implementado
  `raw_hid_receive()` con el handler para la firma `'M'`.
