# Backend

## Inicialización local de base de datos

Este backend **no crea tablas en startup**. Después de levantar servicios con `docker compose up`, inicializa la DB local así:

```bash
docker compose exec backend bash
./scripts/init_db.sh
```

Validación rápida:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/x-www-form-urlencoded" -d "username=superadmin@lab.com&password=changeme123"
```
