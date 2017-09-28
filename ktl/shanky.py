#!/usr/bin/env python
#

from ktl.msgq                           import MsgQueue

def send_to_shankbot(msg):
    mq = MsgQueue()

    msg = {
        "key"            : "kernel.irc",
        "op"             : "notice",
        "msg"            : msg,
        "notice"         : True,
    }
    return mq.publish(msg['key'], msg)

# vi:set ts=4 sw=4 expandtab:
