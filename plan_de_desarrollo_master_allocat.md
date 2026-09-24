# PLAN DE DESARROLLO ESTRUCTURADO - SISTEMA WEB "ALLOCAT"
**Versión:** 1.0
**Documento dirigido a:** Agente de IA para Generación y Desarrollo de Código.
**Contexto del Proyecto:** ALLOCAT es un sistema web de gestión de recursos organizacionales, diseñado para optimizar el uso y brindar transparencia en la asignación de recursos.

---

## 1. ARQUITECTURA Y STACK TECNOLÓGICO
El sistema operará bajo una arquitectura **Monolítica Modular** (preparada para una futura migración a microservicios).

*   **Frontend:** React.js (Hooks, Context API/Redux para manejo del estado global).
*   **Backend:** Python (FastAPI o Django REST Framework) o Java (Spring Boot). *Para efectos de esta instrucción, se priorizará Python (FastAPI) debido a su rapidez y facilidad para testing con Pytest.*
*   **Base de Datos:** MySQL (Relacional).
*   **Seguridad:** JWT (JSON Web Tokens) y Hashing de contraseñas (Argon2 o bcrypt).
*   **Manejo de Concurrencia:** Bloqueo Optimista (Optimistic Locking) a nivel de base de datos.
*   **Notificaciones:** Protocolo SMTP integrado con un sistema de colas (ej. Celery + Redis o BackgroundTasks).

---

## 2. INSTRUCCIONES ESTRICTAS PARA EL AGENTE DE IA
Como agente de desarrollo, debes seguir estas reglas absolutas al generar el código:
1.  **Modularidad:** Mantén el código estrictamente separado por dominios (Seguridad, Catálogo, Reservas, Reportes, Notificaciones).
2.  **Manejo de Errores:** Implementa respuestas HTTP estandarizadas (400, 401, 403, 404, 500) con mensajes claros en formato JSON.
3.  **Trazabilidad:** Cada acción de escritura (POST, PUT, DELETE, PATCH) debe disparar una inserción automática en la tabla de `logs` (Auditoría).
4.  **Cobertura de Pruebas:** Todo código generado debe venir acompañado de su respectivo archivo de pruebas (Jest para Frontend, Pytest para Backend) garantizando un **Mínimo del 80% de cobertura**.

---

## 3. FASE 1: DESARROLLO DEL MÓDULO BÁSICO Y CI/CD (REQUISITO PRIORITARIO)

Este módulo es la base del sistema y debe desarrollarse primero. Contiene la gestión de usuarios, roles y autenticación.

### 3.1. Requerimientos del Módulo de Autenticación y Usuarios
*   **Entidades de BD (Modelos):**
    *   `User`: `id`, `name`, `email` (único), `hashed_password`, `role_id`, `created_at`, `is_active`.
    *   `Role`: `id`, `name` (Valores: 'ADMIN', 'REQUESTER', 'AUDITOR').
*   **Endpoints requeridos (API REST):**
    *   `POST /api/v1/auth/register`: Registro de nuevas personas (por defecto rol 'REQUESTER').
    *   `POST /api/v1/auth/login`: Autenticación. Recibe email/password, retorna token JWT.
    *   `GET /api/v1/users/me`: Devuelve la información del usuario autenticado basado en el JWT.
*   **Implementación de JWT:**
    *   El token debe incluir en su payload el `user_id` y el `role`.
    *   Expiración del token: 2 horas.
    *   Implementar un Middleware o Dependency para proteger rutas verificando el token.
*   **Roles y Permisos:**
    *   `ADMIN`: Acceso total (CRUD de recursos, aprobación/rechazo de solicitudes, asignar roles).
    *   `REQUESTER`: Solo puede ver recursos, crear solicitudes y ver su propio historial.
    *   `AUDITOR`: Solo lectura de reportes y logs del sistema.

### 3.2. Pruebas Unitarias (Testing)
El agente de IA debe generar scripts de prueba estrictos:
*   **Backend (Pytest):**
    *   `test_auth.py`: Probar registro exitoso, fallo por email duplicado, login exitoso (recepción de JWT), login fallido (credenciales incorrectas).
    *   Probar middleware de roles (ej. asegurar que un `REQUESTER` reciba un error HTTP 403 Forbidden si intenta acceder a un endpoint de `ADMIN`).
