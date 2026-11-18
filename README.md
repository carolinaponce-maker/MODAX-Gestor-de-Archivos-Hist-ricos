# MODAX | Gestor de Archivos Historicos

Aplicacion Windows en desarrollo para inventariar, clasificar y posteriormente gestionar copias verificadas de archivos historicos.

## Estado
**Piloto local - Entrega 1 en preparacion.** Todavia no existe un ejecutable validado.

## Alcance de la Entrega 1
- Seleccion manual de una carpeta local de prueba.
- Inventario recursivo de archivos y subcarpetas, incluidos archivos sueltos.
- Clasificacion por fecha de ultima modificacion y criterios configurables.
- Exclusiones por carpetas y extensiones; carpetas protegidas se inventarian pero no se proponen para migracion.
- Registro de errores de acceso y resultados por carpeta.

## Reglas de seguridad del piloto
- No utilizar carpetas del servidor ni unidades de red.
- No modificar, mover ni eliminar archivos del origen.
- La futura eliminacion se probara solo como **simulacion**, sin borrado fisico.
- No incorporar datos empresariales, rutas internas, contrasenas ni archivos reales a este repositorio publico.
- Ninguna aprobacion en Excel habilita por si sola una operacion destructiva.

## Entregas posteriores
1. Exportacion e importacion controlada de Excel.
2. Copia entre carpetas locales de prueba y verificacion SHA-256.
3. Simulacion auditada de eliminacion.
4. Empaquetado Windows mediante GitHub Actions y pruebas progresivas.

## Estructura de carpetas
El gestor no presupone nombres ni niveles fijos: cada raiz seleccionada puede contener archivos sueltos y subcarpetas anidadas. Se preservaran rutas relativas en las copias de prueba. Los enlaces simbolicos y puntos de union no se recorreran por defecto, para evitar ciclos o salir del arbol seleccionado.

## Uso
El proyecto aun no esta listo para ejecutarse. La documentacion y el codigo del piloto se incorporaran por entregas.
