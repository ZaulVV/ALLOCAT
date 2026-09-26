#!/usr/bin/env bash
# Escaneo OWASP ZAP de la API de ALLOCAT.
# Se ejecuta DENTRO del contenedor zap:
#     docker compose --profile zap exec -T zap bash /zap/scan/scan.sh
#
# Por que dentro del contenedor: la API de ZAP 2.17 solo responde en el
# loopback de su propio namespace de red.
#
# En ZAP 2.17 el proxy y la API comparten el mismo puerto (8090 aqui), asi que
# curl con -x hacia ese puerto hace de proxy y alimenta el arbol de ZAP.
#
# API de ZAP 2.17 (cambio respecto a 2.x antigua), lo que este script respeta:
#   - la API key va en el header X-ZAP-API-KEY
#   - en un POST los parametros van en el cuerpo form-encoded, nunca en la query
#   - ya no existen /JSON/core/view/tree ni .../messageCount ni .../urlTable
#   - ascan/action/scan exige contextId + url, y ya NO acepta scanPolicyId,
#     defaultPolicy, threadPerHost ni maxScanDurationInMins
#   - las policies por defecto estan divididas en 5 categorias (ascan/view/policies):
#     0 Information Gathering, 1 Client Browser, 2 Server Security,
#     3 Miscellaneous, 4 Injection
#   - context/action/includeInContext exige un regex de URL COMPLETO
#
# Variables (las inyecta docker-compose desde tools/test.env):
#   ZAP_API_KEY, ALLOCAT_ADMIN_EMAIL, ALLOCAT_ADMIN_PASSWORD
#   SCAN_QUICK=1 (default) | 0
#   SCAN_CAT_TIMEOUT, ZAP_TARGET, REPORT_DIR

set -euo pipefail

ZAP_API_KEY="${ZAP_API_KEY:?falta ZAP_API_KEY}"
ZAP_HOST="http://127.0.0.1:8090"
TARGET="${ZAP_TARGET:-http://backend:8000}"
REPORT_DIR="${REPORT_DIR:-/zap/reports}"
CTX_NAME="ALLOCAT"
CTX=""

QUICK="${SCAN_QUICK:-1}"
# Tope de reloj por categoria. La API REST de 2.17 ya no acepta
# maxScanDurationInMins, asi que el corte lo hacemos nosotros con ascan/stop.
# Las reglas de inyeccion son las caras (las de timing prueban muchos payloads).
if [ "$QUICK" = "1" ]; then
  CATEGORIES="0 2 4"                                  # Gathering, Server Security, Injection
  CAT_TIMEOUT="${SCAN_CAT_TIMEOUT:-600}"             # 10 min por categoria
else
  CATEGORIES="0 1 2 3 4"
  CAT_TIMEOUT="${SCAN_CAT_TIMEOUT:-1500}"            # 25 min por categoria
fi

ADMIN_EMAIL="${ALLOCAT_ADMIN_EMAIL:?falta ALLOCAT_ADMIN_EMAIL}"
ADMIN_PASSWORD="${ALLOCAT_ADMIN_PASSWORD:?falta ALLOCAT_ADMIN_PASSWORD}"

declare -A CAT_NAME=(
  [0]="Information Gathering" [1]="Client Browser" [2]="Server Security"
  [3]="Miscellaneous" [4]="Injection"
)

