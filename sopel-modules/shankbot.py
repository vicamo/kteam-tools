from sys                                import stdout
from subprocess                         import Popen, PIPE, STDOUT
from threading                          import Thread
from time                               import sleep

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

import sopel.module

# enqueue_output
#
def enqueue_output(out, queue, quiet=False):
    for line in iter(out.readline, b''):
        queue.put(line)
        if not quiet:
            stdout.write(line)
            stdout.flush()
    out.close()

# sh
#
def sh(cmd, timeout=None, ignore_result=False, quiet=False):
    out = []
    p = Popen(cmd, stdout=PIPE, stderr=STDOUT, bufsize=1, shell=True)
    q = Queue()
    t = Thread(target=enqueue_output, args=(p.stdout, q, quiet))
    t.daemon = True # thread dies with the program
    t.start()

    if timeout is not None:
        t.join(timeout)
        if t.is_alive():
            p.terminate()
            raise ShellTimeoutError(cmd, timeout)

    while p.poll() is None:
        # read line without blocking
        try:
            line = q.get_nowait()
        except Empty:
            pass
        else: # got line
            out.append(line)
        sleep(1)

    while True:
        try:
            line = q.get_nowait()
        except Empty:
            break
        else: # got line
            out.append(line)

    return p.returncode, out

@sopel.module.nickname_commands('shank')
def shank_all(bot, trigger):
    '''
    When a user asks the bot to 'shank' or 'shank <bugid>' run the swm utility against the
    indicated bug(s).
    '''
    what = trigger.match.groups()[1]
    if what is None:
        # No bugs were specified so shank them all.
        #
        bot.say(trigger.nick + ', gimme some love boss')
        cmd = '/home/work/kteam-tools/stable/swm --logfile=/dev/null'
        (rc, output) = sh(cmd, quiet=True)
        if rc == 0:
            bot.say(trigger.nick + ', ' + 'I shanked them all')
        elif rc == 254:
            cmd = 'pastebinit -f python /tmp/exceptions.log'
            (rc, output) = sh(cmd, quiet=True)
            bot.say(trigger.nick + ', ' + 'That didn\'t go very well: ' + output[0].strip())
    else:
        # A list of bugs were specified on the command line. Shank each of them
        # in order.
        #
        bot.say(trigger.nick + ', roger, roger')
        for bug in what.split():
            if not bug.isdigit():
                bot.say(trigger.nick + ', ' + '%s is not a vaid bug id' % bug)
                continue
            cmd = '/home/work/kteam-tools/stable/swm %s --logfile=/dev/null' % bug
            (rc, output) = sh(cmd, quiet=True)
            if rc == 0:
                bot.say(trigger.nick + ', ' + 'bug %s has been shanked' % bug)
            elif rc == 254:
                cmd = 'pastebinit -f python /tmp/exceptions.log'
                (rc, output) = sh(cmd, quiet=True)
                bot.say(trigger.nick + ', ' + 'That didn\'t go very well: ' + output[0].strip())

# vi:set ts=4 sw=4 expandtab syntax=python:
