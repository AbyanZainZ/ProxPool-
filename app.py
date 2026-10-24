import os
import re
import json
import subprocess
import psutil
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"
PROXIES_FILE = BASE_DIR / "proxies.txt"
PROXIES_EXAMPLE = BASE_DIR / "proxies.txt.example"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="ProxPool Command Center", version="1.0.0")

# Ensure .env and proxies.txt exist locally
if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
    ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

if not PROXIES_FILE.exists():
    if PROXIES_EXAMPLE.exists():
        PROXIES_FILE.write_text(PROXIES_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        PROXIES_FILE.write_text(
            "# Format: socks5://user:pass@ip:port or http://user:pass@ip:port (1 proxy per line)\n",
            encoding="utf-8",
        )


class EnvPayload(BaseModel):
    values: Dict[str, str]


class ProxiesPayload(BaseModel):
    proxies_raw: str


def parse_env_file(path: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        result[k.strip()] = v.strip()
    return result


def save_env_values(updates: Dict[str, str]) -> None:
    template_lines = (
        ENV_FILE.read_text(encoding="utf-8").splitlines()
        if ENV_FILE.exists()
        else (ENV_EXAMPLE.read_text(encoding="utf-8").splitlines() if ENV_EXAMPLE.exists() else [])
    )
    updated_keys = set()
    out_lines = []
    for line in template_lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _ = s.split("=", 1)
            key = k.strip()
            if key in updates:
                out_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)
    for k, v in updates.items():
        if k not in updated_keys:
            out_lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def get_docker_containers() -> List[Dict[str, str]]:
    try:
        res = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Image}}|{{.Status}}|{{.State}}"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if res.returncode != 0:
            return []
        containers = []
        for line in res.stdout.strip().splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                name, image, status, state = parts
                if any(
                    prefix in name
                    for prefix in [
                        "-worker",
                        "proxpool_",
                        "tun_",
                        "tm_",
                        "hg_",
                        "pawns_",
                        "ps_",
                        "rp_",
                        "efm_",
                        "pr_",
                        "bp_",
                        "pl_",
                        "pb_",
                        "ea_",
                    ]
                ):
                    containers.append(
                        {"name": name, "image": image, "status": status, "state": state}
                    )
        return containers
    except Exception:
        return []


def get_earnapp_claims(containers: List[Dict[str, str]]) -> List[Dict[str, str]]:
    claims = []
    direct_claim = BASE_DIR / "data" / "earnapp" / "claim_url.txt"
    if direct_claim.exists():
        url = direct_claim.read_text(encoding="utf-8").strip()
        if url:
            claims.append(
                {
                    "node": "earnapp-worker (Single Host)",
                    "uuid": url.split("/")[-1],
                    "url": url,
                }
            )
    data_earnapp = BASE_DIR / "data" / "earnapp"
    if data_earnapp.exists():
        for sub in sorted(data_earnapp.iterdir()):
            if sub.is_dir():
                cfile = sub / "claim_url.txt"
                if cfile.exists():
                    url = cfile.read_text(encoding="utf-8").strip()
                    if url:
                        claims.append(
                            {
                                "node": sub.name,
                                "uuid": url.split("/")[-1],
                                "url": url,
                            }
                        )
    for c in containers:
        if "earnapp" in c["name"] or c["name"].startswith("ea_"):
            try:
                logs = subprocess.run(
                    ["docker", "logs", "--tail", "30", c["name"]],
                    capture_output=True,
                    text=True,
                    timeout=4,
                )
                combined = (logs.stdout or "") + "\n" + (logs.stderr or "")
                m = re.search(r"https://earnapp\.com/r/(sdk-node-[a-f0-9]{32})", combined)
                if m:
                    uuid_val = m.group(1)
                    if not any(x["uuid"] == uuid_val for x in claims):
                        claims.append(
                            {
                                "node": c["name"],
                                "uuid": uuid_val,
                                "url": f"https://earnapp.com/r/{uuid_val}",
                            }
                        )
            except Exception:
                pass
    return claims


@app.get("/api/status")
def api_status() -> Dict[str, Any]:
    mem = psutil.virtual_memory()
    net = psutil.net_io_counters()
    containers = get_docker_containers()
    running = sum(1 for c in containers if c["state"] == "running")
    proxies_list = []
    if PROXIES_FILE.exists():
        proxies_list = [
            l.strip()
            for l in PROXIES_FILE.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "net_sent_mb": round(net.bytes_sent / (1024**2), 2),
        "net_recv_mb": round(net.bytes_recv / (1024**2), 2),
        "containers_total": len(containers),
        "containers_running": running,
        "proxies_count": len(proxies_list),
        "containers": containers,
        "earnapp_claims": get_earnapp_claims(containers),
    }


@app.get("/api/env")
def api_get_env() -> Dict[str, Any]:
    return {"values": parse_env_file(ENV_FILE)}


@app.post("/api/env")
def api_save_env(payload: EnvPayload) -> Dict[str, Any]:
    save_env_values(payload.values)
    return {"status": "ok", "message": "Environment configuration saved to .env"}


@app.get("/api/proxies")
def api_get_proxies() -> Dict[str, Any]:
    raw = PROXIES_FILE.read_text(encoding="utf-8") if PROXIES_FILE.exists() else ""
    valid = [
        l.strip()
        for l in raw.splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    return {"proxies_raw": raw, "count": len(valid)}


@app.post("/api/proxies")
def api_save_proxies(payload: ProxiesPayload) -> Dict[str, Any]:
    PROXIES_FILE.write_text(payload.proxies_raw.strip() + "\n", encoding="utf-8")
    valid = [
        l.strip()
        for l in payload.proxies_raw.splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    return {"status": "ok", "count": len(valid), "message": f"Saved {len(valid)} proxies to proxies.txt"}


@app.post("/api/action/{action_name}")
def api_action(action_name: str) -> Dict[str, Any]:
    try:
        if action_name == "start_single":
            res = subprocess.run(
                ["docker", "compose", "-f", "docker-compose.yml", "up", "-d", "--build"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=180,
            )
            return {
                "status": "ok" if res.returncode == 0 else "error",
                "output": (res.stdout + "\n" + res.stderr).strip(),
            }
        elif action_name == "start_multiproxy":
            gen = subprocess.run(
                ["python3" if os.name != "nt" else "python", "generate_multiproxy_compose.py"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if gen.returncode != 0:
                return {"status": "error", "output": (gen.stdout + "\n" + gen.stderr).strip()}
            up = subprocess.run(
                ["docker", "compose", "-f", "docker-compose.multiproxy.yml", "up", "-d", "--build"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=300,
            )
            return {
                "status": "ok" if up.returncode == 0 else "error",
                "output": (gen.stdout + "\n" + up.stdout + "\n" + up.stderr).strip(),
            }
        elif action_name == "stop_all":
            out = []
            r1 = subprocess.run(
                ["docker", "compose", "-f", "docker-compose.yml", "down"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=60,
            )
            out.append(r1.stdout + "\n" + r1.stderr)
            if (BASE_DIR / "docker-compose.multiproxy.yml").exists():
                r2 = subprocess.run(
                    ["docker", "compose", "-f", "docker-compose.multiproxy.yml", "down"],
                    cwd=str(BASE_DIR),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                out.append(r2.stdout + "\n" + r2.stderr)
            return {"status": "ok", "output": "\n".join(out).strip()}
        else:
            raise HTTPException(status_code=400, detail="Unknown action")
    except Exception as e:
        return {"status": "error", "output": str(e)}


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8899, reload=False)
