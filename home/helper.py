from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
import os

def send_forget_password_mail(email, otp_code):
    subject = f'Lightcircle Verification Code: {otp_code}'

    html_content = f"""
    <html>
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verification Code</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        body {{
            width: 100%;
            background-color: #f1f1f1;
            padding-top: 120px;
            text-align: center;
        }}
        img {{
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: 5px solid #4f64ff;
            box-shadow: 0px 0px 10px #4f64ff;
        }}
        h2 {{
            margin-top: 10px;
        }}
        .otp {{
            font-size: 30px;
            font-weight: bold;
            padding: 10px 20px;
            background-color: #4f64ff;
            display: inline-block;
            color: #fff;
            border-radius: 5px;
            margin-top: 15px;
        }}
    </style>
    </head>

    <body style="text-align:center; font-family:Arial, sans-serif;">

        <div style="text-align:center; margin-bottom:20px;">
            <img src="cid:logo_image" alt="Logo"
                style="width:90px; height:90px; border-radius:50%; border:4px solid #4f64ff; box-shadow:0 0 10px #4f64ff; display:block; margin:0 auto;">
            
            <h2 style="margin-top:12px; font-size:24px;">Lightcircle</h2>
        </div>

        <h2 style="font-size:22px; margin-bottom:15px;">
            Please enter this code to verify your account.
        </h2>

        <span class="otp"
            style="display:inline-block; background:#4f64ff; color:#fff; padding:8px 18px; font-size:26px; font-weight:bold; border-radius:6px;">
            {otp_code}
        </span>

        <p style="margin-top:15px; font-size:16px; color:#444;">
            This code is for account verification only.
        </p>

        <footer style="margin-top: 30px; color: #c2410c; font-weight: bold; font-size:14px;">
            © 2023 ZKC INDIA. All rights reserved.
        </footer>

    </body>
    </body>
    </html>
    """

    text_content = f"Your OTP code is {otp_code}"

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.EMAIL_HOST_USER,
        [email]
    )

    msg.attach_alternative(html_content, "text/html")

    # ---------- Attach Offline Image ----------
    logo_path = os.path.join(settings.BASE_DIR, "static/images/Pasted image.png")

    with open(logo_path, "rb") as f:
        mime_image = MIMEImage(f.read())
        mime_image.add_header("Content-ID", "<logo_image>")
        mime_image.add_header("Content-Disposition", "inline", filename="Pasted image.png")
        msg.attach(mime_image)

    msg.send()
    return True
