import io
import os
from PIL import Image, ImageDraw, ImageFont

from services import torneo_service, tabla_general_service, estadisticas_generales_service

FUENTES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "fonts")

COLOR_PAPEL = (12, 12, 14)      # --paper
COLOR_CARD = (23, 23, 26)       # --card
COLOR_TINTA = (242, 241, 237)   # --ink
COLOR_GRAFITO = (139, 138, 135) # --graphite
COLOR_STAMP = (227, 30, 36)     # --stamp
COLOR_SELLO = COLOR_STAMP       # alias, mantiene compatibilidad con el resto del archivo
COLOR_MARCADOR = (41, 211, 198) # --marker
COLOR_LINEA = (42, 42, 46)      # --line

ANCHO = 1000
MARGEN = 60


# Los modos se guardan con su nombre técnico ('cinco_vidas'), que quedó de
# cuando el formato se llamaba así. Acá se traduce al nombre visible, igual
# que hace el filtro nombre_modo del frontend.
NOMBRES_VISIBLES_MODO = {
    "cinco_vidas": "Rey de la cancha",
    "todos_contra_todos": "Todos contra todos",
    "grupos_eliminacion": "Grupos + eliminación",
}


def _nombre_modo(valor):
    return NOMBRES_VISIBLES_MODO.get(valor, (valor or "").replace("_", " "))


def generar_imagen_tabla_general(excluidos_ids=None):
    """Exporta el RANKING GENERAL tal como está en pantalla en ese
    momento -- respeta los torneos tildados para excluir, no siempre
    es 'todos los torneos'."""
    excluidos_ids = excluidos_ids or []
    tabla = tabla_general_service.calcular_tabla_general(excluidos_ids)

    ancho = 1400
    margen = 50
    alto_fila = 54
    max_insignias = 15  # las mas recientes -- evita que una carrera muy larga se salga del ancho

    # Columnas: (etiqueta, x, ancho)
    columnas = [
        ("#", margen, 40),
        ("MOV", margen + 40, 65),
        ("JUGADOR", margen + 105, 190),
        ("PTS", margen + 295, 55),
        ("TORN", margen + 350, 55),
        ("PJ", margen + 405, 45),
        ("PG", margen + 450, 45),
        ("PP", margen + 495, 45),
        ("WR", margen + 540, 60),
        ("HISTORIAL", margen + 600, ancho - margen - (margen + 600)),
    ]

    alto_header = 200
    alto = alto_header + len(tabla) * alto_fila + 110
    img = Image.new("RGB", (ancho, alto), COLOR_PAPEL)
    draw = ImageDraw.Draw(img)

    y = 50
    draw.text((margen, y), estadisticas_generales_service.obtener_nombre_club().upper(), font=_fuente_mono(24, medium=True), fill=COLOR_TINTA)
    y += 55
    draw.line([(margen, y), (ancho - margen, y)], fill=COLOR_TINTA, width=3)
    y += 40

    nota = f"{len(excluidos_ids)} TORNEO(S) EXCLUIDO(S)" if excluidos_ids else "TODOS LOS TORNEOS INCLUIDOS"
    draw.text((margen, y), f"RANKING GENERAL · {nota}", font=_fuente_mono(17, medium=True), fill=COLOR_STAMP)
    y += 50

    # Encabezado de columnas
    fuente_header = _fuente_mono(13, medium=True)
    for etiqueta, x, _ in columnas:
        draw.text((x, y), etiqueta, font=fuente_header, fill=COLOR_GRAFITO)
    y += 26
    draw.line([(margen, y), (ancho - margen, y)], fill=COLOR_TINTA, width=2)
    y += 6

    fuente_fila = _fuente_mono(16)
    fuente_fila_medium = _fuente_mono(16, medium=True)
    fuente_emoji_fila = _fuente_emoji(20)

    col = {c[0]: (c[1], c[2]) for c in columnas}

    for i, fila in enumerate(tabla):
        y_fila_inicio = y
        # banda alternada, para separar bien cada renglón (pedido explícito)
        if i % 2 == 1:
            draw.rectangle([(margen - 10, y), (ancho - margen + 10, y + alto_fila)], fill=COLOR_CARD)

        y_centro = y + alto_fila // 2 - 10
        color_puesto = COLOR_STAMP if fila["puesto"] == 1 else COLOR_TINTA

        x, _ = col["#"]
        draw.text((x, y_centro), str(fila["puesto"]), font=fuente_fila_medium, fill=color_puesto)

        x, _ = col["MOV"]
        _dibujar_movimiento(draw, fila.get("movimiento"), x, y_centro)

        x, _ = col["JUGADOR"]
        draw.text((x, y_centro), fila["nombre"], font=fuente_fila_medium, fill=color_puesto)

        x, _ = col["PTS"]
        draw.text((x, y_centro), str(fila["puntos"]), font=fuente_fila, fill=COLOR_TINTA)

        x, _ = col["TORN"]
        draw.text((x, y_centro), str(fila["torneos_jugados"]), font=fuente_fila, fill=COLOR_GRAFITO)

        x, _ = col["PJ"]
        draw.text((x, y_centro), str(fila["partidos_jugados"]), font=fuente_fila, fill=COLOR_GRAFITO)

        x, _ = col["PG"]
        draw.text((x, y_centro), str(fila["partidos_ganados"]), font=fuente_fila, fill=COLOR_MARCADOR)

        x, _ = col["PP"]
        draw.text((x, y_centro), str(fila["partidos_perdidos"]), font=fuente_fila, fill=COLOR_STAMP)

        x, _ = col["WR"]
        draw.text((x, y_centro), f"{round(fila['win_rate'] * 100)}%", font=fuente_fila, fill=COLOR_TINTA)

        x, ancho_col = col["HISTORIAL"]
        insignias = fila["insignias"][-max_insignias:]
        for ins in insignias:
            draw.text((x, y_centro - 2), ins["emoji"], font=fuente_emoji_fila, fill=COLOR_TINTA)
            x += 28

        y = y_fila_inicio + alto_fila

    y += 15
    _dibujar_linea_punteada(draw, margen, y, ancho - margen)
    y += 25
    draw.text((margen, y), f"Generado con {estadisticas_generales_service.obtener_nombre_club()}", font=_fuente_mono(14), fill=COLOR_GRAFITO)
    y += 40

    buffer = io.BytesIO()
    img.crop((0, 0, ancho, y)).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _dibujar_movimiento(draw, movimiento, x, y):
    if not movimiento:
        return
    fuente = _fuente_mono(14, medium=True)
    tipo = movimiento["tipo"]
    if tipo == "subio":
        _dibujar_triangulo(draw, x, y + 4, arriba=True, color=COLOR_MARCADOR)
        draw.text((x + 16, y), str(movimiento["cantidad"]), font=fuente, fill=COLOR_MARCADOR)
    elif tipo == "bajo":
        _dibujar_triangulo(draw, x, y + 4, arriba=False, color=COLOR_STAMP)
        draw.text((x + 16, y), str(movimiento["cantidad"]), font=fuente, fill=COLOR_STAMP)
    elif tipo == "nuevo":
        draw.text((x, y), "NUEVO", font=_fuente_mono(11, medium=True), fill=COLOR_GRAFITO)
    else:
        draw.ellipse([(x + 2, y + 6), (x + 10, y + 14)], fill=COLOR_LINEA)


