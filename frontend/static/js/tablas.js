// JS mínimo: al tildar/destildar un torneo, reenvía el form -- el
// backend recalcula la tabla general con la lista de excluidos nueva.
(function () {
  const form = document.getElementById("form-excluir");
  if (!form) return;
  form.querySelectorAll(".excluir-checkbox").forEach((cb) => {
    cb.addEventListener("change", () => form.requestSubmit());
  });
})();
