# Laboratorio de Modelamiento Institucional con IA

Plataforma web que permite a líderes organizacionales diagnosticar cómo funciona su organización internamente, combinando estructura organizacional, entrevistas a miembros y análisis con IA.

## Stack

- **Backend:** FastAPI + SQLModel + PostgreSQL + Alembic
- **Frontend:** Next.js 14 + React 18 + TypeScript + TailwindCSS
- **Infraestructura:** Docker Compose

## Cómo ejecutar

```bash
# Clonar y entrar
cd laboratorio_v5

# Copiar variables de entorno
cp .env.example .env

# Levantar servicios
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# Health check: http://localhost:8000/health
```

### Frontend local (sin Docker)

```bash
cd frontend
cp .env.local.example .env.local
# Configurar NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

## Estructura del proyecto

```
laboratorio_v5/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLModel: User, Organization, Group, Member, Interview, QuickAssessment
│   │   ├── routers/         # FastAPI routers: auth, organizations, members, interviews, quick_assessment
│   │   ├── questions.py     # Banco de preguntas premium (5 lentes)
│   │   └── questions_free.py # Banco de preguntas free (4 dimensiones)
│   ├── alembic/             # Migraciones de base de datos
│   └── Dockerfile
├── frontend/
│   ├── app/                 # Next.js App Router
│   │   ├── login/           # Autenticación
│   │   ├── register/        # Registro
│   │   ├── onboarding/      # Flujo free: bienvenida → encuesta → miembros
│   │   ├── score/[id]/      # Score radar con CTA upgrade
│   │   └── interview/[token]/ # Encuesta para miembros invitados
│   ├── lib/                 # API client y tipos
│   └── Dockerfile
├── docs/
│   ├── PRD_v2.1_Diagnostico_Organizacional.docx     # Fuente de verdad del producto
│   └── ARQUITECTURA_ANALISIS_RESULTADOS.md          # Arquitectura UI capas Análisis/Resultados
├── docker-compose.yml
└── CLAUDE.md               # Guía para Claude Code
```

## Modelo de negocio

### Plan Free (Fase 0 - actual)
Diagnóstico rápido: encuesta corta del líder + encuestas de miembros → score radar en 4 dimensiones (Liderazgo, Comunicación, Cultura, Operación).

### Plan Premium (fases futuras)
Canvas organizacional interactivo, 8 dimensiones, entrevistas profundas, motor IA y diagnóstico narrativo.

## Documentación

- **PRD v2.1:** `docs/PRD_v2.1_Diagnostico_Organizacional.docx` — fuente de verdad del producto
- **Arquitectura UI:** `docs/ARQUITECTURA_ANALISIS_RESULTADOS.md` — especificación de capas Análisis/Resultados
- **CLAUDE.md:** guía de desarrollo, arquitectura, roadmap de fases, motor de análisis
