#!/usr/bin/env python3
"""
Genera el trafico de la API de ALLOCAT a partir de su OpenAPI y lo reproduce
a traves del proxy de ZAP, para que cada operacion quede en el arbol de ZAP como
un nodo con metodo, ruta, query, body JSON y header Authorization.

Por que hace falta esto: importar el OpenAPI con la API de ZAP solo crea nodos
de URL sin cuerpo, y el active scan no encuentra nada que atacar (lo comprobamos:
0 alertas activas y 2-3 requests por regla). En cambio una peticion real
reproducida por el proxy deja el nodo completo, y como el active scanner parte
de ese nodo, todas las peticiones que genera heredan el header Authorization.

Uso (dentro del contenedor de ZAP):
    gen-traffic.py <openapi.json> <url_base> <proxy> <token_env_var>
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid

SPEC_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/allocat-openapi.json"
BASE = (sys.argv[2] if len(sys.argv) > 2 else "http://backend:8000").rstrip("/")
PROXY = sys.argv[3] if len(sys.argv) > 3 else "http://127.0.0.1:8090"
TOKEN = os.environ.get("ALLOCAT_TOKEN", "")

with open(SPEC_PATH, encoding="utf-8") as fh:
    SPEC = json.load(fh)

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY}))
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))

GREEN, YELLOW, RED, DIM, OFF = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"

# Sufijo unico por corrida: /auth/register rejeita emails repetidos.
RUN_TAG = uuid.uuid4().hex[:8]


def deref(node):
    """Resuelve $ref locales del documento."""
    seen = 0
    while isinstance(node, dict) and "$ref" in node and seen < 10:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            return {}
        target = SPEC
        for part in ref[2:].split("/"):
            target = target.get(part, {}) if isinstance(target, dict) else {}
        node = target
        seen += 1
    return node if isinstance(node, dict) else {}


def sample(schema, name="", depth=0):
    """Valor plausible para un esquema JSON. Los ids reales se corrigen luego."""
    schema = deref(schema)
    if depth > 6:
        return "x"
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    if "default" in schema:
        return schema["default"]
    if "example" in schema:
        return schema["example"]
    for combo in ("allOf", "anyOf", "oneOf"):
        if combo in schema and schema[combo]:
            merged = {}
            for part in schema[combo]:
                merged.update(deref(part))
            return sample(merged, name, depth + 1)

    fmt = schema.get("format", "")
    kind = schema.get("type", "string")
    if kind == "object" or "properties" in schema:
        return build_body(schema, depth + 1)
    if kind == "array":
        item = sample(schema.get("items", {}), name, depth + 1)
        return [item] if item is not None else []
    if kind == "integer":
        return 1
    if kind == "number":
        return 1
    if kind == "boolean":
        return True
    if kind == "null":
        return None
    low = (name or "").lower()
    if fmt == "date-time":
        return "2026-01-15T10:30:00Z"
    if fmt == "date":
        return "2026-01-15"
    if fmt == "email" or "email" in low:
        return f"scan-{RUN_TAG}@example.com"
    if fmt == "uuid":
        return "3f2504e0-4f89-41d3-9a0c-0305e82c3301"
    if fmt == "uri" or "url" in low:
        return "https://example.com/allocat"
    if "contras" in low or "password" in low:
        return "ZapAllocat2026!"
    return "allocat-scan"


def build_body(schema, depth=0):
    schema = deref(schema)
    props = schema.get("properties") or {}
    if not props:
        return {}
    required = set(schema.get("required") or [])
    body = {}
    for pname, pschema in props.items():
        pschema = deref(pschema)
        if pname in required or len(body) < 4:
            body[pname] = sample(pschema, pname, depth + 1)
    # Anadir campos opcionales da mas superficie al fuzzer del active scan.
    for pname, pschema in props.items():
        if pname not in body and pname not in required:
            body[pname] = sample(pschema, pname, depth + 1)
        if len(body) >= 8:
            break
    return body


def api(method, path, body=None, via_proxy=True, timeout=30):
    url = f"{BASE}{path}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method.upper())
    req.add_header("Accept", "application/json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    opener = OPENER if via_proxy else DIRECT
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc).encode()


def collect_ids():
    """Descubre ids reales de recursos/reservas para no chocar contra 404."""
    found = {}
    for path, ops in SPEC.get("paths", {}).items():
        if "get" not in ops or "{" in path:
            continue
        status, raw = api("GET", path, via_proxy=False)
        if status != 200:
            continue
        try:
            payload = json.loads(raw)
        except ValueError:
            continue
        items = payload if isinstance(payload, list) else None
        if items is None and isinstance(payload, dict):
            for key in ("data", "items", "results", "content"):
                if isinstance(payload.get(key), list):
                    items = payload[key]
                    break
        if not items:
            continue
        first = items[0]
        ident = first.get("id") if isinstance(first, dict) else None
        if ident is not None:
            found[path] = ident
    return found


def real_ids():
    """Mapa collection_path -> id real."""
    return collect_ids()


def resolve_path(path, known):
    """Sustituye {param} por ids reales cuando la coleccion tiene elementos."""
    if "{" not in path:
        return path
    base = path[: path.rindex("/{")] if "/{" in path else path
    ident = known.get(base, 1)
    out = path
    while "{" in out:
        start = out.index("{")
        end = out.index("}", start)
        out = out[:start] + str(ident) + out[end + 1:]
    return out


def query_for(op):
    params = op.get("parameters") or []
    parts = []
    for p in params:
        if p.get("in") != "query":
            continue
        p = deref(p)
        parts.append(f"{p['name']}={sample(p.get('schema', {}), p['name'])}")
    return "&".join(parts)


def fix_ids_in_body(value, known):
    """Corrige resource_id / reservation_id del cuerpo con ids reales."""
    if isinstance(value, dict):
        return {k: (known.get("/resources", 1) if k == "resource_id"
                    else known.get("/reservations", 1) if k == "reservation_id"
                    else fix_ids_in_body(v, known))
                for k, v in value.items()}
    if isinstance(value, list):
        return [fix_ids_in_body(v, known) for v in value]
    return value


START_WORDS = ("start", "inicio", "desde", "from", "desde_fecha")
END_WORDS = ("end", "fin", "hasta", "to", "hasta_fecha")


def looks_like_date(value):
    return isinstance(value, str) and len(value) >= 8 and any(c.isdigit() for c in value)


def fix_date_range(body):
    """El backend exige que el fin sea posterior al inicio; el spec solo dice string."""
    if not isinstance(body, dict):
        return body
    starts = [k for k in body if any(w in k.lower() for w in START_WORDS) and looks_like_date(body[k])]
    ends = [k for k in body if any(w in k.lower() for w in END_WORDS) and looks_like_date(body[k])]
    for s in starts:
        for e in ends:
            if body[e] <= body[s]:
                try:
                    import datetime

                    base = datetime.datetime.fromisoformat(body[s].replace("Z", "+00:00"))
                    body[e] = (base + datetime.timedelta(days=1)).isoformat().replace("+00:00", "Z")
                except ValueError:
                    body[e] = body[s] + "T23:59:59"
    return body


def readonly_props(op):
    """Propiedades que el spec marca como readOnly: no se pueden reenviar."""
    out = set()
    rb = deref(op.get("requestBody") or {})
    for media in (rb.get("content") or {}).values():
        schema = deref(media.get("schema") or {})
        for name, prop in (schema.get("properties") or {}).items():
            if deref(prop).get("readOnly"):
                out.add(name)
    return out


def body_from_live(method, path, op):
    """
    Para PUT/PATCH usamos el objeto real como cuerpo: sus valores ya cumplen
    las validaciones del servidor (versiones de concurrencia optimista, estados
    permitidos, etc.). El active scanner igual mutara cada campo, asi que la
    semilla solo tiene que ser valida.
    """
    if method.lower() not in ("put", "patch"):
        return None
    status, raw = api("GET", path, via_proxy=False)
    obj = None
    if status == 200:
        try:
            obj = json.loads(raw)
        except ValueError:
            obj = None
    if not isinstance(obj, dict):
        obj = find_in_collection(path)
    if not isinstance(obj, dict):
        return None
    skip = readonly_props(op)
    return {k: v for k, v in obj.items() if k not in skip}


def find_in_collection(path):
    """
    No toda API expone GET /{id}. Si no existe, buscamos el objeto dentro del
    listado de la coleccion: /resources/1 -> GET /resources y el item con id 1.
    """
    if "/{" not in path and path.count("/") < 2:
        return None
    collection = path[: path.rindex("/")]
    ident = path.rsplit("/", 1)[-1]
    if not ident.isdigit():
        return None
    status, raw = api("GET", collection, via_proxy=False)
    if status != 200:
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    items = payload if isinstance(payload, list) else None
    if items is None and isinstance(payload, dict):
        for key in ("data", "items", "results", "content"):
            if isinstance(payload.get(key), list):
                items = payload[key]
                break
    for item in items or []:
        if isinstance(item, dict) and str(item.get("id")) == ident:
            return item
    return None


def learn_from_422(body, raw):
    """
    Pydantic devuelve el patron/enum que exige. ALLOCAT tiene validaciones que
    no estan en el OpenAPI (por ejemplo status de reserva), asi que en vez de
    adivinar las satisfacemos con lo que el propio servidor nos dice.
    """
    try:
        detail = json.loads(raw)
    except ValueError:
        return None, None
    if not isinstance(detail, dict) or not isinstance(detail.get("detail"), list):
        return None, None
    changed = False
    for err in detail["detail"]:
        if not isinstance(err, dict):
            continue
        loc = err.get("loc") or []
        if len(loc) < 2 or loc[0] != "body":
            continue
        field = loc[-1]
        ctx = err.get("ctx") or {}
        kind = err.get("type", "")
        new = None
        if kind == "string_pattern_mismatch" and ctx.get("pattern"):
            alts = re.findall(r"[A-Za-z0-9_.\-]+", ctx["pattern"])
            new = alts[-1] if alts else None
        elif kind in ("enum", "literal_error") and ctx.get("expected"):
            new = ctx["expected"]
        if new is None or field not in body:
            continue
        body[field] = new
        changed = True
    return (body if changed else None), changed


def main():
    if not TOKEN:
        print("falta ALLOCAT_TOKEN", file=sys.stderr)
        return 1

    known = real_ids()
    if known:
        print(f"{DIM}ids reales detectados: "
              f"{ {k.rsplit('/', 1)[-1]: v for k, v in known.items()} }{OFF}")

    # El login se hace primero para tener token, pero se reenvia por el proxy
    # para que ese nodo tambien quede en el arbol con su body.
    total = ok = bad = 0
    print(f"{'operacion':<52} {'estado':>7}")
    print("-" * 62)

    for path, ops in SPEC.get("paths", {}).items():
        for method, op in ops.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            total += 1
            real_path = resolve_path(path, known)
            qs = query_for(op)
            target = f"{real_path}?{qs}" if qs else real_path

            body = None
            rb = op.get("requestBody")
            if rb:
                content = deref(rb).get("content") or {}
                json_schema = (content.get("application/json") or {}).get("schema")
                if json_schema is None and content:
                    json_schema = list(content.values())[0].get("schema")
                if json_schema is not None:
                    body = build_body(json_schema)

            # El cuerpo real manda: si el objeto existe, sus valores ya son validos.
            live = body_from_live(method, target, op)
            if live:
                body = live
            elif body is not None:
                body = fix_ids_in_body(body, known)
                body = fix_date_range(body)

            status, raw = api(method, target, body, via_proxy=True)

            # Si el servidor se quejo de un patron/enum, se lo satisfacemos y
            # reintentamos una vez.
            if status == 422 and body:
                learned, changed = learn_from_422(json.loads(json.dumps(body)), raw)
                if changed:
                    status, raw = api(method, target, learned, via_proxy=True)
            flag = GREEN + "ok" + OFF if status < 400 else RED + str(status) + OFF
            if status < 400:
                ok += 1
            else:
                bad += 1
            label = f"{method.upper():<6} {target}"
            if len(label) > 51:
                label = label[:48] + "..."
            print(f"{label:<52} {flag:>12}")
            if status >= 400:
                print(f"{YELLOW}        {raw[:160].decode('utf-8', 'replace')}{OFF}")

    print("-" * 62)
    print(f"{GREEN}{ok}/{total} operaciones reproducidas sin error{OFF}"
          + (f"  ({YELLOW}{bad} con error, ideal para probar manejo de errores{OFF})" if bad else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
