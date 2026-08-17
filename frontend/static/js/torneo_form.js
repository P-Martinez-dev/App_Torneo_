// JS mínimo: solo decide qué campos mostrar según el modo, sincroniza la
// lista de orden de rey_de_la_cancha con los jugadores tildados, y maneja el
// drag-and-drop para reordenarla. Nada de esto valida ni calcula nada de
// negocio -- eso lo hace el backend.
(function () {
  const modoSelect = document.getElementById("modo");
  const secciones = document.querySelectorAll(".modo-extra");
  const rosterCheckboxes = document.querySelectorAll('.roster-item input[type="checkbox"]');
  const ordenLista = document.getElementById("orden-lista");
  const ordenHint = document.getElementById("orden-hint");
  const cantidadGruposInput = document.getElementById("cantidad_grupos");
  const gruposHint = document.getElementById("grupos-hint");
  const vidasGrupos = document.getElementById("vidas-grupos");

  function actualizarSeccionesPorModo() {
    const modo = modoSelect.value;
    secciones.forEach((seccion) => {
      const visible = seccion.dataset.modo === modo;
      seccion.hidden = !visible;
      seccion.querySelectorAll("input").forEach((input) => {
        if (input.closest("#orden-lista") || input.classList.contains("roster-grupo-input")) return;
        input.disabled = !visible;
      });
    });
    sincronizarOrdenLista();
    sincronizarGrupoInputs();
    sincronizarVidasGrupos();
  }

  // El campo de vidas de los grupos solo tiene sentido si los grupos se
  // juegan a rey de la cancha: en todos contra todos nadie tiene vidas.
  function sincronizarVidasGrupos() {
    if (!vidasGrupos) return;
    const activo = document.querySelector('input[name="formato_grupos"]:checked');
    const esRey = modoSelect.value === "grupos_eliminacion" && !!activo && activo.value === "rey_de_la_cancha";
    vidasGrupos.hidden = !esRey;
    vidasGrupos.querySelectorAll("input").forEach((input) => { input.disabled = !esRey; });
  }

  function gruposEsManual() {
    const activo = document.querySelector('input[name="grupos_tipo"]:checked');
    return modoSelect.value === "grupos_eliminacion" && !!activo && activo.value === "manual";
  }

  function sincronizarGrupoInputs() {
    const manual = gruposEsManual();
    if (gruposHint) gruposHint.hidden = !manual;
    const maxGrupos = cantidadGruposInput ? parseInt(cantidadGruposInput.value, 10) || 99 : 99;
    rosterCheckboxes.forEach((cb) => {
      const input = cb.closest(".roster-item").querySelector(".roster-grupo-input");
      if (!input) return;
      const visible = manual && cb.checked;
      input.hidden = !visible;
      input.disabled = !visible;
      input.max = maxGrupos;
    });
  }

  function ordenEsManual() {
    const activo = document.querySelector('input[name="orden_tipo"]:checked');
    return !!activo && activo.value === "manual";
  }

  function sincronizarOrdenLista() {
    if (!ordenLista) return;
    const esManual = modoSelect.value === "rey_de_la_cancha" && ordenEsManual();
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
  document.querySelectorAll('input[name="formato_grupos"]').forEach((r) => {
    r.addEventListener("change", sincronizarVidasGrupos);
  });
    actualizarSeccionesPorModo();
  }

  document.querySelectorAll('input[name="orden_tipo"]').forEach((radio) =>
    radio.addEventListener("change", sincronizarOrdenLista)
  );
  document.querySelectorAll('input[name="grupos_tipo"]').forEach((radio) =>
    radio.addEventListener("change", sincronizarGrupoInputs)
  );
  if (cantidadGruposInput) {
    cantidadGruposInput.addEventListener("input", sincronizarGrupoInputs);
  }
  rosterCheckboxes.forEach((cb) => {
    cb.addEventListener("change", sincronizarOrdenLista);
    cb.addEventListener("change", sincronizarGrupoInputs);
  });
})();
