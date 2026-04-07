# Backend

## Inicialización segura de base de datos (desarrollo)

Este backend **no crea tablas en startup**. Para inicializar la DB local, usa migraciones:

```bash
./scripts/init_db.sh
```

Luego corre el seed idempotente:

```bash
python seed.py
```
