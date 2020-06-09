import os
import json
try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, Request, HTTPError

from .msgq                           import MsgQueue
from .messaging                      import Email
from .cfg                            import Cfg


class Announce:

    def __init__(self, config=None):
        defaults = {}
        paths = []
        if 'HOME' in os.environ:
            paths.append(os.path.join(os.environ['HOME'], '.ktl-announce.yaml'))
        paths.append(os.path.join(os.path.dirname(__file__), 'announce.yaml'))
        for path in paths:
            if os.path.exists(path):
                defaults['configuration_file'] = path
                break

        if config == None:
            config = dict()
        self.cfg = Cfg.merge_options(defaults, config)

        self.routing = self.cfg.get('routing', {})

        self.mq = None

    def __message(self, key, message, lcfg):
        cfg = self.cfg.get('message', {})
        cfg.update(lcfg)

        if not self.mq:
            if self.cfg.get('local', False):
                self.mq = MsgQueue(address='localhost', port=9123)
            else:
                self.mq = MsgQueue()

        msg = {
            "key"            : "kernel.irc",
            "op"             : cfg['type'],
            "channel"        : cfg['channel'],
            "msg"            : message,
        }
        self.mq.publish(msg['key'], msg)

    def __email(self, key, subject, body, lcfg):
        cfg = self.cfg.get('email', {})
        cfg.update(lcfg)

        email = Email(smtp_server=cfg['smtp_server'], smtp_port=cfg['smtp_port'])
        email.send(cfg['from'], cfg['to'], subject, body)

    def __mattermost(self, key, summary, lcfg):
        cfg = self.cfg.get('mattermost', {})
        cfg.update(lcfg)

        url = cfg['hook']
        payload = {'text': summary}
        #if body != subject:
        #    payload['props'] = {'card': '```\n'+body+'```'}
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(payload).encode('ascii')

        req = Request(url, headers=headers, data=data)
        f = urlopen(req)
        f.close()

    def send(self, key, subject=None, body=None, summary=None):
        if subject == None and summary == None:
            raise ValueError("subject or summary required")

        if summary == None:
            summary = subject
        if body == None:
            body = subject

        routing = self.routing.get(key, [])
        for route in routing:
            if route.get('type') == 'email':
                self.__email(key, subject, body, route)
            elif route.get('type') in ('notice', 'message'):
                self.__message(key, summary, route)
            elif route.get('type') == 'mattermost':
                self.__mattermost(key, subject, body, route)
