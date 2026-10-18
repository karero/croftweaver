"""A local stand-in for the homepage and the four AI engines, for the GEO tests.

One threaded HTTP server on 127.0.0.1 serves every route. Each test sets `STATE`
to decide what the homepage says and how each engine answers; every request is
recorded in `STATE["hits"]` so a test can prove the real code path reached it.
"""
import json
import time
from urllib.parse import parse_qs, urlparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {}


def reset():
    STATE.clear()
    STATE.update({
        "homepage": ("<html><head><title>Bäckerei Example — Sourdough in Schwabing</title>"
                     "<meta name='description' content='Fresh sourdough bread every morning.'>"
                     "</head><body><h1>Bäckerei Example</h1></body></html>"),
        "homepage_status": 200,
        # engine -> {"status": int, "text": str, "model": str, "sources": [url], "body": str}
        "engines": {},
        # SerpApi engine name -> (status, JSON body), e.g. "google_ai_mode", "google"
        "serp": {},
        "hits": [],
        # (path, request body as text, start, end) per POST, for tests that check timing
        "spans": [],
    })


def engine_reply(engine, text, model="m-1", sources=(), status=200, body=None, searched=True, raw=None):
    STATE["engines"][engine] = {"text": text, "model": model, "sources": list(sources),
                                "status": status, "body": body, "searched": searched, "raw": raw}


def _payload(engine, spec, finds):
    t, m, src = spec["text"], spec["model"], spec["sources"] if finds else []
    searched = finds and spec.get("searched", True)
    if engine == "gemini":
        return {"modelVersion": m, "candidates": [{"content": {"parts": [{"text": t}]}}]}
    if engine == "openai":
        out = [{"type": "web_search_call", "status": "completed"}] if searched else []
        out.append({"type": "message", "content": [{
            "type": "output_text", "text": t,
            "annotations": [{"type": "url_citation", "url": s} for s in src]}]})
        return {"model": m, "output": out}
    if engine == "anthropic":
        return {"model": m, "content": [{"type": "text", "text": t,
                                         "citations": [{"url": s} for s in src]}],
                "usage": {"server_tool_use": {"web_search_requests": 1 if searched else 0}}}
    if engine == "perplexity":
        out = [{"type": "message", "content": [{"type": "output_text", "text": t}]}]
        if src:
            out.append({"type": "search_results", "results": [{"url": s} for s in src]})
        return {"model": m, "output": out,
                "usage": {"tool_calls_details": {"search_web": {"invocation": 1 if searched else 0}}}}
    raise ValueError(engine)


ROUTER_PREFIX = {"google/": "gemini", "openai/": "openai", "anthropic/": "anthropic", "perplexity/": "perplexity"}


def _router_payload(spec, body):
    """OpenRouter's OpenAI-compatible chat completion, as it answers our requests."""
    # Perplexity's Sonar always searches (no plugin needed or allowed); others only with the plugin.
    finds = bool(body.get("plugins")) or str(body.get("model", "")).startswith("perplexity/")
    ann = [{"type": "url_citation", "url_citation": {"url": u, "title": ""}} for u in (spec["sources"] if finds else [])]
    return {"model": body.get("model"), "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": spec["text"], "annotations": ann}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 100, "cost": 0.0012}}


def _engine_of(path):
    if ":generateContent" in path:
        return "gemini"
    return {"/v1/responses": "openai", "/v1/messages": "anthropic", "/v1/agent": "perplexity"}.get(path)


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/search"):
            params = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            STATE["hits"].append(("GET", "/search", dict(self.headers), params))
            status, body = STATE["serp"].get(params.get("engine"), (500, {"error": "no stub"}))
            return self._send(status, json.dumps(body))
        STATE["hits"].append(("GET", self.path, dict(self.headers), None))
        self._send(STATE["homepage_status"], STATE["homepage"], "text/html; charset=utf-8")

    def do_POST(self):
        start = time.time()
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}"
        try:
            self._post(json.loads(raw))
        finally:
            STATE["spans"].append((self.path, raw.decode("utf-8", "replace"), start, time.time()))

    def _post(self, body):
        STATE["hits"].append(("POST", self.path, dict(self.headers), body))
        if self.path == "/api/v1/chat/completions":          # OpenRouter
            engine = next((e for p, e in ROUTER_PREFIX.items() if str(body.get("model", "")).startswith(p)), None)
            spec = STATE["engines"].get(engine) or STATE.get("router_error")
            if not spec:
                return self._send(500, '{"error": {"message": "no stub for this model"}}')
            if spec.get("status", 200) != 200:
                return self._send(spec["status"], spec["body"] or '{"error": {"message": "stubbed failure"}}')
            if spec.get("raw") is not None:       # a reply given verbatim (cut off, empty, …);
                raw = spec["raw"]                  # a str is sent as is (e.g. not JSON at all)
                return self._send(200, raw if isinstance(raw, str) else json.dumps(raw))
            return self._send(200, json.dumps(_router_payload(spec, body)))
        engine = _engine_of(self.path)
        if STATE.get("gate") is not None:        # a threading.Event the test sets to let replies through
            STATE["gate"].wait(60)
        if STATE.get("delay", {}).get(engine):
            time.sleep(STATE["delay"][engine])
        spec = STATE["engines"].get(engine)
        if not spec:
            return self._send(500, '{"error": "no stub for this engine"}')
        if spec["status"] != 200:
            return self._send(spec["status"], spec["body"] or '{"error": "stubbed failure"}')
        if spec.get("raw") is not None:           # replay a real captured response verbatim
            return self._send(200, json.dumps(spec["raw"]))
        finds = bool(body.get("tools"))
        self._send(200, json.dumps(_payload(engine, spec, finds)))


def start():
    reset()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def env_for(base_url):
    """The environment that points geo_check at this stub — test mode only."""
    return {"GEO_TEST_MODE": "1", "GEO_HOMEPAGE_URL": base_url + "/",
            "GEO_GEMINI_BASE_URL": base_url, "GEO_OPENAI_BASE_URL": base_url,
            "GEO_ANTHROPIC_BASE_URL": base_url, "GEO_PERPLEXITY_BASE_URL": base_url,
            "GEO_SERPAPI_BASE_URL": base_url, "GEO_OPENROUTER_BASE_URL": base_url}
