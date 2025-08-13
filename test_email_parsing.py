import imaplib
import email
from email.header import decode_header
import webbrowser
import os

# -----------------------
# 🔐 CONFIGURE YOUR EMAIL
# -----------------------
EMAIL = "replicantsys@gmail.com"
PASSWORD = "htgamdnoniiuwcpg"  # Must be an App Password if 2FA is enabled

# -----------------------
# CONNECT TO GMAIL
# -----------------------
def fetch_last_5_emails():
    try:
        # Connect to the Gmail IMAP server
        imap = imaplib.IMAP4_SSL("imap.gmail.com")

        # Login to your account
        imap.login(EMAIL, PASSWORD)

        # Select the mailbox you want to check (use 'inbox')
        imap.select("inbox")

        # Search for all emails
        status, messages = imap.search(None, "ALL")
        if status != "OK":
            print("Failed to retrieve emails.")
            return

        # Get list of email IDs
        mail_ids = messages[0].split()

        # Get the latest 5 email IDs
        latest_5_ids = mail_ids[-5:]

        for mail_id in reversed(latest_5_ids):
            status, msg_data = imap.fetch(mail_id, "(RFC822)")
            if status != "OK":
                print(f"Failed to fetch mail ID: {mail_id}")
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    # Parse the email
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="ignore")

                    from_ = msg.get("From")

                    print("="*50)
                    print(f"From: {from_}")
                    print(f"Subject: {subject}")

                    # Extract email body
                    body = None
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body = part.get_payload(decode=True)
                                if body:
                                    body = body.decode(errors="ignore")
                                    break
                    else:
                        body = msg.get_payload(decode=True)
                        if body:
                            body = body.decode(errors="ignore")

                    if body:
                        print(f"Body:\n{body[:500].strip()}")  # Show only first 500 chars
                    else:
                        print("No plain text body found.")

        # Logout
        imap.logout()

    except imaplib.IMAP4.error as e:
        print("❌ IMAP login failed. Check your credentials or app password.")
        print("Error:", e)
    except Exception as ex:
        print("❌ An error occurred:", ex)

# -----------------------
# RUN THE SCRIPT
# -----------------------
if __name__ == "__main__":
    fetch_last_5_emails()
