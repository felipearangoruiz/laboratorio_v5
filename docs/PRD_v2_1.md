# PRD v2.2 — Sistema de Diagnóstico Organizacional con IA

**Versión:** 2.2 · Abril 2026
**Autor:** Martín Guzmán
**Estado:** Actualización de v2.1 con decisiones del refactor Sprint 0
**Clasificación:** Confidencial

> **Nota sobre esta versión markdown:** este archivo es la versión 2.2 del PRD, generada a partir del PRD v2.1 (.docx original) con actualizaciones aplicadas tras las decisiones tomadas durante el Sprint 0 del refactor de modelo de nodos y unificación de capas. La versión .docx original sigue siendo referencia histórica.

---

## Changelog v2.1 → v2.2 (21 de abril de 2026)

Esta versión incorpora cuatro decisiones tomadas durante el Sprint 0 del refactor de modelo de nodos y unificación de capas. Estas decisiones modifican secciones específicas del PRD original y prevalecen sobre cualquier afirmación contradictoria del v2.1.

**Decisión A1 — Tres capas en lugar de cuatro.** Las capas Estructura y Recolección se fusionan en una sola capa unificada llamada Estructura+Captura. El canvas pasa de tener cuatro capas (Estructura, Recolección, Análisis, Resultados) a tener tres (Estructura+Captura, Análisis, Resultados). Afecta secciones 7.3, 7.4, 7.8, 8.3.

**Decisión A2 — AssessmentCampaign como entidad de schema.** El sistema soporta múltiples diagnósticos a lo largo del tiempo sobre la misma organización mediante la entidad AssessmentCampaign. El schema existe desde el Sprint 1 del refactor; la UI que expone campañas múltiples se entrega en el Sprint 3. Cada diagnóstico ejecutado pertenece a una Campaign. La migración inicial crea automáticamente una Campaign llamada "Diagnóstico Inicial" para preservar los datos existentes. Afecta sección 12 (modelo de datos).

**Decisión A3 — Tipos de relación lateral con enum cerrado.** Los tipos válidos de relación lateral entre nodos quedan cerrados a `lateral` y `process`. Se elimina cualquier valor de tipo "otro" como cajón de sastre. Si aparece un caso real que no encaja, será señal para agregar un tipo nuevo con semántica clara. Afecta sección 12 (modelo de datos) y cualquier referencia a LateralRelation.

**Decisión A4 — Member absorbido en Node.** La distinción entre Group y Member como entidades separadas se elimina. Ambas se unifican en una única entidad Node con un campo `type` que toma los valores `unit` (cuando es un área, equipo o agrupación organizacional) o `person` (cuando es una persona individual). La jerarquía organizacional vive en el campo `parent_node_id` de la misma entidad. Afecta sección 12 (modelo de datos) y todas las menciones a Group y Member en el cuerpo del PRD.

Para detalle conceptual completo del nuevo modelo, consultar `docs/MODEL_PHILOSOPHY.md` en el repositorio. Para deuda documental pendiente, consultar `docs/DEUDA_DOCUMENTAL.md`. En caso de conflicto entre este PRD y MODEL_PHILOSOPHY.md, prevalece MODEL_PHILOSOPHY.md sobre las cuatro áreas anteriores.

---

# 1. Resumen ejecutivo

Este documento define los requisitos de producto, funcionales, técnicos y de diseño para una plataforma web que permite a líderes organizacionales capturar, estructurar e interpretar la realidad interna de sus organizaciones mediante un diagnóstico profundo asistido por inteligencia artificial.

El sistema combina tres capas: (i) una capa estructural que modela la organización como un grafo de nodos interrelacionados, (ii) una capa perceptiva construida a partir de entrevistas a los miembros, y (iii) una capa analítica donde un motor híbrido (scoring cuantitativo + LLM) interpreta tensiones, coherencias y contradicciones entre ambas dimensiones.

**Modelo de negocio:** Freemium. El plan gratuito ofrece una experiencia ligera de diagnóstico rápido (encuesta corta + score radar). El plan premium desbloquea el producto completo: canvas organizacional, entrevistas profundas, motor de IA, diagnóstico narrativo y recomendaciones.

**Plataforma:** Web app (desktop + responsive).

**Principio rector de interfaz:** El canvas organizacional es la pantalla principal del sistema en el plan premium. No existe un dashboard genérico ni navegación basada en módulos. Las funcionalidades se acceden mediante capas de interacción y paneles contextuales sobre el mismo espacio visual.

**Alcance del MVP:** Flujo completo de ambos planes: free (encuesta rápida → score) y premium (canvas → entrevistas → IA → diagnóstico narrativo).

# 2. Problema, contexto y propuesta de valor

## 2.1. Problema

Los líderes de organizaciones operan con una comprensión fragmentada, intuitiva y sesgada de cómo funciona internamente su organización. La información crítica sobre cultura, comunicación, liderazgo, procesos y estructura está dispersa en percepciones individuales, documentos internos y dinámicas no visibles.

Las herramientas actuales no resuelven esto de manera integrada:

- Las encuestas de clima miden percepción pero no la cruzan con la estructura real ni generan análisis profundo.

- La consultoría organizacional tradicional es costosa, lenta y no escalable.

- Los organigramas son estáticos y no capturan dinámicas reales de poder, comunicación o dependencia.

## 2.2. Propuesta de valor diferenciada

El producto integra estructura formal + percepciones individuales + evidencia documental, procesados por un motor de IA que genera un diagnóstico que ningún actor aislado podría producir. El resultado es una narrativa estructurada que explica qué está pasando, por qué, y qué hacer al respecto.

## 2.3. Usuario objetivo

Tomadores de decisión que necesitan entender cómo opera su organización para intervenir de forma informada:

- CEOs y fundadores de startups y empresas en crecimiento.

- Gerentes generales y directores de área.

- Directores ejecutivos de ONGs y organizaciones sin ánimo de lucro.

- Líderes de unidades de negocio que gestionan equipos de cualquier tamaño.

## 2.4. Jobs-to-be-Done

- Quiero entender qué está pasando realmente en mi organización, más allá de lo que me dicen en reuniones.

- Quiero identificar cuellos de botella, tensiones o desalineaciones antes de que se conviertan en crisis.

- Quiero tomar decisiones de reestructuración, contratación o cambio cultural con evidencia, no con intuición.

- Quiero medir el impacto de las intervenciones que hago a lo largo del tiempo.

# 3. Métricas de éxito del producto


| **Métrica** | **Definición** | **Objetivo MVP** |
|---|---|---|
| Activación Free | % de registros que completan la encuesta rápida y obtienen su score | 65% |
| Conversión Free → Premium | % de usuarios free que pasan a plan pago | 8% |
| Activación Premium | % de usuarios premium que completan estructura + al menos 1 entrevista de miembro | 50% |
| Tasa de respuesta de entrevistas | % de miembros invitados que completan la entrevista completa | 60% |
| Tiempo a primer diagnóstico (free) | Minutos desde registro hasta ver score radar | ≤15 min |
| Tiempo a primer diagnóstico (premium) | Días desde activación premium hasta diagnóstico IA | ≤14 días |
| Retención a 90 días (premium) | % de usuarios premium que ejecutan un segundo diagnóstico | 25% |
| NPS post-diagnóstico | Net Promoter Score | ≥40 |


