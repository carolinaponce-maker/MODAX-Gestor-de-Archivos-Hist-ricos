# MODAX | Documento Maestro del Gestor de Archivos Historicos

**Version publica de consulta 0.11 | 18/11/2026 | Piloto local**

> Documento de trabajo para compartir con el equipo. Adaptacion publica del Documento Maestro v0.10: se omiten rutas de infraestructura, nombres personales y detalles internos sensibles. No sustituye el documento interno completo. Las estructuras indicadas son **parciales**, no un inventario exhaustivo.

## 1. Objetivo y alcance

Aplicacion visual para Windows, inicialmente ejecutable desde una PC, destinada a analizar archivos historicos, elaborar un inventario revisable, copiar exclusivamente archivos aprobados a un repositorio historico y, en una fase independiente, gestionar una eliminacion autorizada. El piloto se ejecuta **fuera del servidor**, con carpetas y archivos ficticios. En el piloto la eliminacion es **simulada** y no borra fisicamente ningun archivo.

La fecha de ultima modificacion es un indicador tecnico de antiguedad, **no una prueba de que un archivo haya dejado de usarse**.

### Arquitectura por modulos

1. **Analisis de solo lectura:** seleccion de raiz, recorrido recursivo, exclusiones, protecciones, clasificacion, resultados y Excel.
2. **Copia y verificacion:** importar aprobaciones, validar identidad/metadatos, preparar lote, copiar sin sobrescribir y comparar SHA-256 en el 100 % de archivos.
3. **Eliminacion independiente:** requerir aprobacion especifica, verificar nuevamente y mostrar confirmacion; en el piloto solo simular. Responsable provisional: area de Diseno.

No utilizar opciones de Robocopy que muevan o eliminen origen (por ejemplo, `/MOV`, `/MOVE`, `/MIR`). La compresion no forma parte del alcance.

## 2. Estructuras de carpetas: modelo de referencia para programacion

Las dos areas tienen organizacion heterogenea. No deben codificarse nombres, profundidades ni convenciones de carpetas. Los arboles siguientes son **ejemplos anonimizados** de la organizacion observada, no rutas completas del servidor.

### Arbol A: area de Diseno Grafico

```text
AREA_DISENO_GRAFICO/
|-- HISTORICO_DISENO/
|   |-- CATALOGO_DIGITAL/
|   |-- COMUNICACION/
|   |-- FICHAS_TECNICAS_TEMPLATES/
|   |-- GEOMETRALES/
|   |-- MOCKUPS/
|   |-- ORDEN_COMPRA_A/
|   |-- ORDEN_COMPRA_B/
|   +-- ... otras ramas ...
|-- PROYECTOS_ACTUALES/
|-- CONTRATOS/
|-- FOTOS_RECIBIDAS/
|-- archivo_suelto.ext
+-- ... otras carpetas y archivos ...
```

### Arbol B: area de Producto y Compras

```text
AREA_PRODUCTO_COMPRAS/
|-- FICHAS_TECNICAS/
|-- DISENO/
|   +-- PROYECTO_A/
|       +-- diseno.ai
|-- BOARD/
|-- ORDENES_DE_COMPRA/
|-- VIAJES/
|-- ALTA_PROVEEDORES/
|-- PRESENTACIONES/
|-- LOGOS/
|-- REBRANDING/
|-- archivo_suelto.ext
+-- ... otras carpetas y archivos ...
```

**Reglas de recorrido y preservacion:**
- Elegir cualquier carpeta local de prueba como raiz; procesar archivos sueltos y todos los niveles inferiores.
- No inferir antiguedad por el nombre de carpeta, aunque incluya un ano.
- La ruta relativa se calcula desde la raiz **efectivamente seleccionada**; guardar ademas el identificador unico de esa raiz e inventario.
- No recorrer enlaces simbolicos, puntos de union o reparse points en el piloto.
- No permitir que origen y destino se superpongan.
- Ejemplo: si la raiz seleccionada es `AREA_PRODUCTO_COMPRAS/DISENO` y el archivo es `PROYECTO_A/diseno.ai`, su ruta relativa es `PROYECTO_A/diseno.ai`. Una copia futura quedaria en `REPOSITORIO/LOTE_UNICO/IDENTIFICADOR_RAIZ/PROYECTO_A/diseno.ai`.
- Si hay carpetas excluidas, no afirmar que se contaron sus archivos internos.

## 3. Reglas funcionales aprobadas

