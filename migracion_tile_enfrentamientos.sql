-- =====================================================================
-- Agrega el toggle del tile "Enfrentamientos" en Inicio.
--
-- Cada tile de Inicio se puede ocultar desde Configuración, y cada uno
-- es una columna mostrar_tile_* en configuracion_general. El tile nuevo
-- sigue el mismo patrón que los otros cuatro.
--
-- DEFAULT TRUE: la fila que ya existe (id = 1) queda con el tile
-- visible sin tener que hacer un UPDATE aparte.
--
-- Hay que correrlo ANTES de desplegar el código nuevo: el backend pide
-- esta columna en cada lectura de la configuración general, y sin ella
-- la consulta falla (y con ella, Inicio).
--
-- ANTES DE CORRER ESTO: sacá un backup.
--   mysqldump --host=... --port=... --user=avnadmin --password \
--             --single-transaction defaultdb > backup_antes_tile_enfrentamientos.sql
-- =====================================================================

ALTER TABLE configuracion_general
    ADD COLUMN mostrar_tile_enfrentamientos BOOLEAN NOT NULL DEFAULT TRUE
    AFTER mostrar_tile_peleadores;
