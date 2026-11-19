# Auditoría técnica Módulo 1 — candidato piloto (19-11-2026)

## Alcance revisado
Archivos: core.py, storage.py, export.py, app.py, run.py, tests y workflows de Windows.
Sin acceso al servidor ni a archivos corporativos. No sustituye revisión de Sistemas.

## Verificaciones y correcciones
- Exportación: carpetas vacías incluidas, antigüedad numérica, Excel incremental y salida sin sobrescritura.
- Seguridad: bloqueo de rutas UNC, unidades no fijas y enlaces en raíz; enlaces/reparse points omitidos durante escaneo; base SQLite fuera del origen.
- SQLite: cierre explícito de conexiones de lectura, comprobado por regresiones en Windows.
- Exclusiones/protecciones: rutas relativas estrictas; rechazar rutas absolutas, con unidad o traversal.
- Interfaz: cuatro pestañas, confirmación antes de analizar, cancelación cooperativa, paginación y exportación solo de inventarios completos.
- GitHub Actions: pruebas sintéticas de Windows y compilación condicionada a pruebas.
- El módulo no contiene funciones para copiar, mover o borrar originales.

## Riesgos y límites que deben quedar visibles
1. **Escalabilidad real**: la prueba de 1.200 registros no demuestra rendimiento de ~458.000 archivos. Medir tiempo y memoria en la validación piloto antes de usar grandes volúmenes.
2. **Interfaz**: exportar Excel se ejecuta en el hilo principal; con inventarios grandes la ventana puede dejar de responder durante la exportación. No realizar exportaciones masivas en el piloto sin medir primero.
3. **TOCTOU**: la comprobación de rutas y enlaces no elimina carreras si un tercero modifica el árbol durante el escaneo; usar solo carpetas locales ficticias bajo control.
4. **Fecha de creación**: Windows puede registrar la fecha de creación local, que no equivale necesariamente a la fecha original del documento.
5. **Carpetas**: el resumen cuenta archivos directamente contenidos en cada carpeta, no el total recursivo de descendientes.
6. **Datos sensibles**: el repositorio público y los logs de Actions no deben contener rutas, credenciales ni archivos corporativos.
7. **Aprobación**: las columnas DECISIÓN, RESPONSABLE y FECHA_APROBACIÓN son informativas en Módulo 1; no habilitan migración.
8. **Seguridad corporativa**: el EXE no está autorizado para el servidor; requiere revisión y aprobación de Sistemas.
9. **Prueba visual**: pendiente en Windows local del usuario, con carpetas ficticias.

## Criterio de salida de etapa 3
- Último commit: suite de Windows en verde.
- Workflow de EXE: build y publicación de artifact completados, con ID de ejecución verificable.
- Ninguna afirmación de aprobación final hasta completar la validación visual y funcional.
