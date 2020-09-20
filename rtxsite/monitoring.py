import smtplib
import requests
import rtxsite


def hit(name):
    url = getattr(rtxsite.config["alerts"], name)
    if url == "nope":
        return
    requests.get(url)


def email(target, status, msg):
    smtp = rtxsite.config["alerts"].smtp
    if smtp == "nope":
        return
    email_from = rtxsite.config["alerts"].email_from
    email_to = rtxsite.config["alerts"].email_to
    s = smtplib.SMTP(smtp)
    s.sendmail(email_from, email_to, f"Subject:  {status}\n\n{msg}")
    s.close()
