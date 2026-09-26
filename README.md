# ALLOCAT

Sistema ALLOCAT - Proyecto Final de Ingenieria en Desarrollo de Software.
Contenedores para backend (FastAPI), frontend (React + nginx), MySQL 8 y un
entorno de pruebas de seguridad con OWASP ZAP.

## Requisitos

- Docker Desktop con Linux containers.
- PowerShell en Windows (o bash si estas en Linux/macOS).

## Levantar el stack

```bash
docker compose up -d --build
docker compose ps
```

| Servicio  | URL                        | Notas                                        |
|-----------|----------------------------|----------------------------------------------|
| Frontend  | http://localhost:8080      | React servido por nginx                      |
| Backend   | http://localhost:8000/docs | FastAPI + OpenAPI                             |
| MySQL     | sin puerto publicado       | la BD no se expone al host                   |
| ZAP       | perfil aparte, ver abajo   | la API solo responde dentro del contenedor   |

Datos de prueba (creados por el servicio `seed`):

| Rol       | Email                  | Contrasena         |
|-----------|------------------------|--------------------|
| admin     | admin@example.com      | ZapAllocat2026!    |
| requester | requester@example.com  | ZapAllocat2026!    |
| auditor   | auditor@example.com    | ZapAllocat2026!    |

El seed tambien crea un recurso (`id=1`) y una reserva (`id=1`, estado
`PENDIENTE`). Es idempotente: se puede volver a ejecutar sin duplicar.

Reset total (borra la base):

```bash
docker compose down -v
```

## OWASP ZAP

El servicio `zap` vive en el perfil `zap` y arranca en modo daemon, con la API
en el puerto 8090 y la misma clave que usa `tools/test.env`
(`ZAP_API_KEY`).

### Escanear la API

```powershell
.\tools\zap\scan.ps1                  # modo rapido: 3 categorias de reglas
.\tools\zap\scan.ps1 -Full            # modo completo: las 5 categorias
.\tools\zap\scan.ps1 -Full -CatTimeout 30
```

El wrapper reinicia MySQL, backend, seed y ZAP, espera a que todo esté sano y
lanza el escaneo. Los reportes quedan en `zap-reports/`:

- `allocat-<timestamp>.json` - alertas crudas.
- `allocat-<timestamp>.html` - reporte navegable.

Que hace el escaneo, paso a paso (`tools/zap/scan.sh`):

1. Espera a que la API de ZAP y el backend respondan.
2. Hace login como admin y saca un token.
3. Borra los contextos de ZAP y crea uno nuevo (`ALLOCAT`) que incluye
   `http://backend:8000.*`, para que el active scan no toque nada externo.
4. Descarga el OpenAPI del backend.
5. Reproduce cada operacion del OpenAPI contra el API real a traves del proxy
   de ZAP (`tools/zap/gen-traffic.py`), de modo que cada nodo del arbol quede
   con metodo, ruta, query, cuerpo JSON y header `Authorization`.
6. Corre el active scan categoria por categoria, esperando a que cada una
   termine y parandola si se pasa del tiempo limite.
7. Genera los reportes JSON y HTML.
8. Imprime un resumen de alertas por riesgo y el detalle de las Medium/High.

Categorias de reglas de ZAP 2.17:

| # | Categorias         | Modo  |
|---|--------------------|-------|
| 0 | Information Gathering | rapido y completo |
| 1 | Client Browser        | solo completo     |
| 2 | Server Security       | rapido y completo |
| 3 | Miscellaneous        | solo completo     |
| 4 | Injection             | rapido y completo |

Variables de entorno (las define `tools/test.env` y `scan.sh` lee):
`ZAP_API_KEY`, `ZAP_TARGET`, `SCAN_QUICK`, `SCAN_CAT_TIMEOUT`, `REPORT_DIR`,
`ALLOCAT_ADMIN_EMAIL`, `ALLOCAT_ADMIN_PASSWORD`.

`SCAN_CAT_TIMEOUT` esta en **segundos** por categoria de reglas. Defaults:
600 s (10 min) en modo rapido, 1500 s (25 min) en modo completo.
`scan.ps1 -CatTimeout` si lo recibe en **minutos** y hace la conversion.

### Por que el escaneo corre dentro del contenedor

ZAP 2.17 no expone su API ni su web a clientes externos, aunque el puerto este
publicado. Cualquier request que no venga de una direccion permitida se
rechaza en el log del contenedor:

```
WARN API - Request to API URL http://zap:8090/JSON/core/view/version from 172.19.0.4 not permitted
```

La allow-list de direcciones de la API (`api.addrs.addr` en `config.xml`) solo
admite loopback por defecto y no hay opcion de linea de comandos para
cambiarla, asi que el puerto `8090` publicado no sirve para el navegador. Por
eso el flujo usa:

```bash
docker compose --profile zap up -d zap
docker compose exec -T zap bash /zap/scan/scan.sh
```

## Hallazgos de la ultima corrida

El modo rapido sobre una base limpia produce 18 nodos y detecta, entre otros:

- Application Error Disclosure en `DELETE /api/v1/resources/1` (codigo 500).
- Information Disclosure - Debug Error Messages.
- Cross Site Scripting Weakness (Persistent in JSON Response).
- X-Content-Type-Options Header Missing.

El `DELETE` con reservas relacionadas es un bug conocido del backend: al
borrar un recurso se dispara un `IntegrityError` de SQLAlchemy y la API responde
500 en vez de un 409 o 422.

## Estructura

```
backend/          API FastAPI
frontend/         React + nginx
tools/            seed de datos y scripts de ZAP
  seed.py         usuarios y datos de prueba
  test.env        credenciales del entorno de pruebas
  zap/
    scan.sh       orquestacion del escaneo (corre dentro del contenedor)
    gen-traffic.py  genera trafico real desde el OpenAPI
    scan.ps1      wrapper de Windows
zap-reports/      reportes JSON/HTML (ignorado por git)
```

## Notas de la API de ZAP 2.17

Cambios que rompian las recetas de ZAP 2.x y que `scan.sh` ya tiene en cuenta:

- La API key va en el header `X-ZAP-API-KEY`, no en `apikey`.
- Los parametros de un POST van en el cuerpo `form-encoded`, no en la query.
- No existen `core/view/tree`, `core/view/messageCount` ni `core/view/urlTable`.
- `ascan/action/scan` pide `contextId` + `url` y ya no acepta
  `scanPolicyId`, `defaultPolicy`, `threadPerHost` ni
  `maxScanDurationInMins` (por eso el corte por tiempo lo hace el script con
  `ascan/action/stop`).
- `context/action/includeInContext` exige un regex de URL completo; con un
  regex corto responde `url_not_in_context`.
- `reports/action/generate` usa `includedRisks` e `includedConfidences` con
  separador `|`, y el template `traditional-html`.
