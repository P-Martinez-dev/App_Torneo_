// JS mínimo: solo abre/cierra los <dialog> nativos y navega. Nada de
// esto decide de negocio -- eliminar el torneo lo hace un form real
// (POST), no un fetch.
(function () {
  const btnCrear = document.getElementById("btn-crear-torneo");
  const dialogContinuar = document.getElementById("dialog-continuar");
  const dialogDescartar = document.getElementById("dialog-descartar");

  if (!btnCrear || !dialogContinuar || !dialogDescartar) return;

  const continuarUrl = dialogContinuar.dataset.continuarUrl;

  btnCrear.addEventListener("click", () => dialogContinuar.showModal());

  document.getElementById("btn-continuar-si").addEventListener("click", () => {
    window.location.href = continuarUrl;
  });

  document.getElementById("btn-continuar-no").addEventListener("click", () => {
    dialogContinuar.close();
    dialogDescartar.showModal();
  });

  document.getElementById("btn-descartar-no").addEventListener("click", () => {
    dialogDescartar.close();
    dialogContinuar.showModal();
  });
})();
