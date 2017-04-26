# -*- coding: utf-8 -*-
from unittest import TestCase
import logging
from foolscrate.notify import EmailNotify
from smtplib import SMTP, SMTP_SSL
import sys

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

class TestEmailNotify(TestCase):
    def test_with_aws(self):
        s = SMTP_SSL("email-smtp.us-east-1.amazonaws.com", 465)
        s.login("AKIAJULZBAVR4FYM3MYA", "AhEH4DUwhDmyHVw/Gs0T2y10ECSnrcZ2jgyRI390D2Mr")
        send = EmailNotify(s, "machines@franzoni.eu")
        send.notify("alan.franzoni@gmail.com", "oggetto notifica", "testo notifica")
