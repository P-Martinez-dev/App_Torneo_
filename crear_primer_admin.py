"""
Crea el primer admin. Hace falta correr esto UNA sola vez (a mano, por
consola) porque para crear un admin desde la app hace falta estar
logueado como admin -- y todavía no hay ninguno.

Corré esto con el backend levantado (puerto 5000).

Uso:
    python3 crear_primer_admin.py
"""
import getpass
import os
import requests

BASE_URL = "http://localhost:5000"
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-key-cambiar-en-produccion")


def main():
    print("=== Crear el primer admin ===")
    usuario = input("Usuario: ").strip()
    password = getpass.getpass("Contraseña (mínimo 8 caracteres, no se muestra en pantalla): ")

    resp = requests.post(
        f"{BASE_URL}/admin",
        json={"usuario": usuario, "password": password},
        headers={"X-Internal-Key": INTERNAL_API_KEY},
    )

    if resp.status_code == 201:
        print(f"Listo, admin '{usuario}' creado. Ya podés loguearte en la app.")
    else:
        print(f"Error ({resp.status_code}): {resp.json().get('error', resp.text)}")


if __name__ == "__main__":
    main()
