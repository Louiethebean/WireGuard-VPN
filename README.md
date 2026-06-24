# WireGuard VPN Installation & Configuration Guide

![License](https://img.shields.io/badge/license-MIT-blue) ![Platform](https://img.shields.io/badge/platform-Ubuntu%20%7C%20Debian-orange) ![Tool](https://img.shields.io/badge/tool-WireGuard-023e8a)

This repository contains a comprehensive guide for installing and configuring **WireGuard VPN** on Ubuntu/Debian systems. WireGuard is a modern, secure, high-performance VPN designed to be simple and easy to deploy.

![Architecture](./architecture.svg)

---

## What Is WireGuard?

[WireGuard](https://www.wireguard.com/) is a fast and modern VPN protocol that uses state-of-the-art cryptography and is built into the Linux kernel. It offers better performance, lower attack surface, and easier setup compared to traditional VPNs like OpenVPN or IPSec.

---

## Requirements

- Ubuntu 18.04+ or Debian 10+
- Root or sudo access
- Two or more devices (server/client) to connect securely

---

## Installation Steps (Ubuntu/Debian)

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install WireGuard

```bash
sudo apt install wireguard -y
```

### 3. Enable IP Forwarding

Edit `/etc/sysctl.conf` and uncomment or add:

```bash
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1
```

Then apply:

```bash
sudo sysctl -p
```

---

## Key Generation

On **both server and client**, generate private/public key pairs:

```bash
wg genkey | tee privatekey | wg pubkey > publickey
```

---

## Server Configuration

Edit `/etc/wireguard/wg0.conf`:

```ini
[Interface]
PrivateKey = <server-private-key>
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
PublicKey = <client-public-key>
AllowedIPs = 10.0.0.2/32
```

---

## Client Configuration

Edit `/etc/wireguard/wg0.conf`:

```ini
[Interface]
PrivateKey = <client-private-key>
Address = 10.0.0.2/24

[Peer]
PublicKey = <server-public-key>
Endpoint = <server-public-ip>:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

---

## ▶Start WireGuard

```bash
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

Check status:

```bash
sudo wg show
```

---

## Firewall Configuration (Optional)

Use `ufw` or `iptables` to allow UDP 51820:

```bash
sudo ufw allow 51820/udp
```

## Contributing

Pull requests are welcome! Open issues or submit improvements as needed.

---

## What I Learned / Skills Demonstrated

- **Modern VPN protocol design** — why WireGuard's small codebase and Curve25519/ChaCha20 cryptography are a deliberate tradeoff against IPsec/OpenVPN's flexibility and complexity.
- **Key-based peer authentication** — public/private keypairs replacing certificate authorities or shared secrets, and what that simplifies (and what it doesn't, like revocation).
- **Network fundamentals** — routing client traffic through a tunnel interface, firewall rules for UDP, and the difference between full-tunnel and split-tunnel configs.
- **Minimal attack surface thinking** — appreciating why a VPN with one open UDP port is easier to reason about securely than a stack of legacy protocol options.

**Problem solved:** a from-scratch, secure remote-access VPN setup that avoids the configuration sprawl of older VPN protocols.

---

## Resources

- [WireGuard Official Site](https://www.wireguard.com/)
- [WireGuard Docs](https://www.wireguard.com/install/)
- [DigitalOcean WireGuard Guide](https://www.digitalocean.com/community/tutorials/how-to-set-up-wireguard-on-ubuntu-20-04)

---

## License

MIT License. See [LICENSE](./MIT%20License.txt) for more details.

---

WireGuard offers fast, secure, and simple VPN connectivity — get started today!
