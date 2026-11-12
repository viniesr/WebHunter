import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.hunter import CarListing


def send_email_alert(listings: list[CarListing]) -> None:
    """Envia um e-mail em HTML com os novos anúncios encontrados."""
    if not listings:
        return

    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    recipient = os.getenv("EMAIL_RECIPIENT")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚗 WebHunter: {len(listings)} novo(s) Civic G10 encontrado(s)!"
    msg["From"] = sender
    msg["To"] = recipient

    html_items = ""
    for car in listings:
        price_formatted = (
            f"R$ {car.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if car.price > 0
            else "Sob consulta"
        )
        html_items += f"""
        <div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; font-family: Arial, sans-serif;">
            <h3 style="margin-top: 0; color: #1a73e8;">{car.title} ({car.year})</h3>
            <p><strong>Versão:</strong> {car.version} | <strong>Preço:</strong> <span style="color: #0d904f; font-weight: bold;">{price_formatted}</span></p>
            <p><strong>Localização:</strong> {car.location} | <strong>Fonte:</strong> {car.source}</p>
            <p style="color: #444;">{car.summary}</p>
            <a href="{car.url}" style="display: inline-block; background-color: #1a73e8; color: white; padding: 10px 16px; text-decoration: none; border-radius: 5px; font-weight: bold;">Ver Anúncio Original</a>
        </div>
        """

    html_body = f"""
    <html>
        <body style="background-color: #f9f9f9; padding: 20px;">
            <h2 style="font-family: Arial, sans-serif; color: #202124;">Novas oportunidades encontradas pelo WebHunter</h2>
            {html_items}
        </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())