# 4. Modelo de negocio (Freemium)

El modelo freemium está diseñado como un embudo de conversión: el plan gratuito ofrece una experiencia rápida y valiosa que demuestra el potencial del producto, generando la motivación para acceder al diagnóstico completo.

## 4.1. Plan Free — Diagnóstico rápido

**Concepto:** El líder obtiene un primer score de su organización en menos de 15 minutos, sin complejidad.

Flujo del plan Free

1. El líder se registra (email + password o SSO).

2. Responde una encuesta corta sobre su percepción de la organización (4 dimensiones, ~5 minutos).

3. Ingresa entre 3 y 5 miembros de su equipo (nombre, rol, correo electrónico).

4. Los miembros reciben un enlace y responden una encuesta corta (~5–8 minutos).

5. Cuando al menos 3 miembros responden, el sistema genera un score radar con las 4 dimensiones evaluadas.

6. El líder ve su score y un CTA claro para desbloquear el diagnóstico completo.

Alcance del plan Free

- 4 dimensiones evaluadas: Liderazgo, Comunicación, Cultura y Operación.

- 1–2 preguntas Likert por dimensión + 1 pregunta abierta general.

- Máximo 5 miembros invitados.

- Resultado: score numérico por dimensión presentado como radar chart.

- **No incluye:** canvas organizacional, diagnóstico narrativo, hallazgos con IA, recomendaciones, exportación, carga de documentos, historial.

Gancho de conversión

Junto al score radar, el sistema muestra un mensaje contextual del tipo: "Tu organización tiene un score de 2.8 en Comunicación. Con el diagnóstico completo podrías entender por qué, identificar dónde está la fricción y recibir recomendaciones específicas."

El CTA ofrece iniciar prueba premium o suscribirse directamente.

## 4.2. Plan Premium — Diagnóstico completo

**Concepto:** El producto completo. Canvas organizacional, entrevistas profundas a toda la organización, motor de IA híbrido, diagnóstico narrativo y recomendaciones accionables.

Incluye

- Canvas organizacional interactivo (construcción visual de estructura).

- Organizaciones y nodos ilimitados.

- 8 dimensiones completas: Liderazgo, Comunicación, Cultura, Procesos, Poder, Economía/Finanzas, Operación, Misión.

- Entrevistas profundas (Likert + abiertas + selección múltiple) por dimensión.

- Invitación a todos los miembros de la organización.

- Motor de IA híbrido: scoring cuantitativo + LLM + análisis de redes.

- Diagnóstico narrativo con hallazgos, scores de confianza y recomendaciones priorizadas.

- Carga de documentos complementarios (RAG).

- Comparación temporal entre diagnósticos.

- Exportación PDF/DOCX.

- Roles adicionales: viewer, colaborador admin.

Pricing (indicativo — requiere validación)

Se sugiere un rango de USD \$49–149/mes para organizaciones pequeñas-medianas y un tier enterprise con precio personalizado para +200 personas. Estas cifras requieren validación con investigación de mercado.

# 5. Modelo de acceso y entrada al sistema

**Principio rector:** la experiencia del producto no está centrada en el usuario sino en la organización como unidad principal de interacción. El usuario actúa como operador de una organización, no como navegador de funcionalidades.

## 5.1. Autenticación

El sistema utiliza autenticación basada en usuario (email + password o SSO con Google/Microsoft). Cada usuario posee un identificador único y puede pertenecer a una o múltiples organizaciones con distintos roles.

## 5.2. Resolución de contexto post-login

Después del login, el sistema resuelve automáticamente el contexto:

- **Caso A — Usuario nuevo sin organización:** accede directamente al flujo de onboarding (sección 8).

- **Caso B — Usuario con 1 organización:** accede directamente al canvas de esa organización (premium) o a su dashboard de score (free).

- **Caso C — Usuario con múltiples organizaciones:** ve un selector ligero (tipo Notion: lista simple, búsqueda, última usada primero) y luego accede al canvas de la organización seleccionada.

## 5.3. Ruta de navegación

**La URL de entrada real es /org/{org_id}/canvas**, no /dashboard ni /admin. En ningún caso la pantalla principal es una lista de funcionalidades.

El sistema no presenta un dashboard genérico post-login. El canvas organizacional es la home del producto para usuarios premium. Para usuarios free, la home es la pantalla de score radar con CTA de upgrade.

## 5.4. Presencia del usuario en la interfaz

El identificador del usuario es protagonista solo en el backend (validación de acceso, permisos, auditoría). En la interfaz aparece únicamente en:

- Avatar arriba a la derecha.

- Settings de cuenta.

- Selector de organización (si tiene múltiples).

- Logout.

**Regla para ingeniería:** no construir rutas tipo /admin/dashboard, /admin/groups, /admin/members. La navegación se estructura alrededor de /org/{org_id}/ con sub-rutas para settings y billing únicamente.

# 6. Roles, permisos y política de privacidad

## 6.1. Roles del sistema


| **Rol** | **Descripción** | **Permisos clave** |
|---|---|---|
| Owner | Quien crea la organización | CRUD estructura, invitar miembros, configurar entrevistas, ejecutar diagnóstico, ver resultados, exportar, billing |
| Admin | Persona con acceso admin delegado | Mismos permisos que Owner excepto eliminar org y gestionar billing |
| Viewer | Stakeholder con acceso de lectura | Ver diagnóstico y visualizaciones. No ve respuestas individuales |
| Entrevistado | Miembro invitado a responder | Acceso único a su entrevista. No ve estructura ni resultados |


## 6.2. Política de anonimato de respuestas

**Regla fundamental:** las respuestas son identificadas internamente (asociadas al rol y posición del respondente para alimentar el análisis contextual) pero anónimas en la presentación de resultados.

- El sistema sabe que "Carlos, equipo técnico" respondió X, y usa esa información para contextualizar el análisis según rol y área.

- El administrador nunca ve quién dijo qué. Los resultados se presentan agregados por rol, área o nivel jerárquico.

- **Umbral mínimo de anonimato:** si un grupo tiene menos de 3 respondentes, sus respuestas se agregan al nivel jerárquico superior para evitar identificación indirecta.

- El entrevistado recibe garantía explícita de anonimato antes de comenzar.

# 7. Arquitectura de interacción basada en canvas (CRÍTICO)

**Esta sección define la decisión de UX más importante del producto.** Todo el equipo de producto, diseño e ingeniería debe leerla antes de comenzar cualquier trabajo.

## 7.1. Principio rector

**El canvas organizacional es el punto de entrada, navegación y acción del sistema.** No es una vista ni un módulo. Es la interfaz principal. El usuario no navega entre secciones; cambia de capa sobre el mismo espacio visual.

El producto es un canvas con capas, no un sistema de módulos con un canvas dentro.

## 7.2. Estructura de navegación

La interfaz tiene dos elementos de navegación:

A. El canvas (centro — ocupa el 85%+ de la pantalla)

Espacio visual donde vive la organización. Todos los nodos, relaciones, estados y resultados se visualizan aquí. Las acciones se ejecutan desde aquí.

B. Sidebar mínimo (lateral izquierdo, colapsable)

Contiene únicamente navegación secundaria que no puede vivir en el canvas:

