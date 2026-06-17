import os


def _bool(val, default=False):
    return str(val).lower() in ("1", "true", "yes") if val is not None else default


class DevConfig:
    DEBUG = _bool(os.environ.get("FLASK_DEBUG"), default=True)
    DEVELOPMENT = True
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-insecure-key").encode("utf8")
    SOLR_ADDRESS = os.environ.get("SOLR_ADDRESS", "http://localhost:8983/solr/")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://dmtc:dmtcpass@localhost/dmtc",
    )
    RSS_EMAIL = os.environ.get("RSS_EMAIL", "noreply@example.com")
    ORCID_CLIENT_ID = os.environ.get("ORCID_CLIENT_ID", "")
    ORCID_CLIENT_SECRET = os.environ.get("ORCID_CLIENT_SECRET", "")
    ORCID_AUTH_URL = os.environ.get("ORCID_AUTH_URL", "https://orcid.org/oauth/authorize")
    ORCID_EXCHANGE_URL = os.environ.get("ORCID_EXCHANGE_URL", "https://orcid.org/oauth/token")
    ORCID_REDIRECT_URL = os.environ.get(
        "ORCID_REDIRECT_URL",
        "http://localhost/api/orcid_sign_in/orcid_callback",
    )
    FRONT_END_URL = os.environ.get("FRONT_END_URL", "http://localhost")
    API_KEYS = [k for k in os.environ.get("API_KEYS", "").split(",") if k]


class ProdConfig(DevConfig):
    DEBUG = False
    DEVELOPMENT = False
