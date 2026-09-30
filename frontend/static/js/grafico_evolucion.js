// Detalle del gráfico de evolución del cara a cara: al pasar el mouse (o
// tocar, en el celular) sobre un partido, una línea vertical lo marca y un
// recuadro muestra de qué partido se trata y cómo iba el acumulado.
// El gráfico ya está dibujado en el SVG de la plantilla; esto solo agrega
// el detalle, así que sin JS el gráfico se sigue viendo igual.
(function () {
  const contenedor = document.getElementById("grafico-evolucion");
  if (!contenedor) return;

  const svg = contenedor.querySelector("svg");
  const cursor = document.getElementById("grafico-cursor");
  const tooltip = document.getElementById("grafico-tooltip");
  const zonas = contenedor.querySelectorAll(".grafico-zona");

  function mostrar(zona) {
    const x = zona.dataset.x;
    cursor.setAttribute("x1", x);
    cursor.setAttribute("x2", x);
    cursor.setAttribute("visibility", "visible");

    tooltip.replaceChildren();
    for (const [clase, texto] of [
      ["grafico-tooltip-titulo", zona.dataset.titulo],
      ["grafico-tooltip-linea", zona.dataset.fase],
      ["grafico-tooltip-linea", zona.dataset.ganador],
      ["grafico-tooltip-marcador", zona.dataset.marcador],
    ]) {
      const p = document.createElement("p");
      p.className = clase;
      p.textContent = texto;
      tooltip.appendChild(p);
    }
    tooltip.hidden = false;

    // El SVG se escala con el ancho de la pantalla: la x del partido está en
    // coordenadas del viewBox y hay que pasarla a píxeles reales.
    const escala = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
    const xPx = parseFloat(x) * escala;
    // En el celular el gráfico se desliza de costado: el recuadro tiene que
    // quedar dentro de la parte VISIBLE, no del gráfico entero.
    const visibleIzq = contenedor.scrollLeft;
    const visibleDer = visibleIzq + contenedor.clientWidth;
    const anchoTooltip = tooltip.offsetWidth;
    // Del lado derecho del cursor, salvo que no entre: ahí va a la izquierda.
    let izquierda = xPx + 12;
    if (izquierda + anchoTooltip > visibleDer) izquierda = xPx - anchoTooltip - 12;
    tooltip.style.left = Math.max(visibleIzq, izquierda) + "px";
  }

  function ocultar() {
    cursor.setAttribute("visibility", "hidden");
    tooltip.hidden = true;
  }

  zonas.forEach((zona) => {
    zona.addEventListener("pointerenter", () => mostrar(zona));
    zona.addEventListener("pointerdown", () => mostrar(zona));
  });
  // Con el mouse se oculta al salir del gráfico. Con el dedo no: en una
  // pantalla táctil el navegador avisa que el puntero "salió" apenas se
  // levanta el dedo, y el recuadro desaparecía en el acto. Ahí se oculta al
  // tocar en cualquier otro lado de la página.
  svg.addEventListener("pointerleave", (e) => {
    if (e.pointerType === "mouse") ocultar();
  });
  document.addEventListener("pointerdown", (e) => {
    if (!contenedor.contains(e.target)) ocultar();
  });
})();
