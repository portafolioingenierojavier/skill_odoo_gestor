# Entorno QA-SKILL (Docker)

Entorno de pruebas aislado para validar la skill `odoo-gestor` sin tocar proyectos reales.

## Uso

```bash
cd docker/qa
docker compose up -d
```

- Odoo 18: http://localhost:8069
- PostgreSQL 16: localhost:5432

## Configuración inicial

```bash
export ODOO_URL="http://localhost:8069"
export ODOO_DB="qa_skill"
export ODOO_ADMIN_LOGIN="admin"
export ODOO_ADMIN_PASSWORD="admin_qa_2026"
export ODOO_IA_LOGIN="ia.sync"
export ODOO_IA_PASSWORD="ia_sync_qa_2026"

python setup.py            # crea DB, usuario IA Sync, proyecto QA-SKILL, etapas y tareas
python setup.py --api-key  # genera la API key "opencode" para IA Sync
```

## Credenciales por defecto (SOLO QA LOCAL — no válidas en producción)

| Recurso | Valor |
|---|---|
| DB master password | `admin_master_qa` |
| Admin Odoo | `admin` / `admin_qa_2026` |
| IA Sync | `ia.sync` / `ia_sync_qa_2026` |
| API key IA Sync | (se muestra al ejecutar `setup.py --api-key`) |
| Proyecto | QA-SKILL (id 7) |

> Las credenciales de este entorno son ficticias y de ámbito local. Nunca reutilizarlas fuera de QA.

## Notas

- El proyecto QA-SKILL se crea con las etapas estándar:
  `Backlog · Especificaciones · En desarrollo · En pruebas · Revisión · Entregado (fold) · Cancelado (fold)`
- `hr_timesheet` se instala automáticamente y se crea el empleado IA Sync.
- Los volúmenes `qa_skill_pgdata` y `qa_skill_odoo_data` persisten la base de datos y el filestore.