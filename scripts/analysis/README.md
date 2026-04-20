# Motor de Análisis — Script de ejecución

Pipeline de 4 pasos que usa OpenAI para analizar una organización y guardar
los resultados en el backend.

---

## Instalación

```bash
cd scripts/analysis
pip install openai requests python-dotenv
```

---

## Variables de entorno

Crea un archivo `.env` en `scripts/analysis/`:

```env
OPENAI_API_KEY=sk-...
DIAGNOSIS_API_TOKEN=eyJ...   # JWT de un usuario admin de la org
```

---

## 1. Correr el seed mock (primera vez)

El seed crea una organización de prueba realista con 8 nodos, 6 entrevistas
completadas y 2 documentos institucionales.

```bash
# El backend debe estar corriendo
docker-compose up -d

# Crear la org mock
python mock/seed_mock_org.py
```

El script imprime al final el `DIAGNOSIS_API_TOKEN` y el `org_id`.
Cópialos en tu `.env`:

```env
OPENAI_API_KEY=sk-...
DIAGNOSIS_API_TOKEN=eyJ...        # lo que imprimió el seed
```

---

## 2. Correr el análisis completo

```bash
python run_analysis.py --org-id <uuid>
```

Con backend en otra URL:

```bash
python run_analysis.py --org-id <uuid> --base-url https://api.miapp.com
```

### Qué hace el script

| Paso | Modelo | Qué hace |
|------|--------|----------|
| 1 | `gpt-4o-mini` | Un prompt por nodo con entrevista completada → `node_analysis` |
| 2 | `gpt-4o-mini` | Un prompt por grupo (agrega nodos del mismo parent) → `group_analysis` |
| 3 | `gpt-4o` | Un prompt con todos los grupos → `org_analysis` |
| 4 | `gpt-4o` | Un prompt final → `findings + recommendations + narrative_md` |

Al terminar, los resultados están disponibles en:
- **Backend:** tablas `node_analyses`, `group_analyses`, `org_analyses`, `findings`, `recommendations`
- **Frontend:** capa Resultados del canvas (`/org/{id}/canvas?capa=resultados`)

---

## 3. Resume de una corrida fallida

Si el script falla en el paso 3 (por ejemplo, error de red), puede continuar
desde donde lo dejó:

```bash
# El run_id se imprime al inicio de la corrida y se guarda en .state_<run_id>.json
python run_analysis.py --org-id <uuid> --resume <run_id>
```

El archivo `.state_<run_id>.json` guarda:
- Qué nodos ya fueron procesados
- Qué grupos ya fueron procesados
- Si el análisis org ya fue completado
- El run_id para continuar

Al completar exitosamente, el archivo de estado se elimina automáticamente.

---

## Estructura de archivos

```
scripts/analysis/
├── run_analysis.py          # Script principal
├── .env                     # Variables de entorno (no commitear)
├── prompts/
│   ├── paso1_nodo.txt       # Prompt Paso 1 — extracción por nodo
│   ├── paso2_grupo.txt      # Prompt Paso 2 — síntesis de grupo
│   ├── paso3_org.txt        # Prompt Paso 3 — análisis organizacional
│   └── paso4_sintesis.txt   # Prompt Paso 4 — síntesis ejecutiva
└── mock/
    └── seed_mock_org.py     # Crea org de prueba con datos realistas
```

---

## Endpoints del backend que usa el script

| Método | Endpoint | Para qué |
|--------|----------|----------|
| GET | `/organizations/{org_id}/analysis/input` | Descarga todos los datos de la org |
| POST | `/organizations/{org_id}/analysis/runs` | Abre la corrida |
| POST | `/analysis/runs/{run_id}/nodes/{group_id}` | Guarda Paso 1 |
| POST | `/analysis/runs/{run_id}/groups/{group_id}` | Guarda Paso 2 |
| POST | `/analysis/runs/{run_id}/org` | Guarda Paso 3 |
| POST | `/analysis/runs/{run_id}/findings` | Guarda Paso 4 y cierra corrida |

El frontend puede consultar el estado con:
```
GET /organizations/{org_id}/analysis/status
```

---

## Costos estimados (Abril 2026)

| Paso | Modelo | Tokens approx | Costo |
|------|--------|---------------|-------|
| Paso 1 (×nodo) | gpt-4o-mini | ~1.5k | ~$0.001/nodo |
| Paso 2 (×grupo) | gpt-4o-mini | ~3k | ~$0.002/grupo |
| Paso 3 | gpt-4o | ~8k | ~$0.08 |
| Paso 4 | gpt-4o | ~12k | ~$0.12 |

**Org típica de 10 nodos / 4 grupos:** ~$0.25 por corrida completa.

---

## Solución de problemas

**`OPENAI_API_KEY` no definida**
```
ERROR: OPENAI_API_KEY no está definida
```
→ Asegúrate de que el archivo `.env` existe en `scripts/analysis/` y tiene la key.

**`DIAGNOSIS_API_TOKEN` expirado**
```
GET /organizations/.../analysis/input → 401
```
→ Vuelve a loguearte y actualiza el token en `.env`.

**JSON inválido del LLM**
El script reintenta automáticamente hasta 3 veces. Si falla, usa `--resume` para continuar.

**Fallo en paso 3 o 4**
```bash
python run_analysis.py --org-id <uuid> --resume <run_id>
```
Los pasos 1 y 2 ya completados no se re-ejecutan.
