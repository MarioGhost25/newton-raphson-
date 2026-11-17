# NewtonLab Web · Frontend

Desde esta carpeta: `npm ci`, `npm run dev`, `npm test`, `npm run build`.
Iniciá FastAPI como indica la [guía de entorno](../../README.md). El proxy `/api` conserva la
configuración de Fase 1. El historial usa PostgreSQL a través de la API; no se agregó despliegue.

Fase 3: `HistoryAccess` carga el diálogo de historial bajo demanda; listado paginado,
búsqueda explícita, restauración y borrados confirmados. `CalculationActions`
guarda explícitamente con ID idempotente y descarga PDF/CSV del servidor.
`ExerciseLibrary` carga los ocho ejemplos tipados de `data/exercises.ts` sin calcular.
Los servicios HTTP nuevos están en `services/history.ts` y `services/exports.ts`.
El token secreto de historial persiste en localStorage; borrarlo pierde el acceso,
y compartirlo compromete el historial. No equivale a una cuenta autenticada.
El estado de diálogos/descargas es local: no vuelve a renderizar Plotly.
Al restaurar, `useCalculation.load` actualiza los datos e incrementa la versión para
reiniciar la selección y limpiar la reproducción anterior. Se conserva la paleta.

## Organización

- `components/ui/`: Button, Input, Table y Dialog del registro oficial
  [shadcn/ui](https://ui.shadcn.com/docs/installation/vite), con Tailwind CSS 4.
  `components.json` y el alias `@` permiten incorporar componentes adicionales.
- `components/`: formulario, resumen, tabla y gráfica. Etiquetas asociadas,
  errores por campo, navegación por teclado, foco de diálogo administrado por
  Radix y tabla accesible como alternativa a la gráfica.
- `hooks/`: estado del cálculo y reproducción. Editar invalida resultados;
  cancelar/desmontar aborta la espera e ignora respuestas obsoletas. Cancelar
  en el navegador no detiene un proceso ya iniciado en el servidor, que conserva
  su límite de tiempo. Los timers se limpian al pausar, editar o desmontar.
- `services/api.ts`: solicitudes HTTP, timeout y validación del JSON recibido.
- `types/`: contrato estricto de la API; `lib/plot.ts`: geometría de visualización
  a partir de los pasos del servidor, sin parser ni solver en JavaScript.
- `styles.css`: paleta Black & Grey compartida por Tailwind y Plotly. Los colores
  adicionales se reservan para las gráficas.

Plotly básico se carga con `React.lazy` sólo al recibir un resultado. Se serializan
actualizaciones, se omiten las obsoletas y se liberan gráfico, observador de tamaño
y animación al desmontar, incluso en StrictMode. Memoización localizada en gráfica,
resumen y filas; no se agregaron gestores globales de estado ni librerías de tablas.

La tabla y la tangente comparten selección. Hay reproducción con tres velocidades,
zoom rectangular y restauración de vista. La curva conserva las 401 muestras del
servidor; el zoom no remuestrea y no garantiza detectar todas las discontinuidades.
El archivo diferido de Plotly pesa aproximadamente 408 kB gzip; la advertencia de
tamaño de Vite se conserva visible. No forma parte del JavaScript inicial.

Verificado inicialmente: 12 pruebas (cancelación, respuestas tardías, fallos HTTP, contratos,
timers, geometría, foco y teclado), TypeScript estricto y build. Flujo real en
navegador para convergencia, no convergencia, raíz inicial exacta y sintaxis inválida;
distribución revisada a 1280 y 390 px. El backend y el escritorio no se modificaron.

Fase 4: `VITE_API_URL` configura el endpoint público terminado en `/api`,
incorporado durante el build; vacío conserva el proxy `NEWTONLAB_API_TARGET`.
Las solicitudes no envían cookies y conservan la cabecera de historial anónimo.
Verificados 21 tests y build TypeScript/Vite. Configuración y despliegue manual
en la guía de entorno, sin modificar Plotly ni la interfaz.
