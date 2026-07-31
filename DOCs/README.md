# 🖥️ Cornell Ready — Documentación del Sistema

Sistema de asistencia para teclado **Corne** con firmware **QMK**.  
Provee overlay visual de capas, calibración de mouse keys, wrap-around
de cursor, scroll lock por gesto, y más.

---

## 🗂️ Índice de funcionalidades

| # | Funcionalidad | Archivo fuente | Documentación |
|---|---|---|---|
| 1 | **QMK Calibración** — envía parámetros de mouse keys al firmware | `utils/qmk_calibracion/` | [`qmk_calibracion.md`](qmk_calibracion.md) |
| 2 | **Wrap-around** — cursor salta de borde a borde | `layer_status_script.py` → `wrap_loop()` | [`wrap_around.md`](wrap_around.md) |
| 3 | **Scroll Lock** — convierte movimiento del mouse en scroll | `utils/scroll_lock.py` | *(pendiente)* |
| 4 | **Overlay de capas** — indicador visual de la capa QMK activa | `layer_status_script.py` | *(pendiente)* |
| 5 | **Alt-Tab reset** — detecta Alt-Tab y libera la tecla Alt | `layer_status_script.py` → `detectar_clic_reset_alt()` | *(pendiente)* |
| 6 | **OneNote Nav** — integración con OneNote 2016 | `utils/onenote_nav.py` | *(pendiente)* |

---

## 🧱 Estructura del proyecto

```
status script/
├── layer_status_script.py          ← Script principal
├── launcher.py                     ← Launcher (atalho)
├── utils/
│   ├── qmk_calibracion/            ← Calibración QMK (independiente)
│   │   └── __init__.py
│   ├── scroll_lock.py              ← Scroll Lock
│   └── onenote_nav.py              ← OneNote 2016
├── DOCs/                           ← 📚 Documentación
│   ├── README.md                   ← Este índice
│   └── qmk_calibracion.md          ← Doc de calibración QMK
├── f22_debug.log                   ← Log de ejecución
└── ...
```

---

## 🚀 Ejecución

```sh
python "layer_status_script.py"
```

O mediante el archivo `.bat`:

```bat
script.bat
```

---

## ⚙️ Configuración rápida

| Qué modificar | Dónde |
|---|---|
| Velocidad del mouse con teclado | `utils/qmk_calibracion/__init__.py` → `MK_MAX_SPEED`, etc. |
| Activar/desactivar envío a QMK | `utils/qmk_calibracion/__init__.py` → `HABILITADA` |
| Wrap-around (márgenes, delay) | `layer_status_script.py` → `WRAP_*` (línea ~55) |
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
