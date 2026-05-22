#!/usr/bin/env bash
# Creates a self-signed certificate and private key for the FLNet Client.
#
# Prerequisites:
#   1. Run fill_san_cnf.py first to populate FLNet_client/self_signed_certs/san.cnf
#   2. openssl must be installed (openssl version)
#
# Usage:
#   ./create_self_signed_certs.sh [DAYS]
#
# DAYS: certificate validity in days (default: 365)
# Output files (referenced in .env by the installer):
#   FLNet_client/self_signed_certs/fullchain.pem  — public certificate
#   FLNet_client/self_signed_certs/privkey.pem    — private key

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="${SCRIPT_DIR}/FLNet_client/self_signed_certs"
SAN_CNF="${CERT_DIR}/san.cnf"
CERT_OUT="${CERT_DIR}/fullchain.pem"
KEY_OUT="${CERT_DIR}/privkey.pem"
DAYS="${1:-365}"

echo "========================================================"
echo "  FLNet Client — Self-Signed Certificate Generation"
echo "========================================================"
echo ""

# Check openssl
if ! command -v openssl &>/dev/null; then
    echo "ERROR: openssl is not installed or not in PATH."
    echo "  Install it with: sudo apt install openssl  (Debian/Ubuntu)"
    echo "                or: sudo dnf install openssl  (Fedora/RHEL)"
    exit 1
fi

# Check that san.cnf has been filled in
if grep -q 'TODO_' "${SAN_CNF}"; then
    echo "ERROR: ${SAN_CNF} still contains TODO placeholders."
    echo "  Run fill_san_cnf.py first to fill in all required fields."
    exit 1
fi

echo "Using config: ${SAN_CNF}"
echo "Validity    : ${DAYS} days"
echo "Output cert : ${CERT_OUT}"
echo "Output key  : ${KEY_OUT}"
echo ""

openssl req \
    -x509 \
    -newkey rsa:2048 \
    -nodes \
    -keyout "${KEY_OUT}" \
    -out    "${CERT_OUT}" \
    -days   "${DAYS}" \
    -config "${SAN_CNF}"

# Restrict private key permissions
chmod 600 "${KEY_OUT}"
chmod 644 "${CERT_OUT}"

echo ""
echo "Certificate generated successfully."
echo ""
echo "You can verify the certificate with:"
echo "  openssl x509 -in ${CERT_OUT} -text -noout"
echo ""
echo "Next step: start the FLNet Client:"
echo "  cd FLNet_client && docker compose up -d"
echo ""
echo "NOTE: Self-signed certificates will show a browser warning."
echo "  You need to add this certificate to your browser's or OS's trust store"
echo "  to avoid the warning. For production use, consider a certificate from"
echo "  a trusted CA (e.g. Let's Encrypt via certbot)."