- Selector de organización (si el usuario tiene múltiples).

- Settings de la organización.

- Billing y plan.

- Carga de documentos complementarios.

- Cuenta de usuario.

**Lo que NO va en el sidebar:** Grupos, Miembros, Entrevistas, Resultados. Estas funcionalidades viven en el canvas, no en una navegación separada.

## 7.3. Capas del canvas

> **Actualizado v2.2 (decisión A1):** el canvas pasa de cuatro a tres capas. Estructura y Recolección se fusionan en una capa unificada llamada Estructura+Captura.

El canvas tiene 3 capas que representan diferentes modos de interacción con la misma información. El usuario cambia de capa mediante un selector visible (tabs o toggle en la parte superior del canvas). Cambiar de capa no cambia de pantalla; cambia qué información es visible y qué acciones están disponibles.

Estructura+Captura es la capa de captura: el administrador construye la organización y gestiona las invitaciones simultáneamente. Análisis y Resultados son capas de lectura densa con coordinación visual: el canvas actúa como ancla estructural mientras los paneles contienen información contextualizada en la estructura real. En la primera el admin actúa; en las segundas, comprende. En Análisis y Resultados el canvas nunca es decorativo: siempre es reactivo.


| **Capa** | **Propósito** | **Qué se ve en el canvas** | **Acciones disponibles** |
|---|---|---|---|
| Estructura+Captura | Construir la organización y gestionar entrevistas | Nodos en modo edición + indicador de estado de entrevista (gris/azul/verde/naranja) | Crear/editar/eliminar nodos, arrastrar conexiones, importar CSV, invitar miembros, enviar recordatorios, ver progreso, revocar invitaciones |
| Análisis | Visualizar el diagnóstico sobre la estructura | Nodos coloreados por nivel de tensión (verde/amarillo/rojo), conexiones con intensidad | Filtrar por dimensión, ver mapa de calor, comparar con diagnóstico anterior |
| Resultados | Leer hallazgos y recomendaciones | Nodos con highlights de insights, badges de hallazgos | Abrir diagnóstico narrativo, ver hallazgos por nodo, exportar |


## 7.4. Panel lateral contextual (crítico)

Al hacer clic en un nodo del canvas, se abre un panel lateral derecho que funciona como el backend visible del usuario. Este panel es contextual: su contenido cambia según la capa activa y el nodo seleccionado.


| **Capa activa** | **Contenido del panel al hacer clic en un nodo** |
|---|---|
| Estructura+Captura | Formulario de edición completo del nodo: nombre, rol/cargo, descripción, área, nivel jerárquico. Campo de email del miembro asignado. Campo de contexto libre (notas sobre la dinámica del nodo). Sección para subir documentos institucionales que alimentarán el análisis de IA. Botón eliminar nodo. Relaciones jerárquicas y laterales. **Captura integrada (sección dentro del mismo panel):** estado de la entrevista para ese nodo (sin invitar / invitado / en progreso / completado / vencido), link copiable único para compartir con el miembro, botón de envío por WhatsApp, fecha de respuesta o expiración si aplica. |
| Análisis | Scores del nodo por dimensión (radar mini), comparación con promedio de su área, alertas de tensión, resumen de percepciones agregadas. |
| Resultados | Hallazgos específicos del nodo o su área, recomendaciones relevantes, enlace al diagnóstico narrativo completo. |


## 7.5. Regla de persistencia del canvas

**El usuario nunca pierde el contexto del canvas.** Toda funcionalidad — sin excepción — se abre como panel lateral, overlay o capa sobre el canvas, no como navegación completa a otra vista. Settings, documentos, billing y diagnóstico narrativo se abren como paneles superpuestos; el canvas permanece visible en segundo plano. La única excepción es la experiencia del entrevistado, que es un flujo independiente fuera del canvas.

Esta regla aplica a todas las fases de desarrollo. Si una funcionalidad nueva no puede resolverse como panel u overlay, debe rediseñarse hasta que pueda.

## 7.6. Reglas de interacción

- Hacer clic en un nodo abre el panel lateral contextual.

- Hacer doble clic en un nodo en capa Estructura permite edición inline del nombre.

- Arrastrar un nodo mueve su posición en el canvas (todas las capas).

- Arrastrar desde el borde de un nodo a otro crea una conexión (solo en capa Estructura).

- Scroll/pinch para zoom. El canvas se adapta al zoom mostrando más o menos detalle (zoom semántico).

- Selección múltiple (clic + shift o lazo) para acciones en bloque (invitar varios, agrupar, eliminar).

- Clic en área vacía del canvas cierra el panel lateral.

## 7.7. Antipatrones explícitos (lo que NO se debe construir)

Para evitar ambigüedades, se listan decisiones de diseño que quedan explícitamente prohibidas:

- **No:** Sidebar con secciones "Grupos", "Miembros", "Entrevistas", "Resultados".

- **No:** Páginas separadas para gestión de entrevistas o visualización de resultados.

- **No:** Dashboard genérico post-login con tarjetas de resumen.

- **No:** Rutas tipo /admin/members, /admin/interviews, /admin/results.

- **No:** Settings, billing o documentos como páginas full-screen que reemplacen el canvas.

- **No:** El diagnóstico narrativo como página separada, modal centrado que oculte el canvas, o ruta independiente.

## 7.8. Jerarquía y flujo progresivo de capas

> **Actualizado v2.2 (decisión A1):** la fila Recolección se elimina; sus acciones quedan integradas en Estructura+Captura. La jerarquía pasa de cuatro a tres capas.

**Las capas siguen un orden lógico que refleja el ciclo del diagnóstico.** El usuario avanza progresivamente; el sistema guía la transición entre capas mediante estados y CTAs contextuales.


| **Orden** | **Capa** | **Estado inicial** | **Se desbloquea cuando...** | **CTA de transición** |
|---|---|---|---|---|
| 1 | Estructura+Captura (default) | Siempre activa. Es la capa de entrada al canvas. Permite tanto construir la estructura como invitar y monitorear entrevistas. | N/A — siempre disponible | Cuando se alcanza umbral de respuestas: "Tienes suficientes respuestas. Genera tu diagnóstico →" |
| 2 | Análisis | Bloqueada hasta que exista un diagnóstico procesado | Diagnóstico en estado "Publicado" | Al entrar por primera vez: "Ve los hallazgos más importantes →" (abre panel lateral con top 3) |
| 3 | Resultados | Bloqueada hasta que exista un diagnóstico procesado | Diagnóstico en estado "Publicado" | "Lee el diagnóstico completo →" (abre panel expandido de diagnóstico narrativo) |


Las capas bloqueadas son visibles en el selector pero no interactivas. Al pasar el cursor muestran un tooltip que explica qué falta para desbloquearlas. Esto cumple dos funciones: evita la confusión de "¿por dónde empiezo?" y genera anticipación del valor que viene después.

**Regla:** el usuario no puede saltar capas. La primera vez que usa el producto, la única capa activa es Estructura+Captura. Análisis y Resultados se desbloquean progresivamente cuando se publica un diagnóstico.

## 7.9. Definición del panel de diagnóstico narrativo

