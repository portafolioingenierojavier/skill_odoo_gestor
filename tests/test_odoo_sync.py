# tests/test_odoo_sync.py — Nivel 1: sin conexión a Odoo
"""Batería unitaria acumulada de odoo_sync.py.

Fase 2: utilidades locales (constantes, ok/error/dry_run, raiz_repo,
cargar_credenciales, texto_o_archivo, registrar_actividad).
Fase 3+: now, doctor y calibración se añaden en sus fases.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parent / "odoo_sync.py"


def correr(args, cwd):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, cwd=cwd)


def correr_codigo(codigo, cwd):
    """Ejecuta un snippet de python que importa odoo_sync y lo usa."""
    snippet = (f"import sys, json; sys.path.insert(0, {str(SCRIPT.parent)!r}); "
               f"import odoo_sync; {codigo}")
    return subprocess.run([sys.executable, "-c", snippet],
                          capture_output=True, text=True, cwd=cwd)


def cargar_modulo():
    spec = importlib.util.spec_from_file_location("odoo_sync", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def repo_temporal():
    """Crea un repo temporal con .ia/."""
    tmp = tempfile.TemporaryDirectory()
    repo = Path(tmp.name)
    (repo / ".ia").mkdir()
    return tmp, repo


class TestConstantes(unittest.TestCase):
    """F2-T1: constantes del módulo."""

    def test_constantes_obligatorias(self):
        mod = cargar_modulo()
        self.assertEqual(sorted(mod.CREDENCIALES),
                         ["ODOO_API_KEY", "ODOO_DB", "ODOO_URL", "ODOO_USER"])
        self.assertIn("en-progreso", mod.ESTADOS)
        self.assertIn("hecho", mod.ESTADOS)
        self.assertIn("name", mod.EDITABLES)
        self.assertNotIn("project_id", mod.EDITABLES)
        self.assertIn("search_read", mod.LECTURA_CRUDA)
        self.assertNotIn("create", mod.LECTURA_CRUDA)
        self.assertIn("FEAT", mod.TIPOS_VALIDOS)


class TestSalida(unittest.TestCase):
    """F2-T2: ok(), error(), dry_run() — exit codes 0/1/2 y JSON."""

    def test_ok_exit0_y_json(self):
        r = correr_codigo("odoo_sync.ok({'clave': 'valor'})", tempfile.gettempdir())
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["clave"], "valor")

    def test_error_exit1_y_json(self):
        r = correr_codigo("odoo_sync.error('mensaje claro', 'detalle')",
                          tempfile.gettempdir())
        self.assertEqual(r.returncode, 1)
        data = json.loads(r.stdout)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"], "mensaje claro")
        self.assertEqual(data["detalle"], "detalle")

    def test_dry_run_exit2_y_json(self):
        r = correr_codigo("odoo_sync.dry_run({'accion': 'crear tarea'})",
                          tempfile.gettempdir())
        self.assertEqual(r.returncode, 2)
        data = json.loads(r.stdout)
        self.assertTrue(data["dry_run"])
        self.assertEqual(data["propuesta"]["accion"], "crear tarea")
        self.assertIn("--confirm", data["siguiente_paso"])


class TestRaizRepo(unittest.TestCase):
    """F2-T3: raiz_repo() / carpeta_ia()."""

    def test_sin_ia_error_limpio(self):
        mod = cargar_modulo()
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                with self.assertRaises(SystemExit) as ctx:
                    mod.raiz_repo()
                self.assertEqual(ctx.exception.code, 1)
            finally:
                os.chdir(cwd)

    def test_detecta_carpeta_ia_en_ancestro(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        subdir = repo / "sub" / "nivel"
        subdir.mkdir(parents=True)
        cwd = os.getcwd()
        try:
            os.chdir(subdir)
            self.assertEqual(mod.raiz_repo(), repo)
            self.assertEqual(mod.carpeta_ia(), repo / ".ia")
        finally:
            os.chdir(cwd)


class TestCredenciales(unittest.TestCase):
    """F2-T4: cargar_credenciales()."""

    VALORES = {"ODOO_URL": "http://qa:8069", "ODOO_DB": "qa_skill",
               "ODOO_USER": "ia.sync", "ODOO_API_KEY": "clave-dummy"}

    def setUp(self):
        self._guardadas = {}
        for k in self.VALORES:
            self._guardadas[k] = os.environ.get(k)
        for k in self.VALORES:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._guardadas.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _env_dummy(self, repo):
        (repo / ".ia" / ".env").write_text(
            "\n".join(f"{k}={v}" for k, v in self.VALORES.items()) + "\n",
            encoding="utf-8")

    def test_parsea_env(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        self._env_dummy(repo)
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            self.assertEqual(mod.cargar_credenciales(), self.VALORES)
        finally:
            os.chdir(cwd)

    def test_faltantes_error_lista_variables(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        (repo / ".ia" / ".env").write_text("# comentario\nODOO_URL=http://qa:8069\n",
                                           encoding="utf-8")
        captured = {}
        original = mod.error
        def fake_error(mensaje, detalle=""):
            captured["mensaje"] = mensaje
            raise SystemExit(1)
        mod.error = fake_error
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            with self.assertRaises(SystemExit):
                mod.cargar_credenciales()
        finally:
            mod.error = original
            os.chdir(cwd)
        for k in self.VALORES:
            self.assertIn(k, captured["mensaje"])

    def test_env_prioridad_sobre_entorno(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        self._env_dummy(repo)
        os.environ["ODOO_USER"] = "otro.usuario"
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            cred = mod.cargar_credenciales()
            self.assertEqual(cred["ODOO_USER"], "otro.usuario")
            self.assertEqual(cred["ODOO_URL"], self.VALORES["ODOO_URL"])
        finally:
            os.chdir(cwd)


class TestTextoOArchivo(unittest.TestCase):
    """F2-T5: texto_o_archivo()."""

    def test_texto_directo(self):
        mod = cargar_modulo()
        self.assertEqual(mod.texto_o_archivo("hola"), "hola")

    def test_archivo_existente_via_arroba_y_strip(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        f = repo / "notas.md"
        f.write_text("  línea con acentos y ñ  ", encoding="utf-8")
        self.assertEqual(mod.texto_o_archivo(f"@{f}"), "línea con acentos y ñ")

    def test_archivo_inexistente_error(self):
        mod = cargar_modulo()
        captured = {}
        original = mod.error
        def fake_error(mensaje, detalle=""):
            captured["mensaje"] = mensaje
            raise SystemExit(1)
        mod.error = fake_error
        try:
            with self.assertRaises(SystemExit):
                mod.texto_o_archivo("@no-existe.md")
        finally:
            mod.error = original
        self.assertIn("no-existe.md", captured["mensaje"])


class TestRegistrarActividad(unittest.TestCase):
    """F2-T6: registrar_actividad()."""

    def test_formato_append_y_utf8(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            mod.registrar_actividad("tarea crear", "#10 «Prueba ñ»")
            mod.registrar_actividad("chatter post", "#10 (25 caracteres)")
            lineas = (repo / ".ia" / "actividad.log").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lineas), 2)
            for linea in lineas:
                partes = linea.split(" | ")
                self.assertEqual(len(partes), 4)
                datetime.fromisoformat(partes[0])   # falla si no es ISO
                self.assertEqual(partes[3], "APLICADO")
            self.assertIn("Prueba ñ", lineas[0])
            self.assertIn("#10 (25 caracteres)", lineas[1])
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()