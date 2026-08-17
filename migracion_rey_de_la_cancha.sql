-- =====================================================================
-- Renombra el valor 'cinco_vidas' a 'rey_de_la_cancha' en la base.
--
-- El formato siempre se llamó "rey de la cancha"; 'cinco_vidas' quedó del
-- nombre con el que se lo pensó al principio. Esto alinea la base con el
-- nombre real, para que dentro de unos meses el identificador no diga una
-- cosa distinta de lo que se ve en pantalla.
--
-- IMPORTANTE: se hace en TRES pasos por tabla, y el orden no es opcional.
-- Un ENUM solo acepta los valores que declara, así que:
--   1. Se AMPLÍA el ENUM para que acepte los dos nombres a la vez.
--   2. Se migran los datos existentes al nombre nuevo.
--   3. Se RESTRINGE el ENUM al nombre nuevo, sacando el viejo.
-- Si se intentara cambiar el ENUM y los datos de una sola vez, MySQL
-- rechazaría las filas que todavía tienen el valor viejo.
--
-- ANTES DE CORRER ESTO: sacá un backup.
--   mysqldump --host=... --port=... --user=avnadmin --password \
--             --single-transaction defaultdb > backup_antes_renombre.sql
-- =====================================================================

-- ---------- torneo.modo ----------
ALTER TABLE torneo MODIFY COLUMN modo
    ENUM('todos_contra_todos', 'grupos_eliminacion', 'cinco_vidas', 'rey_de_la_cancha') NOT NULL;

UPDATE torneo SET modo = 'rey_de_la_cancha' WHERE modo = 'cinco_vidas';

ALTER TABLE torneo MODIFY COLUMN modo
    ENUM('todos_contra_todos', 'grupos_eliminacion', 'rey_de_la_cancha') NOT NULL;


-- ---------- torneo.formato_grupos ----------
ALTER TABLE torneo MODIFY COLUMN formato_grupos
    ENUM('todos_contra_todos', 'cinco_vidas', 'rey_de_la_cancha') NULL;

UPDATE torneo SET formato_grupos = 'rey_de_la_cancha' WHERE formato_grupos = 'cinco_vidas';

ALTER TABLE torneo MODIFY COLUMN formato_grupos
    ENUM('todos_contra_todos', 'rey_de_la_cancha') NULL;


-- ---------- partido.fase ----------
ALTER TABLE partido MODIFY COLUMN fase
    ENUM('todos_contra_todos', 'grupos', 'repechaje', 'desempate',
         'eliminacion', 'tercer_puesto', 'cinco_vidas', 'rey_de_la_cancha') NOT NULL;

UPDATE partido SET fase = 'rey_de_la_cancha' WHERE fase = 'cinco_vidas';

ALTER TABLE partido MODIFY COLUMN fase
    ENUM('todos_contra_todos', 'grupos', 'repechaje', 'desempate',
         'eliminacion', 'tercer_puesto', 'rey_de_la_cancha') NOT NULL;


-- ---------- verificación ----------
-- Si todo salió bien, estas tres consultas tienen que devolver 0 filas.
SELECT COUNT(*) AS torneos_sin_migrar        FROM torneo  WHERE modo = 'cinco_vidas';
SELECT COUNT(*) AS formatos_sin_migrar       FROM torneo  WHERE formato_grupos = 'cinco_vidas';
SELECT COUNT(*) AS partidos_sin_migrar       FROM partido WHERE fase = 'cinco_vidas';
