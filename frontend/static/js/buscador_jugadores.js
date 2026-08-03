// JS mínimo: filtra las fichas ya renderizadas por nombre, sin pegarle
// al servidor -- la lista completa ya está en la página.
(function () {
  const input = document.getElementById("buscador-jugadores");
  const grid = document.getElementById("jugador-grid");
  const sinResultados = document.getElementById("buscador-sin-resultados");
  if (!input || !grid) return;

  const fichas = Array.from(grid.querySelectorAll(".jugador-tile[data-nombre]"));

  input.addEventListener("input", () => {
    const termino = input.value.trim().toLowerCase();
    let visibles = 0;
    fichas.forEach((ficha) => {
      const coincide = ficha.dataset.nombre.includes(termino);
      ficha.hidden = !coincide;
      if (coincide) visibles += 1;
    });
    if (sinResultados) sinResultados.hidden = !(termino && visibles === 0);
  });
})();
