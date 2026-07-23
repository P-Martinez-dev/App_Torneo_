CREATE TABLE jugador (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE
);

CREATE TABLE torneo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    modo ENUM('todos_contra_todos', 'grupos_eliminacion', 'cinco_vidas') NOT NULL,
    fecha DATE NOT NULL,
    estado ENUM('planificado', 'en_curso', 'finalizado') DEFAULT 'planificado',
    cupos_eliminacion INT NULL
);

CREATE TABLE grupo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    torneo_id INT NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    tipo ENUM('grupo', 'repechaje', 'desempate') DEFAULT 'grupo',
    slots_a_clasificar INT NULL,
    FOREIGN KEY (torneo_id) REFERENCES torneo(id)
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
    torneo_jugador_id INT PRIMARY KEY,
    grupo_id INT NOT NULL,
    clasificado BOOLEAN NULL,
    clasificacion_forzada BOOLEAN DEFAULT FALSE,
    observacion_forzado TEXT NULL,
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
    estado ENUM('pendiente', 'en_curso', 'finalizado', 'pospuesto') DEFAULT 'pendiente',
    fecha_jugado DATETIME NULL,
    FOREIGN KEY (torneo_id) REFERENCES torneo(id),
    FOREIGN KEY (jugador1_id) REFERENCES jugador(id),
    FOREIGN KEY (jugador2_id) REFERENCES jugador(id),
    FOREIGN KEY (ganador_id) REFERENCES jugador(id),
    FOREIGN KEY (grupo_id) REFERENCES grupo(id)
);