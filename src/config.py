"""Environment config + startup validation. Mirrors RAGaaS pattern: prod aborts on placeholder values."""
import logging
import os

log = logging.getLogger("reconbob.config")


class Config:
    def __init__(self) -> None:
        self.env = os.getenv("ENV", "development")
        self.gcp_project_id = os.getenv("GCP_PROJECT_ID", "reconbob-local")
        self.gcp_region = os.getenv("GCP_REGION", "us-central1")
        self.gemini_ocr_model = os.getenv("GEMINI_OCR_MODEL", "gemini-2.0-flash")
        self.gemini_pro_model = os.getenv("GEMINI_PRO_MODEL", "gemini-2.0-pro")

        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "")

        self.max_receipts_per_user_day = int(os.getenv("MAX_RECEIPTS_PER_USER_DAY", "100"))
        self.max_gemini_calls_day = int(os.getenv("MAX_GEMINI_CALLS_DAY", "5000"))

    @property
    def is_prod(self) -> bool:
        return self.env == "production"

    def validate(self) -> None:
        """Fail fast at startup. In prod, refuse to run with dev placeholders or missing secrets."""
        if self.is_prod:
            if self.gcp_project_id in ("", "reconbob-local", "your-project-id"):
                raise RuntimeError("GCP_PROJECT_ID must be a real project in production")
            missing = [
                name
                for name, val in (
                    ("TWILIO_ACCOUNT_SID", self.twilio_account_sid),
                    ("TWILIO_AUTH_TOKEN", self.twilio_auth_token),
                    ("TWILIO_WHATSAPP_FROM", self.twilio_whatsapp_from),
                )
                if not val
            ]
            if missing:
                raise RuntimeError(f"Missing required prod secrets: {', '.join(missing)}")
        log.info("config validated", extra={"env": self.env, "project": self.gcp_project_id})


config = Config()