**Arquitectura híbrida (no negociable): el canvas actúa como ancla estructural durante toda la exploración de resultados. Los paneles son contenedores de información densa, siempre contextualizados en el canvas. La navegación es bidireccional: el usuario puede partir del canvas (clic en nodo → panel de análisis del nodo) o del contenido narrativo (clic en hallazgo → el canvas resalta los nodos relevantes). El diagnóstico narrativo ocupa el 60–70% del viewport como panel lateral derecho expandido, manteniendo el canvas visible y reactivo en segundo plano. La coordinación visual canvas-narrativa es obligatoria: cuando el diagnóstico menciona un área o dimensión, el canvas resalta los nodos afectados en tiempo real.**

Comportamiento:

- Se abre desde la Capa Resultados al hacer clic en "Lee el diagnóstico completo" o al seleccionar un hallazgo que requiere contexto narrativo.

- El panel es scrolleable internamente. El contenido sigue la estructura definida: resumen ejecutivo → análisis por dimensión → hallazgos transversales → recomendaciones → advertencias.

- El canvas en segundo plano permanece visible y responde al scroll del diagnóstico: cuando el diagnóstico llega a una dimensión específica, el canvas puede resaltar los nodos relevantes (efecto de coordinación visual).

- El panel se cierra con clic en área del canvas, botón de cierre, o tecla Escape.

- En móvil, el panel ocupa el 100% de la pantalla (no hay espacio para canvas + panel).

Navegación bidireccional obligatoria: clic en hallazgo o dimensión en el panel → canvas resalta los nodos relevantes; clic en nodo del canvas → panel navega al contenido correspondiente.

## 7.10. Criterio de validación de diseño

Antes de implementar cualquier elemento de UI en las capas Análisis o Resultados: ¿Esta información se puede ubicar en la organización (asignar a nodo(s) específicos)?

Si la respuesta es sí → conectar al canvas: resaltar el o los nodos relevantes cuando se visualiza esa información.

Si la respuesta es no → puede vivir fuera del canvas, pero debe incluir un mecanismo de retorno claro al contexto estructural.

Este criterio aplica a: hallazgos, recomendaciones, scores por dimensión, gráficas comparativas y cualquier dato derivado del análisis. El usuario nunca debe perder la conexión entre la información y la organización real que está diagnosticando.

# 8. Onboarding, activación y resolución del canvas vacío

El onboarding es crítico para la activación. Un canvas vacío es intimidante y destruye la conversión. Esta sección define cómo se resuelve la primera experiencia de cada tipo de usuario.

## 8.1. Onboarding Free (diagnóstico rápido)

El objetivo es que el usuario llegue a su score radar en menos de 15 minutos desde el registro.

Flujo paso a paso

7. Registro (email + password o SSO). Máximo 2 pantallas.

8. **Pantalla de bienvenida:** "Conoce cómo está tu organización en 10 minutos." Breve explicación del proceso (3 pasos visuales: Tú respondes → Tu equipo responde → Ves tu score).

9. **Datos básicos de la organización:** Nombre, tipo (empresa/ONG/equipo/otro), tamaño aproximado. Un formulario simple, no un wizard largo.

10. **Encuesta del líder:** 4 dimensiones (Liderazgo, Comunicación, Cultura, Operación). 1–2 preguntas Likert por dimensión + 1 pregunta abierta general. Duración: ~5 minutos. Presentada como flujo lineal tipo formulario, no como canvas.

11. **Ingreso de miembros:** El líder ingresa 3–5 personas (nombre, rol, correo). Interfaz simple de tabla editable o formulario repetible. Botón "Enviar invitaciones".

12. **Pantalla de espera:** Muestra progreso de respuestas en tiempo real ("2 de 4 miembros han respondido"). Opción de enviar recordatorio. Se genera el score cuando al menos 3 miembros responden.

13. **Pantalla de resultados Free:** Radar chart con scores de 4 dimensiones. Mensaje contextual personalizado basado en el score más bajo. CTA: "Desbloquea el diagnóstico completo →".

Criterios de aceptación

- Todo el flujo del líder (registro → encuesta → ingreso de miembros) se completa en menos de 10 minutos.

- La encuesta de los miembros invitados se completa en menos de 8 minutos.

- El score se genera automáticamente al alcanzar el umbral de 3 respuestas, sin acción adicional del líder.

- La pantalla de espera se actualiza en tiempo real (WebSocket o polling cada 30 segundos).

## 8.2. Onboarding Premium (primer uso del canvas)

Cuando un usuario activa el plan premium (sea por upgrade desde free o por suscripción directa), accede al canvas organizacional. El primer uso debe resolver el problema del lienzo en blanco.

Tres caminos de entrada (el usuario elige)

Al acceder al canvas por primera vez, el sistema presenta tres opciones:

14. **Templates prediseñados:** "Startup (10–30 personas)", "ONG pequeña", "Empresa por departamentos", "Equipo de proyecto". El template precarga una estructura básica que el usuario puede editar. Incluye nodos de ejemplo con nombres genéricos que invitan a ser reemplazados.

15. **Importar estructura:** Desde CSV, Excel o Google Sheets. El sistema lee columnas (nombre, cargo, área, jefe directo) y genera el organigrama automáticamente. Un wizard de 3 pasos: subir archivo → mapear columnas → confirmar estructura.

16. **Empezar de cero:** Canvas vacío con un tooltip guía que indica "Haz clic para crear tu primer nodo" y una animación sutil que invita a la acción.

Guía contextual para primeros usos

El sistema incluye tooltips progresivos (no un tutorial bloqueante) que guían las primeras acciones:

17. "Crea tu primer nodo" (al entrar al canvas vacío o después de cargar template).

18. "Conecta nodos arrastrando desde el borde" (después de crear 2+ nodos).

19. "Invita a tu primer miembro" (después de construir estructura mínima).

20. "Abre el panel lateral del nodo para ver el estado de la entrevista" (después de enviar primera invitación).

Los tooltips se desactivan permanentemente cuando el usuario completa la acción sugerida o los cierra manualmente.

## 8.3. Estado 0 del canvas — primer uso premium (CRÍTICO)

**Esta es la pantalla más importante del producto.** Si el usuario no entiende qué hacer aquí en los primeros 10 segundos, se pierde. La definición de este estado debe ser quirúrgica.

Layout exacto del Estado 0

Lo que el usuario ve al entrar al canvas por primera vez:


| **Zona** | **Ubicación** | **Contenido exacto** |
|---|---|---|
| Header bar | Top, ancho completo | Logo del producto (izquierda). Nombre de la organización (centro). Avatar + dropdown de usuario (derecha). |
| Selector de capas | Top, debajo del header, alineado a la izquierda | 3 tabs: Estructura+Captura (activa, color primario), Análisis (gris, candado), Resultados (gris, candado). Al pasar cursor sobre las bloqueadas: tooltip "Genera tu primer diagnóstico para desbloquear". |
| Sidebar mínimo | Lateral izquierdo, colapsado por defecto | Ícono de menú hamburguesa. Al expandir: selector de org, settings, documentos, billing, cuenta. |
| Canvas (centro) | 85%+ del viewport | Fondo limpio con grid sutil. En el centro exacto: ilustración minimalista de un organigrama (3 nodos conectados, estilo wireframe) + texto debajo. |
| Texto central del canvas | Centro del canvas, sobre la ilustración | "Construye tu organización" (heading, 20px, bold). Debajo: "Empieza creando tu primer nodo o importa tu estructura." (subtext, 14px, gris). |
| CTAs centrales | Centro, debajo del texto | Tres botones horizontales: "+ Crear primer nodo" (primario, color de accent), "Usar template" (secundario, outline), "Importar CSV" (terciario, link style). |
| Panel lateral derecho | Lateral derecho | No visible hasta que el usuario haga clic en un nodo o seleccione una acción. |


