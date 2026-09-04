from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ENVIRONMENT: str = "development"

    EMAIL_PIN_EXPIRE_MINUTES: int = 10
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "no-reply@taxismitu.com"
    SMTP_USE_TLS: bool = True

    # Módulo de pagos Wompi: apagado por defecto durante el piloto. El router
    # /api/payments ni se registra en la app mientras PAYMENTS_ENABLED sea False.
    PAYMENTS_ENABLED: bool = False
    WOMPI_PUBLIC_KEY: str | None = None
    WOMPI_PRIVATE_KEY: str | None = None
    WOMPI_EVENTS_SECRET: str | None = None
    WOMPI_INTEGRITY_SECRET: str | None = None
    WOMPI_BASE_URL: str = "https://sandbox.wompi.co/v1"


settings = Settings()
