#!/usr/bin/env python

import re

import config
from mandrill_client import mandrill_client
from mailgun_client import mailgun_client

# regex for email address validation
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

class EmailClient:
    '''A simple email client abstraction'''
    sender_name = config.sender_name
    sender_email = config.sender_email

    def __init__(self):
        pass

    def send_email(self, email_request):
        cl = mailgun_client()
        status = cl.send_email(email_request)
        if status is False:
            cl = mandrill_client()
            status = cl.send_email(email_request)
        return status

class EmailRequest:
    def __init__(self,
                 recipient,
                 sender_email="",
                 sender_name="",
                 subject="",
                 text=""):
        if len(sender_email) == 0:
            self.sender_email = config.sender_email
        else:
            self.sender_email = sender_email
        if len(sender_name) == 0:
            self.sender_name = config.sender_name
        else:
            self.sender_name = sender_name
        self.recipient = recipient
        self.subject = subject
        self.text = text

    def validate(self):
        # subject can not be longer than 500 due GAE limitation
        if (len(self.subject) >= 500):
            return False, "subject too long"
        if not EMAIL_REGEX.match(self.recipient):
            return False, "recipient email address not vailid"
        return True, ""
