# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)

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
