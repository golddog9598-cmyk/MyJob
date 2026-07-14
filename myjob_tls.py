"""Local TLS certificate helpers for the MyJob development server.

Production deployments should provide a trusted certificate through
``MYJOB_TLS_CERT`` and ``MYJOB_TLS_KEY`` (or the matching command-line
arguments).  When neither is provided, MyJob creates a local self-signed
certificate under ``.boss_profile/tls``.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_TLS_DIR = PROJECT_DIR / ".boss_profile" / "tls"
DEFAULT_CERT_PATH = DEFAULT_TLS_DIR / "myjob-local.crt"
DEFAULT_KEY_PATH = DEFAULT_TLS_DIR / "myjob-local.key"


def _first_env(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def resolve_tls_paths(
    cert_path: str | os.PathLike[str] | None = None,
    key_path: str | os.PathLike[str] | None = None,
) -> tuple[Path, Path]:
    """Resolve explicit paths, environment variables, then local defaults."""

    cert_env = _first_env("MYJOB_TLS_CERT", "MYJOB_SSL_CERTFILE")
    key_env = _first_env("MYJOB_TLS_KEY", "MYJOB_SSL_KEYFILE")
    cert_value = cert_path or cert_env
    key_value = key_path or key_env
    if bool(cert_value) != bool(key_value):
        raise ValueError("HTTPS 证书和私钥必须同时指定")
    return (
        Path(cert_value).expanduser() if cert_value else DEFAULT_CERT_PATH,
        Path(key_value).expanduser() if key_value else DEFAULT_KEY_PATH,
    )


def ensure_local_certificate(
    cert_path: str | os.PathLike[str] | None = None,
    key_path: str | os.PathLike[str] | None = None,
    *,
    force: bool = False,
) -> tuple[Path, Path]:
    """Return usable TLS files, generating a local self-signed pair if needed."""

    cert_file, key_file = resolve_tls_paths(cert_path, key_path)
    if not force and cert_file.is_file() and key_file.is_file():
        return cert_file.resolve(), key_file.resolve()
    if cert_file.exists() != key_file.exists():
        raise FileNotFoundError("HTTPS 证书或私钥不完整，请同时提供有效文件")

    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError as exc:  # pragma: no cover - exercised only on incomplete installs
        raise RuntimeError(
            "HTTPS 证书缺失，且未安装 cryptography；请执行 pip install -r requirements.txt"
        ) from exc

    cert_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.parent.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MyJob"),
            x509.NameAttribute(NameOID.COMMON_NAME, "MyJob Local Development"),
        ]
    )
    hostnames = {"localhost"}
    machine_name = socket.gethostname().strip()
    if machine_name:
        hostnames.add(machine_name)
    san_entries = [x509.DNSName(name) for name in sorted(hostnames)]
    san_entries.extend(
        [
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            x509.IPAddress(ipaddress.ip_address("::1")),
        ]
    )
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )

    key_file.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    try:
        key_file.chmod(0o600)
    except OSError:
        pass
    cert_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    return cert_file.resolve(), key_file.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 MyJob 本地 HTTPS 自签名证书")
    parser.add_argument("--cert", help="证书输出路径")
    parser.add_argument("--key", help="私钥输出路径")
    parser.add_argument("--force", action="store_true", help="覆盖已有证书")
    args = parser.parse_args()
    cert_file, key_file = ensure_local_certificate(args.cert, args.key, force=args.force)
    print(f"证书: {cert_file}")
    print(f"私钥: {key_file}")


if __name__ == "__main__":
    main()
