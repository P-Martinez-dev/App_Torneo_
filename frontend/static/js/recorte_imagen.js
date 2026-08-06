// Intercepta la selección de cualquier <input type="file" data-recorte="PROPORCION">,
// muestra un recorte con esa proporción fija (Cropper.js) y, al confirmar,
// reemplaza el archivo del input por la versión recortada -- el form sigue
// subiendo multipart/form-data normal, no hace falta tocar nada del backend.
// Uso: <input type="file" data-recorte="0.75"> (3:4) o data-recorte="1" (1:1).
(function () {
  let contador = 0;

  function activarRecorte(input) {
    const proporcion = parseFloat(input.dataset.recorte);
    const form = input.closest("form");
    if (!form || Number.isNaN(proporcion)) return;

    input.addEventListener("change", () => {
      const archivo = input.files[0];
      if (!archivo) return;

      contador += 1;
      const idPreview = `recorte-preview-${contador}`;

      const dialog = document.createElement("dialog");
      dialog.className = "dialog-ticket dialog-recorte";
      dialog.innerHTML = `
        <p class="dialog-texto">Recortá la imagen</p>
        <div class="recorte-contenedor"><img id="${idPreview}"></div>
        <div class="dialog-acciones">
          <button type="button" class="btn btn-stamp" data-accion="confirmar">Confirmar</button>
          <button type="button" class="btn btn-ghost" data-accion="cancelar">Cancelar</button>
        </div>
      `;
      document.body.appendChild(dialog);
      const imgPreview = dialog.querySelector("img");
      let cropper = null;

      const lector = new FileReader();
      lector.onload = (evento) => {
        imgPreview.src = evento.target.result;
        dialog.showModal();
        cropper = new Cropper(imgPreview, {
          aspectRatio: proporcion,
          viewMode: 1,
          background: false,
        });
      };
      lector.readAsDataURL(archivo);

      function cerrarYLimpiar() {
        if (cropper) cropper.destroy();
        dialog.close();
        dialog.remove();
      }

      dialog.querySelector('[data-accion="cancelar"]').addEventListener("click", () => {
        input.value = ""; // cancela la selección, no sube nada
        cerrarYLimpiar();
      });

      dialog.querySelector('[data-accion="confirmar"]').addEventListener("click", () => {
        cropper.getCroppedCanvas().toBlob((blob) => {
          const archivoRecortado = new File([blob], archivo.name, { type: archivo.type });
          const transferencia = new DataTransfer();
          transferencia.items.add(archivoRecortado);
          input.files = transferencia.files;
          cerrarYLimpiar();
          form.requestSubmit();
        }, archivo.type);
      });
    });
  }

  document.querySelectorAll('input[type="file"][data-recorte]').forEach(activarRecorte);
})();
