# D1 Frontend Debug Context

## Problema observado

El backend está funcionando, pero el frontend navega a rutas que terminan en 404.

## Hallazgos confirmados

* El login sí funciona.
* El backend responde `200 OK` en `/auth/login`.
* El frontend muestra `404` al navegar a:
  * `/admin/organizacion`
  * `/admin/grupos`
  * `/admin/miembros`

## Hipótesis principal

Las rutas del frontend no coinciden con la estructura real del App Router.

## Posible causa

Se está usando un route group `(admin)` en `app/`, pero el código navega a rutas `/admin/...` como si existiera un segmento real `admin` en la URL.

## Objetivo del debugging

* Identificar el desajuste exacto entre targets de navegación y rutas reales del App Router.
* Proponer una corrección concreta en navegación/redirects sin cambiar aún código de producto.