def _dibujar_triangulo(draw, x, y, arriba, color):
    tam = 10
    if arriba:
        puntos = [(x, y + tam), (x + tam, y + tam), (x + tam / 2, y)]
    else:
        puntos = [(x, y), (x + tam, y), (x + tam / 2, y + tam)]
    draw.polygon(puntos, fill=color)


def generar_imagen_resumen(torneo_id):
    """Genera una imagen PNG (en memoria, sin tocar disco) con la tabla de
    un torneo -- pensada para compartir el resultado en un chat, sin mandar
    un link. Devuelve un BytesIO listo para servir.

    Sigue el mismo criterio visual que la imagen del ranking general:
    encabezado con el nombre del club, columnas con encabezado, bandas
    alternadas por fila y el campeón en rojo. Las columnas cambian según
    el modo, porque cada uno mide cosas distintas (en rey de la cancha no hay
    win rate, por ejemplo: ahí lo que vale son las rachas).
    """
    resumen = torneo_service.obtener_resumen(torneo_id)
    torneo = resumen["torneo"]
    tabla = resumen.get("tabla") or []
    modo = torneo["modo"]

    # Si no hay tabla (torneo sin terminar, o un modo sin tabla general),
    # se cae al podio para no devolver una imagen vacía.
    if not tabla:
        return _imagen_solo_podio(resumen, torneo)

    ancho = 1200
    margen = 50
    alto_fila = 54

    if modo == "cinco_vidas":
        columnas = [("#", margen, 45), ("", margen + 45, 45),
                    ("JUGADOR", margen + 90, 300),
                    ("PTS RACHA", margen + 390, 130),
                    ("ELIMINACION", margen + 520, 300)]
    elif modo == "grupos_eliminacion":
        columnas = [("#", margen, 45), ("", margen + 45, 45),
                    ("JUGADOR", margen + 90, 300),
                    ("PJ", margen + 390, 70), ("PG", margen + 460, 70),
                    ("PP", margen + 530, 70), ("WR", margen + 600, 90)]
    else:  # todos_contra_todos
        columnas = [("#", margen, 45), ("", margen + 45, 45),
                    ("JUGADOR", margen + 90, 300),
                    ("PJ", margen + 390, 70), ("PG", margen + 460, 70),
                    ("PP", margen + 530, 70), ("WR", margen + 600, 90),
                    ("PTS", margen + 690, 70)]

    alto = 320 + len(tabla) * alto_fila + 110
    img = Image.new("RGB", (ancho, alto), COLOR_PAPEL)
    draw = ImageDraw.Draw(img)

    y = 50
    draw.text((margen, y), estadisticas_generales_service.obtener_nombre_club().upper(),
              font=_fuente_mono(24, medium=True), fill=COLOR_TINTA)
    y += 55
    draw.line([(margen, y), (ancho - margen, y)], fill=COLOR_TINTA, width=3)
    y += 40

    draw.text((margen, y), f"{_nombre_modo(modo).upper()} · {torneo['fecha']}",
              font=_fuente_mono(17, medium=True), fill=COLOR_STAMP)
    y += 45

    y = _dibujar_texto_envuelto(draw, torneo["nombre"].upper(), margen, y, ancho - margen * 2,
                                _fuente_display(56, 800), COLOR_TINTA, alto_linea=64)
    y += 10

    if torneo.get("descripcion"):
        y = _dibujar_texto_envuelto(draw, torneo["descripcion"], margen, y, ancho - margen * 2,
                                    _fuente_mono(15), COLOR_GRAFITO)
    y += 30

    fuente_header = _fuente_mono(13, medium=True)
    for etiqueta, x, _ in columnas:
        if etiqueta:
            draw.text((x, y), etiqueta, font=fuente_header, fill=COLOR_GRAFITO)
    y += 26
    draw.line([(margen, y), (ancho - margen, y)], fill=COLOR_TINTA, width=2)
    y += 6

    fuente_fila = _fuente_mono(16)
    fuente_fila_medium = _fuente_mono(16, medium=True)
    fuente_emoji_fila = _fuente_emoji(22)

    for i, fila in enumerate(tabla):
        y_inicio = y
        if i % 2 == 1:
            draw.rectangle([(margen - 10, y), (ancho - margen + 10, y + alto_fila)], fill=COLOR_CARD)

        y_centro = y + alto_fila // 2 - 10
        es_campeon = fila.get("puesto") == 1
        color = COLOR_STAMP if es_campeon else COLOR_TINTA

        col = {e: x for e, x, _ in columnas}

        draw.text((col["#"], y_centro), str(fila.get("puesto") or "-"), font=fuente_fila_medium, fill=color)
        if fila.get("emoji"):
            draw.text((col[""], y_centro - 2), fila["emoji"], font=fuente_emoji_fila, fill=COLOR_TINTA)
        draw.text((col["JUGADOR"], y_centro), fila["nombre"], font=fuente_fila_medium, fill=color)

        if modo == "cinco_vidas":
            draw.text((col["PTS RACHA"], y_centro), str(fila.get("puntos_racha", 0)),
                      font=fuente_fila, fill=COLOR_MARCADOR)
            texto = (f"{fila['orden_eliminacion']}° en caer" if fila.get("eliminado")
                     else "Nunca eliminado")
            draw.text((col["ELIMINACION"], y_centro), texto, font=fuente_fila, fill=COLOR_GRAFITO)
        else:
            draw.text((col["PJ"], y_centro), str(fila.get("pj", 0)), font=fuente_fila, fill=COLOR_GRAFITO)
            draw.text((col["PG"], y_centro), str(fila.get("pg", 0)), font=fuente_fila, fill=COLOR_MARCADOR)
            draw.text((col["PP"], y_centro), str(fila.get("pp", 0)), font=fuente_fila, fill=COLOR_STAMP)
            draw.text((col["WR"], y_centro), f"{round(fila.get('win_rate', 0) * 100)}%",
                      font=fuente_fila, fill=COLOR_TINTA)
            if "PTS" in col:
                draw.text((col["PTS"], y_centro), str(fila.get("puntos", 0)),
                          font=fuente_fila_medium, fill=COLOR_TINTA)

        y = y_inicio + alto_fila

    y += 15
    _dibujar_linea_punteada(draw, margen, y, ancho - margen)
    y += 25
    draw.text((margen, y), f"Generado con {estadisticas_generales_service.obtener_nombre_club()}",
              font=_fuente_mono(14), fill=COLOR_GRAFITO)
    y += 40

    buffer = io.BytesIO()
    img.crop((0, 0, ancho, y)).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _imagen_solo_podio(resumen, torneo):
    """Respaldo para cuando no hay tabla (torneo en curso, por ejemplo):
    muestra el podio, que es lo único disponible."""
    podio = resumen.get("podio") or []
    ancho, margen = 1000, 50
    img = Image.new("RGB", (ancho, 500 + len(podio) * 80 + 200), COLOR_PAPEL)
    draw = ImageDraw.Draw(img)

    y = 50
    draw.text((margen, y), estadisticas_generales_service.obtener_nombre_club().upper(),
              font=_fuente_mono(22, medium=True), fill=COLOR_TINTA)
    y += 55
    draw.line([(margen, y), (ancho - margen, y)], fill=COLOR_TINTA, width=3)
    y += 40
    draw.text((margen, y), f"{_nombre_modo(torneo['modo']).upper()} · {torneo['fecha']}",
              font=_fuente_mono(18, medium=True), fill=COLOR_STAMP)
    y += 45
    y = _dibujar_texto_envuelto(draw, torneo["nombre"].upper(), margen, y, ancho - margen * 2,
                                _fuente_display(60, 800), COLOR_TINTA, alto_linea=68)
    y += 35

    if podio:
        draw.text((margen, y), "PODIO", font=_fuente_mono(20, medium=True), fill=COLOR_TINTA)
        y += 55
        for fila in podio:
            puesto = fila["puesto"]
            destacado = puesto <= 3
            tamano = 46 if destacado else 28
            draw.text((margen, y), f"{puesto}°  {fila['nombre']}",
                      font=_fuente_display(tamano, 800 if destacado else 500),
                      fill=COLOR_STAMP if puesto == 1 else COLOR_TINTA)
            y += tamano + 22

    y += 15
    _dibujar_linea_punteada(draw, margen, y, ancho - margen)
    y += 25
    draw.text((margen, y), f"Generado con {estadisticas_generales_service.obtener_nombre_club()}",
              font=_fuente_mono(14), fill=COLOR_GRAFITO)
    y += 40

    buffer = io.BytesIO()
    img.crop((0, 0, ancho, y)).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _fuente_emoji(tamano):
    fuente = ImageFont.truetype(os.path.join(FUENTES_DIR, "NotoEmoji-Bold.ttf"), tamano)
    try:
        fuente.set_variation_by_axes([700])
    except Exception:
        pass
    return fuente


