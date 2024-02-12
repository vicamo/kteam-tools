#!/usr/bin/python3

import sys
import os
import json
import uuid

from ktl.msgq import MsgQueueService, MsgQueueCredentials

from wfl.secrets import Secrets


class SwmWorkCmds:
    _group = None

    def _publish(self, payload, priority=None):
        if priority is None:
            priority = 4
        key = "swm.{}".format(payload["type"])
        self.mq.publish(key, payload, priority=priority)

    def group_id(self, rotate=False):
        if self._group is None or rotate:
            self._group = uuid.uuid4().hex
        return self._group

    def send_admin_quit(self, name, priority=None):
        if priority is None:
            priority = 6
        payload = {"type": "quit"}
        self._publish(payload, priority)

    def send_shank(self, tracker, scanned=None, priority=None):
        payload = {
            "type": "shank",
            "tracker": tracker,
            "scanned": str(scanned),
            "id": uuid.uuid4().hex,
            "group": self.group_id(),
        }
        self._publish(payload, priority)

    def send_instantiate(self, tracker, scanned=None, priority=None):
        payload = {
            "type": "instantiate",
            "tracker": tracker,
            "id": uuid.uuid4().hex,
            "group": self.group_id(),
        }
        self._publish(payload, priority)

    def send_dependants(self, priority=None):
        payload = {"type": "dependants"}
        self._publish(payload, priority)

    def send_complete(self, payload, priority=None):
        payload["type"] += "-complete"
        self._publish(payload, priority)

    def send_barrier(self, priority=None):
        self.group_id(rotate=True)


class SwmWork(SwmWorkCmds):
    def __init__(self, local=False, config=None):
        if config is None:
            raise ValueError("config required")

        self.secrets = Secrets(os.path.expanduser(config))

        # Pass in credentials if we have them, else use the limited defaults.
        hostname = self.secrets.get("amqp-hostname")
        username = self.secrets.get("amqp-username")
        password = self.secrets.get("amqp-password")
        credentials = None
        if username is not None and password is not None:
            credentials = MsgQueueCredentials(username, password)

        self.mq = MsgQueueService(
            service="swm", local=local, host=hostname, credentials=credentials, exchange="swm", heartbeat=60
        )
