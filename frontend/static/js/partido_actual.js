(function () {
  const dialogOpciones = document.getElementById("dialog-opciones");
  const dialogCargarDatos = document.getElementById("dialog-cargar-datos");
  if (!dialogOpciones) return;

  document.getElementById("btn-opciones").addEventListener("click", () => dialogOpciones.showModal());
  document.getElementById("btn-cerrar-opciones").addEventListener("click", () => dialogOpciones.close());
  document.getElementById("btn-abrir-cargar-datos").addEventListener("click", () => {
    dialogOpciones.close();
    dialogCargarDatos.showModal();
  });
})();
