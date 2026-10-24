#!/usr/bin/env python3
"""
⚡ Ultimate Multi-Proxy Docker Compose Generator (15+ Platforms per Proxy IP)
Inspired by engageub/InternetIncome + ProxyBase + DePIN Suite.
Reads .env and proxies.txt, and generates isolated tun2socks clusters for each proxy.
"""

import os
import re
import uuid

PROXIES_FILE = "proxies.txt"
ENV_FILE = ".env"
OUTPUT_COMPOSE = "docker-compose.multiproxy.yml"


def load_env(filepath: str) -> dict:
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


def parse_proxy_line(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    match = re.match(r"^(?:(socks5|http)://)?(?:([^:@]+):([^@]+)@)?([^:]+):(\d+)$", line)
    if match:
        proto, user, password, host, port = match.groups()
        return {
            "proto": proto or "http",
            "host": host,
            "port": port,
            "user": user or "",
            "pass": password or ""
        }

    parts = line.split(":")
    if len(parts) == 4:
        return {
            "proto": "http",
            "host": parts[0],
            "port": parts[1],
            "user": parts[2],
            "pass": parts[3]
        }
    elif len(parts) == 2:
        return {
            "proto": "http",
            "host": parts[0],
            "port": parts[1],
            "user": "",
            "pass": ""
        }
    return None


def main():
    env = load_env(ENV_FILE)
    dev_prefix = env.get("DEVICE_NAME", "US-Node")

    if not os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, "w", encoding="utf-8") as f:
            f.write("# Add your Residential / ISP Proxies here (1 proxy per line)\n")
            f.write("# Format: IP:PORT:USER:PASS or socks5://user:pass@IP:PORT\n")
        print(f"⚠️ Created {PROXIES_FILE}. Please add your proxies before running again!")
        return

    proxies = []
    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            p = parse_proxy_line(line)
            if p:
                proxies.append((idx, p))

    if not proxies:
        print(f"⚠️ No valid proxies found in {PROXIES_FILE}. Please add your proxies first.")
        return

    compose = "version: '3.8'\n\nservices:\n"

    for idx, p in proxies:
        node_id = f"{idx:02d}"
        node_name = f"node_{node_id}"
        dev_name = f"{dev_prefix}-{node_id}"
        proxy_url = (
            f"{p['proto']}://{p['user']}:{p['pass']}@{p['host']}:{p['port']}"
            if p["user"]
            else f"{p['proto']}://{p['host']}:{p['port']}"
        )

        # 0. Tun2Socks Network Router for this Proxy
        compose += f"""
  # =====================================================================
  # 🌐 PROXY CLUSTER #{node_id} -> {p['host']}:{p['port']}
  # =====================================================================
  tun_{node_name}:
    image: xjasonlyu/tun2socks:v2.5.2
    container_name: tun_{node_name}
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    environment:
      - LOGLEVEL=warning
      - PROXY={proxy_url}
    mem_limit: 64m
    networks:
      - income-net
"""

        # 1. EarnApp
        if env.get("ENABLE_EARNAPP", "true").lower() == "true":
            compose += f"""
  earnapp_{node_name}:
    build:
      context: .
      dockerfile: Dockerfile.earnapp
    container_name: earnapp_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 96m
    volumes:
      - ./data/earnapp/{node_name}:/etc/earnapp
"""

        # 2. TraffMonetizer
        if env.get("TRAFFMONETIZER_TOKEN"):
            compose += f"""
  traffmonetizer_{node_name}:
    image: traffmonetizer/cli_v2:latest
    container_name: traffmonetizer_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    command: start accept --token {env['TRAFFMONETIZER_TOKEN']} --device-name {dev_name}
"""

        # 3. Pawns.app / IPRoyal
        if env.get("PAWNS_EMAIL") and env.get("PAWNS_PASSWORD"):
            compose += f"""
  pawns_{node_name}:
    image: iproyal/pawns-cli:latest
    container_name: pawns_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    command: -email={env['PAWNS_EMAIL']} -password={env['PAWNS_PASSWORD']} -device-name={dev_name} -device-id={node_name} -accept-tos
"""

        # 4. PacketStream
        if env.get("PACKETSTREAM_CID"):
            compose += f"""
  packetstream_{node_name}:
    image: packetstream/psclient:latest
    container_name: packetstream_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    environment:
      - CID={env['PACKETSTREAM_CID']}
"""

        # 5. Honeygain
        if env.get("HONEYGAIN_EMAIL") and env.get("HONEYGAIN_PASSWORD"):
            compose += f"""
  honeygain_{node_name}:
    image: honeygain/honeygain:latest
    container_name: honeygain_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    command: -tou-accept -email {env['HONEYGAIN_EMAIL']} -pass {env['HONEYGAIN_PASSWORD']} -device {dev_name}
"""

        # 6. EarnFM
        if env.get("EARNFM_TOKEN"):
            compose += f"""
  earnfm_{node_name}:
    image: earnfm/earnfm-client:latest
    container_name: earnfm_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    environment:
      - EARNFM_TOKEN={env['EARNFM_TOKEN']}
"""

        # 7. Repocket
        if env.get("REPOCKET_EMAIL") and env.get("REPOCKET_API_KEY"):
            compose += f"""
  repocket_{node_name}:
    image: repocket/repocket:latest
    container_name: repocket_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    environment:
      - RP_EMAIL={env['REPOCKET_EMAIL']}
      - RP_API_KEY={env['REPOCKET_API_KEY']}
"""

        # 8. ProxyRack Peer
        if env.get("PROXYRACK_API_KEY"):
            pr_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"proxyrack-{p['host']}-{idx}"))
            compose += f"""
  proxyrack_{node_name}:
    image: proxyrack/pop:latest
    container_name: proxyrack_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    environment:
      - UUID={pr_uuid}
"""

        # 9. ProxyLite
        if env.get("PROXYLITE_USER_ID"):
            compose += f"""
  proxylite_{node_name}:
    image: proxylite/proxyservice:latest
    container_name: proxylite_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    environment:
      - USER_ID={env['PROXYLITE_USER_ID']}
"""

        # 10. PacketShare
        if env.get("PACKETSHARE_EMAIL") and env.get("PACKETSHARE_PASSWORD"):
            compose += f"""
  packetshare_{node_name}:
    image: packetshare/packetshare:latest
    container_name: packetshare_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    command: -accept-tos -email={env['PACKETSHARE_EMAIL']} -password={env['PACKETSHARE_PASSWORD']}
"""

        # 11. Grass Network
        if env.get("GRASS_USER_ID"):
            compose += f"""
  grass_{node_name}:
    image: mrcolorrain/get-grass:latest
    container_name: grass_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 96m
    environment:
      - USER_ID={env['GRASS_USER_ID']}
"""

        # 12. Presearch Node
        if env.get("PRESEARCH_REGISTRATION_CODE"):
            compose += f"""
  presearch_{node_name}:
    image: presearch/node:latest
    container_name: presearch_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 96m
    environment:
      - REGISTRATION_CODE={env['PRESEARCH_REGISTRATION_CODE']}
    volumes:
      - ./data/presearch/{node_name}:/app/node
"""

        # 13. ProxyBase
        if env.get("PROXYBASE_WALLET"):
            compose += f"""
  proxybase_{node_name}:
    build:
      context: .
      dockerfile: Dockerfile.proxybase
    container_name: proxybase_{node_name}
    restart: unless-stopped
    network_mode: "service:tun_{node_name}"
    depends_on:
      - tun_{node_name}
    mem_limit: 64m
    environment:
      - WALLET_ADDRESS={env['PROXYBASE_WALLET']}
"""

    compose += """
networks:
  income-net:
    driver: bridge
"""

    with open(OUTPUT_COMPOSE, "w", encoding="utf-8") as f:
        f.write(compose)

    print(f"✅ Successfully generated {OUTPUT_COMPOSE} for {len(proxies)} proxy clusters!")
    print("🚀 Start with: start_multiproxy.bat (Windows) or bash start_multiproxy.sh (Linux)")


if __name__ == "__main__":
    main()
