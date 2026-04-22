# Hooks y utils del refactor (Sprint 2.2)

Este documento describe cuándo usar cada hook / util nuevo
introducido por el Sprint 2.2, antes de migrar componentes al
nuevo modelo en Sprint 2.3.

## `useOrg()` vs prop drilling de `orgId`

- **Úsalo** en componentes nuevos bajo `/org/[orgId]/...` que
  necesiten el `orgId` actual o la `Organization` cargada.
- **No lo uses** en componentes legacy durante Sprint 2.2: la
  prop `orgId` se conserva deliberadamente; su eliminación es
  trabajo explícito del Sprint 2.3.
- Lanza si se llama fuera de un `<OrgProvider>` — el layout
  `app/org/[orgId]/layout.tsx` ya lo monta.

```tsx
import { useOrg } from "@/lib/contexts/OrgContext";

function MyPanel() {
  const { orgId, organization, isLoading } = useOrg();
  // ...
}
```

## `useCanvasData()` vs `listNodes` / `listEdges` / `listNodeStates` directos

- **Úsalo** cuando un componente necesite al menos dos de las
  tres colecciones (nodes + edges + node_states). Deduplica
  fetches, centraliza el `isLoading`, ofrece `refetch()`.
- **No lo uses** para un solo endpoint puntual (p. ej. tomar un
  `NodeState` específico para editar): llama al helper directo.
- Excluye por defecto nodes/edges con `deleted_at != null`
  (soft-delete). Pasa `{ includeDeleted: true }` si necesitás
  ver tombstones.
- Filtra `node_states` por `campaignId` si se pasa.

```tsx
import { useCanvasData } from "@/lib/hooks/useCanvasData";

function CanvasView() {
  const { nodes, edges, nodeStates, isLoading, refetch } =
    useCanvasData({ campaignId });
  // ...
}
```

## `auth-utils` — `getAuthToken` / `authHeader` / `clearAuth`

- **Úsalo siempre** que necesites el token o un header de
  autorización en una request manual (`fetch` directo).
- Reemplaza `localStorage.getItem("access_token")` y la
  construcción manual de `Authorization: Bearer ...`.
- Son funciones puras (no hooks). Usa `useAuth` cuando necesites
  reactividad al cambio de sesión en un componente React.
- `authHeader()` devuelve un objeto spreadable (vacío si no hay
  sesión), diseñado para componer dentro de un objeto de
  headers.

```ts
import { authHeader, getAuthToken, clearAuth } from "@/lib/auth-utils";

const res = await fetch(url, {
  headers: { "Content-Type": "application/json", ...authHeader() },
});
```

## Política de tipado: `unknown` > `any`

- En código nuevo, evitá `any`. Preferí `unknown` + refinamiento
  explícito, o un tipo concreto contra el schema de backend
  (ver `backend/app/routers/*.py`).
- Los helpers legacy (`getOrgGroups`, `createGroup`,
  `updateGroup`, `deleteGroup`, `getPremiumQuestions`) mantienen
  `any` y están marcados `@deprecated`. Serán removidos cuando
  Sprint 2.3 migre sus consumers al nuevo modelo.

## View-models en `lib/view-models/`

- **Regla**: los componentes del canvas NO consumen `Node` /
  `Edge` crudos del backend. Siempre pasan por
  `toCanvasNode(node, nodeState?)` y `toCanvasEdge(edge)`.
- Esto aísla el shape del backend (soft-delete, `attrs`
  libres, FKs) del shape que espera React Flow.
- Si un componente necesita un dato nuevo del backend,
  extendé `CanvasNode.data` / `CanvasEdge.data` antes de
  exponerlo.
