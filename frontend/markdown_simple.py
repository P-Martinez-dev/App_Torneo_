"""
Convierte el Markdown liviano de los textos de Info a HTML.

Se soporta a propósito un subconjunto muy chico (títulos, negritas, listas
y párrafos): alcanza de sobra para estos textos y evita sumar una
dependencia entera al proyecto solo para esto.

IMPORTANTE: el texto lo escribe el admin desde un formulario, así que
primero se escapa todo (para que nadie pueda inyectar HTML) y recién
después se arma el marcado permitido.
"""
import re
from html import escape

from markupsafe import Markup


def markdown_a_html(texto):
    if not texto:
        return Markup("")

    html = []
    lista_abierta = False

    for linea in escape(texto).split("\n"):
        linea = linea.strip()

        if not linea:
            if lista_abierta:
                html.append("</ul>")
                lista_abierta = False
            continue

        # **negrita** -- se aplica después de escapar, así el asterisco
        # solo produce el <strong> y nada más.
        linea = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", linea)

        if linea.startswith("## "):
            if lista_abierta:
                html.append("</ul>")
                lista_abierta = False
            html.append(f'<h2 class="ticket-nombre">{linea[3:]}</h2>')
        elif linea.startswith("- "):
            if not lista_abierta:
                html.append('<ul class="info-lista">')
                lista_abierta = True
            html.append(f"<li>{linea[2:]}</li>")
        else:
            if lista_abierta:
                html.append("</ul>")
                lista_abierta = False
            html.append(f'<p class="empty-body">{linea}</p>')

    if lista_abierta:
        html.append("</ul>")

    return Markup("\n".join(html))
