#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
odoo_sync.py — CLI de la skill «odoo-gestor» (Open Code ↔ Odoo).

Único punto de entrada a Odoo para la IA.
Principio: la IA decide y redacta; este script ejecuta, valida y registra.

Salida       : JSON por stdout, siempre parseable.
Exit codes   : 0 = OK · 1 = error · 2 = dry-run correcto (pendiente --confirm).
Escrituras   : solo whitelist de campos y en dos fases (dry-run → --confirm).
Credenciales : .ia/.env o variables de entorno (nunca versionadas).
Dependencias : únicamente la librería estándar de Python.
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

# ------------------------------------------------------------------ constantes

CREDENCIALES = ("ODOO_URL", "ODOO_DB", "ODOO_USER", "ODOO_API_KEY")

ESTADOS = {  # alias amigable → valor del campo state (Odoo 16+)
    "en-progreso": "01_in_progress",
    "espera": "02_waiting_normal",
    "cambios": "02_changes_requested",
    "aprobado": "03_approved",
    "hecho": "1_done",
    "cancelado": "1_canceled",
}

EDITABLES = ("name", "description", "date_deadline", "planned_hours")

LECTURA_CRUDA = ("search_read", "read", "fields_get", "search_count")

TIPOS_VALIDOS = ("FEAT", "FIX", "REF", "DOC", "OPS", "SEC", "TST", "CHK")

PATRON_ENTRADA = re.compile(
    r"^##\s*(?P<fecha>\S+)\s*\|\s*(?P<tipo>[A-Za-z]+)\s*\|\s*(?P<ref>.*?)\s*\|\s*"
    r"estimado_h:(?P<est>[\d.]+)\s*\|\s*real_h:(?P<real>[\d.]+)"
    r"(?:\s*\|\s*invertido_h:(?P<inv>[\d.]+))?"
    r"(?:\s*\|\s*archivos:(?P<arch>\d+))?"
    r"(?:\s*\|\s*lineas:(?P<lin>\d+))?"
    r"(?:\s*\|\s*interrupciones:(?P<int>\w+))?\s*$"
)

# ------------------------------------------------------------------ utilidades

def ok(data, codigo=0):
    print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
    sys.exit(codigo)


def error(mensaje, detalle=None):
    print(json.dumps({"ok": False, "error": mensaje, "detalle": detalle or ""},
                     ensure_ascii=False))
    sys.exit(1)


def dry_run(propuesta):
    print(json.dumps({"ok": True, "dry_run": True, "propuesta": propuesta,
                      "siguiente_paso": "Repite el comando con --confirm para aplicar"},
                     ensure_ascii=False))
    sys.exit(2)


def raiz_repo():
    p = Path.cwd()
    for carpeta in (p, *p.parents):
        if (carpeta / ".ia").is_dir():
            return carpeta
    error("No se encontró carpeta .ia/ desde el directorio actual. "
          "Ejecuta el script dentro del repo del proyecto.")


def carpeta_ia():
    return raiz_repo() / ".ia"


def cargar_credenciales():
    cred = {}
    fenv = carpeta_ia() / ".env"
    if fenv.exists():
        for linea in fenv.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                cred[clave.strip()] = valor.strip()
    for clave in CREDENCIALES:            # el entorno tiene prioridad sobre .env
        if os.environ.get(clave):
            cred[clave] = os.environ[clave]
    faltan = [c for c in CREDENCIALES if not cred.get(c)]
    if faltan:
        error("Faltan credenciales: " + ", ".join(faltan) + " (define ODOO_URL, "
              "ODOO_DB, ODOO_USER y ODOO_API_KEY en .ia/.env o el entorno)")
    return cred


def registrar_actividad(comando, detalle):
    with (carpeta_ia() / "actividad.log").open("a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='seconds')} | "
                f"{comando} | {detalle} | APLICADO\n")


def texto_o_archivo(valor):
    """Texto directo o '@archivo.md' para textos largos (evita escaping de bash)."""
    if valor and valor.startswith("@"):
        ruta = Path(valor[1:])
        if not ruta.exists():
            error(f"Archivo no encontrado: {ruta}")
        return ruta.read_text(encoding="utf-8").strip()
    return valor


if __name__ == "__main__":
    # Fase 2: aún sin parser de comandos. El contrato JSON y los exit codes
    # ya están en ok()/error()/dry_run(); los comandos llegan en F3+.
    error("odoo_sync aún no implementa comandos (Fase 2 en curso). "
          "Los comandos (now, doctor, tarea, ...) se añaden en F3 en adelante.")