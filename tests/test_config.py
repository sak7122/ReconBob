"""Config startup-validation tests. Prod must refuse placeholder/missing secrets."""
import pytest

from src.config import Config


def _cfg(env, **over):
    import os

    base = {
        "ENV": env,
        "GCP_PROJECT_ID": "real-project",
        "TWILIO_ACCOUNT_SID": "ACx",
        "TWILIO_AUTH_TOKEN": "tok",
        "TWILIO_WHATSAPP_FROM": "whatsapp:+1",
    }
    base.update(over)
    for k, v in base.items():
        os.environ[k] = v
    return Config()


def test_dev_validates_with_defaults(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("GCP_PROJECT_ID", "reconbob-local")
    Config().validate()  # no raise


def test_prod_rejects_placeholder_project():
    cfg = _cfg("production", GCP_PROJECT_ID="your-project-id")
    with pytest.raises(RuntimeError, match="GCP_PROJECT_ID"):
        cfg.validate()


def test_prod_rejects_missing_twilio_secret():
    cfg = _cfg("production", TWILIO_AUTH_TOKEN="")
    with pytest.raises(RuntimeError, match="TWILIO_AUTH_TOKEN"):
        cfg.validate()


def test_prod_ok_with_real_values():
    _cfg("production").validate()  # no raise
