#!/usr/bin/env python3
"""Automate WireGuard peer provisioning: keypair generation, IP allocation,
and config rendering, backed by a tracked peers.json registry.

Usage:
    python wg_peer_manager.py add <peer-name> \\
        --subnet 10.8.0.0/24 --registry peers.json \\
        --server-public-key <key> --server-endpoint vpn.example.com:51820

    python wg_peer_manager.py list --registry peers.json
"""
import argparse
import base64
import ipaddress
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519


@dataclass
class Peer:
    name: str
    public_key: str
    address: str
    created_at: str
    private_key: Optional[str] = None  # only ever written to the client's own config, never the registry


def generate_keypair() -> tuple:
    """Return (private_key_b64, public_key_b64) as WireGuard expects them."""
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return (
        base64.b64encode(private_bytes).decode("ascii"),
        base64.b64encode(public_bytes).decode("ascii"),
    )


def load_registry(path: str) -> List[Peer]:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text())
    return [Peer(**entry) for entry in data]


def save_registry(path: str, peers: List[Peer]) -> None:
    # never persist private keys to the shared registry
    sanitized = [{k: v for k, v in asdict(p).items() if k != "private_key"} for p in peers]
    Path(path).write_text(json.dumps(sanitized, indent=2))


def allocate_next_ip(subnet: str, used_addresses: List[str]) -> str:
    network = ipaddress.ip_network(subnet, strict=False)
    used = {ipaddress.ip_address(addr.split("/")[0]) for addr in used_addresses}
    # skip network address and the first usable IP (reserved for the server itself)
    hosts = list(network.hosts())
    if not hosts:
        raise ValueError(f"Subnet {subnet} has no usable host addresses")

    reserved_server_ip = hosts[0]
    for candidate in hosts[1:]:
        if candidate not in used and candidate != reserved_server_ip:
            return str(candidate)

    raise ValueError(f"No available addresses remaining in {subnet}")


def render_server_peer_block(peer: Peer) -> str:
    return (
        f"# {peer.name}\n"
        f"[Peer]\n"
        f"PublicKey = {peer.public_key}\n"
        f"AllowedIPs = {peer.address}/32\n"
    )


def render_client_config(
    peer: Peer,
    private_key: str,
    server_public_key: str,
    server_endpoint: str,
    dns: str = "1.1.1.1",
) -> str:
    return (
        f"[Interface]\n"
        f"PrivateKey = {private_key}\n"
        f"Address = {peer.address}/32\n"
        f"DNS = {dns}\n"
        f"\n"
        f"[Peer]\n"
        f"PublicKey = {server_public_key}\n"
        f"Endpoint = {server_endpoint}\n"
        f"AllowedIPs = 0.0.0.0/0\n"
        f"PersistentKeepalive = 25\n"
    )


def add_peer(name: str, subnet: str, registry_path: str) -> dict:
    peers = load_registry(registry_path)
    if any(p.name == name for p in peers):
        raise ValueError(f"Peer '{name}' already exists in {registry_path}")

    used_addresses = [p.address for p in peers]
    address = allocate_next_ip(subnet, used_addresses)
    private_key, public_key = generate_keypair()

    peer = Peer(
        name=name,
        public_key=public_key,
        address=address,
        created_at=datetime.now(timezone.utc).isoformat(),
        private_key=private_key,
    )

    peers.append(peer)
    save_registry(registry_path, peers)

    return {
        "peer": peer,
        "private_key": private_key,
        "server_peer_block": render_server_peer_block(peer),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Automate WireGuard peer provisioning.")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Provision a new peer")
    add_p.add_argument("name")
    add_p.add_argument("--subnet", required=True, help="VPN subnet, e.g. 10.8.0.0/24")
    add_p.add_argument("--registry", default="peers.json")
    add_p.add_argument("--server-public-key", required=True)
    add_p.add_argument("--server-endpoint", required=True, help="host:port of the WireGuard server")

    list_p = sub.add_parser("list", help="List provisioned peers")
    list_p.add_argument("--registry", default="peers.json")

    args = parser.parse_args()

    if args.command == "add":
        result = add_peer(args.name, args.subnet, args.registry)
        peer = result["peer"]
        client_config = render_client_config(
            peer, result["private_key"], args.server_public_key, args.server_endpoint
        )
        sys.stdout.write("# Add this to the server's wg0.conf:\n")
        sys.stdout.write(result["server_peer_block"])
        sys.stdout.write("\n# Client config (save as a .conf and import):\n")
        sys.stdout.write(client_config)
    elif args.command == "list":
        peers = load_registry(args.registry)
        for p in peers:
            sys.stdout.write(f"{p.name}\t{p.address}\t{p.created_at}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
