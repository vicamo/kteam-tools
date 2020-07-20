import os
import json
try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, Request, HTTPError

from .msgq                           import MsgQueue, MsgQueueService
from .messaging                      import Email
from .cfg                            import Cfg


class Announce:

    def __init__(self, local=False):
        self.mq = MsgQueueService(service='announce', local=local, exchange='announce-todo')

    def deliver_to(self, payload):
        key = 'announce.' + payload['destination']['type']
        self.mq.publish(key, payload)

    def send(self, key, subject=None, body=None, summary=None):
        if subject == None and summary == None:
            raise ValueError("subject or summary required")

        destination = {'type': 'key', 'key': key}
        message = {}
        if subject is not None:
            message['subject'] = subject
        if body is not None:
            message['body'] = body
        if summary is not None:
            message['summary'] = summary

        payload = {'destination': destination, 'message': message}

        self.deliver_to(payload)
