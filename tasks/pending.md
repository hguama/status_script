---
cssclasses: no-title
---

# 🚀 status script

> [!focus] **poll-eventos**<span class="sep">│</span><span class="count">0/1 tasks</span><span class="sep">│</span><span class="tasknums"><span class="status-paused">❚❚</span> <span class="num num-paused">16</span></span><span class="sep">│</span><span class="annex">📎 [contrato](attachments/poll-eventos/spec-polls-eventos.md)</span>
> > [!task]+ <span class="status-paused">❚❚</span>**Task 16** · Pasar los polls del script principal a eventos<span class="sep">│</span><span class="risk-high">⬟ high</span><span class="sep">│</span><span class="beat">▰▱▱<span class="beat-hero">▱</span></span><span class="sep">│</span><span class="since" data-since="2026-09-10">0d</span>
> > Pasar los 6 polls permanentes del script principal a eventos, con el modelo de `utils/captura`.
> > Mismo comportamiento, CPU en reposo; excluidos firmware (acotado), captura (ya es eventos) y delays de automatización.
> > - [ ] Ajustar el contrato según los hallazgos de la auditoría (contrato §5)
> > - [ ] Convertir los 6 polls (lector hid, clic-alt, 2× mouse-ui, wrap, scroll-lock) en este repo
> > - [ ] 👤 Contrastar en uso diario (comportamiento idéntico, sin regresiones)
> >
> > > [!desc]- completed (1)
> > > - [x] Auditar polls del script principal: 6 convertibles y 3 excluidos

<!-- queue -->

> [!block]- **wrap-bloqueo**<span class="sep">│</span><span class="count">0/1 tasks</span><span class="sep">│</span><span class="tasknums"><span class="status-untouched">☐</span> <span class="num num-untouched">17</span></span><span class="sep">│</span><span class="annex">📎 [contrato](attachments/wrap-bloqueo/spec-bloqueo-wrap.md)</span>
> > [!task]+ <span class="status-untouched">☐</span>**Task 17** · Bloquear el wrap al seleccionar o capturar<span class="sep">│</span><span class="risk-high">⬟ high</span><span class="sep">│</span><span class="beat">▰▰▱<span class="beat-hero">▱</span></span>
> > El wrap salta aunque se esté seleccionando texto o recortando pantalla.
> > Se bloquea con botón presionado u overlay visible; el wrap libre no cambia.
> > Related to: Task 16 — el predicado debe servir en su hilo único de cursor.
> > - [ ] Implementar `debe_bloquear()` en `wrap_loop` tras la bandera
> > - [ ] 👤 Contrastar en uso diario (selección, captura, wrap normal) y decidir
> >
> > > [!desc]- completed (2)
> > > - [x] Especificar el bloqueo en el contrato (casos, predicado, riesgos) — **Resultado (2026-09-10):** contrato `spec-bloqueo-wrap.md` con 8 casos, diseño del predicado, diagrama y matriz de riesgos
> > > - [x] 👤 Aprobar la especificación y el diagrama — **aprobado por Hero el 2026-09-10**
