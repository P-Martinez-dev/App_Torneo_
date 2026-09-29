// JS mínimo: marca hasta dos fichas y, al elegir la segunda, navega a
// /enfrentamientos/<a>/<b>. No calcula nada -- el cara a cara lo arma el
// backend. Tocar una ficha ya elegida la desmarca (por si te equivocaste).
(function () {
  const grid = document.getElementById("enfrentamiento-grid");
  const estado = document.getElementById("selector-estado");
  if (!grid) return;

  const urlBase = grid.dataset.urlBase;
  let primera = null;

  function actualizarEstado() {
    if (!estado) return;
    estado.textContent = primera
      ? `${primera.dataset.nombreVisible} vs... elegí el rival.`
      : "Elegí el primer jugador.";
  }

  function marcar(ficha, seleccionada) {
    ficha.classList.toggle("jugador-tile-seleccionado", seleccionada);
    ficha.setAttribute("aria-pressed", seleccionada ? "true" : "false");
  }

  grid.querySelectorAll(".jugador-tile-boton").forEach((ficha) => {
    ficha.addEventListener("click", () => {
      if (primera === ficha) {
        marcar(ficha, false);
        primera = null;
        actualizarEstado();
        return;
      }
      if (!primera) {
        primera = ficha;
        marcar(ficha, true);
        actualizarEstado();
        return;
      }
      marcar(ficha, true);
      window.location.href = `${urlBase}/${primera.dataset.id}/${ficha.dataset.id}`;
    });
  });

  // Al volver con el botón "atrás" del navegador, la página puede salir
  // del cache con las dos fichas todavía marcadas: se limpia todo.
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    grid.querySelectorAll(".jugador-tile-seleccionado").forEach((f) => marcar(f, false));
    primera = null;
    actualizarEstado();
  });
})();
