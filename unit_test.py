#!/usr/bin/env python
# -*- coding: utf-8 -*-

# fix gae library path first
import os
import sys
sys.path.insert(0, '/usr/local/google_appengine')
import dev_appserver
dev_appserver.fix_sys_path()
# fix django path
sys.path.append(os.path.join("/usr/local/google_appengine",
                             'lib', 'django-1.3'))
from django.template.loaders import filesystem
filesystem.load_template_source = filesystem._loader.load_template_source

import re
import unittest
import webtest
import webapp2

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

from email_client import EmailRequest
from mailgun_client import mailgun_client
from mandrill_client import mandrill_client
from main import (
    Email,
    MainHandler,
    ComposeHandler,
    DeleteHandler,
    OutboxHandler,
)

class TestEmailClient(unittest.TestCase):
    ''' test class for email client'''
    def testValidEmailAddress(self):
        request = EmailRequest('test@example.com')
        ret, reason = request.validate()
        self.assertTrue(ret)

    def testBadEmailAddress(self):
        request = EmailRequest('badFormat')
        ret, reason = request.validate()
        self.assertFalse(ret)

    def testValidEmailSubject(self):
        request = EmailRequest('test@example.com', subject='subject')
        ret, reason = request.validate()
        self.assertTrue(ret)

    def testBadEmailSubject(self):
        long_subject = 'a' * 501
        request = EmailRequest('test@example.com', subject=long_subject)
        ret, reason = request.validate()
        self.assertFalse(ret)

    def testMailgunClient(self):
        request = EmailRequest('test@example.com', subject='mailgun',
                               sender_email='cosql@github.com', text="test")
        cl = mailgun_client(
            api_key='key-c57536663caee62c3a30f367562b19c7',
            sandbox='sandboxc90288b9f29f4d4997fb800e74d89111.mailgun.org')
        ret = cl.send_email(request)
        self.assertTrue(ret)

    def testMandrillClient(self):
        request = EmailRequest('test@example.com', subject='mandrill',
                               sender_email='cosql@github.com', text='test')
        cl = mandrill_client(api_key='LNLWrN12hPA6Afju_h3gWQ')
        ret = cl.send_email(request)
        self.assertTrue(ret)

class TestDataStore(unittest.TestCase):
    ''' test class for data store and memcache'''
    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def testEntityDataStore(self):
        email = Email()
        email.put()

        # fetch 2 records, we should only get 1
        self.assertEqual(1, len(Email.query().fetch(2)))

        # delete email, Email data store is empty now
        email.key.delete()
        self.assertEqual(0, len(Email.query().fetch(2)))

    def testSearchDataStore(self):
        email = Email()
        email.subject = "test"
        email.put()

        # search email with subject "test", should find 1 match
        self.assertEqual(1, len(Email.query(Email.subject == "test").fetch()))

        # delete email, Email data store is empty now
        email.key.delete()
        # search email with subject "test", should find 0 match
        self.assertEqual(0, len(Email.query(Email.subject == "test").fetch()))

    def testEntityMemcache(self):
        # list of Emails are cached for each user
        email = Email()
        email.subject = "test"
        memcache.add("test", [email])

        # get Email list for user "test"
        emails = memcache.get("test")
        self.assertNotEqual(emails, None)
        self.assertEqual(1, len(emails))

        emailCache = emails[0]
        # cached email should not the same object as the original email object
        self.assertNotEqual(id(emailCache), id(email))
        self.assertEqual(emailCache.subject, "test")

        emailCache.subject = "test v2"
        memcache.set("test", [emailCache])

        # get Email list for user "test"
        emails = memcache.get("test")
        self.assertNotEqual(emails, None)
        self.assertEqual(1, len(emails))

        emailCache = emails[0]
        # test if email subject changes in the cache
        self.assertEqual(emailCache.subject, "test v2")

        memcache.delete("test")
        emailCache = memcache.get("test")
        self.assertEqual(emailCache, None)

