# NewtonLab · Fase 4

Aplicación local para Windows 11 con Python 3.11+, PySide6, SymPy, NumPy, Matplotlib y ReportLab.
Motor matemático independiente de la interfaz. No utiliza servidor web.

## Instalación y ejecución

Desde la carpeta que contiene `NewtonLab`, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r NewtonLab\requirements.txt
.\.venv\Scripts\python.exe NewtonLab\main.py
```

Pruebas:

```powershell
cd NewtonLab
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
..\.venv\Scripts\python.exe -m pytest -q
```

## Uso y alcance

### Historial, biblioteca y exportaciones

- **Biblioteca de ejercicios:** elegí uno de los ocho ejercicios en el selector del
  panel izquierdo. Se cargan función, punto inicial, tolerancia y límite; la
  descripción explica qué demuestra. Podés editar los valores. El cálculo se
  ejecuta únicamente al presionar Calcular raíz o su atajo.
- **Acciones > Guardar cálculo:** guarda explícitamente el cálculo actual,
  convergente o fallido. No hay guardado automático. La acción se deshabilita
  después de guardar para evitar duplicados por clics repetidos.
- **Historial:** muestra fecha local, función, punto inicial, raíz confirmada y
  estado. Permite búsqueda literal por función, abrir con botón o doble clic,
  eliminar y vaciar con confirmación. Abrir restaura entradas y vuelve a ejecutar
  el motor actual para reconstruir tabla y gráfica; no inserta otro registro.
  Por eso resultados antiguos pueden cambiar si se actualiza el motor.
- **Acciones > Exportar PDF:** elegí destino y nombre. Incluye parámetros,
  derivada, resultado, residuo, error, fórmula, gráfica de 200 dpi y tabla completa
  con encabezados repetidos. La gráfica usa una figura independiente, rango
  automático y la tangente seleccionada; no modifica el zoom ni la selección
  visibles. Los resultados fallidos se identifican sin afirmar una raíz.
- **Acciones > Exportar CSV:** exporta los seis campos de cada paso con UTF-8 BOM,
  delimitador coma, punto decimal y precisión de los floats originales. En Excel
  con otra configuración regional, usá Datos > Desde texto/CSV y elegí coma como
  delimitador. Si no hay pasos, se avisa sin generar un archivo vacío.

Los destinos se eligen mediante diálogos Qt y se confirman al finalizar. Los
archivos se escriben primero en un temporal del directorio elegido y se reemplazan
solo al completar la escritura. Los fallos de escritura se informan en la interfaz.

SQLite guarda entradas y resumen (UUID, fecha UTC, función, derivada, parámetros,
raíz confirmada o NULL, estado y cantidad de pasos), sin duplicar el historial de
iteraciones. En Windows se utiliza `%LOCALAPPDATA%\NewtonLab\history.sqlite3`.
La base se crea al guardar o consultar, nunca al iniciar la aplicación. Fuera de
Windows, sin LOCALAPPDATA, se utiliza `~/.local/share/NewtonLab/`. Las pruebas
inyectan una base temporal y nunca escriben en el historial real del usuario.

Introducí una función, el punto inicial, una tolerancia positiva y un máximo de
1 a 1000 iteraciones. `x**2 - 2`, con x₀ = 1.5, aproxima √2.
La interfaz muestra función introducida, derivada simbólica, aproximación, valor
con signo de f(x), error final, número de iteraciones y estado de convergencia.
Al editar parámetros se borran el resultado y la tabla anteriores para evitar
confusiones. La validación se muestra junto al campo incorrecto.

La tabla presenta todos los pasos completados: n, xₙ, f(xₙ), f′(xₙ), xₙ₊₁ y
error absoluto. La numeración conserva el índice del motor, comenzando en 1.
Los valores visibles tienen hasta 12 cifras significativas; el tooltip de cada
celda y la copia conservan la precisión del float almacenado.
Seleccioná filas con clic, Ctrl o Mayús; copiá con Ctrl+C o el menú contextual.
Las columnas se pueden redimensionar y la tabla admite desplazamiento horizontal
y vertical. Si el motor falla después de algunos pasos, se muestran únicamente
los pasos completados en ese cálculo. Una raíz inicial exacta tiene cero pasos
y error final «—», porque no se realizó ninguna actualización.

Enter en los campos o Ctrl+Enter ejecuta el cálculo. «Limpiar» o Ctrl+L vacía la
función, restablece x₀=1.5, tolerancia=1e-8 y límite=100, y elimina los resultados,
la selección y los mensajes de error. Los divisores permiten ajustar el ancho del
panel lateral y el espacio entre la gráfica y la tabla. En ventanas
pequeñas, los paneles incorporan scroll. El cálculo continúa siendo síncrono;
expresiones simbólicas costosas pueden mantener ocupada la interfaz.

## Gráfica y recorrido de Newton

La gráfica muestra f(x), los ejes, las aproximaciones sobre el eje X y la raíz final
solo si hubo convergencia. La tangente y sus puntos usan la iteración almacenada
por el motor, sin ejecutar otra vez Newton. El panel contextual muestra los
valores y su sustitución en la fórmula. La línea auxiliar apunta al siguiente
valor de f(x) cuando existe otro paso completado.

Seleccioná una fila o usá Primera, Anterior, Siguiente y Última. Ambos controles
mantienen el mismo índice. Reproducir/Pausar utiliza QTimer; Reiniciar vuelve al
primer paso y queda pausado. Las velocidades son Lenta (1600 ms), Normal (900 ms)
y Rápida (300 ms). La reproducción se detiene al finalizar, editar parámetros,
calcular nuevamente, limpiar o cerrar. Una raíz inicial exacta no tiene tangente.

Zoom permite arrastrar un rectángulo; Desplazar permite mover los ejes. La rueda
acerca o aleja alrededor del cursor. Restaurar vista recupera el intervalo del
recorrido original. Se reutilizan la figura y el canvas con `draw_idle()`;
los cambios de intervalo se remuestrean tras 100 ms para agrupar eventos.

El muestreo vectorizado interpreta únicamente los nodos SymPy admitidos, sin
ejecutar cadenas ni compilar expresiones del usuario. Se usan 1601 muestras por
intervalo, se omiten valores no reales/no finitos y se separan cruces de polos
detectados en denominadores y tangentes trigonométricas. Se filtran también
saltos abruptos de forma conservadora. El muestreo finito no garantiza detectar
todas las singularidades ni oscilaciones de frecuencia arbitraria; al hacer
zoom se recalcula la curva con mayor resolución local.

El límite visual es ±1e12; los datos originales siguen disponibles en la tabla.
La escala vertical inicial usa percentiles de la curva, incluye y=0 y los valores
representables de las iteraciones. Los avisos de visualización no cambian el
estado matemático de convergencia. Si todo el intervalo está fuera del dominio,
se conserva el resultado y se muestra un aviso en lugar de inventar una curva.

Se admiten `x`, `pi`, `e`, `E`, números, `+ - * / **`, paréntesis y las funciones
de un argumento `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sinh`, `cosh`, `tanh`,
`exp`, `log` (logaritmo natural), `sqrt` y `abs`. Los ángulos se expresan en radianes.
La multiplicación debe ser explícita. Los exponentes se limitan a números simples
entre -100 y 100 o `x`; otras exponenciales pueden escribirse con `exp(...)`.
El analizador recorre una lista cerrada de nodos AST, sin ejecutar texto del usuario
con `eval`, `exec`, `parse_expr` ni `sympify` de cadenas. Limita longitud, profundidad
y cantidad de nodos; no constituye un aislamiento de recursos para entradas hostiles.

El motor calcula con números reales de precisión de máquina. Exige tanto error
absoluto como residuo ≤ tolerancia; una raíz inicial exacta termina sin pasos.
Una derivada de magnitud ≤ 1e-12 detiene el cálculo (umbral configurable en `solve`).
El umbral es absoluto: funciones con escalas extremas pueden requerir ajustarlo.
Se distinguen dominio inválido, valores no finitos y agotamiento de iteraciones.
Los pasos completados se conservan en dataclasses inmutables, incluso ante fallo
posterior; un paso que no puede evaluarse no se incorpora al historial.
Newton no garantiza convergencia para cualquier función o punto inicial.

## Estructura y diseño

- `app/core/expression_parser.py`: gramática restringida y derivación.
- `app/core/newton_raphson.py`: algoritmo y comprobaciones.
- `app/core/models.py`: estados, pasos y resultados tipados.
- `app/core/plot_data.py`: muestreo, intervalos visuales y geometría de tangentes.
- `app/ui/main_window.py`: espacio de trabajo adaptable, validación y resultados.
- `app/ui/iteration_table.py`: modelo Qt del historial, formato y copia de filas.
- `app/ui/plot_widget.py`: canvas Qt/Matplotlib, interacción y reproducción.
- `app/ui/history_dialog.py`: búsqueda, restauración y eliminación de registros.
- `app/services/history_service.py`: acceso SQLite y resumen tipado del cálculo.
- `app/services/export_service.py`: reportes PDF y exportación CSV, sin dependencia de Qt.
- `app/data/examples.py`: biblioteca de ocho ejercicios.
- `app/ui/theme.py`: única configuración de colores de interfaz y gráfica.
- `app/ui/styles.qss`: superficies planas y controles monocromáticos.
- `tests/test_newton_raphson.py`: pruebas del motor y entradas.
- `tests/test_ui.py`: cálculo, validación, limpieza, atajos, tabla y distribución.
- `tests/test_iteration_table.py`: formato, precisión y contrato del modelo Qt.
- `tests/test_plot_data.py`: tangentes, dominio, discontinuidades y escalas.
- `tests/test_plot_widget.py`: sincronización, navegación y ciclo de reproducción.
- `tests/preview_gui.py`: comprobación nativa y capturas para revisión visual.
- `tests/test_phase4.py`: historial, biblioteca y exportaciones con archivos temporales.
- `tests/preview_phase4.py`: comprobación nativa y reportes de prueba, con base temporal.

Verificación de Fase 4: base inicial de 86 pruebas aprobadas; suite ampliada a
110 pruebas. Incluye historial, restauración sin duplicados, ocho ejercicios,
CSV con precisión completa, PDF convergente/fallido, tablas multipágina y errores
de escritura, además de las comprobaciones de fases anteriores.
Se revisaron visualmente el reporte convergente de dos páginas y el reporte sin
convergencia de cinco páginas, además del historial y la ventana en Windows.
Se abrió la ventana nativa en Windows y se revisaron capturas en 900×700,
1240×860 y 1600×1000 (unidades lógicas de Qt). El motor y su API no se modificaron.

La imagen de referencia recibida guía la distribución: parámetros y resultados
compactos a la izquierda, gráfica dominante y tabla debajo. Se mantiene la paleta
BLACK & GREY, con colores reservados a los elementos matemáticos.

Pendiente para Fase 5: pruebas integrales finales, optimización y empaquetado para
Windows. No se implementaron instaladores, actualizaciones, telemetría ni servicios
externos. El motor matemático permanece sin cambios.
