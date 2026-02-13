# 🏥 Sistema de Gestión de Citas Médicas - Backend

Este backend gestiona las operaciones principales del sistema de citas médicas: registro de usuarios (pacientes, médicos, administradores), creación y gestión de citas, historial, autenticación, y conexión a la base de datos en Supabase.

---

## Tecnologías utilizadas

- **Python 3.11+**
- **FastAPI** – Framework principal para API REST.
- **Supabase** – Base de datos PostgreSQL con autenticación integrada.
- **Uvicorn** – Servidor ASGI para ejecutar la API.
- **Pydantic** – Validación de datos.
- **dotenv** – Manejo de variables de entorno.

---

## ⚙️ Instalación y configuración

-**Crear entorno Virtual**

python -m venv venv
venv\Scripts\activate     


-**Instalar Dependencias**-

pip install -r requirements.txt


-**Ejecutar el Servidor**

uvicorn main:app --reload