BLUE='\033[1;34m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; RED='\033[1;31m'; OFF='\033[0m'
log()  { printf "${BLUE}[zap]${OFF} %s\n" "$*"; }
ok()   { printf "${GREEN}[ ok]${OFF} %s\n" "$*"; }
warn() { printf "${YELLOW}[warn]${OFF} %s\n" "$*" >&2; }
die()  { printf "${RED}[fail]${OFF} %s\n" "$*" >&2; exit 1; }

zget()  { curl -sS -m 120 -H "X-ZAP-API-KEY: ${ZAP_API_KEY}" "$@"; }
zgetu() { zget "${ZAP_HOST}$1"; }
zpost() { local path="$1"; shift; zget -X POST "$@" "${ZAP_HOST}${path}"; }

zap_ready() { zget -m 5 "${ZAP_HOST}/JSON/core/view/version" 2>/dev/null | grep -q '"version"'; }
node_count() { zgetu "/JSON/core/view/urls" 2>/dev/null | jq -r '(.urls // []) | length' 2>/dev/null || echo 0; }
wait_for() { local what="$1" limit="$2"; shift 2; local i; for ((i = 0; i < limit; i++)); do "$@" >/dev/null 2>&1 && return 0; sleep 2; done; die "timeout esperando ${what}"; }

# --- 1. espera -------------------------------------------------------------------
log "esperando la API de ZAP..."
wait_for "la API de ZAP" 180 zap_ready
ok "ZAP responde"
log "esperando el backend en ${TARGET}..."
wait_for "el backend" 180 bash -c "curl -fsS -m 5 '${TARGET}/health' >/dev/null"
ok "backend sano"

# --- 2. token --------------------------------------------------------------------
log "autenticando como ADMIN..."
LOGIN="$(curl -sS -m 20 -X POST "${TARGET}/api/v1/auth/login" -H 'Content-Type: application/json' \
  --data "$(jq -nc --arg e "$ADMIN_EMAIL" --arg p "$ADMIN_PASSWORD" '{email:$e,password:$p}')" || true)"
TOKEN="$(printf '%s' "$LOGIN" | jq -r '.access_token // empty' 2>/dev/null || true)"
[ -n "$TOKEN" ] || die "login fallido: ${LOGIN:-<sin respuesta>}"
ok "token obtenido (${#TOKEN} chars)"

# --- 3. contexto limpio ------------------------------------------------------------
# Sin contexto nuevo el scan arrastraria los nodos sin cuerpo de corridas previas.
log "creando contexto limpio ${CTX_NAME}..."
zgetu "/JSON/context/view/contextList" | jq -r '(.contextList // [])[] | select(type == "string")' | while read -r c; do
  [ -n "$c" ] && zpost "/JSON/context/action/removeContext" --data-urlencode "contextName=$c" >/dev/null 2>&1 || true
done
CTX="$(zpost "/JSON/context/action/newContext" --data-urlencode "contextName=${CTX_NAME}" | jq -r '.contextId // empty')"
[ -n "$CTX" ] || die "no se pudo crear el contexto de ZAP"
# El regex debe ser la URL completa; si no, ascan responde url_not_in_context.
zpost "/JSON/context/action/includeInContext" \
  --data-urlencode "contextName=${CTX_NAME}" --data-urlencode "regex=${TARGET}.*" >/dev/null
zpost "/JSON/context/action/setCurrentContext" --data-urlencode "contextName=${CTX_NAME}" >/dev/null 2>&1 || true
ok "contexto ${CTX_NAME} (id=${CTX})"

# --- 4. spec ------------------------------------------------------------------------
log "bajando el OpenAPI de la API..."
SPEC=/tmp/allocat-openapi.json
curl -fsS -m 30 "${TARGET}/openapi.json" \
  | jq --arg s "$TARGET" '.servers = [{"url": $s}]' > "$SPEC" \
  || die "no se pudo bajar ${TARGET}/openapi.json"
ok "spec con $(jq '[.paths[] | keys[]] | length' "$SPEC") operaciones"

# --- 5. sembrar el arbol con trafico real ------------------------------------------------
# Importar el OpenAPI con la API de ZAP solo crea nodos de URL sin cuerpo: el
# active scan no encuentra nada que atacar (lo medimos: 0 alertas activas y 2-3
# requests por regla). Reproduciendo cada operacion por el proxy, cada nodo
# queda con metodo, ruta, query, body JSON y --clave-- el header Authorization,
# que el scanner hereda en todas las peticiones que luego genera.
log "reproduciendo el trafico de la API por el proxy de ZAP..."
ALLOCAT_TOKEN="$TOKEN" python3 /zap/scan/gen-traffic.py "$SPEC" "$TARGET" "$ZAP_HOST" || warn "el generador reporto fallos"
NODES="$(node_count)"
[ "$NODES" -gt 0 ] || die "no quedo ningun nodo en el arbol de ZAP"
ok "${NODES} nodos en el arbol de ZAP"

# --- 6. active scan por categoria ---------------------------------------------------------
log "active scan modo $([ "$QUICK" = 1 ] && echo rapido || echo completo): categorias [${CATEGORIES}]"
START_ALL="$(date +%s)"
for CAT in $CATEGORIES; do
  log "categoria ${CAT} (${CAT_NAME[$CAT]:-desconocida})..."
  RESP="$(zpost "/JSON/ascan/action/scan" \
    --data-urlencode "contextId=${CTX}" \
    --data-urlencode "url=${TARGET}" \
    --data-urlencode "policy=${CAT}" || true)"
  SID="$(printf '%s' "$RESP" | jq -r '.scan // empty' 2>/dev/null || true)"
  if [ -z "$SID" ]; then
    warn "no se pudo lanzar la categoria ${CAT}: ${RESP:-<sin respuesta>}"
    continue
  fi
  DEADLINE=$(( $(date +%s) + CAT_TIMEOUT ))
  LAST=-1
  while :; do
    sleep 15
    STATUS="$(zgetu "/JSON/ascan/view/status?scanId=${SID}" | jq -r '.status // 0' 2>/dev/null || echo 0)"
    [ "$STATUS" != "$LAST" ] && { log "  categoria ${CAT}: ${STATUS}%"; LAST="$STATUS"; }
    [ "$STATUS" = "100" ] && break
    if [ "$(date +%s)" -ge "$DEADLINE" ]; then
      # CAT_TIMEOUT va en segundos; con menos de 60 mostrar segundos, si no
      # el mensaje diria "tope de 0 min".
      if [ "$CAT_TIMEOUT" -lt 60 ]; then
        warn "  categoria ${CAT} supero el tope de ${CAT_TIMEOUT} s: se detiene"
      else
        warn "  categoria ${CAT} supero el tope de $((CAT_TIMEOUT / 60)) min: se detiene"
      fi
      zpost "/JSON/ascan/action/stop" --data-urlencode "scanId=${SID}" >/dev/null 2>&1 || true
      break
    fi
  done
  ok "categoria ${CAT} terminada"
done
ELAPSED=$(( $(date +%s) - START_ALL ))
if [ "$ELAPSED" -lt 60 ]; then
  ok "active scan completo en ${ELAPSED} s"
else
  ok "active scan completo en $((ELAPSED / 60)) min"
fi

# --- 7. reportes ------------------------------------------------------------------------
STAMP="$(date +%Y%m%d-%H%M%S)"
JSON_OUT="${REPORT_DIR}/allocat-${STAMP}.json"
HTML_OUT="${REPORT_DIR}/allocat-${STAMP}.html"
mkdir -p "$REPORT_DIR" 2>/dev/null || warn "no se pudo crear ${REPORT_DIR}; revisa el bind mount"
[ -w "$REPORT_DIR" ] || die "${REPORT_DIR} no es escribible (bind mount roto?)"

zgetu "/JSON/core/view/alerts" | jq '.' > "$JSON_OUT"
ok "JSON: ${JSON_OUT}"

# reports/action/generate exige estos nombres exactos en 2.17: includedRisks /
# includedConfidences (no risks/confidences) y separador '|' (no espacios).
# includedRisks no acepta "False Positive".
TEMPLATE="$(zgetu "/JSON/reports/view/templates" | jq -r '[((.templates // [])[] | (.name // .))] | map(select(test("traditional-html"))) | .[0] // "traditional-html"' 2>/dev/null || echo traditional-html)"
REPORT="$(zpost "/JSON/reports/action/generate" \
  --data-urlencode "template=${TEMPLATE}" \
  --data-urlencode "reportDir=${REPORT_DIR}" \
  --data-urlencode "reportFileName=$(basename "$HTML_OUT")" \
  --data-urlencode "title=ALLOCAT - OWASP ZAP" \
  --data-urlencode "description=Escaneo de la API, modo $([ "$QUICK" = 1 ] && echo rapido || echo completo)" \
  --data-urlencode "contexts=${CTX_NAME}" \
  --data-urlencode "includedRisks=Informational|Low|Medium|High" \
  --data-urlencode "includedConfidences=False Positive|Low|Medium|High|Confirmed" \
  --data-urlencode "display=false" || true)"
if printf '%s' "$REPORT" | jq -e '.generate' >/dev/null 2>&1 && [ -s "$HTML_OUT" ]; then
  ok "HTML:  ${HTML_OUT} (plantilla ${TEMPLATE})"
else
  warn "no se genero el HTML con la plantilla '${TEMPLATE}': ${REPORT:-<sin respuesta>}"
  [ -s "$HTML_OUT" ] || rm -f "$HTML_OUT"
fi

# --- 8. resumen --------------------------------------------------------------------------
echo
printf "${BLUE}=== RESUMEN DE ALERTAS ===${OFF}\n"
TOTAL="$(jq '(.alerts // []) | length' "$JSON_OUT")"
if [ "$TOTAL" -eq 0 ]; then
  echo "  sin alertas"
else
  echo "  ${TOTAL} alertas en total"
  echo
  # Una linea por tipo de hallazgo, para no repetir la misma alerta endpoint por
  # endpoint (ZAP emite una entrada por cada URL afectada).
  jq -r '(.alerts // [])
         | group_by(.risk + " " + .name)[]
         | "  [\(.[0].risk)] \(.[0].name)  x\(length)"' "$JSON_OUT" | sort
  echo
  printf "${BLUE}  detalle de Medium/High:${OFF}\n"
  MEDHIGH="$(jq '[.alerts[]? | select(.risk == "High" or .risk == "Medium")] | length' "$JSON_OUT")"
  if [ "$MEDHIGH" = "0" ]; then
    echo "    (ninguna)"
  else
    jq -r '(.alerts // [])
           | map(select(.risk == "High" or .risk == "Medium"))[]
           | "    \(.risk): \(.name)\n      \(.method // "?") \(.url)\(if .param then "  param=\(.param)" else "" end)"' "$JSON_OUT" \
      | sort -u
  fi
  echo
  printf "${BLUE}  endpoints con hallazgos Low/Informational:${OFF}\n"
  jq -r '(.alerts // [])
         | map(select(.risk == "Low" or .risk == "Informational"))
         | map(.url) | unique | .[]' "$JSON_OUT" | sed 's/^/    /'
fi
echo
ok "reportes en ${REPORT_DIR}"
