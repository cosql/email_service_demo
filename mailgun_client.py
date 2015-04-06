#!/usr/bin/env python

import json
import logging

import requests

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class mailgun_client():
    def __init__(self,
                 api_key=config.mailgun_key,
                 sandbox=config.mailgun_sandbox):
        self.api_key = api_key
        self.request_url = \
          'https://api.mailgun.net/v2/{0}/messages'.format(sandbox)

    def send_email(self, email_request):
        # send message using requests library
        try:
            response = requests.post(self.request_url,
                                     auth=('api', self.api_key),
                                     data={
                                         'from' : '{0} {1}'.format(
                                             email_request.sender_name,
                                             email_request.sender_email),
                                         'to': email_request.recipient,
                                         'subject': email_request.subject,
                                         'text': email_request.text,
                                         })

        except e:
            logger.error("mailgun request failed %s" % e)
            return False

        if response.status_code == 200:
            return True
        else:
            # response message returned as json
            logger.error("mailgun error memssage %s" %
                         json.loads(response.text)["message"][1:-1])
            return False

if __name__ == "__main__":
    cl = mailgun_client()
    cl.send_email()
