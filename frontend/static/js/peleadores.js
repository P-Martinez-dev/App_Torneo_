(function () {
  document.querySelectorAll(".btn-abrir-dialog").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dialog = document.getElementById(btn.dataset.dialog);
      if (dialog) dialog.showModal();
    });
  });
  document.querySelectorAll(".btn-cerrar-dialog").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dialog = document.getElementById(btn.dataset.dialog);
      if (dialog) dialog.close();
    });
  });
})();
