# NewtonLab · Web Fase 4

Escritorio conservado en `NewtonLab/app` y en la rama `desktop-v1`. La web reutiliza
el motor Python; React sólo accede a FastAPI. No se realizó ningún despliegue.

## Entorno local (PowerShell, desde la raíz)

Requisitos: Python 3.12, Node.js 22.12+ y Docker Desktop iniciado con contenedores
Linux y Docker Compose. Sólo PostgreSQL se ejecuta en Docker.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r NewtonLab/backend/requirements-dev.txt
# Sólo la primera vez; rechaza cualquier .env existente sin sobrescribirlo:
.\.venv\Scripts\python.exe scripts/configure_local.py
docker compose up -d --wait postgres
# Idempotente, también sirve si el volumen ya existía:
docker compose exec -T postgres sh /docker-entrypoint-initdb.d/10-test-database.sh
cd NewtonLab
..\.venv\Scripts\python.exe -m backend.app.database
..\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

En otra terminal, desde la raíz:

```powershell
cd NewtonLab/frontend
npm ci
npm run dev
```

Abrí http://127.0.0.1:5173. El generador crea tres `.env` ignorados por Git con
una contraseña aleatoria de desarrollo. Alternativamente copiá cada `.env.example`
y completá los valores consistentes. Para otro puerto usá `--port 5434` al generar;
si ya existe configuración, ajustá `POSTGRES_PORT` y ambas URLs manualmente.
Cambiar la contraseña en `.env` **no cambia** la del volumen ya inicializado.
No borres el volumen para corregir credenciales.

PostgreSQL queda en `127.0.0.1:5432`, con volumen nombrado y healthcheck TCP.
Imagen oficial fijada a `postgres:17.12-bookworm` ([imagen oficial](https://hub.docker.com/_/postgres)).
El script crea `newtonlab_test` sólo si falta, distinta de `newtonlab`.
La orden Python crea tablas/índices faltantes únicamente en `DATABASE_URL`;
el arranque de FastAPI no inicializa esquemas. No modifica tablas existentes:
futuros cambios del esquema requerirán migración.

## Variables

| Archivo/servicio | Variables |
| --- | --- |
| `.env` raíz / Compose | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_TEST_DB`, `POSTGRES_PORT` |
| `NewtonLab/backend/.env` / FastAPI | `DATABASE_URL`, `TEST_DATABASE_URL` (sólo pruebas), `NEWTONLAB_CALCULATION_TIMEOUT`, `CORS_ORIGINS` |
| `NewtonLab/frontend/.env` / Vite | `VITE_API_URL`, `NEWTONLAB_API_TARGET` (proxy local) |

FastAPI carga su `.env` sin reemplazar variables del proceso. CORS acepta orígenes
HTTP/HTTPS explícitos separados por comas, sin rutas; vacío no permite acceso
desde otro origen. Permite `X-History-Token` y expone `Content-Disposition` para
descargas. El token anónimo viaja en cabecera, sin cookies; nunca se imprime.

Con `VITE_API_URL` vacío se usa `/api` y el proxy local existente. En producción
usá `https://<backend>/api`: Vite incorpora el valor **al compilar**; cambiarlo
después exige otro build. Las variables `VITE_` son públicas: ninguna contiene
credenciales PostgreSQL. `NEWTONLAB_API_TARGET` sólo configura el servidor Vite.

## Pruebas y parada

Desde `NewtonLab`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_web_postgres.py tests/test_web_configuration.py
cd frontend
npm test
npm run build
```

Las integraciones usan `TEST_DATABASE_URL`, rechazan la base principal y crean
un esquema aleatorio que eliminan al terminar. No uses bases personales.
Verificación local: cuatro integraciones PostgreSQL, ocho pruebas de configuración,
tres regresiones API y 21 pruebas frontend aprobadas; build TypeScript/Vite correcto.
Desde React se guardó un cálculo, se reinició PostgreSQL y se restauró el resultado
tras recargar el navegador, usando CORS y la URL directa del backend. El registro
de demostración permanece en el historial local. No se probaron servicios remotos.
Desde la raíz, `docker compose stop postgres` detiene sin perder datos;
`docker compose up -d --wait postgres` vuelve a iniciarlo. `docker compose down`
también conserva el volumen; **no añadas `-v`**.

## Preparación para despliegue manual

Heroku detectará Python mediante `requirements.txt`; `.python-version` selecciona
3.12 y `Procfile` inicia Uvicorn en `0.0.0.0:$PORT` desde `NewtonLab`. Sólo instala
dependencias backend; no necesita Qt ni el build de React. Ver
[soporte Python de Heroku](https://devcenter.heroku.com/articles/python-support).

Cuando crees los servicios manualmente, configurá en Heroku `DATABASE_URL` del
proveedor, `CORS_ORIGINS=https://<frontend>` y `NEWTONLAB_CALCULATION_TIMEOUT=10`.
No configures `TEST_DATABASE_URL` en producción. Se aceptan URLs `postgres://`
y `postgresql://`, normalizadas a psycopg 3, conservando parámetros TLS como
`sslmode=require` o `verify-full` según el proveedor y sus certificados.
El pool tiene máximo cinco conexiones por proceso; dimensioná los procesos
según el límite del proveedor. Inicializá el esquema explícitamente con
`cd NewtonLab && python -m backend.app.database` sólo en la base elegida.

En el hosting frontend, raíz `NewtonLab/frontend`, configurá
`VITE_API_URL=https://<backend>/api`, ejecutá `npm ci && npm run build` y publicá
`dist`. Ambos servicios deben usar HTTPS. Verificá después salud, CORS,
guardado/restauración y descargas con las URLs reales. No se crearon servicios
remotos ni se ejecutaron comandos de publicación en esta fase.

Contrato del historial y exportaciones: [backend](NewtonLab/backend/README.md).
Organización React: [frontend](NewtonLab/frontend/README.md).
