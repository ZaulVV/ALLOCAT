# Informe de calidad de código — SonarQube

**Proyecto:** ALLOCAT · Sistema de gestión de recursos y reservas
**Fecha del análisis:** 26 de septiembre de 2026
**Commit analizado:** `2b8fcef`
**Servidor:** SonarQube Community Edition `26.9.0.129388` (instancia local en Docker)
**Scanner:** SonarScanner CLI `6.2.1.4610` (Windows x64)
**Quality Gate aplicado:** `Sonar way` (puerta por defecto de Community Edition)

---

## 1. Resumen ejecutivo

| Métrica | Valor | Evaluación |
|---|---:|---|
| Quality Gate | **OK** | Ver la advertencia de la sección 7 |
| Deuda técnica | **99 min** (1 h 39 min) | 0.8 % sobre la duración del código |
| Rating de mantenibilidad | **A** (1.0) | Excelente |
| **Code smells** | **20** | 1 crítico, 10 mayores, 9 menores |
| **Bugs** | **2** | Ambos mayores |
| Vulnerabilidades | **0** | — |
| Security hotspots | **0** | — |
| Rating de fiabilidad | **C** (3.0) | Degradado por los 2 bugs |
| Rating de seguridad | **A** (1.0) | — |
| Cobertura | **77.9 %** | **Por debajo del 80 % exigido** |
| Duplicación | **0.0 %** | Sin bloques duplicados |
| Líneas de código (ncloc) | 411 | — |

**Conclusión:** el código es sólido en mantenibilidad y está libre de vulnerabilidades y
duplicación. Los dos puntos débiles son la **cobertura global (77.9 %, bajo el objetivo del
80 % del plan maestro)** y **2 bugs de tipo real** en el frontend. La Puerta de Calidad
reporta `OK`, pero ese resultado no es significativo: las cuatro condiciones del gate
evalúan únicamente *código nuevo* y, al ser el primer análisis, no hay periodo de código
nuevo que evaluar (sección 7).

---

## 2. Alcance y metodología

### Qué se analizó

| Componente | Rutas | Archivos |
|---|---|---:|
| Backend (Python) | `backend/app` | 17 |
| Frontend (JavaScript) | `frontend/src` | 3 |
| Pruebas | `backend/tests`, `frontend/src/*.test.jsx` | 4 |

Excluido del alcance: `tools/` (scripts de infraestructura para OWASP ZAP, no código de
producto), `frontend/dist`, `node_modules`, `__pycache__` y los archivos de base de datos.

### Cobertura: cómo se midió

SonarQube no calcula cobertura por sí solo, se le importa la de las pruebas:

| Pila | Origen del dato | Comando |
|---|---|---|
| Backend | Cobertura de `pytest-cov` | `py -3 -m pytest backend/tests --cov=backend/app` |
| Frontend | Reporte LCOV de `vitest` | `npx vitest run --coverage --coverage.reporter=lcov` |

