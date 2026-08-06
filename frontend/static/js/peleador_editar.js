(function () {
  const btn = document.getElementById("btn-eliminar-peleador");
  const dialog = document.getElementById("dialog-eliminar-peleador");
  if (!btn) return;
  btn.addEventListener("click", () => dialog.showModal());
  document.getElementById("btn-cancelar-eliminar-peleador").addEventListener("click", () => dialog.close());
})();
