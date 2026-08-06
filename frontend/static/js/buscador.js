// JS mínimo: filtra fichas ya renderizadas por nombre, sin pegarle al
// servidor -- la lista completa ya está en la página.
// Uso: <input data-buscador="id-del-contenedor" data-buscador-vacio="id-opcional-mensaje-vacio">
// Las fichas dentro del contenedor necesitan un atributo data-nombre="...".
(function () {
  document.querySelectorAll("[data-buscador]").forEach((input) => {
    const contenedor = document.getElementById(input.dataset.buscador);
    if (!contenedor) return;

    const sinResultadosId = input.dataset.buscadorVacio;
    const sinResultados = sinResultadosId ? document.getElementById(sinResultadosId) : null;
    const fichas = Array.from(contenedor.querySelectorAll("[data-nombre]"));

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
  });
})();