Ambos reportes se normalizaron a rutas relativas con `/` antes de importarse, porque
Windows las genera con separadores `\` que el servidor no resuelve. La importación se
verificó en el log del scanner (`Cobertura Sensor for Python coverage` y
`JavaScript/TypeScript Coverage`), sin advertencias.

> **Nota sobre el resultado del gate de CI:** el comando anterior se ejecutó **sin**
> `--cov-fail-under=80`. `py -3 -m pytest` reporta **84 %** de cobertura de sentencias en
> el backend, es decir el umbral del 80 % **sí se cumple** para Python. La cobertura global
> del 77.9 % que reporta SonarQube es menor porque incorpora la cobertura de *condiciones*
> (ramas), que en este proyecto es de apenas 14.3 %.

### Estado del código analizado

El análisis se ejecutó sobre el **árbol de trabajo**, no sobre un commit limpio: había 5
archivos modificados y 5 sin trackear. SonarQube no pudo asignar historial (*blame*) a los
archivos no versionados, por lo que las métricas de «código nuevo» no son fiables en este
informe. Los hallazgos de este documento corresponden al contenido actual de los archivos.

---

## 3. Tamaño y complejidad

| Métrica | Valor |
|---|---:|
| Líneas de código (ncloc) | 411 |
| Líneas totales | 541 |
| Archivos | 19 |
| Clases | 18 |
| Funciones | 56 |
| Sentencias | 344 |
| Densidad de comentarios | 0.7 % |
| **Complejidad ciclomática total** | 103 |
| **Complejidad cognitiva total** | 42 |
| Bloques duplicados | 0 |
| **Líneas duplicadas** | **0 (0.0 %)** |

La complejidad total de 103 sobre 411 líneas es baja (promedio ≈ 2.5 por función), y la
duplicación es cero. Son indicadores de un código directo.

### Archivos con mayor densidad de hallazgos

| Archivo | ncloc | Cobertura | Code smells | Bugs | Complejidad | Líneas sin cubrir |
|---|---:|---:|---:|---:|---:|---:|
| `backend/app/routers/reservations.py` | 32 | **46.9 %** | 4 | 0 | 9 | 17 |
| `backend/app/routers/auth.py` | 25 | 100.0 % | 3 | 0 | 5 | 0 |
| `backend/app/routers/resources.py` | 30 | **53.3 %** | 3 | 0 | 8 | 14 |
| `frontend/src/main.jsx` | 52 | **38.6 %** | 2 | 2 | 53 | 29 |
| `backend/app/routers/audit.py` | 9 | 88.9 % | 2 | 0 | 1 | 1 |
| `backend/app/routers/notifications.py` | 9 | 88.9 % | 2 | 0 | 1 | 1 |
| `backend/app/routers/users.py` | 8 | 100.0 % | 1 | 0 | 1 | 0 |
| `backend/app/models.py` | 56 | 100.0 % | 1 | 0 | 1 | 0 |
| `backend/app/routers/reports.py` | 23 | **60.9 %** | 0 | 0 | 4 | 9 |
| `backend/app/database.py` | 19 | 72.2 % | 0 | 0 | 3 | 5 |

`frontend/src/main.jsx` concentra la mayor complejidad del proyecto (53) y la menor
cobertura (38.6 %): es el punto más débil del codebase.

---

## 4. Deuda técnica

| Métrica | Valor |
|---|---:|
| **Deuda técnica (`sqale_index`)** | **99 minutos** (1 h 39 min) |
| Deuda técnica en código nuevo | 0 min (sin periodo evaluado) |
| **Ratio de deuda técnica** | **0.8 %** |
| Rating de mantenibilidad | **A** (1.0) |
| Violaciones totales | 22 (1 crítica, 12 mayores, 9 menores) |

Con un ratio del **0.8 %**, SonarQube clasifica el coste de remediación en la categoría
*A* («deuda técnica inferior al 5 % del esfuerzo de desarrollo»). Es la clasificación más
favorable posible.

### Deuda técnica por regla

| Regla | Ocurrencias | Deuda |
|---|---:|---:|
| `python:S8415` — `HTTPException` sin documentar en `responses` | 8 | 40 min |
| `python:S8410` — dependencias FastAPI sin `Annotated` | 7 | 35 min |
| `python:S1192` — literal `"users.id"` duplicado 4 veces | 1 | 8 min |
| `python:S9073` — aserción compuesta sin separar | 1 | 5 min |
| `javascript:S2681` — bloque multilínea sin llaves | 1 | 5 min |
| `javascript:S7744` — objeto vacío innecesario en spread | 1 | 5 min |
| `javascript:S9011` — `<button>` sin atributo `type` | 2 | 4 min |
| `python:S9083` — decorador con paréntesis vacíos | 1 | 1 min |
| **Total** | **22** | **~99 min** |

Las dos reglas que más aportan a la deuda (`S8415` + `S8410`, 75 de los 99 minutos) son
cuestiones de **estilo idiomático de FastAPI**, no de defectos funcionales.

---

## 5. Code smells (20)

### 5.1 Crítico (1)

| Regla | Ubicación | Descripción |
|---|---|---|
| `python:S1192` | `backend/app/models.py:44` | **Definir una constante en vez de duplicar el literal `"users.id"` 4 veces.** El literal aparece en las claves foráneas de `Reservation.requester_id` y `Reservation.approved_by`, y en dos relaciones de `User`. |

### 5.2 Mayores (10)

**`python:S8415` — «Las `HTTPException` deberían documentarse en los metadatos del endpoint»** (8 ocurrencias, 40 min)

Ninguno de los códigos de error que la API lanza está declarado en el parámetro `responses`
de la ruta, por lo que el esquema OpenAPI no los refleja:

| Ubicación | Código no documentado |
|---|---|
| `backend/app/routers/auth.py:15` | 400 |
| `backend/app/routers/reservations.py:22` | 400 |
| `backend/app/routers/reservations.py:24` | 404 |
| `backend/app/routers/reservations.py:25` | 409 |
| `backend/app/routers/reservations.py:37` | 404 |
| `backend/app/routers/resources.py:27` | 404 |
| `backend/app/routers/resources.py:28` | 409 |
| `backend/app/routers/resources.py:38` | 404 |

**`javascript:S2681` — «Los bloques multilínea deberían encerrarse en llaves» (1, 5 min)**

`frontend/src/main.jsx:53`. La función `App()` concentra toda su lógica —dos `useState`, un
`useEffect` con cadena de promesas, un `if` de carga y un `return` ternario— en una única
línea de 53. El análisis advierte que solo la primera sentencia se ejecutará de forma
condicional y el resto se ejecutará incondicionalmente. Es un problema de legibilidad
reducido por la densidad de la línea, no un defecto de comportamiento.

### 5.3 Menores (9)

**`python:S8410` — «Las dependencias de FastAPI deberían usar type hints `Annotated`»** (7 ocurrencias, 35 min)

| Ubicación | Detalle |
|---|---|
| `backend/app/routers/auth.py:13` | `db: Session = Depends(get_db)` |
| `backend/app/routers/auth.py:26` | idem |
| `backend/app/routers/audit.py:11` | dos parámetros afectados en la misma línea |
| `backend/app/routers/notifications.py:11` | dos parámetros afectados en la misma línea |
| `backend/app/routers/users.py:10` | `db: Session = Depends(get_db)` |

**`javascript:S7744` — «Los objetos vacíos de reserva son innecesarios al extender un objeto»** (1, 5 min)

`frontend/src/main.jsx:10`. La expresión `...(options.headers || {})` es redundante: extender
un objeto con `undefined` ya es una operación sin efecto en JavaScript.

**`python:S9083` — «Los decoradores de pytest deberían usar un estilo de paréntesis coherente»** (1, 1 min)

`backend/tests/conftest.py:15`. El decorador está escrito como `@pytest.fixture()` cuando la
forma canónica es `@pytest.fixture`.

---

## 6. Bugs (2) y seguridad

### Bugs — ambos MAJOR

| Regla | Ubicación | Descripción |
|---|---|---|
| `javascript:S9011` | `frontend/src/main.jsx:33` | **El `<button>` de envío del formulario de login/registro no tiene atributo `type` explícito.** Al estar dentro de un `<form>`, el navegador lo interpreta como `type="submit"`. |
| `javascript:S9011` | `frontend/src/main.jsx:48` | **El `<button>` de «Agregar recurso» tampoco declara `type`.** Mismo caso: envío implícito dentro del formulario de administración. |

Ambos botones son de envío intencional, así que hoy funcionan por el valor por defecto del
navegador. Se clasifican como bugs y no como code smells porque el comportamiento depende de
un valor implícito: cualquier cambio futuro en el formulario (por ejemplo, añadir un
`onClick` que llame a `preventDefault`) alteraría el comportamiento de forma silenciosa.

### Seguridad

| Métrica | Valor |
|---|---:|
| Vulnerabilidades | **0** |
| Security hotspots pendientes de revisión | **0** |
| Rating de seguridad | **A** (1.0) |
| Rating de revisión de seguridad | **A** (1.0) |

SonarQube no detectó secretos embebidos, inyección de SQL, autenticación débil ni
configuración insegura. Conviene señalar que **no se escanearon dependencias**
(«Dependency analysis skipped» en el log): en Community Edition el análisis de
vulnerabilidades de dependencias no está disponible, de modo que este resultado cubre
únicamente el código propio.

---

## 7. Quality Gate

**Resultado: `OK`**

La puerta `Sonar way` de Community Edition contiene exactamente cuatro condiciones:

| Condición | Umbral | Resultado |
|---|---|---|
| `new_violations` | 0 | Sin evaluar |
| `new_coverage` | ≥ 80 % | Sin evaluar |
| `new_duplicated_lines_density` | ≤ 3 % | Sin evaluar |
| `new_security_hotspots_reviewed` | ≥ 100 % | Sin evaluar |

### Advertencia importante sobre este `OK`

**Las cuatro condiciones se evalúan exclusivamente sobre «código nuevo»**, y este es el
**primer análisis** del proyecto: no existe versión anterior contra la que comparar, por lo
que **no hay periodo de código nuevo**. La API de métricas no devuelve ninguna medida
`new_*`, y SonarQube da las condiciones por satisfechas.

Por tanto el `OK` **no significa que el proyecto cumpla la Puerta de Calidad**: significa
que las condiciones no se pudieron evaluar. Las 22 violaciones del proyecto —incluida una
de severidad crítica— no son tenidas en cuenta por esta puerta. El rating de fiabilidad
`C (3.0)` reflete esa realidad mejor que el `OK` del gate.

---

## 8. Cobertura de pruebas

| Métrica | Valor |
|---|---:|
| **Cobertura global** | **77.9 %** |
| Cobertura de líneas | 79.0 % (316 de 400) |
| Cobertura de condiciones | **14.3 %** (1 de 7) |
| Líneas cubiertas objetivo | 400 |
| Líneas sin cubrir | 84 |
| Condiciones sin cubrir | 6 |
| Cobertura en código nuevo | Sin periodo evaluado |

### Desglose por pila

| Pila | Cobertura | Objetivo del plan | Estado |
|---|---:|---:|---|
| Backend (Python) | 84 % (sentencias) | ≥ 80 % | **Cumple** |
| Frontend (JavaScript) | 38.6 % | ≥ 80 % | **No cumple** |
| Global (SonarQube) | 77.9 % | ≥ 80 % | **No cumple** |

### Desglose por archivo

| Archivo | Cobertura | Líneas sin cubrir |
|---|---:|---:|
| `backend/app/routers/auth.py` | 100.0 % | 0 |
| `backend/app/routers/users.py` | 100.0 % | 0 |
| `backend/app/models.py` | 100.0 % | 0 |
| `backend/app/schemas.py` | 100.0 % | 0 |
| `backend/app/config.py` | 100.0 % | 0 |
| `backend/app/audit.py` | 100.0 % | 0 |
| `backend/app/main.py` | 92.9 % | 2 |
| `backend/app/routers/audit.py` | 88.9 % | 1 |
| `backend/app/routers/notifications.py` | 88.9 % | 1 |
| `backend/app/security.py` | 88.6 % | 4 |
| `backend/app/database.py` | 72.2 % | 5 |
| `backend/app/routers/reports.py` | 60.9 % | 9 |
| `backend/app/routers/resources.py` | 53.3 % | 14 |
| `backend/app/routers/reservations.py` | 46.9 % | 17 |
| `frontend/src/main.jsx` | 38.6 % | 29 |

El backend cumple el objetivo en los módulos de dominio (`models`, `schemas`, `auth`,
`users`), pero decae exactamente donde está la lógica de negocio: `reservations`
(46.9 %), `resources` (53.3 %) y `reports` (60.9 %) suman 40 de las 84 líneas sin cubrir.
Es coherente con el inventario de pruebas: el proyecto tiene **3 pruebas de backend**
(2 de autenticación y 1 de roles) y **1 de frontend** (renderizado del login), mientras que
los routers `resources`, `reservations`, `reports`, `audit` y `notifications` no tienen
ninguna prueba que las ejercite de forma directa.

El dato más preocupante de la tabla es la cobertura de **condiciones**: solo 1 de las 7
ramas del proyecto está cubierta (14.3 %), porque las 3 pruebas de backend recorren
esencialmente caminos felices. Es coherente con los 2 bugs del frontend: las rutas
alternativas de la UI (botones de envío) no están ejercitadas.

---

## 9. Resumen de hallazgos por severidad

| Severidad | Code smells | Bugs | Total |
|---|---:|---:|---:|
| Blocker | 0 | 0 | 0 |
| Crítico | 1 | 0 | 1 |
| Mayor | 10 | 2 | 12 |
| Menor | 9 | 0 | 9 |
| **Total** | **20** | **2** | **22** |

### Hallazgos por archivo

| Archivo | Hallazgos |
|---|---:|
| `backend/app/routers/reservations.py` | 4 |
| `backend/app/routers/auth.py` | 3 |
| `backend/app/routers/resources.py` | 3 |
| `frontend/src/main.jsx` | 4 |
| `backend/app/routers/audit.py` | 2 |
| `backend/app/routers/notifications.py` | 2 |
| `backend/app/models.py` | 1 |
| `backend/app/routers/users.py` | 1 |
| `backend/tests/conftest.py` | 1 |
| `backend/tests/test_auth.py` | 1 |

---

## 10. Anexo — Reproducir el análisis

Comandos ejecutados, en orden:

```powershell
# 1. Instancia local de SonarQube
docker run -d --name allocat-sonarqube -p 9000:9000 `
  -e "SONAR_CE_JAVAOPTS=-Xmx2g" -e "SONAR_ES_JAVAOPTS=-Xmx1g" -e "SONAR_WEB_JAVAOPTS=-Xmx512m" `
  -v allocat-sonar-data:/opt/sonarqube/data -v allocat-sonar-logs:/opt/sonarqube/logs `
  sonarqube:community

# 2. Token de análisis (usuario por defecto admin/admin)
curl -u admin:admin -X POST "http://localhost:9000/api/user_tokens/generate?name=allocat-scanner"

# 3. Cobertura
py -3 -m pytest backend/tests --cov=backend/app --cov-report=xml:coverage.xml --cov-report=term
npx vitest run --coverage --coverage.reporter=lcov      # desde frontend/

# 4. Análisis
sonar-scanner -Dsonar.projectKey=allocat -Dsonar.projectName=ALLOCAT `
  -Dsonar.projectVersion=2b8fcef -Dsonar.host.url=http://localhost:9000 -Dsonar.token=<TOKEN> `
  -Dsonar.scm.provider=git -Dsonar.sources=backend/app,frontend/src `
  -Dsonar.tests=backend/tests,frontend/src `
  -Dsonar.test.inclusions=**/test_*.py,**/*.test.jsx,**/*.test.js,**/conftest.py `
  -Dsonar.exclusions=**/node_modules/**,**/dist/**,**/__pycache__/**,**/*.css `
  -Dsonar.python.coverage.reportPaths=coverage.xml `
  -Dsonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info
```

Dashboard: <http://localhost:9000/dashboard?id=allocat> (usuario `admin`, contraseña `admin`).
Para detener la instancia: `docker stop allocat-sonarqube`.

### Limitaciones de este análisis

1. **Es el primer análisis del proyecto**, por lo que las cuatro condiciones del Quality
   Gate no se evaluaron (sección 7). El `OK` no es indicativo.
2. **No se escanearon dependencias.** La Community Edition no incluye el análisis de
   vulnerabilidades de dependencias (Security Hotspots y SCA de third-party requieren
   Developer Edition). El log indica explícitamente `Dependency analysis skipped`.
3. **La Community Edition no soporta Java ni C#**, por lo que un eventual módulo Java
   quedaría fuera del análisis. No aplica a ALLOCAT (Python + JavaScript).
4. **El análisis se hizo sobre el árbol de trabajo con cambios sin commitear**, lo que
   impide asignar historial a los archivos no versionados y deja las métricas de «código
   nuevo» sin significación estadística.
5. **Los reportes de cobertura se normalizaron** (rutas relativas y separadores `/`)
   porque los generadores de Windows producen rutas que el servidor no resuelve.
