# tests/INTEGRACION.md — Plan de validación de 3 niveles

Batería oficial contra QA-SKILL (ARQUITECTURA §7). Cada ejecución registra su
fecha y resultados en la tabla de la sección correspondiente. **Nunca** validar
escrituras contra el proyecto real.

## Nivel 0 — Entorno (pre-requisitos)

| # | Comprobación | Comando | Resultado esperado | F10 (2026-09-10) |
|---|---|---|---|---|
| 0.1 | Contenedor Odoo arriba | `docker ps` | Contenedor odoo en `Up` | ✅ `odoo:18` Up |
| 0.2 | HTTP responde | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8069/web/database/selector` | `200` | ✅ 200 |
| 0.3 | Usuario IA Sync existe | UI Odoo → Usuarios | Usuario interno, grupo Proyecto | ✅ uid=8 login `ia.sync` |
| 0.4 | API key creada | Preferencias → Claves API | Clave «opencode» | ✅ doctor autentica |
| 0.5 | Zona horaria correcta | Formulario del usuario | Igual que la tuya | ✅ `America/Guayaquil` |
| 0.6 | Proyecto QA-SKILL | Proyectos | Existe, con etapas estándar | ✅ id=7, 7 etapas |

## Nivel 1 — Unitarios (sin Odoo)

Ejecutar: `python -m unittest tests/test_odoo_sync.py -v`

| # | Caso | Criterio PASS | F10 (2026-09-10) |
|---|---|---|---|
| 1.1 | `now` | exit 0, JSON `ok:true`, `ahora` ISO válido | ✅ |
| 1.2 | Sin `.ia/` | exit 1, error JSON que menciona `.ia` (sin traceback) | ✅ |
| 1.3 | `calibracion stats` sin histórico | exit 0, `tareas:0`, `ratio_global:null` | ✅ |
| 1.4 | registrar + stats | ratio = real/estimado exacto | ✅ |
| 1.5 | Patrón de entrada | Parsea fecha, tipo, ref y todos los opcionales | ✅ |
| 1.6 | Saneado de nombre | `"Claude Sonnet 4.5!"` → `claude-sonnet-4.5.md` | ✅ |

**Resultado F10:** 50/50 en verde · 0 skips.

## Nivel 2 — Integración (contra QA-SKILL, conexión real)

| # | Comando | Salida esperada | Verificación posterior | F10 (2026-09-10) |
|---|---|---|---|---|
| 2.1 | `now` | exit 0 | Coincide con `date` ±1 min | ✅ |
| 2.2 | `doctor --proyecto 7` | exit 0; version/uid/campos/modo_horas/etapas | config.json creado desde cero y coherente | ✅ `18.0-20260619`, uid 8, timesheet |
| 2.3 | `doctor` con API key inválida | exit 1 «Autenticación fallida» | Mensaje limpio, sin traceback | ✅ |
| 2.4 | `proyecto info` | exit 0; etapas con IDs | Coincide con el kanban en Odoo | ✅ 7 etapas |
| 2.5 | `tarea list` | exit 0; array de tareas QA | Mismas que la vista kanban | ✅ 4 tareas (60–57) |
| 2.6 | `tarea crear "[TST] Prueba de humo"` sin confirm | exit 2, `dry_run:true` | En Odoo NO existe la tarea | ✅ exit 2 |
| 2.7 | ídem con `--confirm` | exit 0, `id` devuelto | Tarea en 1ª etapa; línea en `actividad.log` | ✅ id=61, Backlog, log |
| 2.8 | `tarea etapa 61 "En pruebas"` sin confirm | exit 2 | `tarea get`: etapa sin cambio | ✅ |
| 2.9 | ídem con `--confirm` | exit 0 | Etapa cambiada; línea en log | ✅ stage 30 |
| 2.10 | `tarea etapa 61 "NoExiste"` | exit 1 con lista de válidas | Sin cambio | ✅ |
| 2.11 | `tarea estado 61 --estado espera` (dry→confirm) | exit 2 → 0 | Tarea muestra «En espera» | ✅ `04_waiting_normal` |
| 2.12 | `chatter post 61 --desde-archivo resumen.md` sin confirm | exit 2, `vista_previa` ≤300 chars | Sin mensaje en Odoo | ✅ 143 chars, exit 2 |
| 2.13 | ídem con `--confirm` | exit 0 | Mensaje visible, texto íntegro | ✅ msg #314 |
| 2.14 | `horas registrar 61 --horas 1.5` | timesheet: exit 0 → hoja de horas | Coherente con `mode.timesheet` | ✅ empleado #21, 1.5h |
| 2.15 | `ticket vincular 61 --ticket 1` | exit 1 con instrucción si no hay campo | Error claro | ✅ (helpdesk no instalable en CE) |
| 2.16 | `raw --modelo project.task` | exit 0, registros | Datos correctos | ✅ 10 registros correctos |
| 2.17 | `raw --metodo create ...` | exit 1 «solo lectura» | Ninguna escritura ocurrió | ✅ total 38 (sin alta) |
| 2.18 | `calibracion registrar` + `stats` | exit 0 | `tareas:1`, ratio correcto | ✅ tareas 1, ratio 1.0 |

**Resultado F10:** 18/18 en verde — ejecutado con `.ia/` recreado desde cero
(config, calibración y log borrados; `.env` conservado) y config regenerado
con `doctor --proyecto 7`.

## Nivel 3 — Comportamiento de la IA (Fase 11)

Pendiente — se ejecuta sobre `qa-dummy/` con `.ia/` apuntando a QA-SKILL.
Escenarios 3.1–3.10 en ARQUITECTURA §7.4.