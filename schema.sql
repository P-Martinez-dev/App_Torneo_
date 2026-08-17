CREATE TABLE jugador (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE,
    imagen_vertical_path VARCHAR(255) NULL,
    imagen_icono_path VARCHAR(255) NULL
);

CREATE TABLE torneo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    modo ENUM('todos_contra_todos', 'grupos_eliminacion', 'cinco_vidas') NOT NULL,
    fecha DATE NOT NULL,
    estado ENUM('planificado', 'en_curso', 'finalizado') DEFAULT 'planificado',
    cupos_eliminacion INT NULL,
    vidas_iniciales INT NULL,
    -- Solo aplica a modo 'grupos_eliminacion': cómo se juega adentro de
    -- cada grupo. Los torneos viejos no lo tienen, y NULL se interpreta
    -- como 'todos_contra_todos', que era el único formato hasta ahora.
    formato_grupos ENUM('todos_contra_todos', 'cinco_vidas') NULL,
    descripcion TEXT NULL
);

CREATE TABLE grupo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    torneo_id INT NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    tipo ENUM('grupo', 'repechaje', 'desempate') DEFAULT 'grupo',
    slots_a_clasificar INT NULL,
    grupo_padre_id INT NULL,
    FOREIGN KEY (torneo_id) REFERENCES torneo(id),
    FOREIGN KEY (grupo_padre_id) REFERENCES grupo(id) ON DELETE CASCADE
);

CREATE TABLE torneo_jugador (
    id INT AUTO_INCREMENT PRIMARY KEY,
    torneo_id INT NOT NULL,
    jugador_id INT NOT NULL,
    FOREIGN KEY (torneo_id) REFERENCES torneo(id),
    FOREIGN KEY (jugador_id) REFERENCES jugador(id),
    UNIQUE (torneo_id, jugador_id)
);

CREATE TABLE torneo_jugador_grupo (
    torneo_jugador_id INT NOT NULL,
    grupo_id INT NOT NULL,
    clasificado BOOLEAN NULL,
    clasificacion_forzada BOOLEAN DEFAULT FALSE,
    observacion_forzado TEXT NULL,
    PRIMARY KEY (torneo_jugador_id, grupo_id),
    FOREIGN KEY (torneo_jugador_id) REFERENCES torneo_jugador(id),
    FOREIGN KEY (grupo_id) REFERENCES grupo(id)
);

CREATE TABLE torneo_jugador_vidas (
    torneo_jugador_id INT PRIMARY KEY,
    vidas INT NOT NULL DEFAULT 3,
    eliminado BOOLEAN DEFAULT FALSE,
    posicion_cola INT NULL,
    en_cancha BOOLEAN DEFAULT FALSE,
    orden_eliminacion INT NULL,
    FOREIGN KEY (torneo_jugador_id) REFERENCES torneo_jugador(id)
);

CREATE TABLE config_estadistica (
    clave VARCHAR(100) PRIMARY KEY,
    visible BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE admin_usuario (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE configuracion_general (
    id INT PRIMARY KEY DEFAULT 1,
    fecha_proximo_torneo DATE NULL,
    descripcion_inicio TEXT NULL,
    descripcion_tablas TEXT NULL,
    info_tablas TEXT NULL,
    info_formatos TEXT NULL,
    nombre_club VARCHAR(100) NULL,
    mostrar_tile_tablas BOOLEAN NOT NULL DEFAULT TRUE,
    mostrar_tile_torneos BOOLEAN NOT NULL DEFAULT TRUE,
    mostrar_tile_jugadores BOOLEAN NOT NULL DEFAULT TRUE,
    mostrar_tile_peleadores BOOLEAN NOT NULL DEFAULT TRUE
);
INSERT INTO configuracion_general (id) VALUES (1);

CREATE TABLE peleador (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    imagen_icono_path VARCHAR(255) NULL
);

CREATE TABLE partido (
    id INT AUTO_INCREMENT PRIMARY KEY,
    torneo_id INT NOT NULL,
    jugador1_id INT NOT NULL,
    jugador2_id INT NOT NULL,
    ganador_id INT NULL,
    fase ENUM('todos_contra_todos', 'grupos', 'repechaje', 'desempate', 'eliminacion', 'tercer_puesto', 'cinco_vidas') NOT NULL,
    ronda INT NULL,
    jornada INT NULL,
    orden INT NOT NULL,
    grupo_id INT NULL,
    jugador1_peleador_id INT NULL,
    jugador2_peleador_id INT NULL,
    rondas_jugadas INT NULL,
    estado ENUM('pendiente', 'en_curso', 'finalizado', 'pospuesto', 'no_realizado') DEFAULT 'pendiente',
    fecha_jugado DATETIME NULL,
    FOREIGN KEY (torneo_id) REFERENCES torneo(id),
    FOREIGN KEY (jugador1_id) REFERENCES jugador(id),
    FOREIGN KEY (jugador2_id) REFERENCES jugador(id),
    FOREIGN KEY (ganador_id) REFERENCES jugador(id),
    FOREIGN KEY (grupo_id) REFERENCES grupo(id),
    FOREIGN KEY (jugador1_peleador_id) REFERENCES peleador(id),
    FOREIGN KEY (jugador2_peleador_id) REFERENCES peleador(id)
);