def _fuente_display(tamano, peso=800):
    fuente = ImageFont.truetype(os.path.join(FUENTES_DIR, "BigShouldersDisplay.ttf"), tamano)
    try:
        fuente.set_variation_by_axes([peso])
    except Exception:
        pass
    return fuente


def _fuente_mono(tamano, medium=False):
    nombre = "IBMPlexMono-Medium.ttf" if medium else "IBMPlexMono-Regular.ttf"
    return ImageFont.truetype(os.path.join(FUENTES_DIR, nombre), tamano)


def _dibujar_linea_punteada(draw, x1, y, x2):
    x = x1
    while x < x2:
        draw.line([(x, y), (min(x + 12, x2), y)], fill=COLOR_LINEA, width=2)
        x += 20


def _dibujar_texto_envuelto(draw, texto, x, y, ancho_maximo, fuente, color, alto_linea=26):
    palabras = texto.split()
    linea = ""
    for palabra in palabras:
        prueba = f"{linea} {palabra}".strip()
        bbox = draw.textbbox((0, 0), prueba, font=fuente)
        if bbox[2] - bbox[0] > ancho_maximo and linea:
            draw.text((x, y), linea, font=fuente, fill=color)
            y += alto_linea
            linea = palabra
        else:
            linea = prueba
    if linea:
        draw.text((x, y), linea, font=fuente, fill=color)
        y += alto_linea
    return y
