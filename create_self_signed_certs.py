#!/usr/bin/env python3
"""
Generate a self-signed certificate for FLNet Client.
This script combines configuration and certificate generation in one step.

Usage:
    ./create_self_signed_certs.py

Prerequisites:
    - openssl must be installed and in PATH
    - FLNet_client/self_signed_certs/san.cnf.template must exist

Output files:
    FLNet_client/self_signed_certs/san.cnf       — certificate configuration (git-ignored)
    FLNet_client/self_signed_certs/fullchain.pem — public certificate
    FLNet_client/self_signed_certs/privkey.pem   — private key
"""
import sys
import subprocess
import os
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent
SAN_TEMPLATE_PATH = BASE_DIR / 'FLNet_client' / 'self_signed_certs' / 'san.cnf.template'
SAN_CNF_PATH = BASE_DIR / 'FLNet_client' / 'self_signed_certs' / 'san.cnf'
CERT_OUT = BASE_DIR / 'FLNet_client' / 'self_signed_certs' / 'fullchain.pem'
KEY_OUT = BASE_DIR / 'FLNet_client' / 'self_signed_certs' / 'privkey.pem'


def ask(prompt: str, example: str = "", required: bool = True) -> str:
    """Prompt user for input, optionally requiring a non-empty answer."""
    hint = f" (e.g. {example})" if example else ""
    while True:
        value = input(f"{prompt}{hint}: ").strip()
        if value:
            return value
        if not required:
            return ""
        print("  This field is required.")


def ask_list(prompt: str, example: str = "") -> list:
    """Prompt user to enter multiple items, one per line."""
    hint = f" (e.g. {example})" if example else ""
    print(f"{prompt}{hint}")
    print("  Enter one per line. Leave blank and press Enter when done.")
    items = []
    while True:
        val = input(f"  Entry {len(items) + 1}: ").strip()
        if not val:
            break
        items.append(val)
    return items


def check_openssl() -> bool:
    """Check if openssl is available."""
    try:
        subprocess.run(
            ["openssl", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_config() -> tuple:
    """Interactively gather certificate configuration from user."""
    print("=" * 60)
    print("  FLNet Client — Self-Signed Certificate Generation")
    print("=" * 60)
    print()

    if not SAN_TEMPLATE_PATH.exists():
        print(f"ERROR: {SAN_TEMPLATE_PATH} not found.")
        print("Please contact a developer and create the certificate files yourself for now.")
        sys.exit(1)

    print("--- Distinguished Name (who the certificate is issued to) ---\n")
    print("Only Common Name (CN) is required. Other fields are optional.\n")
    country = ask("Country code (2 letters)", "DE", required=False)
    if country and (len(country) != 2 or not country.isalpha()):
        print("WARNING: Country code should be exactly 2 letters (e.g. DE, US, AT).")
    state = ask("State or province", "Bavaria", required=False)
    city = ask("City", "Munich", required=False)
    org = ask("Organization name", "My Hospital GmbH", required=False)
    unit = ask("Organizational unit", "IT Department", required=False)
    cn = ask("Common name (primary hostname or IP)", "myserver.example.com")

    print("\n--- Subject Alternative Names (SANs) ---\n")
    print("SANs tell browsers which hostnames/IPs this certificate is valid for.")
    print("Modern browsers require SANs — the Common Name above alone is not enough.\n")

    dns_names = ask_list("DNS hostnames (leave blank to skip)", "myserver.example.com")
    ip_addrs = ask_list("IP addresses (leave blank to skip)", "192.168.1.100")

    if not dns_names and not ip_addrs:
        print("\nERROR: At least one DNS hostname or IP address is required.")
        sys.exit(1)

    print("\n--- Certificate validity ---\n")
    days_input = ask("Validity in days", "365", required=False)
    days = int(days_input) if days_input.isdigit() else 365
    print(f"  Certificate will be valid for {days} days.")

    return country, state, city, org, unit, cn, dns_names, ip_addrs, days


def generate_san_config(country: str, state: str, city: str, org: str, unit: str,
                       cn: str, dns_names: list, ip_addrs: list) -> None:
    """Generate san.cnf from template with user values."""
    # Read template
    template_content = SAN_TEMPLATE_PATH.read_text()

    # Build alt_names block
    alt_lines = []
    for i, name in enumerate(dns_names, start=1):
        alt_lines.append(f"DNS.{i} = {name}")
    for i, ip in enumerate(ip_addrs, start=1):
        alt_lines.append(f"IP.{i}  = {ip}")
    alt_block = "\n".join(alt_lines)

    # Replace [dn] section (clean, no comments, only include non-empty fields)
    dn_lines = ["[dn]"]
    if country:
        dn_lines.append(f"C  = {country.upper()}")
    if state:
        dn_lines.append(f"ST = {state}")
    if city:
        dn_lines.append(f"L  = {city}")
    if org:
        dn_lines.append(f"O  = {org}")
    if unit:
        dn_lines.append(f"OU = {unit}")
    dn_lines.append(f"CN = {cn}")
    dn_section = "\n".join(dn_lines)

    template_content = re.sub(
        r'\[dn\].*?(?=\n\[)',
        dn_section,
        template_content,
        flags=re.DOTALL
    )

    # Replace [alt_names] section
    alt_section = f"""\
[alt_names]
{alt_block}"""

    template_content = re.sub(
        r'\[alt_names\].*$',
        alt_section,
        template_content,
        flags=re.DOTALL
    )

    SAN_CNF_PATH.write_text(template_content)
    print(f"\nSAN config written to:\n  {SAN_CNF_PATH}")


def generate_certificate(days: int) -> None:
    """Generate certificate using openssl."""
    print("\nGenerating certificate...")
    print(f"Using config: {SAN_CNF_PATH}")
    print(f"Validity    : {days} days")
    print(f"Output cert : {CERT_OUT}")
    print(f"Output key  : {KEY_OUT}")
    print()

    try:
        subprocess.run([
            "openssl", "req",
            "-x509",
            "-newkey", "rsa",
            "-nodes",
            "-keyout", str(KEY_OUT),
            "-out", str(CERT_OUT),
            "-days", str(days),
            "-config", str(SAN_CNF_PATH)
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to generate certificate: {e}")
        sys.exit(1)

    # Set file permissions
    # Needs read for other so that the user in the nginx container can read the certs
    os.chmod(str(KEY_OUT), 0o644)
    os.chmod(str(CERT_OUT), 0o644)

    print()
    print("Certificate generated successfully.")
    print()
    print("You can verify the certificate with:")
    print(f"  openssl x509 -in {CERT_OUT} -text -noout")
    print()
    print("NOTE: Self-signed certificates will show a browser warning.")
    print("  You need to add this certificate to your browser's or OS's trust store")
    print("  to avoid the warning.")


def main():
    # Check openssl
    if not check_openssl():
        print("ERROR: openssl is not installed or not in PATH.")
        print("  Install it with: sudo apt install openssl  (Debian/Ubuntu)")
        print("                or: sudo dnf install openssl  (Fedora/RHEL)")
        sys.exit(1)

    # Gather config interactively (includes days prompt)
    country, state, city, org, unit, cn, dns_names, ip_addrs, days = generate_config()

    # Generate san.cnf from template
    generate_san_config(country, state, city, org, unit, cn, dns_names, ip_addrs)

    # Generate certificate
    generate_certificate(days)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(1)
