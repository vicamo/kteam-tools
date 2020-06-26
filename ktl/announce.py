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
        if local:
            self.mq = MsgQueueService(service='kernel-announce', host='localhost', port=9123, exchange='announce-todo', heartbeat_interval=60)
        else:
            self.mq = MsgQueueService(service='kernel-announce', exchange='announce-todo', heartbeat_interval=60)

    def send(self, key, subject=None, body=None, summary=None):
        if subject == None and summary == None:
            raise ValueError("subject or summary required")

        payload = {'key': key}
        if subject is not None:
            payload['subject'] = subject
        if body is not None:
            payload['body'] = body
        if summary is not None:
            payload['summary'] = summary

        self.mq.publish('announce', payload)
