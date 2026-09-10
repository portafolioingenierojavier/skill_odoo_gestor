# odoo-gestor

Skill para IAs de desarrollo: gestiona proyectos Odoo 18 como project manager — tareas, etapas, chatter, horas y calibración de tiempos vía CLI determinista.

## Arquitectura

```
Usuario ⇄ Open Code (IA + skill odoo-gestor) ⇄ odoo_sync.py ⇄ XML-RPC ⇄ Odoo (Docker)
                        ⇅ archivos locales (.ia/)
```

## Estructura

```
├── SKILL.md                     ← reglas y protocolos que lee la IA
├── odoo_sync.py                 ← CLI puente a Odoo
├── plantillas/
│   ├── FOCO.md                  ← plantilla del foco por repo
│   └── calibracion.md           ← cabecera del archivo de calibración
├── tests/
│   ├── test_odoo_sync.py        ← unitarios (sin Odoo)
│   └── INTEGRACION.md           ← checklist de integración
├── docs/
│   ├── ARQUITECTURA.md          ← especificación completa
│   ├── PAUTAS.md                ← reglas de desarrollo
│   └── ROADMAP.md               ← plan de desarrollo por fases
├── CHANGELOG.md
└── instalar.sh
```

## Instalación

```bash
# Clonar y ejecutar instalador (crea symlink en ~/.config/opencode/skill/)
git clone https://github.com/portafolioingenierojavier/skill_odoo_gestor.git
cd skill_odoo_gestor
bash instalar.sh
```

## Requisitos

- Python 3.8+ (solo librería estándar)
- Odoo 18 (Docker o local)
- PostgreSQL

## Documentación

- [ARQUITECTURA.md](docs/ARQUITECTURA.md) — qué se construye
- [PAUTAS.md](docs/PAUTAS.md) — cómo se construye
- [ROADMAP.md](docs/ROADMAP.md) — en qué orden y con qué pruebas

## Licencia

MIT
