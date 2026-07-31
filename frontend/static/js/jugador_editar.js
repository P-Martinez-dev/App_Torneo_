(function () {
  const btn = document.getElementById("btn-eliminar-jugador");
  const dialog = document.getElementById("dialog-eliminar-jugador");
  if (!btn) return;
  btn.addEventListener("click", () => dialog.showModal());
  document.getElementById("btn-cancelar-eliminar").addEventListener("click", () => dialog.close());
})();
