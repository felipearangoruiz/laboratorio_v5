# Migration Execution Report (APPLY)

_Generated: 2026-04-21T17:44:16.202776+00:00 (UTC)_

```
[migrate] APPLY — 2026-04-21T17:44:16.202776+00:00
================================================================

## SNAPSHOT MOTOR (antes)
  analysis_runs: 3
  node_analyses: 10
  group_analyses: 3
  org_analyses: 1
  findings: 4
  recommendations: 4
  evidence_links: 0
  document_extractions: 0

  Orgs: 4 | Groups: 20 | Members: 6 | Interviews: 6

## PARTE 1 — AssessmentCampaigns
  Organizaciones: 4
  SKIP  [Laboratorio Demo] campaign ya existe (1b7ff690-dd24-4f2c-8a0a-ceac735af501)
  SKIP  [katronix] campaign ya existe (6de4e4c9-4510-41d0-ae5f-eb42de664daf)
  SKIP  [ca] campaign ya existe (23fcf517-f3d7-4a71-8823-22905f862416)
  SKIP  [Constructora Meridian SAS] campaign ya existe (8f944c91-54ef-410e-aaa7-ec7aabc2047a)
  → 0 creadas, 4 saltadas.

## PARTE 2 — Groups → Nodes (type=unit)
  Groups encontrados: 20
  D7: 2 grupo(s) con posición (0,0) → auto-grid
  SKIP  [default] Node ae41c538-38ca-4350-a58e-e131fff43bb4 ya existe
  SKIP  [Gerente General] Node 706236b7-c0d7-4996-9a10-636414728918 ya existe
  SKIP  [CEO] Node 27c6e175-3ad7-480e-969d-61754b629fa8 ya existe
  SKIP  [Dir. Financiero] Node d108b8b6-6dc6-4a5b-991f-c86b2e71c16b ya existe
  SKIP  [Dir. Comercial] Node bfd0a363-1328-42b9-9c41-82f6a65a48e6 ya existe
  SKIP  [Dir. Operaciones] Node 5dfff697-00a7-47c7-b98c-d8b67b7429f6 ya existe
  SKIP  [Dir. Talento Humano] Node 9d02487e-4761-4516-be5b-f8eb811b73fe ya existe
  SKIP  [Operaciones] Node 5150db27-477b-428d-862c-4e9388c51b80 ya existe
  SKIP  [Comercial] Node a0a2b445-4c5c-44f4-a517-c7f6780301fa ya existe
  SKIP  [Finanzas / CFO] Node c915a6fa-8f82-4e39-9d61-410ccba404d6 ya existe
  SKIP  [Contabilidad] Node 88d98167-6b4d-4f65-9194-f73dbbcda9bd ya existe
  SKIP  [Tesorería] Node 0a05860b-433a-4911-bf96-4498c6a44f87 ya existe
  SKIP  [Ventas] Node 4be36290-8f91-44e8-b506-06763bdca5bb ya existe
  SKIP  [Marketing] Node 8cef4216-c149-42cb-b3b7-dcb060c2223d ya existe
  SKIP  [Producción] Node 23de9d91-f843-4c2c-a1d7-7cc169f7a643 ya existe
  SKIP  [Logística] Node 0597d688-89d7-45be-8c74-d0c7e48a2e9d ya existe
  SKIP  [Gerente de Operaciones] Node 1d92b0cf-59cb-4461-96d1-371b7962a419 ya existe
  SKIP  [Coordinador de Operaciones] Node 561c5e86-3d87-47cd-b126-465201078524 ya existe
  SKIP  [Director Comercial] Node 5ce841be-24f9-4a5a-8176-a47ea8138091 ya existe
  SKIP  [Ejecutivo Comercial] Node f735630d-7aee-401c-be9c-c30e10a4bd59 ya existe
  → 0 creados, 20 saltados.

## PARTE 3 — Members → Nodes (type=person)
  Members encontrados: 6
  SKIP  [CEO] Node c8518ccc-bcdc-4017-b269-6bf288875f98 ya existe
  SKIP  [Gerente de Operaciones] Node 4c020b06-6e03-45e7-87c2-e7a38ebb349e ya existe
  SKIP  [Coordinador de Operaciones] Node 62022319-6595-4294-bb65-2cdf9553d1e5 ya existe
  SKIP  [Director Comercial] Node e771d372-cb7c-4d29-bc55-e14f6a1c631a ya existe
  SKIP  [Ejecutivo Comercial] Node 51013fc4-0743-4822-b428-745081e0d546 ya existe
  SKIP  [Finanzas / CFO] Node 3a576991-89b7-4b77-98b2-b3261d9f3dad ya existe
  → 0 creados, 0 descartados (D3a).

## PARTE 4 — Interviews → NodeStates
  Interviews encontradas: 6
  [Adaptaciones de schema activas — ver docstring del módulo]
  SKIP  NodeState 296685d6-49c1-4864-b79a-a62b2050a2fd ya existe
  SKIP  NodeState 11c8a53e-2d93-4c4c-9dad-1f8554cd24fb ya existe
  SKIP  NodeState 901d6902-59cd-4c4b-8571-1838034ff84c ya existe
  SKIP  NodeState 826b9279-7148-41b9-84bd-7cd0e61f469a ya existe
  SKIP  NodeState 1ad16c1b-3cc5-4116-b2df-7fe4610b50b9 ya existe
  SKIP  NodeState 342b498f-5a5b-4e5f-8c7a-4ef3908e3069 ya existe
  → 0 creados, 0 descartados (D2).

## PARTE 6 — Validaciones post-migración
  ✅ (a) groups == nodes(unit): expected=20 actual=20
  ✅ (b) members == nodes(person)+discarded_D3: expected=6 actual=6
  ✅ (c) interviews == node_states+discarded_D2: expected=6 actual=6
  ✅ (d) node_analyses.group_id FKs válidas (orphans==0): expected=0 actual=0
  ✅ (e) analysis_runs unchanged: expected=3 actual=3
  ✅ (f) node_analyses unchanged: expected=10 actual=10
  ✅ (f) group_analyses unchanged: expected=3 actual=3
  ✅ (f) org_analyses unchanged: expected=1 actual=1
  ✅ (f) findings unchanged: expected=4 actual=4
  ✅ (f) recommendations unchanged: expected=4 actual=4
  ✅ (f) evidence_links unchanged: expected=0 actual=0
  ✅ (f) document_extractions unchanged: expected=0 actual=0
  ✅ (g) org 26a11ff1-14d5-44a8-83bd-ce2e26e49bd4 tiene 1 campaign: expected=1 actual=1
  ✅ (g) org 598b3037-9241-4b99-9c35-2b3a13e523a5 tiene 1 campaign: expected=1 actual=1
  ✅ (g) org 5f9faec5-56c4-4550-84a3-b9c6d55388b5 tiene 1 campaign: expected=1 actual=1
  ✅ (g) org 984bdeaf-14e8-47b9-b1e0-3c595b44bff8 tiene 1 campaign: expected=1 actual=1

✅ COMMIT: migración aplicada exitosamente.

## RESUMEN FINAL
  Modo: APPLY | Estado: OK
```