Comportamiento al elegir cada CTA

**"+ Crear primer nodo":** Aparece un nodo nuevo en el centro del canvas con nombre editable inline ("Mi primer nodo" seleccionado, listo para ser reescrito). Simultáneamente se abre el panel lateral derecho con el formulario de atributos (nombre, rol, área). Tooltip animado sutil: "Arrastra desde el borde para conectar con otro nodo."

**"Usar template":** Se abre un panel central (overlay ligero) con 4–6 templates visuales: cada uno muestra un mini-preview del organigrama que generaría. Al seleccionar uno, los nodos aparecen en el canvas con nombres genéricos ("CEO", "Director Comercial", etc.) listos para ser editados. El overlay se cierra y el usuario está en el canvas con estructura precargada.

**"Importar CSV":** Se abre un panel lateral derecho con wizard de 3 pasos: (1) subir archivo o pegar desde Google Sheets, (2) mapear columnas (nombre, cargo, área, jefe directo), (3) preview y confirmar. Al confirmar, los nodos aparecen en el canvas auto-organizados.

Qué pasa después del primer nodo

Una vez que existe al menos 1 nodo en el canvas:

- El estado vacío (ilustración + CTAs centrales) desaparece permanentemente.

- Aparece un botón flotante "+ Agregar" en la esquina inferior derecha del canvas.

- El tooltip guía cambia a: "Crea más nodos y conéctalos arrastrando desde los bordes."

- Cuando hay 3+ nodos, aparece un CTA contextual en la parte superior: "Tu estructura está tomando forma. Cuando estés listo, invita a tu equipo →" (este CTA enfoca la sección de captura dentro del panel lateral del nodo).

Criterios de aceptación del Estado 0

- El usuario entiende qué hacer sin leer documentación externa.

- En menos de 30 segundos desde que llega al canvas, puede ejecutar una acción (crear nodo, abrir template o iniciar importación).

- Los CTAs del estado vacío son suficientemente grandes y claros para funcionar en tablet.

- El estado vacío se ve profesional y acogedor, no genérico ni improvisado.

- Si el usuario cierra la sesión y vuelve a entrar con nodos creados, no vuelve a ver el estado vacío.

## 8.4. Migración Free → Premium

Cuando un usuario free hace upgrade:

- Los datos de su encuesta rápida y los miembros ingresados se migran automáticamente como nodos iniciales en el canvas.

- El score radar free se conserva como "lectura inicial" y se podrá comparar con el primer diagnóstico premium.

- El líder no empieza de cero: ya tiene 3–5 nodos y datos básicos precargados.

- El sistema sugiere: "Ya tienes 5 miembros. Completa tu estructura para un diagnóstico más profundo."

# 9. Arquitectura funcional detallada (Plan Premium)

Las siguientes historias de usuario describen el flujo completo del plan premium. Todas las funcionalidades se ejecutan desde el canvas y el panel lateral contextual, siguiendo la arquitectura de interacción definida en la sección 7.

## 9.1. Construcción de la estructura organizacional

Historia de usuario

Como **administrador**, quiero construir visualmente la estructura de mi organización en el canvas, para representar cómo está organizada.

Flujo (dentro de Capa Estructura)

21. El usuario crea nodos haciendo clic en el canvas o usando botón "+ Agregar".

22. Define atributos en el panel lateral: nombre, rol/cargo, descripción, área, nivel jerárquico.

23. Conecta nodos arrastrando líneas desde el borde de un nodo al otro (relación jerárquica: reporta a).

24. Puede definir relaciones laterales (colaboración, dependencia funcional) con conexión de tipo distinto.

25. Puede agrupar nodos en contenedores visuales (áreas/departamentos).

26. Puede importar estructura desde CSV/Excel.

Reglas de negocio

- Un nodo puede tener 0 o 1 jefe directo. El nodo raíz no tiene jefe.

- Un nodo puede tener múltiples relaciones laterales.

- No se permiten ciclos en relaciones jerárquicas (validación en tiempo real).

- Nombre y rol son obligatorios. Los demás atributos son opcionales.

Casos borde

- Importación CSV con jefe inexistente: el sistema crea el nodo automáticamente y lo marca como incompleto.

- Nodo eliminado con entrevista completada: confirmación explícita con advertencia de pérdida de datos.

- Reorganización durante recolección: se permite pero se advierte que entrevistas en curso reflejan la estructura anterior.

## 9.2. Gestión de entrevistas

Historia de usuario

Como **administrador**, quiero invitar miembros a responder desde el canvas, para capturar su percepción.

Flujo (dentro de Capa Estructura+Captura, sección de captura del panel lateral)

27. Desde un nodo (o selección múltiple), abre el panel lateral y registra el email del miembro.

28. El sistema genera un enlace único con token (no requiere registro del entrevistado).

29. Se envía email con invitación (texto personalizable).

30. El canvas muestra el estado de cada nodo en tiempo real (gris/azul/verde/naranja).

31. El admin puede enviar recordatorios (máximo 3 por invitación) y revocar invitaciones.

Reglas de negocio

- Enlace expira en 14 días (configurable 7–30).

- Un email se asocia a un solo nodo por organización.

- **Umbral mínimo para diagnóstico:** 40% de nodos con entrevista completada, mínimo absoluto 5 entrevistas.

Estados del nodo (sección de captura del panel lateral en Estructura+Captura)


| **Estado** | **Descripción** | **Color** |
|---|---|---|
| Sin invitar | Nodo sin entrevista asociada | Gris |
| Invitado | Invitación enviada | Azul (outline) |
| En progreso | Entrevistado comenzó pero no terminó | Azul (parcial) |
| Completado | Entrevista terminada | Verde |
| Vencido | Invitación expirada sin respuesta | Naranja |


## 9.3. Experiencia del entrevistado

**Nota:** el entrevistado NO interactúa con el canvas. Su experiencia es un flujo lineal de formulario, optimizado para móvil.

Flujo

32. Abre el enlace desde cualquier dispositivo.

33. Ve pantalla de bienvenida con garantía de anonimato y estimación de duración (15–25 minutos).

34. Responde sección por sección (una dimensión a la vez).

35. Cada sección combina preguntas Likert (1–5), selección múltiple y texto libre.

36. Puede guardar progreso y retomar antes de la expiración.

37. Al finalizar ve pantalla de agradecimiento. No accede a resultados.

Criterios de aceptación

- Funciona correctamente en móvil (responsive, touch-friendly).

- Progreso se guarda automáticamente cada 30 segundos.

- Puede navegar hacia atrás para modificar respuestas antes de enviar.

- No ve organigrama, nombres de otros participantes ni información de la estructura.

# 10. Dimensiones del diagnóstico y cuestionario

## 10.1. Dimensiones completas (plan premium — 8 dimensiones)


