#!/usr/bin/env python
#

from argparse                           import ArgumentParser, RawDescriptionHelpFormatter
from logging                            import basicConfig, INFO, DEBUG, info, warning
import os
import sys

from msgq                           import MsgQueue
from messaging                      import Email
from cfg                            import Cfg

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
            "op"             : "notice",
            "channel"        : cfg['channel'],
            "msg"            : message,
            "notice"         : True
        }
        self.mq.publish(msg['key'], msg)

    def __email(self, key, subject, body, lcfg):
        cfg = self.cfg.get('email', {})
        cfg.update(lcfg)
            
        email = Email(smtp_server=cfg['smtp_server'], smtp_port=cfg['smtp_port'])
        email.send(cfg['from'], cfg['to'], subject, body)

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
            elif route.get('type') == 'message':
                self.__message(key, summary, route)


if __name__ == '__main__':
    # Command line argument setup and initial processing
    #
    app_description = '''
    '''
    app_epilog = '''
examples:
    listen --help
    '''
    parser = ArgumentParser(description=app_description, epilog=app_epilog, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--debug', action='store_true', default=False, help='Print out a lot of messages about what is going on.')
    parser.add_argument('--local', action='store_true', default=False, help='Assume we have ssh tunnel setup to the MQ server.')
    parser.add_argument('routing', help='routing key')
    parser.add_argument('subject', help='subject for the message')
    parser.add_argument('body', help='body of the message')

    args = parser.parse_args()

    try:
        # If logging parameters were set on the command line, handle them
        # here.
        #
        log_format = "%(levelname)s - %(message)s"
        if args.debug:
            basicConfig(level=DEBUG, format=log_format)
        else:
            basicConfig(level=INFO, format=log_format)

        announce = Announce()

        announce.send(args.routing, args.subject, args.body)

    # Handle the user presses <ctrl-C>.
    #
    except KeyboardInterrupt:
        warning("Aborting ...")

    # vi:set ts=4 sw=4 expandtab:
