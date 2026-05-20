from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
import os


def send_approved_mail(email, username, login_url):

    subject = "Account Approved"

    html_content = f"""
    <html>
    <body style="text-align:center; font-family:Arial;">

        <img src="cid:logo_image"
             style="width:90px;height:90px;border-radius:50%;">

        <h2>Lightcircle</h2>

        <h1 style="color:green;">
            Account Approved
        </h1>

        <p>Hello {username},</p>

        <p>
            Your account has been approved successfully.
        </p>

        <a href="{login_url}"
           style="
                background:#4f64ff;
                color:white;
                padding:12px 20px;
                text-decoration:none;
                border-radius:5px;
                display:inline-block;
                margin-top:20px;
           ">
            Login Now
        </a>

    </body>
    </html>
    """

    text_content = f"Your account has been approved. Login here: {login_url}"

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.EMAIL_HOST_USER,
        [email]
    )

    msg.attach_alternative(html_content, "text/html")

    attach_logo(msg)

    msg.send()

    return True


# ================= REJECTED MAIL =================

def send_rejected_mail(email, username):

    subject = "Account Rejected"

    html_content = f"""
    <html>
    <body style="text-align:center; font-family:Arial;">

        <img src="cid:logo_image"
             style="width:90px;height:90px;border-radius:50%;">

        <h2>Lightcircle</h2>

        <h1 style="color:red;">
            Account Rejected
        </h1>

        <p>Hello {username},</p>

        <p>
            Your account request has been rejected.
        </p>

    </body>
    </html>
    """

    text_content = "Your account request has been rejected."

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.EMAIL_HOST_USER,
        [email]
    )

    msg.attach_alternative(html_content, "text/html")

    attach_logo(msg)

    msg.send()

    return True

# ================= COMMON LOGO FUNCTION =================

def attach_logo(msg):

    logo_path = os.path.join(
        settings.BASE_DIR,
        'static',
        'images',
        'Pasted image.png'
    )

    with open(logo_path, "rb") as f:

        mime_image = MIMEImage(f.read())

        mime_image.add_header(
            "Content-ID",
            "<logo_image>"
        )

        mime_image.add_header(
            "Content-Disposition",
            "inline",
            filename="Pasted image.png"
        )

        msg.attach(mime_image)