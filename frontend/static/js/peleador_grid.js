// Maneja el click en la grilla de selección de peleador (estilo character
// select): tocar un ícono marca ese peleador como elegido y actualiza el
// input oculto que el form realmente envía.
(function () {
  document.querySelectorAll(".peleador-grid").forEach((grilla) => {
    const campo = grilla.dataset.campo;
    const inputOculto = document.getElementById(campo);
    if (!inputOculto) return;

    grilla.querySelectorAll(".peleador-grid-item").forEach((item) => {
      item.addEventListener("click", () => {
        inputOculto.value = item.dataset.valor;
        grilla.querySelectorAll(".peleador-grid-item").forEach((otro) => {
          otro.classList.toggle("peleador-grid-item-activo", otro === item);
        });
      });
    });
  });
})();
