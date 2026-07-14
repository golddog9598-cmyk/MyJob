from pathlib import Path

import pytest
from cryptography import x509
from fastapi.testclient import TestClient

import boss_app
from myjob_tls import ensure_local_certificate


def test_generated_certificate_supports_local_hosts(tmp_path: Path):
    cert_file, key_file = ensure_local_certificate(
        tmp_path / "myjob.crt",
        tmp_path / "myjob.key",
    )

    assert cert_file.is_file()
    assert key_file.is_file()
    certificate = x509.load_pem_x509_certificate(cert_file.read_bytes())
    names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "localhost" in names.get_values_for_type(x509.DNSName)
    assert "127.0.0.1" in {str(value) for value in names.get_values_for_type(x509.IPAddress)}


def test_certificate_and_key_must_be_configured_together(tmp_path: Path):
    with pytest.raises(ValueError, match="必须同时指定"):
        ensure_local_certificate(tmp_path / "only-cert.crt")


def test_app_identity_and_spa_routes():
    client = TestClient(boss_app.app)
    expected = client.get("/").text

    assert boss_app.app.title == "MyJob"
    assert boss_app.app.version == "V0.0.3"
    for path in ("/login", "/register", "/app", "/docs", "/changelog", "/MyJobaAdmin"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.text == expected


def test_default_cors_origins_are_https_only():
    origins = [origin.strip() for origin in boss_app._default_origins.split(",") if origin.strip()]

    assert origins
    assert all(origin.startswith("https://") for origin in origins)


def test_legacy_admin_route_redirects_to_new_admin_login():
    client = TestClient(boss_app.app, follow_redirects=False)
    response = client.get("/admin")

    assert response.status_code == 307
    assert response.headers["location"] == "/MyJobaAdmin"
