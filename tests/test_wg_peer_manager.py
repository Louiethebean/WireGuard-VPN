import base64
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from wg_peer_manager import (  # noqa: E402
    add_peer,
    allocate_next_ip,
    generate_keypair,
    load_registry,
    render_client_config,
    render_server_peer_block,
)


def test_generate_keypair_returns_valid_base64_32_byte_keys():
    private_key, public_key = generate_keypair()
    assert len(base64.b64decode(private_key)) == 32
    assert len(base64.b64decode(public_key)) == 32
    assert private_key != public_key


def test_allocate_next_ip_skips_reserved_server_address():
    ip = allocate_next_ip("10.8.0.0/24", used_addresses=[])
    # .1 is reserved for the server, so the first peer should get .2
    assert ip == "10.8.0.2"


def test_allocate_next_ip_skips_used_addresses():
    ip = allocate_next_ip("10.8.0.0/24", used_addresses=["10.8.0.2", "10.8.0.3"])
    assert ip == "10.8.0.4"


def test_allocate_next_ip_raises_when_subnet_exhausted():
    network_hosts = [f"10.8.0.{i}" for i in range(1, 255)]
    with pytest.raises(ValueError):
        allocate_next_ip("10.8.0.0/24", used_addresses=network_hosts)


def test_add_peer_writes_registry_without_private_key(tmp_path):
    registry = tmp_path / "peers.json"
    result = add_peer("laptop", "10.8.0.0/24", str(registry))

    assert result["peer"].name == "laptop"
    assert result["peer"].address == "10.8.0.2"
    assert "private_key" in result  # returned to caller for the client config

    peers = load_registry(str(registry))
    assert len(peers) == 1
    assert peers[0].private_key is None  # never persisted to disk


def test_add_peer_rejects_duplicate_name(tmp_path):
    registry = tmp_path / "peers.json"
    add_peer("laptop", "10.8.0.0/24", str(registry))
    with pytest.raises(ValueError):
        add_peer("laptop", "10.8.0.0/24", str(registry))


def test_add_peer_allocates_sequential_addresses(tmp_path):
    registry = tmp_path / "peers.json"
    r1 = add_peer("phone", "10.8.0.0/24", str(registry))
    r2 = add_peer("laptop", "10.8.0.0/24", str(registry))
    assert r1["peer"].address == "10.8.0.2"
    assert r2["peer"].address == "10.8.0.3"


def test_render_server_peer_block_contains_public_key_and_ip(tmp_path):
    registry = tmp_path / "peers.json"
    result = add_peer("laptop", "10.8.0.0/24", str(registry))
    block = render_server_peer_block(result["peer"])
    assert result["peer"].public_key in block
    assert "10.8.0.2/32" in block


def test_render_client_config_contains_endpoint_and_dns():
    from wg_peer_manager import Peer

    peer = Peer(name="laptop", public_key="pub", address="10.8.0.2", created_at="now")
    config = render_client_config(peer, "priv", "server-pub", "vpn.example.com:51820")
    assert "Endpoint = vpn.example.com:51820" in config
    assert "DNS = 1.1.1.1" in config
    assert "AllowedIPs = 0.0.0.0/0" in config
