# App Report DevOps Backend

Una aplicación backend en FastAPI para reportes de DevOps que sincroniza repositorios desde GitHub y monitorea su integración con Backstage.

## Visión General

Esta aplicación funciona como un servicio backend para seguir y monitorear repositorios a través de las plataformas GitHub y Backstage. Proporciona endpoints de API REST para sincronizar repositorios y obtener información sobre ellos, incluyendo:

- Uso de GitHub Actions
- Colaboradores
- Estado de integración con Backstage
- Listado de repositorios

El sistema utiliza MongoDB para almacenar datos de repositorios y proporciona una API para sincronizar esta información con GitHub y Backstage.

## Características

- Sincronización de repositorios desde la organización de GitHub a MongoDB
- Seguimiento de repositorios con GitHub Actions
- Listado de colaboradores para cada repositorio
- Verificación del estado de integración con Backstage
- API RESTful para acceso a datos

## Requisitos

- Python 3.13+
- MongoDB
- Token de API de GitHub
- Token de Backstage

## Instalación

### Configuración del Entorno

1. Clonar el repositorio:

```bash
git clone https://github.com/the-palace-company/app-report-devops-backend.git
cd app-report-devops-backend
```

2. Crear un entorno virtual e instalar dependencias usando `uv`:

```bash
uv venv
source .venv/bin/activate  # En Windows usar: .venv\Scripts\activate
uv sync
```

### Configuración

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```
github_org=<tu-organización-github>
github_token=<tu-token-github>
mongo_string_connection=<cadena-conexión-mongodb>
mongo_collection_name=<nombre-colección-mongodb>
backstage_token=<tu-token-backstage>
cors_origins=<orígenes-separados-por-comas>  # Ejemplo: "http://localhost:3000,https://app.ejemplo.com"
```

## Uso

### Iniciando la Aplicación

Ejecuta la aplicación FastAPI en desarrollo:

```bash
uv run fastapi dev
```

La API estará disponible en http://localhost:8000

### Endpoints de API

#### Endpoints de GitHub

- `GET /github/`: Obtener todos los repositorios con detalles
- `GET /github/active-repositories`: Obtener nombres de todos los repositorios activos
- `POST /github/sync`: Sincronizar repositorios desde GitHub a MongoDB
- `GET /github/test`: Probar la conexión a la API de Backstage

### Documentación Swagger

Accede a la documentación Swagger generada automáticamente en:

```
http://localhost:8000/docs
```

## Desarrollo

### Estructura del Proyecto

```
app-report-devops-backend/
├── app/
│   ├── db/
│   │   ├── github_commands.py  # Operaciones de BD para GitHub
│   │   └── mongo.py            # Gestor de conexión a MongoDB
│   ├── modules/
│   │   ├── backstage.py        # Cliente de API para Backstage
│   │   ├── github.py           # Cliente de API para GitHub
│   │   └── pyobject_mongo.py   # Serialización de objetos MongoDB
│   ├── routers/
│   │   └── github.py           # Rutas de API para GitHub
│   ├── schemas/
│   │   ├── repository.py       # Modelos de datos para repositorios
│   │   ├── settings.py         # Configuraciones de la aplicación
│   │   └── sync_response.py    # Modelos de respuesta para operaciones de sincronización
│   ├── dependencies.py         # Dependencias de FastAPI
│   └── main.py                 # Punto de entrada de la aplicación
├── .env                        # Variables de entorno (crear este archivo)
├── pyproject.toml              # Metadatos del proyecto y dependencias
└── README.md                   # Este archivo
```