| ID | Regla |
|---|---|
| EST-001 | Seleccionar manualmente una carpeta accesible como origen. |
| EST-002 | Recorrer recursivamente, con exclusiones de subcarpetas. |
| EST-003 a EST-006 | Aprobadas: estructura heterogenea, archivos sueltos, no inferir edad por nombre, preservar rutas y raiz. |
| EST-007 | Evaluar archivos individualmente y agrupar resultados por carpeta. |
| EST-008 | Usar ultima modificacion para antiguedad; registrar creacion como informacion. |
| EST-009 | Permitir umbrales 3, 5, 7, 10 anos, personalizados o fecha de corte. |
| EST-010 | Clasificar carpetas antiguas, recientes o mixtas; representar errores y cobertura parcial aparte. |
| EST-011 | Mostrar resumen, explorador de carpetas y detalle progresivo. |
| EST-012 | Exportar XLSX con resumen por carpeta e inventario individual. |
| EST-013 | Excluir carpetas/subarboles y extensiones, informando exclusiones. |
| EST-014 | Proteger carpetas contra migracion sin excluirlas del analisis. |
| EST-015 | Aprobar por Excel y reimportar; nunca copiar automaticamente al importar. |
| EST-016 | DECISION: APROBAR, NO APROBAR, PENDIENTE; vacio equivale a pendiente. |
| EST-017 | RESPONSABLE y FECHA_APROBACION obligatorios para aprobaciones. |
| EST-018 | Inventario de 14 columnas detalladas debajo. |
| EST-019 | Revalidar ruta, nombre, tamano y ultima modificacion antes de copiar. |
| EST-020 | Copiar por lotes identificables, sin sobrescritura y preservando estructura. |
| EST-021 | Comparar SHA-256 de origen y destino para cada archivo copiado. |
| EST-022 | Registrar fallos y permitir reanudacion segura; detenerse ante fallos sistemicos. |
| EST-023 | Mostrar revision previa obligatoria y confirmacion explicita de copia. |
| EST-024 | Recordar solo las ultimas rutas, no filtros ni criterios anteriores. |
| EST-025 | Piloto local en dos etapas: diagnostico y luego copia/verificacion. |
| EST-026 | Validacion integral y pruebas progresivas de volumen. |

### Columnas del inventario individual

`ID_ARCHIVO`, `NOMBRE`, `RUTA_ORIGINAL`, `CARPETA_RELATIVA`, `EXTENSION`, `TAMANO_MB`, `FECHA_CREACION`, `FECHA_MODIFICACION`, `ANTIGUEDAD`, `CLASIFICACION`, `PROTEGIDO`, `DECISION`, `RESPONSABLE`, `FECHA_APROBACION`.

La identidad del inventario no debe depender exclusivamente de campos editables de Excel. Solo los campos de decision y aprobacion son editables para el circuito de autorizacion. Ante diferencias, rechazar el archivo afectado. La fecha de corte incluye el dia seleccionado (hasta 23:59:59 local); esta convencion debera probarse en bordes de fecha.

## 4. Flujo operativo

1. Seleccionar raiz local y configurar criterios.
2. Inventariar sin modificar archivos; registrar errores y cobertura.
3. Revisar resultados y exportar Excel.
4. Completar decisiones, responsable y fecha de aprobacion.
5. Reimportar y validar contra inventario original.
6. Revisar protecciones, metadatos, destino, lote y conflictos.
7. Confirmar expresamente la copia.
8. Copiar sin sobrescribir y verificar SHA-256 por archivo.
9. Registrar estado de cada archivo y lote, con posibilidad de reanudar.
10. Emitir manifiesto de copias verificadas, sin borrar originales.
11. Preparar orden **separada** de eliminacion, con autorizacion de Diseno (provisional).
12. En el piloto, **simular** la eliminacion y registrar lo que habria ocurrido, sin borrar nada.

Una copia aprobada no equivale a una eliminacion aprobada. No declarar un lote completo si tiene archivos pendientes o con errores.

## 5. Controles de seguridad

- Piloto solo con carpetas locales ficticias. Bloquear rutas UNC y unidades de red, incluidas unidades mapeadas.
- Rechazar enlaces y puntos de union para evitar ciclos y escapes del arbol.
- No permitir sobreescritura ni borrado automatico.
- Mantener registros por archivo y lote; validar cambios entre inventario y ejecucion.
- Evitar duplicados de ID, alteraciones de Excel y rutas fuera del origen permitido.
- Para una futura eliminacion real, exigir autorizacion independiente, hash coincidente, origen sin cambios, destino accesible y confirmacion explicita.
- Si falta evidencia, bloquear la accion y dejar constancia.

## 6. Plan de prueba piloto

**Etapa 1:** inventario, fechas, exclusiones, protecciones, errores, resumen por carpetas y Excel. Comparar resultados con conteos manuales; medir tiempo y memoria en escalas crecientes.

**Etapa 2:** aprobaciones validas e invalidas, copia entre carpetas locales, hashes, interrupciones y reanudacion. Comprobar que ningun archivo no autorizado se copie y que ningun original se altere.

**Etapa 3 de simulacion:** generar listado de eliminables, pedir confirmacion y producir informe de simulacion; no implementar borrado fisico en el piloto.

**Criterios propuestos:** cero archivos no autorizados copiados, cero originales modificados/eliminados, 100 % de las copias declaradas verificadas con SHA-256 coincidente, errores y estados recuperables registrados.

## 7. Pendientes y dependencias

**No bloquean la programacion de la primera entrega:** definir las carpetas ficticias concretas, escalas y tiempos esperados de la prueba.

**Antes de usar infraestructura real:** confirmar permisos, mapeos de red, capacidad del repositorio, estrategia de respaldo/restauracion, convencion de lotes, autorizaciones empresariales y procedimiento de eliminacion real.

**Estado de desarrollo:** existe un prototipo inicial de inventario de solo lectura. Aun no se ha validado un ejecutable ni completado la interfaz, Excel, copia o simulacion de eliminacion. No usar en produccion.
