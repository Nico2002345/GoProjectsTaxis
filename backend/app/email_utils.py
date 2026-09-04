import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("taxismitu.email")


def send_verification_email(to_email: str, full_name: str, pin: str) -> None:
    subject = "Tu código de verificación · TaxisMitu"
    body = (
        f"Hola {full_name},\n\n"
        f"Tu código de verificación de correo es: {pin}\n"
        f"Este código vence en {settings.EMAIL_PIN_EXPIRE_MINUTES} minutos.\n\n"
        "Si no solicitaste este registro, ignora este mensaje.\n\n"
        "— Equipo TaxisMitu"
    )

    if not settings.SMTP_HOST:
        logger.warning(
            "SMTP no configurado; código de verificación para %s: %s", to_email, pin
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)