| **#** | *Dimensión** | *Qué evalúa** | *Ejemplo de tensión detectable** |
|---|---|---|---|
| 1 | Liderazgo | Estilo, toma de decisiones, visión, confianza en la dirección | Líder dice tener puertas abiertas pero equipos reportan no poder acceder a él |
| 2 | Comunicación | Flujos de información, transparencia, canales, claridad | Info crítica llega por canales informales; formales percibidos como ineficaces |
| 3 | Cultura | Valores, normas implícitas, pertenencia, diversidad | Valores declarados no coinciden con normas de comportamiento observadas |
| 4 | Procesos | Claridad, eficiencia operativa, documentación, mejora continua | Procesos en papel que no se siguen; duplicidad de tareas |
| 5 | Poder | Dinámicas formales e informales, autonomía, centralización | Decisiones formalmente delegadas pero concentradas en una persona |
| 6 | Economía/Finanzas | Percepción de estabilidad, transparencia económica, compensación | Desalineación entre expectativas salariales y política de compensación |
| 7 | Operación | Ejecución, recursos, capacidad, carga de trabajo | Equipos sobrecargados mientras otros subutilizados |
| 8 | Misión | Claridad del propósito, alineación estratégica, impacto | Misión formal no resuena con propósito percibido |


## 10.2. Dimensiones Free (4 dimensiones)

El plan free evalúa: Liderazgo, Comunicación, Cultura y Operación. Con 1–2 preguntas Likert por dimensión y 1 pregunta abierta general. Duración objetivo: 5 minutos para el líder, 5–8 minutos para los miembros.

## 10.3. Estructura del cuestionario premium

Cada dimensión contiene 3–5 preguntas Likert (1–5), 1 pregunta de selección múltiple y 1–2 preguntas abiertas.

**Nota:** El cuestionario específico debe diseñarse con un psicólogo organizacional. Este PRD define estructura y tipos de pregunta; las preguntas concretas son un entregable separado.

# 11. Carga de documentos complementarios (premium)

Como **administrador premium**, quiero subir documentos internos para que el motor de IA los incorpore al análisis.

- Acceso desde el sidebar mínimo (no desde el canvas).

- Tipos: PDF, DOCX, PPTX, XLSX, TXT, CSV. Máximo 25 MB por archivo, 2 GB total.

- El admin etiqueta cada documento con dimensiones relevantes.

- Opcional: el diagnóstico puede generarse sin documentos.

# 12. Motor de IA y lógica analítica

## 12.1. Arquitectura híbrida

Capa 1: Scoring cuantitativo

- Score promedio (1–5) por dimensión basado en Likert.

- Desviación estándar para medir consenso vs. dispersión.

- Segmentación por área, nivel jerárquico y rol.

- Índice de coherencia: coincidencia entre percepciones de diferentes segmentos.

Capa 2: Análisis NLP (LLM)

- Respuestas abiertas procesadas por LLM para: extraer temas, identificar sentimientos, detectar contradicciones cuanti-cuali, generar narrativas.

- Documentos procesados mediante RAG: indexación, extracción de fragmentos relevantes por dimensión, contexto adicional al LLM.

Capa 3: Análisis de redes

- Métricas de grafo sobre la estructura: centralidad, densidad, clusters, nodos puente.

- Cruce con datos perceptivos: ¿nodos centrales tienen mejor o peor percepción? ¿Equipos aislados reportan más problemas?

## 12.2. Pipeline de procesamiento

38. **Validación:** umbral mínimo cumplido (40%, mínimo 5).

39. **Scoring:** agregación cuantitativa por dimensión y segmento.

40. **NLP:** prompt estructurado al LLM con respuestas abiertas anonimizadas.

41. **Red:** métricas de grafo, nodos críticos, asimetrías.

42. **Síntesis cruzada:** segundo paso de LLM que integra las 3 capas y genera diagnóstico narrativo + hallazgos + recomendaciones.

43. **Validación de calidad:** score de confianza por hallazgo (alto/medio/bajo).

## 12.3. Manejo de calidad y alucinaciones

- **Score de confianza:** cada hallazgo tiene nivel basado en volumen de evidencia y consistencia.

- **Marcado:** hallazgos con confianza baja se presentan como "posible patrón -- requiere verificación".

- **Trazabilidad:** cada afirmación incluye referencia a fuentes ("Basado en 12 respuestas del área técnica").

- **Sin invención:** el prompt instruye: "no generes hallazgos sin soporte en los datos. Si la evidencia es insuficiente, indícalo."

- **Feedback humano (premium):** el admin marca hallazgos como correcto/incorrecto/parcial.

## 12.4. Motor Free vs. Premium


| **Aspecto** | **Free** | **Premium** |
|---|---|---|
| Scoring | Promedio simple por dimensión | Promedio + desviación + segmentación + coherencia |
| NLP | No aplica | Análisis completo de respuestas abiertas |
| Red | No aplica | Análisis de grafo completo |
| Output | Score radar (4 dimensiones) | Diagnóstico narrativo + hallazgos + recomendaciones |
| Documentos | No aplica | RAG sobre documentos cargados |


# 13. Presentación de resultados

## 13.1. Resultados Free

Pantalla simple con radar chart de 4 dimensiones, scores numéricos y mensaje contextual personalizado. CTA de upgrade visible y prominente.

## 13.2. Resultados Premium (viven en el canvas)

Los resultados se presentan como capas sobre el canvas, no como páginas separadas:

Capa Análisis — Organigrama enriquecido

Nodos coloreados por nivel de tensión (verde/amarillo/rojo). Conexiones con intensidad de flujo o fricción. Filtrado por dimensión. Comparación temporal con diagnósticos anteriores.

Capa Resultados — Hallazgos y recomendaciones

Nodos con badges de hallazgos. Panel lateral muestra hallazgos específicos por nodo/área.

Diagnóstico narrativo

Se presenta como panel expandido lateral derecho (60–70% del viewport) según la definición de la sección 7.9. El canvas permanece visible en segundo plano y puede coordinarse visualmente con el contenido del panel. Estructura del contenido:

44. **Resumen ejecutivo:** 1 párrafo con los 3 hallazgos más relevantes.

45. **Análisis por dimensión:** score, interpretación, evidencia, tensiones.

46. **Hallazgos transversales:** patrones que cruzan múltiples dimensiones.

47. **Recomendaciones:** priorizadas por impacto y viabilidad.

48. **Advertencias:** tasa de respuesta, sesgos potenciales, áreas con evidencia insuficiente.

Dashboard de scores

Radar chart con 8 dimensiones, desviación, segmentación. Accesible desde la Capa Análisis como panel expandible.

Exportación (premium)

- PDF con diagnóstico completo incluyendo gráficas.

- DOCX editable.

- CSV con datos cuantitativos agregados (nunca individuales).

# 14. Ciclo continuo de diagnóstico

- Modificar estructura en cualquier momento.

- Lanzar nuevas rondas de entrevistas.

- Ejecutar nuevo diagnóstico y comparar con anteriores.

- Ver evolución de cada dimensión en el tiempo.

El sistema almacena snapshots inmutables de cada diagnóstico.

## 14.1. Estados del diagnóstico


