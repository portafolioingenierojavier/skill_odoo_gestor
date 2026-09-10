# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)

## [1.0.0-rc2] — 2026-09-10

### Añadido
- **Fase 11 completa — Nivel 3 (G11 en verde)**: validación del comportamiento
  de la IA con la skill cargada, sobre el repo dummy `qa-dummy/` (proyecto QA
  #8 «-=QA=- Recursos Humanos») con la misión ficticia «módulo RRHH
  `hr_custom`».
- Batería N3 documentada en `tests/INTEGRACION.md`: 3.1–3.10 con prompt,
  respuesta real y veredicto (9/10 🟢 directos, 3.10 🔴 corregido).
- Hallazgo del ensayo: la IA afirmó un bloqueo ambiental («IA Sync sin empleado
  vinculado») sin ejecutar el comando. Corrección: horas de las 6 tareas
  registradas (timesheets 348–353) y regla nueva en `SKILL.md` § Manejo de
  fallos («no des por hecho un bloqueo del entorno: ejecuta el comando en
  dry-run y muestra la salida real»), sincronizada a ARQUITECTURA §4.1.
- El ensayo generó además 6 tareas Odoo reales en QA (62–67, de vuelta a
  Revisión) y un mini-módulo `hr_custom` (~580 líneas) fuera del repo de
  desarrollo.

## [1.0.0-rc1] — 2026-09-10

### Cambiado
- **Fase 10 completa — DoD Nivel 2** (G10 en verde): la skill es técnicamente
  confiable.
- `instalar.sh` para instalar la skill global vía symlink (en Windows se crea
  un junction, equivalente transparente) con verificación del target.
- Batería completa en verde con entorno recreado **desde cero**: N0 6/6 ·
  N1 50/50 (0 skips) · N2 2.1–2.18 (18/18) contra QA-SKILL.
- `tests/INTEGRACION.md` creado con las 3 tablas de validación y resultados de
  la regresión F10.

## [0.7.0] — 2026-09-10

### Añadido
- **Fase 9 — `SKILL.md` y plantillas** (G9 en verde).
- `SKILL.md` completo (reglas duras 1–7, arranque 1–5, ciclo de tarea,
  protocolo de tiempo, escrituras, chatter, nombres, fallos, modelo) con
  índice de los 15 comandos.
- `plantillas/FOCO.md` y `plantillas/calibracion.md` per ARQUITECTURA
  §4.3–§4.4; la plantilla de calibración ahora incluye un ejemplo real que
  parsea con `PATRON_ENTRADA`.
- 4 tests nuevos de coherencia plantilla↔SKILL.md (N1: 50/50).

### Corregido
- Duplicado de `PATRON_ENTRADA` en `odoo_sync.py` (el segundo sombreaba al
  primero; sin cambio de comportamiento).

## [0.6.0] — 2026-09-10

### Añadido
- **Fase 8 — `raw` + auditoría de seguridad** (G8 en verde, gate de bloqueo).
- `raw` (SÓLO lectura): `search_read` por defecto + `read`/`fields_get`/
  `search_count`; `--metodo create` → exit 1 sin contacto de escritura
  (N2 2.16/2.17 ✅); dominio JSON inválido e `--ids` no numérico → error limpio.
- Auditoría 5/5: sin secretos en `*.py`, en `actividad.log` ni en
  `git log -p`; 0 `.env` versionados; `raw` sin escritura y `xmlrpc` solo en
  la clase `Odoo`.

## [0.5.0] — 2026-09-10

### Añadido
- **Fase 7 — Calibración** (G7 en verde, TDD estricto 100% local, sin Odoo).
- `calibracion registrar`: crea cabecera, append de entrada con formato §4.4,
  `--notas @archivo`, `--interrupciones`, campos opcionales `--invertido`,
  `--archivos`, `--lineas`.
- `calibracion stats`: `tareas`, `ratio_global`, `por_tipo` (ratio + conteo
  para «≥3» de §6.4) y avisos («sin histórico» / «histórico corto <5»).
- `PATRON_ENTRADA` (regex) y `archivo_calibracion(modelo)` (`Claude Sonnet 4.5!`
  → `claude-sonnet-4.5.md`).
- 16 tests N1 de calibración (TDD: rojos primero → verdes).

### Corregido
- Harness de tests `correr()` decodifica en UTF-8 (el script emite UTF-8 desde
  0.4.0); antes los avisos acentuados salían mojibake.

## [0.4.0] — 2026-09-10

### Añadido
- **Fase 6 — Chatter, horas y tickets** (G6 en verde).
- `chatter post ID --desde-archivo F.md | --mensaje TEXTO`: dry-run muestra
  `vista_previa`; confirm publica en el chatter y loguea (N2 2.12/2.13 ✅).
- `horas registrar ID --horas X --nota`: crea línea de timesheet
  (`account.analytic.line`) con validación de empleado y modo; modulo
  `hr_timesheet` detectado en G3 ✅ (N2 2.14).
- `ticket vincular ID --ticket N [--campo]`: dry-run/confirm; error detallado
  y accionable si no hay campo (N2 2.15). Detección de `doctor` ampliada a
  `ticket`/`helpdesk`/`issue`.

### Corregido
- `chatter post --desde-archivo` lee el archivo vía `texto_o_archivo("@"+ruta)`;
  antes publicaba la ruta literal.
- `-h`/ayuda de argparse: crasheaba con `UnicodeEncodeError` en consolas cp1252;
  ahora stdout/stderr se reconfiguran a UTF-8 al arrancar.

## [0.3.0] — 2026-09-10

### Añadido
- **Fase 5 — Escrituras seguras** (G5 en verde): mecanismo dry-run (exit 2) →
  `--confirm` (exit 0) → línea en `actividad.log`, verificado para los 4 comandos.
- `tarea crear` (`--nombre --descripcion --etapa --confirm`): crea en la 1ª
  etapa por defecto; advertencia si el nombre no sigue la convención `[TIPO]` (N2 2.6/2.7 ✅).
- `tarea editar --set CAMPO=VALOR` (múltiples, whitelist `EDITABLES`): dry-run
  muestra `de → a`; confirm aplica y loguea (N2 editar name ✅).
- `tarea etapa --etapa <nombre>`: dry-run/confirm + error con lista de etapas
  válidas (N2 2.8/2.9/2.10 ✅).
- `tarea estado --estado <alias>`: dry-run/confirm; fallback claro si la
  instancia no expone `state` (N2 2.11 ✅).
- Funciones puras `validar_convencion()` y `parsear_set()` (+ 7 tests N1).

### Corregido
- `ejec()` pasa los args tal cual: `read`/`fields_get`/`search_read` usan
  keywords explícitas y `write` conserva el dict de valores posicional
  (o rompía con `ProjectTask.write() got an unexpected keyword argument`).
- `ESTADOS` alineado con la selección real de la instancia Odoo 18
  (`espera`→`04_waiting_normal`, `hecho`→`1_done`, ...); config regenerado.

## [0.2.0] — 2026-09-09

### Añadido
- `proyecto info`: datos del proyecto + etapas con IDs (N2 2.4 ✅).
- `tarea get`: campos según config + `chatter_reciente`; inexistente → exit 1 limpio.
- `tarea list` con filtros `--etapa`, `--estado`, `--limite` (N2 2.5 ✅).
- `coincidir_etapa()` extraída como función pura; `id_de_etapa()` con error que lista las válidas.
- Tests N1 de `coincidir_etapa`/`id_de_etapa`/`campos_tarea`.

## [0.1.0] — 2026-09-09

### Añadido
- Clase `Odoo`: conexión XML-RPC (`version`, `authenticate`), `ejec` con manejo
  centralizado de `Fault`, `buscar` (lecturas).
- Comando `now`: reloj exacto (ISO, `zona_horaria`, `epoch`).
- Comando `doctor --proyecto <ID>`: diagnóstico de campos, módulo `hr_timesheet`,
  usuario, proyectos, etapas; escribe `.ia/config.json`.
- Config de QA generado por `doctor` y versionado (`.ia/config.json`).
- Tests N1 de `now` y de la estructura del config.

## [0.0.0] — 2026-09-09

### Añadido
- Documentación base: ARQUITECTURA.md, PAUTAS.md, ROADMAP.md
- Plantillas: FOCO.md, calibracion.md
- Estructura del repo según PAUTAS §5
- Entorno QA Docker: composición Odoo 18 + PostgreSQL 16 + bootstrap `docker/qa/setup.py`
- Fase 0 completada: usuario IA Sync, API key, proyecto QA-SKILL, etapas y tareas de prueba
