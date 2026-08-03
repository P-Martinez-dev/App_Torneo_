(function () {
  const btn = document.getElementById("btn-eliminar-torneo");
  const dialog = document.getElementById("dialog-eliminar-torneo");
  if (!btn) return;
  btn.addEventListener("click", () => dialog.showModal());
  document.getElementById("btn-cancelar-eliminar-torneo").addEventListener("click", () => dialog.close());
})();
