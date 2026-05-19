import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Pull credentials from environment variables (set these in your .env file)
# See .env.example for the exact variable names to use
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = os.getenv("ALERT_EMAIL", "")
SMTP_PASSWORD = os.getenv("ALERT_PASSWORD", "")
ALERT_TO      = os.getenv("ALERT_TO", "")


def send_price_alert(title, old_price, new_price, target_price, reason):
    # reason is either "drop" (fell 10%+) or "target" (hit your price goal)
    change_pct = ((old_price - new_price) / old_price) * 100

    if reason == "target":
        subject  = f"🎯 Target Price Hit: {title[:50]}"
        headline = f"The price hit your target of £{target_price:.2f}!"
    else:
        subject  = f"📉 Price Drop Alert: {title[:50]}"
        headline = f"Price dropped by {change_pct:.1f}%!"

    target_row = ""
    if target_price:
        target_row = f"<tr><td style='padding:8px;border:1px solid #ddd;'><b>Your Target</b></td><td style='padding:8px;border:1px solid #ddd;'>£{target_price:.2f}</td></tr>"

    body = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
      <h2 style="color: #e44d26;">{headline}</h2>
      <table style="border-collapse: collapse; width: 360px;">
        <tr>
          <td style="padding: 8px; border: 1px solid #ddd;"><b>Product</b></td>
          <td style="padding: 8px; border: 1px solid #ddd;">{title}</td>
        </tr>
        <tr>
          <td style="padding: 8px; border: 1px solid #ddd;"><b>Old Price</b></td>
          <td style="padding: 8px; border: 1px solid #ddd;">£{old_price:.2f}</td>
        </tr>
        <tr>
          <td style="padding: 8px; border: 1px solid #ddd;"><b>New Price</b></td>
          <td style="padding: 8px; border: 1px solid #ddd; color: green;"><b>£{new_price:.2f}</b></td>
        </tr>
        {target_row}
        <tr>
          <td style="padding: 8px; border: 1px solid #ddd;"><b>Drop</b></td>
          <td style="padding: 8px; border: 1px solid #ddd; color: red;">{change_pct:.1f}% off</td>
        </tr>
      </table>
      <p style="color: #888; font-size: 12px; margin-top: 20px;">Sent by your Price Scraper</p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    msg["To"]      = ALERT_TO
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, ALERT_TO, msg.as_string())
        print(f"[email] alert sent → {title}")
    except Exception as e:
        print(f"[email] failed to send: {e}")
        print("        double-check your ALERT_EMAIL / ALERT_PASSWORD in .env")
