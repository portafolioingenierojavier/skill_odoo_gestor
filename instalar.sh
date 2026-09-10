#!/usr/bin/env bash
# F10-T1 — Instala odoo-gestor como skill global de Open Code vía symlink.
# Uso: bash instalar.sh
# Crea: ~/.config/opencode/skill/odoo-gestor -> <este repo>
set -euo pipefail

ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINO="${HOME}/.config/opencode/skill/odoo-gestor"

if [ ! -f "${ORIGEN}/SKILL.md" ]; then
  echo "error: no hay SKILL.md en ${ORIGEN}" >&2
  exit 1
fi

mkdir -p "$(dirname "${DESTINO}")"

if [ -L "${DESTINO}" ] || [ -e "${DESTINO}" ]; then
  echo "Ya existe ${DESTINO}:"
  ls -ld "${DESTINO}"
else
  ln -s "${ORIGEN}" "${DESTINO}"
fi

if [ -f "${DESTINO}/SKILL.md" ]; then
  echo "OK: la skill odoo-gestor queda disponible en ${DESTINO}"
  echo "Valida en la proxima sesion que aparece en la lista de skills."
else
  echo "error: el enlace no resuelve a SKILL.md" >&2
  exit 1
fi