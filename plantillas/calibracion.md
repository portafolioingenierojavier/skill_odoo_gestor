# Calibración de tiempos — <modelo>
# Ratios: odoo_sync.py calibracion stats --modelo <modelo>
# Formato de entrada (una por tarea, la escribe `calibracion registrar`):
# ## <fecha> | <tipo> | <ref> | estimado_h:X | real_h:X | invertido_h:X | archivos:N | lineas:N | interrupciones:si|no
# Ejemplo real (debe parsear con PATRON_ENTRADA):
# ## 2026-09-10T09:00 | FEAT | SKILL-T9 | estimado_h:2 | real_h:1.5 | interrupciones:si
