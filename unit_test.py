#!/usr/bin/env python
# -*- coding: utf-8 -*-

# fix gae library path first
import sys
sys.path.insert(0, '/usr/local/google_appengine')
import dev_appserver
dev_appserver.fix_sys_path()

import unittest

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

from email_client import EmailRequest
from mailgun_client import mailgun_client
from mandrill_client import mandrill_client
from main import Email

class TestEmailClient(unittest.TestCase):
    ''' test class for email client'''
    def test_validEmailAddress(self):
        request = EmailRequest('test@example.com')
        ret, reason = request.validate()
        self.assertTrue(ret)

    def test_badEmailAddress(self):
        request = EmailRequest('badFormat')
        ret, reason = request.validate()
        self.assertFalse(ret)

    def test_validEmailSubject(self):
        request = EmailRequest('test@example.com', subject='subject')
        ret, reason = request.validate()
        self.assertTrue(ret)

    def test_badEmailSubject(self):
        long_subject = 'a' * 501
        request = EmailRequest('test@example.com', subject=long_subject)
        ret, reason = request.validate()
        self.assertFalse(ret)

    def test_mailgunClient(self):
        request = EmailRequest('test@example.com', subject='mailgun',
                               sender_email='cosql@github.com', text="test")
        cl = mailgun_client(
            api_key='key-c57536663caee62c3a30f367562b19c7',
            sandbox='sandboxc90288b9f29f4d4997fb800e74d89111.mailgun.org')
        ret = cl.send_email(request)
        self.assertTrue(ret)

    def test_mandrillClient(self):
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

if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestEmailClient))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestDataStore))

    unittest.TextTestRunner(verbosity=2).run(suite)
