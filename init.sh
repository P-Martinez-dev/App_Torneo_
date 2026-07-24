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

echo "==> Instalando dependencias..."
pip install --upgrade pip --quiet
pip install flask mysql-connector-python python-dotenv requests --quiet

echo "==> Congelando dependencias en requirements.txt..."
pip freeze > requirements.txt

echo "==> Creando backend/.env (si no existe)..."
if [ ! -f "backend/.env" ]; then
    cat > backend/.env <<EOF
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=torneos
FLASK_DEBUG=True
FLASK_PORT=5000
SECRET_KEY=dev
EOF
    echo "   backend/.env creado. Completá DB_USER / DB_PASSWORD con tus datos de MySQL."
else
    echo "   backend/.env ya existe, no se sobreescribe."
fi

echo "==> Creando frontend/.env (si no existe)..."
if [ ! -f "frontend/.env" ]; then
    cat > frontend/.env <<EOF
API_BASE_URL=http://localhost:5000
FLASK_DEBUG=True
FLASK_PORT=3000
SECRET_KEY=dev
EOF
    echo "   frontend/.env creado."
else
    echo "   frontend/.env ya existe, no se sobreescribe."
fi

echo ""
read -p "==> ¿(Re)inicializar la base de datos MySQL desde cero? Esto BORRA todo lo que tengas en 'torneos'. [s/N] " respuesta
if [[ "$respuesta" =~ ^[sS]$ ]]; then
    read -p "    Usuario de MySQL: " db_user
    mysql -u "$db_user" -p -e "DROP DATABASE IF EXISTS torneos; CREATE DATABASE torneos;"
    mysql -u "$db_user" -p torneos < schema.sql
    echo "    Base de datos 'torneos' recreada desde cero con schema.sql."
else
    echo "    Se salteó la inicialización de la base. Podés correrla después con:"
    echo "      mysql -u tu_usuario -p -e \"DROP DATABASE IF EXISTS torneos; CREATE DATABASE torneos;\""
    echo "      mysql -u tu_usuario -p torneos < schema.sql"
fi

echo ""
echo "==> Listo. Para levantar el proyecto:"
echo "    source venv/bin/activate"
echo "    cd backend  && python app.py    # puerto 5000"
echo "    cd frontend && python app.py    # puerto 3000 (en otra terminal)"