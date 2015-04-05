#!/usr/bin/env python
# -*- coding: utf-8 -*-

# fix gae library path first
import sys
sys.path.insert(0, '/usr/local/google_appengine')
import dev_appserver
dev_appserver.fix_sys_path()

import unittest

sys.path.insert(0, '/usr/local/google_appengine/lib')
sys.path.insert(0, '/usr/local/google_appengine/lib/webapp2-2.5.2')

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

from email_client import EmailRequest
from mailgun_client import mailgun_client
from mandrill_client import mandrill_client
import main

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
        email = main.Email()
        email.put()

        # request 2, we should only get 1
        self.assertEqual(1, len(main.Email.query().fetch(2)))

        # delete email, Email data store is empty now
        email.key.delete()
        self.assertEqual(0, len(main.Email.query().fetch(2)))

    def testEntityMemcache(self):
        email = main.Email()
        memcache.add("test", email)

        emailCache = memcache.get("test")
        self.assertNotEqual(emailCache, None)
        self.assertNotEqual(id(emailCache), id(email))

        memcache.delete("test")
        emailCache = memcache.get("test")
        self.assertEqual(emailCache, None)

if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestEmailClient))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestDataStore))

    unittest.TextTestRunner(verbosity=2).run(suite)
