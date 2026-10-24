#!/usr/bin/env python3
"""
🔍 Status & Claim Link Scanner for ProxPool Docker Matrix
Scans and displays all generated EarnApp claim links, node IDs, and running container status.
"""

import os
import glob
import subprocess

def get_docker_ps():
    try:
        res = subprocess.run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"], capture_output=True, text=True)
        lines = res.stdout.strip().split("\n")
        status_map = {}
        for line in lines:
            if line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    status_map[parts[0]] = parts[1]
        return status_map
    except Exception:
        return {}

def main():
    print("=" * 70)
    print("⚡ PROXPOOL PASSIVE DOCKER MATRIX MONITOR")
    print("=" * 70)

    direct_claim_file = os.path.join("data", "earnapp", "claim_url.txt")
    if os.path.exists(direct_claim_file):
        with open(direct_claim_file, "r") as f:
            url = f.read().strip()
            print(f"👉 Single Mode EarnApp Claim URL:")
            print(f"   {url}\n")

    multi_nodes = glob.glob(os.path.join("data", "earnapp", "*", "claim_url.txt"))
    if multi_nodes:
        print("👉 Multi-Proxy EarnApp Claim URLs:")
        for path in sorted(multi_nodes):
            node_dir = os.path.basename(os.path.dirname(path))
            with open(path, "r") as f:
                url = f.read().strip()
                print(f"   [{node_dir}] -> {url}")
        print()

    ps_map = get_docker_ps()
    if ps_map:
        print("📊 Running Docker Containers:")
        print(f"{'Container Name':<35} | {'Status'}")
        print("-" * 70)
        for name, status in sorted(ps_map.items()):
            if any(k in name.lower() for k in ["earn", "traff", "pawn", "packet", "honey", "proxy", "tun", "repocket", "bitping", "grass", "presearch"]):
                print(f"{name:<35} | {status}")
    else:
        print("💡 No active Docker containers detected (make sure Docker Desktop / Daemon is running).")

    print("=" * 70)

if __name__ == "__main__":
    main()