class TestApp(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        # login as a user
        self.testbed.init_user_stub()
        self.testbed.setup_env(
            user_email='hello@gmail.com',
            user_id='123456',
            user_is_admin='1',
            overwrite=True,
        )
        # setup handlers
        self.mainApp = webapp2.WSGIApplication([('/', MainHandler)])
        self.composeApp = webapp2.WSGIApplication([('/compose',
                                                    ComposeHandler)])
        self.deleteApp = webapp2.WSGIApplication([('/delete',
                                                    DeleteHandler)])
        self.outboxApp = webapp2.WSGIApplication([('/outbox',
                                                    OutboxHandler)])

    def tearDown(self):
        self.testbed.deactivate()

    def testMainHandler(self):
        # request home page
        testapp = webtest.TestApp(self.mainApp)
        response = testapp.get('/')
        # check the status code
        self.assertEqual(200, response.status_code)

    def testComposeHandlerSave(self):
        # request home page
        testapp = webtest.TestApp(self.composeApp)
        # no email for now
        self.assertEqual(0, len(Email.query(Email.user_id == "123456").fetch()))
        params = { "action" : "save",
                   "sender_name" : "unit test",
                   "sender_email" : "cosql@github.com",
                   "recipient" : "test@example.com",
                   "subject" : "saving unit test",
                   "text" : "unit test text",
                 }
        response = testapp.post('/compose', params)
        # check the status code, redirect to home
        self.assertEqual(302, response.status_code)

        emails = Email.query(Email.user_id == "123456",
                             Email.status == False).fetch()
        # 1 unsent email found
        self.assertEqual(1, len(emails))
        email = emails[0]
        self.assertEqual(False, email.status)
        # check the email fields are the same in the request
        self.assertEqual("unit test", email.sender)
        self.assertEqual("cosql@github.com", email.sender_email)
        self.assertEqual("test@example.com", email.recipient)
        self.assertEqual("saving unit test", email.subject)
        self.assertEqual("unit test text", email.text)

        params = { "email_id" : email.msg_id}
        # request to edit the email we just saved
        response = testapp.get('/compose', params)

        self.assertEqual(200, response.status_code)
        # the field should be filled by compose handler, i.e., email text
        self.assertNotEqual(-1, response.body.find('value="unit test text"'))

        email.key.delete()

    def testComposeHandlerSend(self):
        # request home page
        testapp = webtest.TestApp(self.composeApp)
        # no email for now
        self.assertEqual(0, len(Email.query(Email.user_id == "123456").fetch()))
        params = { "action" : "send",
                   "sender_name" : "unit test",
                   "sender_email" : "cosql@github.com",
                   "recipient" : "test@example.com",
                   "subject" : "sending unit test",
                   "text" : "unit test text",
                 }
        response = testapp.post('/compose', params)
        # check the status code, result page is returned
        self.assertEqual(200, response.status_code)

        emails = Email.query(Email.user_id == "123456",
                             Email.status == True).fetch()
        # 1 sent email found
        self.assertEqual(1, len(emails))
        email = emails[0]
        self.assertEqual(True, email.status)
        # check the email fields are the same in the request
        self.assertEqual("unit test", email.sender)
        self.assertEqual("cosql@github.com", email.sender_email)
        self.assertEqual("test@example.com", email.recipient)
        self.assertEqual("sending unit test", email.subject)
        self.assertEqual("unit test text", email.text)

        email.key.delete()

    def testDeleteHandler(self):
        # save an email first, then delete it by requesting DeleteHandler
        testapp = webtest.TestApp(self.composeApp)
        # no email for now
        self.assertEqual(0, len(Email.query(Email.user_id == "123456").fetch()))
        params = { "action" : "save",
                   "sender_name" : "unit test",
                   "sender_email" : "cosql@github.com",
                   "recipient" : "test@example.com",
                   "subject" : "saving unit test",
                   "text" : "unit test text",
                 }
        response = testapp.post('/compose', params)
        # check the status code, redirect to home
        self.assertEqual(302, response.status_code)

        testapp = webtest.TestApp(self.deleteApp)
        emails = Email.query(Email.user_id == "123456",
                             Email.status == False).fetch()
        # 1 unsent email found
        self.assertEqual(1, len(emails))
        email = emails[0]
        self.assertEqual(False, email.status)

        params = { "email_id" : email.msg_id}
        # delete the email using DeleteHandler
        response = testapp.post('/delete', params)

        self.assertEqual(200, response.status_code)
        # email is deleted by DeleteHandler
        self.assertEqual(0, len(Email.query(Email.user_id == "123456").fetch()))

    def testOutboxHandler(self):
        # save an email first, then send another one
        testapp = webtest.TestApp(self.composeApp)
        # no email for now
        self.assertEqual(0, len(Email.query(Email.user_id == "123456").fetch()))
        params = { "action" : "save",
                   "sender_name" : "unit test",
                   "sender_email" : "cosql@github.com",
                   "recipient" : "test@example.com",
                   "subject" : "saving unit test",
                   "text" : "unit test text",
                 }
        response = testapp.post('/compose', params)
        # check the status code, redirect to home
        self.assertEqual(302, response.status_code)
        # get the unsent email id in data store
        unsentEmailID = Email.query(Email.user_id == "123456",
                                    Email.status == False).fetch()[0].msg_id

        params = { "action" : "send",
                   "sender_name" : "unit test",
                   "sender_email" : "cosql@github.com",
                   "recipient" : "test@example.com",
                   "subject" : "sending unit test",
                   "text" : "unit test text",
                 }
        response = testapp.post('/compose', params)
        # check the status code, showing result page
        self.assertEqual(200, response.status_code)
        # get the sent email id in data store
        sentEmailID = Email.query(Email.user_id == "123456",
                                  Email.status == True).fetch()[0].msg_id

        testapp = webtest.TestApp(self.outboxApp)
        emails = Email.query(Email.user_id == "123456").fetch()
        # 2 emails found
        self.assertEqual(2, len(emails))

        # request the default outbox page
        response = testapp.get('/outbox')
        self.assertEqual(200, response.status_code)
        # should contain two emails in the result html
        self.assertEqual(2, len(re.findall("tr email_id =", response.body)))
        self.assertNotEqual(-1, response.body.find(unsentEmailID))
        self.assertNotEqual(-1, response.body.find(sentEmailID))

        # request drafts page
        params = { "target" : "unsent"}
        response = testapp.get('/outbox', params)
        self.assertEqual(200, response.status_code)
        # should see two emails in the result html
        self.assertEqual(1, len(re.findall("tr email_id =", response.body)))
        self.assertNotEqual(-1, response.body.find(unsentEmailID))

        # search by keyword
        params = { "keyword" : "sending unit test"}
        response = testapp.get('/outbox', params)
        self.assertEqual(200, response.status_code)
        # should see two emails in the result html
        self.assertEqual(1, len(re.findall("tr email_id =", response.body)))
        self.assertNotEqual(-1, response.body.find(sentEmailID))

        # delete all emails in data store at the end of the test
        for email in Email.query(Email.user_id == "123456").fetch():
            email.key.delete()

if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestEmailClient))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestDataStore))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestApp))

    unittest.TextTestRunner(verbosity=2).run(suite)
