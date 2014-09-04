#!/usr/bin/env python
#

# The named pipe used for getting messages to shankbot, the irc bot.
#
shank_pipe_path = "/tmp/shank.pipe"

def send_to_shankbot(msg):
    with open(shank_pipe_path, 'w') as shank_pipe:
        shank_pipe.write(msg)


if __name__ == "__main__":
    import sys
    send_to_shankbot(' '.join(sys.argv[1:]) + '\n')

# vi:set ts=4 sw=4 expandtab:
