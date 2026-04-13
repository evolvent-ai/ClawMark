---
name: email
description: "Send and receive emails via local IMAP/SMTP mail server (GreenMail)"
---

# Email Skill

Send and receive emails through a local mail server. Use Python's `imaplib` and `smtplib` (standard library, no pip install needed).

Accounts are auto-created on first use — no setup needed.

## Server Info

| Protocol | Host | Port | TLS |
|----------|------|------|-----|
| IMAP | `greenmail` | `3143` | No |
| SMTP | `greenmail` | `3025` | No |

Your email address and password will be provided in the task context.

## Send Email

```python
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Body text here", "plain", "utf-8")
msg["From"] = "your@address.com"
msg["To"] = "recipient@address.com"
msg["Subject"] = "Subject line"

with smtplib.SMTP("greenmail", 3025) as s:
    s.send_message(msg)
```

## Read Emails

```python
import imaplib
import email

imap = imaplib.IMAP4("greenmail", 3143)
imap.login("your@address.com", "your_password")
imap.select("INBOX")

_, data = imap.search(None, "ALL")
for num in data[0].split():
    _, msg_data = imap.fetch(num, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])
    print(f"From: {msg['From']}")
    print(f"Subject: {msg['Subject']}")
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                print(part.get_payload(decode=True).decode())
    else:
        print(msg.get_payload(decode=True).decode())

imap.logout()
```

## Search Emails

```python
# By sender
_, data = imap.search(None, '(FROM "someone@example.com")')

# By subject keyword
_, data = imap.search(None, '(SUBJECT "keyword")')

# Recent emails
import datetime
since = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%d-%b-%Y")
_, data = imap.search(None, f'(SINCE {since})')
```
