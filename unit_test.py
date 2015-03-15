import unittest

from email_client import EmailRequest
from mailgun_client import mailgun_client
from mandrill_client import mandrill_client

class TestEmailClient(unittest.TestCase):
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

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEmailClient)
    unittest.TextTestRunner(verbosity=2).run(suite)
