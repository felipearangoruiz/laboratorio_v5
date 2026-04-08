# laboratorio_v5

1. Clona este repositorio y entra a `laboratorio_v5/`.
2. Copia `.env.example` a `.env`.
3. Completa las variables necesarias en `.env`.
4. Ejecuta `docker-compose up --build`.
5. Verifica `http://localhost:8000/health`.

## Frontend local (sin Docker)

Para evitar errores de conexión en páginas admin renderizadas en servidor (SSR), copia `frontend/.env.local.example` a `frontend/.env.local` y configura:

- `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `API_URL=http://localhost:8000`

