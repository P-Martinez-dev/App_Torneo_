// Achica visualmente la tabla del ranking para que entre completa en la
// pantalla, sin cambiarle nada a la tabla en sí.
//
// La idea: la tabla tiene 11 columnas y en un celular no entra. Antes había
// que hacer zoom out a mano para verla entera. Esto hace ese mismo zoom
// out, pero solo y en la medida justa: mide cuánto ocupa la tabla, cuánto
// espacio hay, y aplica la escala necesaria. Así el zoom manual queda para
// cuando querés mirar algo puntual, no como requisito para leerla.
(function () {
  const contenedor = document.querySelector(".tabla-ranking-contenedor");
  if (!contenedor) return;

  const tabla = contenedor.querySelector("table");
  if (!tabla) return;

  // Por debajo de esto la letra queda ilegible: si ni así entra, es
  // preferible dejar que se pueda deslizar de costado.
  const ESCALA_MINIMA = 0.45;

  function ajustar() {
    // Se resetea antes de medir: si no, la segunda medición saldría
    // afectada por la escala que aplicamos la primera vez.
    contenedor.style.transform = "";
    contenedor.style.width = "";
    contenedor.style.height = "";

    const anchoDisponible = contenedor.parentElement.clientWidth;
    const anchoTabla = tabla.scrollWidth;

    if (anchoTabla <= anchoDisponible) return;  // ya entra, no hay nada que hacer

    const escala = Math.max(anchoDisponible / anchoTabla, ESCALA_MINIMA);
    contenedor.style.transform = `scale(${escala})`;

    // Al escalar, el elemento sigue ocupando su tamaño original en el
    // layout y deja un hueco en blanco abajo. Se corrige el alto a mano
    // para que el contenido que sigue quede pegado como corresponde.
    contenedor.style.width = `${100 / escala}%`;
    contenedor.style.height = `${tabla.scrollHeight * escala}px`;
  }

  ajustar();

  // Al rotar el celular o cambiar el tamaño de la ventana hay que
  // recalcular, porque el ancho disponible cambió.
  let pendiente;
  window.addEventListener("resize", () => {
    clearTimeout(pendiente);
    pendiente = setTimeout(ajustar, 150);
  });
})();
