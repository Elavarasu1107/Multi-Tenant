import sendgrid
from fastapi import HTTPException, status
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    ClickTracking,
    Content,
    Email,
    Mail,
    To,
    TrackingSettings,
)

from core.settings import settings


async def send_mail(to_email, subject, content):
    sg = SendGridAPIClient(api_key=settings.EMAIL_KEY)
    from_email = Email(settings.EMAIL_USER)
    to_email = To(to_email)
    subject = subject
    content = Content("text/plain", content)
    mail = Mail(from_email, to_email, subject, content)

    tracking = TrackingSettings(click_tracking=ClickTracking(enable=False, enable_text=False))
    mail.tracking_settings = tracking

    mail_json = mail.get()
    response = sg.client.mail.send.post(request_body=mail_json)
    return response.status_code
