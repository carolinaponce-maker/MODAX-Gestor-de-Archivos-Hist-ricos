# Auditorias adversariales - Entrega 1

**Fecha:** 2026-11-18  
**Estado:** revision estatica; no se ha ejecutado prueba funcional Windows, prueba de penetracion ni auditoria externa.  
**Decision:** no liberar ejecutable piloto hasta cerrar bloqueantes y verificar pruebas.

## A. UX/UI - revision senior adversarial

**Objetivo de interfaz aprobado:** cuatro pantallas: (1) Configuracion, (2) Analisis en curso, (3) Resultados, (4) Revision y exportacion.

| ID | Severidad | Hallazgo | Criterio de cierre |
|---|---|---|---|
| UX-01 | Critica | Sin arbol ni resumen por carpetas | Navegacion jerarquica y clasificacion antigua/reciente/mixta; estados parcial/error/vacia |
| UX-02 | Alta | Vista limitada a 3000 filas sin busqueda | Paginacion/virtualizacion, filtros y acceso a todo el inventario |
| UX-03 | Alta | No se puede cancelar | Cancelacion cooperativa y estado final diferenciado |
| UX-04 | Alta | Exclusiones por nombre ambiguas | Seleccion de rutas relativas y vista previa del alcance |
| UX-05 | Alta | Sin revision previa de configuracion | Pantalla de confirmacion con raiz, fecha, exclusiones y protecciones |
| UX-06 | Alta | Errores reducidos a contador | Detalle de incidencias, cobertura y estado parcial visible |
| UX-07 | Media | Corte solo manual | Atajos 3/5/7/10 anos, personalizado y fecha explicita |
| UX-08 | Media | Sin busqueda/ordenamiento/progreso | Busqueda, filtros, orden, progreso verificable sin porcentaje inventado |
| UX-09 | Media | Accesibilidad no comprobada | Pruebas teclado, foco, contraste, escalado y resoluciones |

## B. Ciberseguridad y QA - revision senior adversarial

**Alcance inspeccionado:** `gestor_historicos/core.py`, `gestor_historicos/app.py`, `tests/test_core.py`, y reglas del documento maestro. **Metodo:** lectura de codigo, razonamiento de escenarios adversos. **No** se ejecutaron pruebas de penetracion ni se valido un EXE.

| ID | Severidad | Hallazgo verificable | Correccion y evidencia requerida |
|---|---|---|---|
| SEC-01 | Critica | `inventory_folder()` confia en que el llamador valido la raiz. Una llamada directa puede omitir la barrera local. | Validacion obligatoria en la capa de servicio, independiente de UI; tests de llamada directa a UNC/unidad mapeada |
| SEC-02 | Alta | `validate_local_root()` comprueba enlace en la ruta final, no todos sus ancestros; una ruta puede atravesar junction/reparse point. | Resolver y validar todos los componentes, bloquear rutas que salgan del disco permitido y probar junctions/links de ancestros |
| SEC-03 | Alta | Se guardan todos los registros en lista y se ordenan al final; no hay presupuesto de memoria ni streaming. | Inventario incremental/persistencia temporal segura, paginacion y prueba de volumen |
| SEC-04 | Alta | No hay cancelacion cooperativa ni limite de duracion o politica de interrupcion. | Token de cancelacion, finalizacion segura y estado parcial/cancelado |
| SEC-05 | Alta | Errores de lectura no invalidan explicitamente la completitud del inventario. | Estados completo/parcial/fallido; prohibir decisiones posteriores sobre zonas no verificadas |
| SEC-06 | Media | `threading.Thread` usa `self.after()` desde el hilo de trabajo; comportamiento debe verificarse ante cierre de ventana/cancelacion. | Cola de mensajes consumida por hilo principal, pruebas de cierre y errores |
| SEC-07 | Media | Solo dos pruebas unitarias; faltan limites de fecha, permisos, rutas, caracteres, archivos modificados durante recorrido, volúmenes y resiliencia. | Matriz de pruebas automatizadas Windows y ejecucion en GitHub Actions con evidencia de resultados |
| SEC-08 | Media | El motor no tiene identificador de corrida ni manifiesto inmutable para auditar un inventario. | ID unico, parametros, raiz canonica, fechas, conteos, incidencias, hash de manifiesto en fases futuras |
| SEC-09 | Media | La interfaz muestra la ruta y errores potencialmente sensibles; el repo es publico. | No subir logs ni inventarios reales; separar datos locales del codigo y redactar errores compartidos |
| SEC-10 | Media | La fecha de creacion se toma de `st_ctime`; semantica y zona horaria requieren validacion Windows. | Documentar semantica Windows, guardar marcas temporales precisas y probar fechas de corte |

### Riesgos de fases futuras (no son vulnerabilidades activas del prototipo actual)

- **Excel:** validar esquema, identidad, metadatos, duplicados, formulas, rutas y autorizaciones; no confiar en celdas editables como prueba de integridad.
- **Copia:** evitar TOCTOU, escapes de ruta, colision de nombres, destino dentro del origen y sobreescritura; copiar a archivo temporal y publicar atomicamente tras verificar SHA-256, segun capacidades del sistema de archivos.
- **Reanudacion:** manifiestos persistentes y estados por archivo; no marcar exitos por mera existencia del destino.
- **Eliminacion:** piloto solo simulacion; en produccion requerira procedimiento separado, aprobacion de Sistemas y respaldo/restauracion probado.
- **Cadena de suministro:** fijar versiones de dependencias y GitHub Actions, permisos minimos del workflow, analizar dependencias y verificar artefactos antes de distribuir.

## C. Criterios de liberacion de la primera entrega

1. Ninguna ruta UNC, unidad mapeada o acceso por reparse point permitido en piloto, comprobado en Windows.
2. El motor rechaza entradas prohibidas incluso cuando se invoca sin interfaz.
3. Cero funciones de mover, sobrescribir o eliminar originales.
4. Cancelacion y cierre de ventana no provocan bloqueo ni estado falsamente completo.
5. Errores de acceso y archivos omitidos visibles; inventarios parciales no se etiquetan completos.
6. Inventario escalable con mediciones documentadas en carpetas ficticias crecientes.
7. Pruebas automatizadas exitosas y registro del commit y artefacto EXE verificados.
8. Revisión manual UX de las cuatro pantallas con navegacion por teclado.

## D. Orden recomendado de correccion

1. **Bloqueantes SEC-01, SEC-02, SEC-05:** frontera de confianza y completitud.
2. **SEC-03, SEC-04, SEC-06:** escalabilidad, cancelacion y concurrencia.
3. **UX-01 a UX-06:** flujo comprensible, navegacion y visibilidad de errores.
4. **SEC-07 a SEC-10 y UX-07 a UX-09:** ampliar pruebas, trazabilidad y accesibilidad.
5. Generar EXE, ejecutar pruebas locales y reevaluar hallazgos antes de Entrega 2.

**Nota:** severidad estimada para priorizar correcciones; no representa explotabilidad demostrada. Ningun hallazgo se considera cerrado solo por documentarlo.
