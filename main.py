#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import os
import time
import uuid

import webapp2
from google.appengine.api import memcache, users
from google.appengine.ext import ndb
from google.appengine.ext.webapp.template import render

from email_client import EmailRequest, EmailClient
header = '<head>' + \
         '<link rel=\"stylesheet\" \
         href=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css\">' + \
         '<meta http-equiv="refresh" content="3;/" />' + \
         '</head>'

# email entity schema in data store
class Email(ndb.Model):
    sender = ndb.StringProperty()
    sender_email = ndb.StringProperty()
    text = ndb.TextProperty()
    # blob property can be indexed
    subject = ndb.BlobProperty(indexed=True)
    status = ndb.BooleanProperty()
    recipient = ndb.StringProperty()
    # blob property can be indexed
    msg_id = ndb.BlobProperty(indexed=True)
    user_id = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now=True)

class MainHandler(webapp2.RequestHandler):
    ''' handler for home page '''
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url('/'))
            return

        user_id = user.user_id()
        # fetch 10 most recent emails of the user from memcache or ndb
        emails = memcache.get(user_id)
        if not emails:
            emails = Email.query(
                Email.user_id == user_id).order(-Email.date).fetch(10)
            memcache.add(user_id, emails)
        # render home page with user's recent emails
        context = {
            'user':      user,
            'emails':    emails,
            'email_count': len(emails),
            'login':     users.create_login_url(self.request.uri),
            'logout':    users.create_logout_url(self.request.uri),
        }
        tmpl = os.path.join(os.path.dirname(__file__), 'template/index.html')
        self.response.write(render(tmpl, context))

class ComposeHandler(webapp2.RequestHandler):
    # handler for email compose
    def get(self):
        # check_list is not empty if user wants to edit some unsent email
        emails = Email.query(
            Email.msg_id == str(self.request.get('email_id')),
            Email.status == False)
        email_context = None
        for e in emails:
            # should be at most one email entity found
            email_context = e
            self.response.set_cookie('msg_id', email_context.msg_id)

        if email_context is None or email_context.sender_email is None:
            sender_email = users.get_current_user().email()
        else:
            sender_email = email_context.sender_email
        context = {
            'sender_email':      sender_email,
            'email_context':     email_context
        }
        tmpl = os.path.join(os.path.dirname(__file__), 'template/compose.html')
        self.response.write(render(tmpl, context))

    def post(self):
        action = self.request.get('action')
        if action == 'save':
            self.__save()
        else:
            self.__send()

    # save email as draft
    def __save(self):
        ''' save an email to ndb data store '''
        # parse requset
        self.__parse_request()
        if  len(self.subject) > 0 or len(self.text) > 0 or \
           len(self.recipient) > 0:
            # we have some text to update
            self.__update_datastore()

        self.response.write(
            header + '[<a href="/"><b>Back To Home</b></a>]<br><body><h2>%s</h2></body>' %
            "Save succeeded")

        return

    def __send(self):
        ''' send an email then save it to ndb data store '''
        self.__parse_request()
        # new email request
        email_request = EmailRequest(
            sender_email=users.get_current_user().email(),
            sender_name=self.sender_name,
            recipient=self.recipient,
            subject=self.subject,
            text=self.text)

        # validate email request (recipient address and subject length)
        valid, reason = email_request.validate()
        if (valid == False):
            self.response.write(
                header + '[<a href="/"><b>Back To Home</b></a>]<br><body><h2>' +
                'Send Failed, reason: <i>%s</i></h2></body>' %
                reason)
            return

        # send email using EmailClient, it defaults to Mailgun
        # and falls back to Mandrill in case of failure
        cl = EmailClient()
        status = False
        try:
            status = cl.send_email(email_request)
        except:
            pass

        self.__update_datastore(status)

        # create result page to return
        if status:
            show_message = "Send succeeded"
        else:
            show_message = "Send failed"
        self.response.write(
            header + '[<a href="/"><b>Back To Home</b></a>]<br><body><h2>%s</h2></body>' %
            show_message)

    def __parse_request(self):
        ''' parse user request from form submit'''
        self.sender_name = self.request.get('sender_name')
        self.sender_email = self.request.get('sender_email')
        self.subject = str(self.request.get('subject').encode('utf8'))
        self.text = self.request.get('text')
        self.recipient = self.request.get('recipient')

        self.user_id = users.get_current_user().user_id()
        self.msg_id = self.request.cookies.get('msg_id')
        self.response.delete_cookie('msg_id')

        # check if there is an existing draft with the same msg_id
        self.email = None
        if self.msg_id is not None:
            emails = Email.query(
                Email.msg_id == str(self.msg_id),
                Email.status == False)
            for e in emails:
                # should be at most email found
                self.email = e

        # no draft found, create a new email entity
        if self.email == None:
            self.email = Email()

    def __update_datastore(self, status=False):
        '''update datastore upon send/save events'''
        # assign msg_id if not existing
        if self.msg_id == None:
            # use uuid as a msg_id
            self.msg_id = str(uuid.uuid1())

        self.email.sender = self.sender_name
        self.email.sender_email = self.sender_email
        self.email.subject = self.subject
        self.email.text = self.text
        self.email.recipient = self.recipient
        self.email.status = status
        self.email.msg_id = str(self.msg_id)
        self.email.user_id = self.user_id
        self.email.put()

        # It seems ndb writes have high latency.
        # Sleep for 1 second to wait for completion
        time.sleep(1)
        memcache.delete(self.user_id)
        memcache.flush_all()

class OutboxHandler(webapp2.RequestHandler):
    ''' handler for outbox/drafts view '''
    def get(self):
        # parse targeted emails, can be either 'all' or 'unsent'
        target = self.request.get('target')
        # parse search keyword if any
        keyword = str(self.request.get('keyword').encode('utf8'))
        user_id = users.get_current_user().user_id()
        if len(keyword) == 0:
            # retrieve all sent messages
            if target != 'unsent':
                emails = Email.query(
                    Email.user_id == user_id).order(-Email.date)
            # retrieve unsent messages
            else:
                emails = Email.query(Email.user_id == user_id,
                                     Email.status == False).order(-Email.date)

        else:
            # it's a search request
            # retrieve messages with certain subject $keyword
            emails = Email.query(Email.user_id == user_id,
                                 Email.subject == keyword).order(-Email.date)
        context = {
            'emails':    emails,
        }
        tmpl = os.path.join(os.path.dirname(__file__), 'template/outbox.html')
        self.response.write(render(tmpl, context))

class DeleteHandler(webapp2.RequestHandler):
    ''' handler for message delete '''
    def post(self):
        # delete request is sent as a post request
        email = Email.query(Email.msg_id == str(self.request.get('email_id')))
        if email is None:
            self.redirect('/outbox')
            return
        user_id = users.get_current_user().user_id()
        for e in email:
            e.key.delete()
        time.sleep(1)
        memcache.delete(user_id)
        memcache.flush_all()
        # JIC it's ajax request, no redirection here any more
        # self.redirect('/outbox')

app = webapp2.WSGIApplication([
    ( '/', MainHandler),
    ( '/compose', ComposeHandler),
    ( '/outbox', OutboxHandler),
    ( '/delete', DeleteHandler),
    ], debug=True)
