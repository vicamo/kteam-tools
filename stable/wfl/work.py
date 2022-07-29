#!/usr/bin/python3

import sys
import os
import json
import uuid

from ktl.msgq import MsgQueueService, MsgQueueCredentials

from wfl.secrets import Secrets


class SwmWork:
    def __init__(self, local=False, config=None):
        if config is None:
            raise ValueError("config required")

        self.secrets = Secrets(os.path.expanduser(config))

        # Pass in credentials if we have them, else use the limited defaults.
        hostname = self.secrets.get('amqp-hostname')
        username = self.secrets.get('amqp-username')
        password = self.secrets.get('amqp-password')
        credentials = None
        if username is not None and password is not None:
            credentials = MsgQueueCredentials(username, password)

        self.mq = MsgQueueService(service="swm", local=local, host=hostname, credentials=credentials, exchange="swm", heartbeat=60)

    def send_admin_quit(self, name, priority=None):
        if priority is None:
            priority = 6
        payload = {"type": "quit"}
        key = "direct.{}.swm.{}".format(name, payload["type"])
        self.mq.publish(key, payload, priority=priority)

    def send_shank(self, tracker, scanned=None, priority=None):
        if priority is None:
            priority = 4
        payload = {
            "type": "shank",
            "tracker": tracker,
            "scanned": str(scanned),
            "id": uuid.uuid4().hex,
        }
        key = "swm.{}".format(payload["type"])
        self.mq.publish(key, payload, priority=priority)

    def send_dependants(self, priority=None):
        if priority is None:
            priority = 4
        payload = {"type": "dependants"}
        key = "swm.{}".format(payload["type"])
        self.mq.publish(key, payload, priority=priority)
