#!/bin/bash
set -e

# Ubicación real del script, sin importar desde dónde se lo invoque
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Creando entorno virtual (venv/)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
else
    echo "   venv/ ya existe, se reutiliza."
fi

source venv/bin/activate

# Se instala DESDE requirements.txt (no una lista escrita a mano acá, que
# quedaría desactualizada cada vez que se suma una dependencia nueva).
echo "==> Instalando dependencias desde requirements.txt..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "   Listo."

# Los .env se arman copiando los .env.example, que son la fuente de verdad:
# si mañana el proyecto necesita una variable nueva, alcanza con agregarla
# al .example y este script la trae sola. Antes estaban escritos a mano acá
# y quedaron viejos (les faltaban DB_PORT, INTERNAL_API_KEY y CLOUDINARY_URL,
# sin las cuales la app ni arranca).
crear_env() {
    local carpeta="$1"
    if [ -f "$carpeta/.env" ]; then
        echo "   $carpeta/.env ya existe, no se toca."
        return
    fi
    if [ ! -f "$carpeta/.env.example" ]; then
        echo "   AVISO: falta $carpeta/.env.example, no se pudo crear el .env."
        return
    fi
    cp "$carpeta/.env.example" "$carpeta/.env"
    echo "   $carpeta/.env creado a partir del .env.example."
}

echo "==> Creando archivos .env (si no existen)..."
crear_env backend
crear_env frontend

# La clave interna tiene que ser LA MISMA en los dos lados, así que se genera
# una sola vez y se escribe en ambos. Se hace solo si quedó el placeholder:
# si ya pusiste una clave real (o copiaste la de producción), no se pisa.
if grep -q "^INTERNAL_API_KEY=cambiar-por" backend/.env 2>/dev/null && \
   grep -q "^INTERNAL_API_KEY=cambiar-por" frontend/.env 2>/dev/null; then
    CLAVE_INTERNA="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    sed -i.bak "s|^INTERNAL_API_KEY=.*|INTERNAL_API_KEY=$CLAVE_INTERNA|" backend/.env frontend/.env
    rm -f backend/.env.bak frontend/.env.bak
    echo "   INTERNAL_API_KEY generada (la misma en backend y frontend)."
fi

# Lo mismo con SECRET_KEY, pero acá NO hace falta que coincidan: cada app
# firma sus propias cookies.
for carpeta in backend frontend; do
    if grep -q "^SECRET_KEY=cambiar-por" "$carpeta/.env" 2>/dev/null; then
        CLAVE="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
        sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=$CLAVE|" "$carpeta/.env"
        rm -f "$carpeta/.env.bak"
        echo "   SECRET_KEY generada para $carpeta."
    fi
done

echo ""
echo "   IMPORTANTE: revisá backend/.env y completá los datos de tu base"
echo "   (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)."
echo "   Si vas a usar la base en la nube, copiá esos valores desde ahí."

echo ""
read -p "==> ¿(Re)inicializar una base MySQL LOCAL desde cero? Esto BORRA todo lo que tengas en esa base. [s/N] " respuesta
if [[ "$respuesta" =~ ^[sS]$ ]]; then
    read -p "    Usuario de MySQL: " db_user
    read -p "    Nombre de la base [torneos]: " db_name
    db_name="${db_name:-torneos}"
    echo "    OJO: esto borra y recrea '$db_name' entera."
    read -p "    Escribí el nombre de la base para confirmar: " confirmacion
    if [ "$confirmacion" != "$db_name" ]; then
        echo "    No coincide. Se canceló, no se tocó nada."
    else
        mysql -u "$db_user" -p -e "DROP DATABASE IF EXISTS \`$db_name\`; CREATE DATABASE \`$db_name\`;"
        mysql -u "$db_user" -p "$db_name" < schema.sql
        echo "    Base '$db_name' recreada desde cero con schema.sql."
    fi
else
    echo "    Se salteó la inicialización de la base."
    echo "    Si hace falta, se corre a mano con:"
    echo "      mysql -u tu_usuario -p -e \"CREATE DATABASE torneos;\""
    echo "      mysql -u tu_usuario -p torneos < schema.sql"
fi

echo ""
echo "==> Listo. Para levantar el proyecto:"
echo "    source venv/bin/activate"
echo "    cd backend  && python app.py    # puerto 5000"
echo "    cd frontend && python app.py    # puerto 3000 (en otra terminal)"
