# NewtonLab Web · Backend

## Configuración local y despliegue

Seguí la [guía de entorno de la raíz](../../README.md): Docker Compose,
variables, inicialización explícita, pruebas y preparación para Heroku.
El backend carga su `.env` sin reemplazar variables del proceso.
Sin `DATABASE_URL`, cálculo y exportaciones siguen disponibles; historial retorna
503, sin fallback SQLite. PostgreSQL usa sesiones por solicitud y pool de hasta
cinco conexiones por proceso, liberado al apagar la aplicación.

## API y persistencia

`React → FastAPI → services/history.py → repositories/history.py → PostgreSQL`.
SQLAlchemy 2.x y psycopg 3, sesiones por solicitud, consultas parametrizadas,
timeout de conexión/consulta y errores sin trazas ni credenciales al cliente.

- `GET /api/history?q=...&limit=20&offset=0`: resumen, paginación y búsqueda literal
  sin tratar `%` o `_` como comodines. Límite 1–50; offset 0–10000.
- `POST /api/history`: `{request_id: UUID, parameters: CalculationRequest}`.
  Guardado explícito, resultados recalculados y validados por el servidor.
  La pareja propietario/request_id es única: reintentar el mismo guardado no
  duplica registros y usar ese ID con otros parámetros devuelve 409.
- `GET /api/history/{id}`: verifica propiedad, retorna resumen guardado y resultado
  reconstruido con el motor actual. No agrega otro registro.
- `DELETE /api/history/{id}` y `DELETE /api/history`: borran sólo registros propios.
  La UI pide confirmación. Un ID ajeno o inexistente responde 404 indistintamente.
- `POST /api/exports/pdf` y `/api/exports/csv`: reciben únicamente
  `CalculationRequest`, nunca resultados/IDs privados. Retornan un archivo adjunto.
  No leen historiales de terceros y no requieren una base de datos disponible.

Todas las rutas de historial exigen `X-History-Token`: 32 bytes aleatorios
generados por Web Crypto, codificados en 64 caracteres hexadecimales y persistidos
en localStorage. Se envía sólo como cabecera; PostgreSQL almacena su SHA-256.
Las respuestas de historial y archivos llevan `Cache-Control: no-store`.
Es una credencial de acceso anónimo, **no una cuenta autenticada**: perder/borrar
el almacenamiento pierde el acceso; compartir el token o sufrir XSS lo compromete.
No registrarlo en logs, URLs ni herramientas de analítica. HTTPS y protección de
tráfico siguen siendo requisitos previos a publicar el servidor.

`web_history` contiene UUID, fecha, hash de propietario, ID de solicitud, expresión
y un resumen JSONB tipado con parámetros, derivada, raíz, convergencia, motivo,
residuo, error y cantidad de iteraciones. No guarda muestras de curva ni pasos.
El índice propietario/fecha/ID soporta lectura ordenada; la búsqueda filtra siempre
por propietario. Restaurar puede cambiar los resultados si cambia el motor.

## Exportaciones

Reutiliza `app/services/export_service.py` y el modelo `Calculation` de escritorio
sin modificarlos ni acceder al SQLite personal. Importa sólo constantes de paleta
de `app/ui/theme.py`, sin Qt. PDF con ReportLab y Matplotlib Agg, fecha, fórmula,
resumen, gráfica y tabla completa paginada. CSV con `csv` y UTF-8 BOM: sólo columnas
fijas y números del servidor, sin texto del usuario interpretable como fórmula.
Si no se completaron iteraciones, CSV responde 422 y su botón está deshabilitado.

Cada exportación corre en el proceso limitado existente. El archivo se genera en
un `TemporaryDirectory`, se lee en memoria y se elimina antes de responder. No se
almacenan reportes permanentemente. El gráfico del PDF usa vista automática y la
primera tangente; no copia el zoom del navegador. El motor se recalcula al guardar
o exportar para no confiar en valores del cliente; navegar por pasos, abrir menús
y consultar listados no recalcula. Una repetición idempotente de guardado tampoco.

## Verificación

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_web_phase3.py tests/test_web_postgres.py tests/test_web_api.py
cd frontend
npm test
npm run build
```

Fase 4: las cuatro integraciones PostgreSQL antes omitidas pasaron contra
PostgreSQL 17.12 real; también ocho pruebas de entorno/CORS/TLS. Frontend:
21 pruebas y compilación TypeScript/Vite correctas. Persiste el aviso de tamaño
del chunk diferido Plotly y la deprecación de TestClient/httpx.

Se conserva la validación previa de PDF/CSV desde React y la inspección visual
de reportes de dos y cinco páginas. No se migró el SQLite personal ni se agregó
autenticación o despliegue público.
