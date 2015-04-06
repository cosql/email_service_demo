#!/usr/bin/env python

import logging

import mandrill.mandrill as mandrill

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class mandrill_client():
    def __init__(self, api_key = config.mandrill_key):
        self.handler = mandrill.Mandrill(api_key)

    def send_email(self, email_request):
        message = {
            'from_name': email_request.sender_name,
            'from_email' : email_request.sender_email,
            'subject': email_request.subject,
            'to': [{'email': email_request.recipient,}],
            'text' : email_request.text,
            }
        # send email using mandrill library
        try:
            result = self.handler.messages.send(message=message,
                                                async=False,
                                                ip_pool='Main Pool')
        except mandrill.Error, e:
            # Mandrill errors are thrown as exceptions
            logger.error('A mandrill error occurred: %s - %s' %
                         (e.__class__, e))
            raise

        if result[0]['status'] == u'sent':
            return True
        else:
            return False

if __name__ == "__main__":
    cl = mandrill_client()
    cl.send_email()
