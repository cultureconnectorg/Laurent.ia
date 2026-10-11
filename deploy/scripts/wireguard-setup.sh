#!/usr/bin/env bash
# Private network between your computer (server) and your laptop, with WireGuard.
# Generates both configurations locally; keys never leave your machines.
# Usage: scripts/wireguard-setup.sh <public address of the computer, e.g. myhome.example:51820>
#   The address is your Internet box's public IP or domain, with UDP 51820 forwarded
#   to the computer. Import wg/computer.conf on the computer and wg/laptop.conf on the laptop.
set -euo pipefail
cd "$(dirname "$0")/.."
ENDPOINT=${1:?public address of the computer, e.g. 203.0.113.10:51820}
command -v wg >/dev/null || { echo "install wireguard-tools first"; exit 1; }
umask 077; mkdir -p wg
wg genkey | tee wg/computer.key | wg pubkey > wg/computer.pub
wg genkey | tee wg/laptop.key | wg pubkey > wg/laptop.pub
wg genpsk > wg/psk
cat > wg/computer.conf <<CONF
[Interface]
Address = 10.77.0.1/24
ListenPort = 51820
PrivateKey = $(cat wg/computer.key)

[Peer]
# laptop
PublicKey = $(cat wg/laptop.pub)
PresharedKey = $(cat wg/psk)
AllowedIPs = 10.77.0.2/32
CONF
cat > wg/laptop.conf <<CONF
[Interface]
Address = 10.77.0.2/24
PrivateKey = $(cat wg/laptop.key)

[Peer]
# computer (Laurent.ia server)
PublicKey = $(cat wg/computer.pub)
PresharedKey = $(cat wg/psk)
Endpoint = $ENDPOINT
AllowedIPs = 10.77.0.1/32
PersistentKeepalive = 25
CONF
rm -f wg/computer.key wg/laptop.key
echo "Created wg/computer.conf and wg/laptop.conf."
echo "Passkeys (WebAuthn) refuse IP addresses: use the private name laurentia.home.arpa (RFC 8375)."
echo "1) On BOTH machines, add to the hosts file:   10.77.0.1  laurentia.home.arpa"
echo "2) In .env:  BIND_ADDRESS=10.77.0.1  PUBLIC_ORIGIN=https://laurentia.home.arpa:8443  SITE_ADDRESSES=\"localhost, laurentia.home.arpa\""
echo "Only the laptop's traffic to 10.77.0.1 goes through the tunnel; nothing else is routed."
