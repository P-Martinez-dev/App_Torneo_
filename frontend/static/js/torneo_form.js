// JS mínimo: solo decide qué campos mostrar según el modo, sincroniza la
// lista de orden de cinco_vidas con los jugadores tildados, y maneja el
// drag-and-drop para reordenarla. Nada de esto valida ni calcula nada de
// negocio -- eso lo hace el backend.
(function () {
  const modoSelect = document.getElementById("modo");
  const secciones = document.querySelectorAll(".modo-extra");
  const rosterCheckboxes = document.querySelectorAll('.roster-item input[type="checkbox"]');
  const ordenLista = document.getElementById("orden-lista");
  const ordenHint = document.getElementById("orden-hint");

  function actualizarSeccionesPorModo() {
    const modo = modoSelect.value;
    secciones.forEach((seccion) => {
      const visible = seccion.dataset.modo === modo;
      seccion.hidden = !visible;
      seccion.querySelectorAll("input").forEach((input) => {
        if (input.closest("#orden-lista")) return; // esos se manejan aparte
        input.disabled = !visible;
      });
    });
    sincronizarOrdenLista();
  }

  function ordenEsManual() {
    const activo = document.querySelector('input[name="orden_tipo"]:checked');
    return !!activo && activo.value === "manual";
  }

  function sincronizarOrdenLista() {
    if (!ordenLista) return;
    const esManual = modoSelect.value === "cinco_vidas" && ordenEsManual();
    ordenLista.hidden = !esManual;
    if (ordenHint) ordenHint.hidden = !esManual;

    const marcados = Array.from(rosterCheckboxes)
      .filter((cb) => cb.checked)
      .map((cb) => ({ id: cb.value, nombre: cb.dataset.nombre }));

    // sacar de la lista a los que se destildaron
    Array.from(ordenLista.children).forEach((li) => {
      if (!marcados.some((j) => j.id === li.dataset.jugadorId)) li.remove();
    });

    // agregar al final a los tildados que todavía no estén en la lista
    marcados.forEach((j) => {
      if (!ordenLista.querySelector(`li[data-jugador-id="${j.id}"]`)) {
        ordenLista.appendChild(crearItemOrden(j.id, j.nombre));
      }
    });

    // los hidden inputs solo se mandan si de verdad estamos en modo manual
    ordenLista.querySelectorAll('input[type="hidden"]').forEach((input) => {
      input.disabled = !esManual;
    });
  }

  function crearItemOrden(id, nombre) {
    const li = document.createElement("li");
    li.className = "orden-item";
    li.draggable = true;
    li.dataset.jugadorId = id;
    li.innerHTML =
      '<span class="orden-handle">\u2630</span>' +
      '<span class="orden-nombre"></span>' +
      `<input type="hidden" name="orden_jugadores_ids" value="${id}">`;
    li.querySelector(".orden-nombre").textContent = nombre;
    li.addEventListener("dragstart", onDragStart);
    li.addEventListener("dragover", onDragOver);
    li.addEventListener("drop", (e) => e.preventDefault());
    li.addEventListener("dragend", onDragEnd);
    return li;
  }

  let arrastrando = null;

  function onDragStart(e) {
    arrastrando = e.currentTarget;
    e.currentTarget.classList.add("orden-item-arrastrando");
    e.dataTransfer.effectAllowed = "move";
  }

  function onDragOver(e) {
    e.preventDefault();
    const objetivo = e.currentTarget;
    if (objetivo === arrastrando || !arrastrando) return;
    const rect = objetivo.getBoundingClientRect();
    const mitad = rect.top + rect.height / 2;
    if (e.clientY < mitad) {
      ordenLista.insertBefore(arrastrando, objetivo);
    } else {
      ordenLista.insertBefore(arrastrando, objetivo.nextSibling);
    }
  }

  function onDragEnd(e) {
    e.currentTarget.classList.remove("orden-item-arrastrando");
    arrastrando = null;
  }

  if (modoSelect) {
    modoSelect.addEventListener("change", actualizarSeccionesPorModo);
    actualizarSeccionesPorModo();
  }

  document.querySelectorAll('input[name="orden_tipo"]').forEach((radio) =>
    radio.addEventListener("change", sincronizarOrdenLista)
  );
  rosterCheckboxes.forEach((cb) => cb.addEventListener("change", sincronizarOrdenLista));
})();
