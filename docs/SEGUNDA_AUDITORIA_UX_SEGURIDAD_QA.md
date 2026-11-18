# Segunda auditoria adversarial - Revision posterior a cambios

**Fecha:** 2026-11-18  
**Alcance:** revision estatica de codigo publicado, sin prueba de ejecucion en Windows ni verificacion visual real.  
**Dictamen:** **NO APROBADO PARA PILOTO**. Se implementaron mitigaciones, pero permanecen bloqueantes. La existencia de pruebas en el repositorio no demuestra que hayan pasado.

## 1. UX/UI (segunda pasada)

| ID | Estado | Evidencia y pendiente |
|---|---|---|
| UX-01 | Parcial | Cuatro pestañas y resumen por carpeta implementados; no existe explorador jerarquico real ni estados por subarbol. |
| UX-02 | Parcial | Paginacion SQL de 200 filas y busqueda; falta conteo de resultados y controles de navegacion completos. |
| UX-03 | Parcial | Cancelacion cooperativa en motor e interfaz; falta probar cancelacion durante carpetas grandes y cierre. |
| UX-04 | Parcial | Exclusiones por ruta relativa, mejor que nombre; todavia texto libre, sin selector visual ni previsualizacion. |
| UX-05 | Implementado sin validar | Dialogo de confirmacion muestra raiz, corte, exclusiones y protecciones. |
| UX-06 | Parcial | Estado PARCIAL e incidencias visibles, pero solo primeras 100 incidencias y resumen parcial. |
| UX-07 | Implementado sin validar | Atajos 3/5/7/10 anos y fecha manual. |
| UX-08 | Parcial | Busqueda y paginacion; barra indeterminada y conteos, sin avance porcentual falso. |
| UX-09 | Pendiente | Sin prueba de accesibilidad, teclado, escalado ni contraste. |

**Observaciones nuevas:** el resumen agrupa por carpeta inmediata, no consolida subcarpetas; la pestaña de Revision no exporta aun Excel; una corrida nueva no conserva consulta historica en UI.

## 2. Seguridad y QA (segunda pasada)

| ID | Estado | Evidencia y pendiente |
|---|---|---|
| SEC-01 | Mitigado sin validar | El nuevo `scan_to_sqlite` llama a `validate_local_root` internamente; requiere pruebas Windows de rutas especiales. |
| SEC-02 | Parcial | Se revisan ancestros y reparse points. Faltan pruebas con junctions, SUBST, rutas DOS especiales y cambios concurrentes. |
| SEC-03 | Mitigado sin validar | Se almacena inventario en SQLite y se consulta por paginas. Falta benchmark y politica de espacio libre/limite de base. |
| SEC-04 | Mitigado sin validar | Evento de cancelacion consultado durante el recorrido; faltan pruebas de latencia e interrupciones reales. |
| SEC-05 | Parcial | Estado PARCIAL ante incidencias; aun no hay cobertura por subarbol ni bloqueo de aprobaciones (Excel no implementado). |
| SEC-06 | Mitigado sin validar | Mensajes del hilo secundario pasan por `Queue`; falta prueba de cierre/cancelacion y ventanas lentas. |
| SEC-07 | Parcial | Nuevos tests Windows y `compileall` en workflow; sin resultados de ejecucion verificados. |
| SEC-08 | Parcial | `run_id` existe en resumen, pero no se guarda en DB con metadatos de corrida y hash de manifiesto. |
| SEC-09 | Pendiente | Errores contienen rutas y excepciones; no publicar logs, inventarios ni capturas reales. |
| SEC-10 | Pendiente | Fechas locales `fromtimestamp` y `st_ctime` requieren pruebas de huso horario y bordes de fecha. |

### Hallazgos adicionales de segunda pasada

- **SEC-11 / Alta:** un atacante o proceso concurrente puede cambiar un directorio entre validacion y lectura (TOCTOU). El piloto es de solo lectura, pero la garantia de no atravesar rutas redireccionadas requiere defensa adicional y pruebas Windows. No afirmar aislamiento absoluto.
- **SEC-12 / Alta:** `scan_to_sqlite` permite que un llamador programe el destino de base de datos fuera del espacio temporal previsto; la UI usa temporal seguro, pero el servicio debe restringir ubicaciones y evitar escribir en rutas de red. La DB no debe crearse hasta validar tambien el destino.
- **SEC-13 / Media:** la UI mantiene la base temporal solo hasta cerrar; si la app termina inesperadamente se pierde el inventario, sin opcion de reanudar. Es un riesgo de disponibilidad, no de borrado.
- **SEC-14 / Media:** la politica de exclusiones por ruta exacta requiere comprobacion de rutas con mayusculas, Unicode, separadores y nombres reservados.
- **QA-01 / Alta:** no se dispone aun de evidencia de tests exitosos en Windows. Los checks de estado del commit no devolvieron resultados; esto no demuestra ni exito ni fallo.

## 3. Criterios de salida pendientes

1. Ejecutar CI en Windows y revisar logs; corregir fallos.
2. Completar bloqueos de origen y destino locales, incluidos junctions, SUBST y rutas UNC.
3. Incorporar proteccion ante cambio concurrente de rutas y prueba de ese escenario.
4. Ensayar 1k, 10k, 100k archivos ficticios; registrar tiempo, RAM y espacio SQLite.
5. Resolver experiencia de explorador por carpetas y estados parciales.
6. Realizar pruebas visuales de accesibilidad y cancelacion real en Windows.
7. Repetir auditorias con evidencia de pruebas, no solo inspeccion de codigo.

**Regla de liberacion:** no generar ni distribuir EXE de piloto como validado hasta aprobar los puntos anteriores. No hay codigo de copia, movimiento ni eliminacion de originales.
