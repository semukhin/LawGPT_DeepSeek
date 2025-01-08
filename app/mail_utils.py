from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.config import MAIL_SETTINGS

conf = ConnectionConfig(
    MAIL_SERVER=MAIL_SETTINGS["MAIL_SERVER"],
    MAIL_PORT=MAIL_SETTINGS["MAIL_PORT"],
    MAIL_STARTTLS=MAIL_SETTINGS.get("MAIL_STARTTLS", True),
    MAIL_SSL_TLS=MAIL_SETTINGS.get("MAIL_SSL_TLS", False),
    MAIL_USERNAME=MAIL_SETTINGS["MAIL_USERNAME"],
    MAIL_PASSWORD=MAIL_SETTINGS["MAIL_PASSWORD"],
    MAIL_FROM=MAIL_SETTINGS["MAIL_FROM"]
)

async def send_verification_email(email_to: str, code: int):
    """Отправка письма с кодом подтверждения."""
    message = MessageSchema(
        subject="Код подтверждения",
        recipients=[email_to],
        body=f"Ваш код подтверждения: {code}",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

async def send_verification_email(email_to: str, code: int):
    subject = "Код восстановления пароля"
    body = f"Ваш код для восстановления пароля: {code}"
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)
