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

    def __message(self, key, subject, body):
        routing = self.routing.get(key)
        if not routing:
            return False

        cfg = self.cfg.get('message', {})
        lcfg = routing.get('message')
        if lcfg:
            cfg.update(lcfg)

        if not cfg.get('enable', False):
            return False
            
        if not self.mq:
            if self.cfg.get('local', False):
                self.mq = MsgQueue(address='localhost', port=9123)
            else:
                self.mq = MsgQueue()

        msg = {
            "key"            : "kernel.irc",
            "op"             : "notice",
            "msg"            : subject,
            "notice"         : True
        }
        self.mq.publish(msg['key'], msg)

        return True

    def __email(self, key, subject, body):
        routing = self.routing.get(key)
        if not routing or 'email' not in routing:
            return False

        cfg = self.cfg.get('email', {})
        lcfg = routing.get('email')
        if lcfg:
            cfg.update(lcfg)
            
        if not cfg.get('enable', False):
            return False
            
        email = Email(smtp_server=cfg['smtp_server'], smtp_port=cfg['smtp_port'])
        email.send(cfg['from'], cfg['to'], subject, body)

        return True

    def send(self, key, subject, body):
        self.__message(key, subject, body)
        self.__email(key, subject, body)


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