| **Estado** | **Descripción** | **Transición** |
|---|---|---|
| Borrador | Estructura creada, sin entrevistas | → En recolección |
| En recolección | Entrevistas enviadas | → Listo para procesar |
| Listo para procesar | Umbral cumplido | → Procesando |
| Procesando | Motor de IA trabajando | → Publicado |
| Publicado | Resultados disponibles | → Nuevo ciclo o Archivado |
| Archivado | Inmutable | N/A |


# 15. Modelo de datos (entidades principales)


> **Actualizado v2.2 (decisiones A2, A3, A4):** el modelo de datos se reestructura. Group y Member se unifican como Node con campo `type` (`unit` o `person`). LateralRelation se reemplaza por Edge con `edge_type` cerrado a `lateral` o `process`. Se introduce AssessmentCampaign como entidad de primera clase para soportar múltiples diagnósticos en el tiempo. NodeState almacena el estado de captura por nodo y por campaña. Para detalle conceptual completo, ver `docs/MODEL_PHILOSOPHY.md`.

| **Entidad** | **Atributos clave** | **Relaciones** |
|---|---|---|
| User | id, email, name, auth_provider, created_at | Tiene muchas Memberships |
| Membership | user_id, org_id, role (owner \| admin \| viewer) | Conecta User con Organization |
| Organization | id, name, type, size_range, plan (free \| premium) | Tiene muchos Nodes, AssessmentCampaigns, Documents |
| Node | id, organization_id, type (unit \| person), name, description, parent_node_id, position_x, position_y, attrs (jsonb), created_at, deleted_at (nullable) | Pertenece a Org. Puede tener children Nodes (jerarquía via parent_node_id). Puede ser source o target de Edges. Tiene NodeStates por cada Campaign en la que participa. `deleted_at` implementa soft-delete para preservar integridad referencial con tablas del motor. |
| Edge | id, source_node_id, target_node_id, edge_type (lateral \| process), edge_metadata (jsonb), created_at, deleted_at (nullable) | Conecta dos Nodes. La jerarquía NO se modela como Edge: vive en Node.parent_node_id. `deleted_at` implementa soft-delete para preservar integridad referencial con `evidence_links` del motor. |
| AssessmentCampaign | id, org_id, name, status (draft \| active \| closed), started_at, ended_at | Pertenece a Organization. Agrupa todos los NodeStates, Documents y Diagnostics de un evento de diagnóstico. |
| NodeState | id, node_id, campaign_id, status (invited \| in_progress \| completed \| skipped), invited_at, completed_at, interview_data (jsonb), respondent_token | Estado de captura de un Node en el contexto de una Campaign específica. Único por (node_id, campaign_id). Semántica del enum `status` documentada en `docs/MODEL_PHILOSOPHY.md` §5.2.1. |
| Document | id, org_id, campaign_id (nullable), filename, type, size, dimension_tags\[\], uploaded_at | Pertenece a Organization. Si campaign_id es null, es permanente del nodo; si tiene valor, está asociado a esa Campaign. |
| Diagnostic | id, org_id, campaign_id, status, structure_snapshot, scores, narrative_md, findings, recommendations, created_at | Pertenece a Organization y a una Campaign específica. |
| Finding | id, diagnostic_id, dimension, title, description, confidence, sources\[\] | Pertenece a Diagnostic |
| Recommendation | id, diagnostic_id, priority, title, description, justification | Pertenece a Diagnostic |
| QuickAssessment | id, org_id, leader_responses, member_count, scores, created_at | Plan Free: almacena datos del diagnóstico rápido |

**Nota sobre nomenclatura legacy:** las tablas del motor de análisis (`node_analyses`, `group_analyses`, `org_analyses`, `findings`, `recommendations`, `evidence_links`, `document_extractions`) descritas en `docs/MOTOR_ANALISIS.md` siguen usando el término "node" en sentido conceptual de "respondiente individual" (equivale a un Node con type=person en este modelo). Las FKs actuales de esas tablas hacia `groups` y `members` se mantienen durante la fase de coexistencia documentada en `docs/DEUDA_DOCUMENTAL.md`.


**Nota:** modelo conceptual. El esquema final se define con backend e incluirá tablas de auditoría, historial, permisos y configuración de cuestionarios.

# 16. Arquitectura técnica de alto nivel

## 16.1. Stack sugerido


| **Capa** | **Tecnología** | **Justificación** |
|---|---|---|
| Frontend | React + TypeScript + TailwindCSS | Ecosistema maduro para canvas interactivo y responsive |
| Canvas | React Flow o D3.js | Grafos interactivos con drag-and-drop |
| Backend / API | Node.js (Fastify) o Python (FastAPI) | Node si JS-first; Python si prioriza ML/NLP |
| BD relacional | PostgreSQL | Robusta, JSON nativo, extensiones para grafos (Apache AGE) |
| BD vectorial | Pinecone, Weaviate o pgvector | Embeddings de documentos para RAG |
| Cola de procesamiento | Redis + BullMQ o Celery | Diagnósticos procesados de forma asíncrona |
| Almacenamiento | AWS S3 o equivalente | Documentos cargados |
| LLM | Anthropic (Claude) vía API | Calidad de razonamiento para análisis organizacional |
| Email | Resend, SendGrid o AWS SES | Invitaciones y recordatorios |
| Auth | Auth0, Clerk o Supabase Auth | SSO Google/Microsoft + tokens de entrevista |
| Hosting | Vercel (frontend) + Railway/AWS (backend) | Escalabilidad progresiva |


## 16.2. Estructura de rutas (alineada con modelo de acceso)

La estructura de rutas del frontend refleja el principio de que la organización es la unidad de navegación:

- **/login** — autenticación

- **/orgs** — selector de organización (solo si tiene múltiples)

- **/org/{org_id}/canvas** — canvas principal (home real del producto premium)

- **/org/{org_id}/settings** — configuración de la organización

- **/org/{org_id}/billing** — plan y facturación

- **/org/{org_id}/documents** — carga de documentos

- **/org/{org_id}/score** — pantalla de score radar (home del plan free)

- **/interview/{token}** — experiencia del entrevistado (independiente, sin auth)

- **/account** — settings de cuenta del usuario

**Rutas prohibidas:** /dashboard, /admin/\*, /org/{id}/members, /org/{id}/interviews, /org/{id}/results. Estas funcionalidades viven en el canvas.

## 16.3. Escalabilidad

- Soporte para organizaciones de 5 a 10,000+ nodos.

- Orgs >500 nodos: procesamiento puede tomar minutos. Indicador de progreso + notificación por email.

- Embeddings procesados asíncronamente al cargar documentos.

- Multi-tenant desde día 1: aislamiento a nivel de datos por organización.

## 16.4. Seguridad y privacidad

- TLS 1.3 en tránsito, AES-256 en reposo.

- PII cifrada a nivel de campo.

- Respuestas desvinculadas de identidad antes de enviar al LLM: el modelo recibe "Respondente área técnica, nivel senior", no "Carlos Pérez".

- Retención configurable. Borrado completo en eliminación de cuenta (GDPR/Habeas Data).

- Logs de auditoría. Tokens de un solo uso con expiración.

# 17. Diseño, UX y estética

## 17.1. Principios

- **La organización como objeto manipulable:** el canvas es el centro, no un accesorio.

- **Complejidad navegable:** zoom, agrupación, filtros, enfoque progresivo.

- **Acción directa:** clic, arrastre, expansión. Respuesta inmediata y predecible.

- **La estética revela, no impresiona:** ligero, preciso, silenciosamente sofisticado. Referentes: Linear, Notion, Figma.

## 17.2. Entregables de diseño requeridos

49. Design system: paleta, tipografía, espaciado, componentes, iconografía.

50. Mapa de navegación (flujo admin + flujo entrevistado + flujo free).

51. Wireframes de alta fidelidad para pantallas críticas.

52. Estados vacíos, de carga y de error.

53. Responsive breakpoints (crítico: experiencia del entrevistado optimizada para móvil).

54. Microinteracciones del canvas (drag-and-drop, cambio de capa, panel lateral).

55. Accesibilidad: WCAG 2.1 AA. Contrastes, navegación por teclado, screen readers.

## 17.3. Pantallas críticas


| **Pantalla** | **Plan** | **Complejidad** |
|---|---|---|
| Registro + onboarding free | Free | Media |
| Encuesta rápida del líder | Free | Baja-Media |
| Ingreso de miembros (3-5) | Free | Baja |
| Pantalla de espera / progreso | Free | Baja |
| Score radar + CTA upgrade | Free | Media |
| Selector de organización | Ambos | Baja |
| Canvas — Capa Estructura+Captura | Premium | Alta (núcleo) |
| Canvas — Capa Análisis | Premium | Alta |
| Canvas — Capa Resultados | Premium | Alta |
| Panel lateral contextual (3 estados) | Premium | Alta |
| Panel expandido diagnóstico narrativo (60–70% viewport) | Premium | Alta |
| Entrevista (mobile-first) | Premium | Media |
| Bienvenida + anonimato (entrevistado) | Premium | Baja |


# 18. Roadmap y fases

El roadmap prioriza el embudo free primero para validar activación y conversión, luego construye el producto premium completo.

## 18.1. Fase 0 -- Free MVP (semanas 1–4)

- Autenticación y registro.

- Flujo de onboarding free completo (encuesta líder + ingreso de miembros + encuesta miembros).

- Motor de scoring simple (promedio por dimensión).

- Pantalla de score radar con CTA de upgrade.

- Email transaccional para invitaciones a miembros.

**Objetivo:** validar que los líderes completan el flujo y que la tasa de respuesta de miembros es viable.

## 18.2. Fase 1 -- Canvas y estructura (semanas 4–8)

- Canvas interactivo con Capa Estructura+Captura.

- CRUD de nodos y relaciones jerárquicas (Edge con tipos lateral y process).

- Panel lateral contextual unificado (sección de identidad + sección de captura).

- Importación CSV + templates prediseñados.

- Sidebar mínimo (settings, billing).

- Migración free → premium (nodos precargados).

- Schema de AssessmentCampaign instalado; UI de campañas múltiples diferida a Fase 5.

## 18.3. Fase 2 -- Captura y entrevistas (semanas 7–11)

> **Actualizado v2.2:** la Fase 2 ya no agrega una capa nueva al canvas, porque las acciones de captura quedan integradas en la Capa Estructura+Captura desde Fase 1. Esta fase ahora se concentra en el sistema de invitaciones y en la experiencia del entrevistado.

- Sistema de invitaciones con tokens, integrado en la sección de captura del panel lateral.

- Experiencia del entrevistado (responsive, mobile-first).

- Cuestionario completo (8 dimensiones).

- Estados de captura por NodeState vinculados a la Campaign activa.

## 18.4. Fase 3 -- Motor de IA (semanas 9–14)

- Pipeline scoring cuantitativo completo.

- Integración LLM para respuestas abiertas.

- Análisis de red.

- Síntesis cruzada y diagnóstico narrativo.

- Scores de confianza.

## 18.5. Fase 4 -- Resultados y entrega (semanas 12–16)

- Capa Análisis y Capa Resultados del canvas.

- Panel lateral en estados Análisis y Resultados.

- Panel expandido de diagnóstico narrativo.

- Dashboard de scores.

- Exportación PDF/DOCX.

## 18.6. Fase 5 -- Producto completo (semanas 15–20)

- Carga de documentos + RAG.

- Comparación temporal entre diagnósticos.

- Relaciones laterales en canvas.

- Roles viewer y admin colaborador.

- Zoom semántico para orgs grandes.

**Nota:** tiempos estimados. Dependen de equipo, velocidad de iteración y complejidad de integración LLM. Planificación recomendada en sprints de 2 semanas con demo al cierre.

# 19. Riesgos, supuestos y dependencias

## 19.1. Riesgos


| **Riesgo** | **Prob.** | **Impacto** | **Mitigación** |
|---|---|---|---|
| Calidad del LLM: diagnósticos genéricos o alucinaciones | Alta | Crítico | Score de confianza, trazabilidad, prompt engineering iterativo, feedback humano |
| Baja tasa de respuesta de entrevistados | Media | Alto | UX móvil, recordatorios, garantía anonimato, duración corta |
| Baja activación free (líderes no completan) | Media | Alto | Flujo <10 min, progreso visible, onboarding sin fricción |
| Baja conversión free → premium | Media | Alto | CTA contextual basado en score, trial premium, mensaje personalizado |
| Costo API LLM por diagnóstico | Media | Medio | Optimizar prompts, cachear intermedios, limitar en free |
| Privacidad y compliance | Baja | Crítico | Anonimización pre-LLM, cifrado, retención, asesoría legal |
| Canvas complejo para orgs grandes | Media | Medio | Agrupación, zoom semántico, lazy rendering |


## 19.2. Supuestos

- Los líderes pueden construir la estructura básica o importarla.

- Los miembros responden con garantía de anonimato.

- Un cuestionario de 15–25 min captura información suficiente.

- Un LLM de frontera genera análisis organizacional de calidad.

- El flujo free de <15 min genera suficiente valor percibido para motivar upgrade.

## 19.3. Dependencias

- **API LLM:** disponibilidad, rate limits, pricing, retención de datos del proveedor.

- **Email:** deliverability (SPF, DKIM, DMARC).

- **Cuestionario:** validación con experto en desarrollo organizacional antes de desarrollo.

# 20. Decisiones pendientes y próximos pasos


| **#** | *Decisión** | *Responsable** | *Plazo** |
|---|---|---|---|
| 1 | Cuestionario final por dimensión (free y premium) | Producto + Psicólogo organizacional | Antes de Fase 0 |
| 2 | Preguntas específicas de la encuesta free (4 dimensiones) | Producto + Psicólogo | Antes de Fase 0 |
| 3 | Pricing concreto de planes | Producto + Negocio | Antes de Fase 5 |
| 4 | Proveedor LLM y modelo definitivo | Tech lead + Producto | Antes de Fase 3 |
| 5 | Política de privacidad y TOS | Legal | Antes de lanzamiento |
| 6 | Design system y wireframes | Diseño | Paralelo a Fase 0–1 |
| 7 | Benchmark calidad diagnósticos (dataset validación) | IA/ML + Producto | Durante Fase 3 |
| 8 | Texto y tono del CTA de conversión free→premium | Producto + Growth | Antes de Fase 0 |
| 9 | Templates de organización para onboarding | Diseño + Producto | Antes de Fase 1 |
| 10 | Integraciones HRIS | Backend | Post-MVP |
