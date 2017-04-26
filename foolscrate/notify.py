# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
import smtplib

from email.mime.text import MIMEText


class Notify(ABC):
    @abstractmethod
    def notify(self, addressee, subject, text):
        pass


class EmailNotify(Notify):
    def __init__(self, smtp, sender):
        self._sender = sender
        self._smtp = smtp

    def notify(self, addressee, subject, text):
        msg = MIMEText(text, _charset="utf-8")

        msg['Subject'] = subject
        msg['From'] = self._sender
        msg['To'] = addressee


        self._smtp.sendmail(self._sender, [addressee], msg.as_bytes())
        self._smtp.quit()