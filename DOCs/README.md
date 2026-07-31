# 🖥️ Cornell Ready — Documentación del Sistema

Sistema de asistencia para teclado **Corne** con firmware **QMK**.  
Provee overlay visual de capas, calibración de mouse keys, wrap-around
de cursor, scroll lock por gesto, y más.

---

## 🗂️ Índice de funcionalidades

| # | Funcionalidad | Archivo fuente | Documentación |
|---|---|---|---|
| 1 | **QMK Calibración** — envía parámetros de mouse keys al firmware | `utils/qmk_calibracion/` | [`qmk_calibracion.md`](qmk_calibracion.md) |
| 2 | **Wrap-around** — cursor salta de borde a borde | `utils/wrap_around/` | [`wrap_around.md`](wrap_around.md) |
| 3 | **Scroll Lock** — convierte movimiento del mouse en scroll | `utils/scroll_lock.py` | *(pendiente)* |
| 4 | **Overlay de capas** — indicador visual de la capa QMK activa | `layer_status_script.py` | *(pendiente)* |
| 5 | **Alt-Tab reset** — detecta Alt-Tab y libera la tecla Alt | `layer_status_script.py` → `detectar_clic_reset_alt()` | *(pendiente)* |
| 6 | **OneNote Nav** — integración con OneNote 2016 | `utils/onenote_nav.py` | *(pendiente)* |

---

## 🧱 Estructura del proyecto

```
status script/
├── layer_status_script.py          ← Script principal
├── close_start_status.bat          ← 🎯 Reinicio completo (mata Python + inicia)
├── Arranque rápido.bat             ← 🚀 Solo inicia (sin matar nada)
├── utils/
│   ├── qmk_calibracion/            ← Calibración QMK (independiente)
│   │   └── __init__.py
│   ├── wrap_around/                ← Wrap-around (independiente)
│   │   └── __init__.py
│   ├── scroll_lock.py              ← Scroll Lock
│   └── onenote_nav.py              ← OneNote 2016
├── DOCs/                           ← 📚 Documentación
│   ├── README.md                   ← Este índice
│   ├── qmk_calibracion.md          ← Doc de calibración QMK
│   └── wrap_around.md              ← Doc de wrap-around
├── f22_debug.log                   ← Log de ejecución
└── ...
```

---

## 🚀 Ejecución

### 🧪 Después de hacer cambios (ciclo de desarrollo)

> **Regla:** cada vez que modifiques el código y quieras probar,
> ejecuta `close_start_status.bat`. Esto mata todas las instancias
> de Python y lanza el script desde cero, garantizando que los
> cambios se apliquen limpiamente.

```bat
close_start_status.bat
```

### 🚀 Arranque rápido (sin necesidad de reiniciar)

Si el script no está corriendo y solo querés iniciarlo:

```bat
Arranque rápido.bat
```

### ⌨️ Desde terminal

```sh
python "layer_status_script.py"
```

---

## ⚙️ Configuración rápida

| Qué modificar | Dónde |
|---|---|
| Velocidad del mouse con teclado | `utils/qmk_calibracion/__init__.py` → `MK_MAX_SPEED`, etc. |
| Activar/desactivar envío a QMK | `utils/qmk_calibracion/__init__.py` → `HABILITADA` |
| Wrap-around (márgenes, delay) | `utils/wrap_around/__init__.py` → `MARGEN_PORCENTAJE`, `DELAY_MS`, `COOLDOWN` |
| Radio para ocultar overlay | `layer_status_script.py` → `RADIO_OCULTAR` |

---

## 📊 Módulos independientes

| Módulo | Extraído | Bandera | Doc |
|---|---|---|---|
| QMK Calibración | ✅ | `HABILITADA` | [`qmk_calibracion.md`](qmk_calibracion.md) |
| WRAP-AROUND | ✅ | `HABILITADA` | [`wrap_around.md`](wrap_around.md) |
| Scroll Lock | ❌ | — | *(pendiente)* |
| OneNote Nav | ❌ | — | *(pendiente)* |
| Overlay capas | ❌ | — | *(pendiente)* |
| Alt-Tab reset | ❌ | — | *(pendiente)* |