*   **Frontend (Jest + React Testing Library):**
    *   `Auth.test.jsx`: Simular la renderización del formulario de login, escritura en inputs, envío del formulario y manejo de la respuesta (guardado del token en `localStorage` o `cookies`).
*   *Meta:* **>80% de code coverage**. Las aserciones deben validar casos de éxito, casos de error y casos límite.

### 3.3. Pipeline CI/CD (GitHub Actions)
Generar un archivo `.github/workflows/ci-cd.yml` que cumpla con:
1.  **Trigger:** `push` y `pull_request` en la rama `main` y `develop`.
2.  **Jobs:**
    *   **Build & Test:**
        *   Instalar dependencias (Python/Node.js).
        *   Levantar una base de datos MySQL efímera usando servicios de GitHub Actions.
        *   Ejecutar Linter.
        *   Ejecutar Pytest (Backend) y Jest (Frontend) verificando que el threshold del 80% se cumpla.
    *   **Deploy (Entorno de Prueba):**
        *   Condición: Solo si el job de "Build & Test" es exitoso y el push es en `main`.
        *   Paso: Empaquetar la aplicación (Docker build) y hacer push a un registry (ej. DockerHub o GitHub Packages), o ejecutar un despliegue vía SSH/Webhook a un servidor de Staging.

---

## 4. FASE 2: DESARROLLO DE MÓDULOS CORE

### 4.1. Módulo de Catálogo de Recursos (CRUD)
*   **Modelos:** `Resource` (`id`, `name`, `category`, `status`, `version` para Optimistic Locking, `created_at`).
*   **Categorías:** Financiero, humano, material, comida, etc.
*   **Estados:** DISPONIBLE, ASIGNADO, EN_ESPERA, MANTENIMIENTO.
*   **Regla de Negocio:** Solo `ADMIN` puede hacer altas, bajas o modificaciones.

### 4.2. Módulo de Reservas (Sistema de Asignación)
*   **Modelos:** `Reservation` (`id`, `resource_id`, `requester_id`, `start_date`, `end_date`, `status`, `approved_by`).
*   **Estados de Reserva:** PENDIENTE, APROBADA, RECHAZADA.
*   **Flujo de Concurrencia (Crucial):** Implementar *Optimistic Locking* utilizando el campo `version` del recurso. Si 2 usuarios (`REQUESTER`) intentan reservar el mismo recurso disponible al mismo tiempo, la BD debe abortar la transacción del segundo con un error manejado, devolviendo al usuario un mensaje: "El recurso ya no está disponible".
*   **Calendario (Frontend):** Integrar una librería de calendario (ej. `react-big-calendar`) que consuma un endpoint `GET /api/v1/reservations` filtrado por mes, para mostrar gráficamente la disponibilidad.

### 4.3. Módulo de Trazabilidad y Logs
*   **Modelo:** `AuditLog` (`id`, `action`, `table_name`, `record_id`, `user_id`, `timestamp`, `details`).
*   **Regla:** Ningún usuario, ni siquiera el administrador, puede modificar o eliminar registros de esta tabla (Inmutabilidad por software).

### 4.4. Módulo de Notificaciones
*   **Implementación:** Usar colas asíncronas (Task Queue) para evitar que el fallo del servicio SMTP bloquee la aplicación.
*   **Eventos disparadores:**
    *   Creación de reserva (Notifica al ADMIN).
    *   Aprobación/Rechazo de reserva (Notifica al REQUESTER).
    *   Recurso con alta demanda / agotado.

### 4.5. Módulo de Reportes
*   **Endpoints:**
    *   Generar métricas: Tasa de utilización, recurso más demandado.
    *   Soporte para filtros por tiempo (mes, trimestre, año).
*   **Exportación:** Implementar librería en el backend (ej. `pdfkit` o `reportlab` en Python) para retornar un Blob binario `application/pdf` al frontend.

---

## 5. ESTRATEGIAS DE MITIGACIÓN DE RIESGOS EN EL CÓDIGO

El agente de IA deberá generar el código considerando las mitigaciones del acta:
1.  **Scope Creep / Extensibilidad:** Usa patrones de diseño como Inyección de Dependencias y Repositorios para que agregar nuevas funciones no requiera reescribir código existente.
2.  **Seguridad (Pruebas de Regresión):** El agente de IA debe generar un test automatizado llamado `test_security_roles.py` que simule a un usuario básico intentando inyectar payloads o acceder a endpoints protegidos de administrador.

---
**FIN DEL DOCUMENTO DE ESPECIFICACIONES**