"""Genera configuración exclusivamente local, sin mostrar claves ni reemplazar archivos."""
import argparse
from pathlib import Path
import secrets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5432)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1 y 65535.")
    root = Path(__file__).resolve().parents[1]
    paths = [root / ".env", root / "NewtonLab/backend/.env", root / "NewtonLab/frontend/.env"]
    if any(path.exists() for path in paths):
        parser.error("Ya existe un .env. No se modificó ninguno; revisá los archivos existentes y .env.example.")
    password = secrets.token_hex(32)
    database_url = f"postgresql+psycopg://newtonlab:{password}@127.0.0.1:{args.port}"
    content = [
        f"POSTGRES_USER=newtonlab\nPOSTGRES_PASSWORD={password}\nPOSTGRES_DB=newtonlab\nPOSTGRES_TEST_DB=newtonlab_test\nPOSTGRES_PORT={args.port}\n",
        f"DATABASE_URL={database_url}/newtonlab\nTEST_DATABASE_URL={database_url}/newtonlab_test\nNEWTONLAB_CALCULATION_TIMEOUT=10\nCORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173\n",
        "VITE_API_URL=\nNEWTONLAB_API_TARGET=http://127.0.0.1:8000\n",
    ]
    for path, text in zip(paths, content):
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    print("Configuración local creada en los tres .env; credenciales no mostradas.")


if __name__ == "__main__":
    main()
