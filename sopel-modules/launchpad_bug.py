import sopel.module
import re
from launchpadlib.launchpad         import Launchpad

# process_matches
#
def process_matches(bot, matches):
    lp = Launchpad.login_anonymously('happy', 'production')
    for g in matches:
        for bug_id in g:
            if bug_id != '':
                try:
                    lp_bug = lp.bugs[bug_id]
                    text = '"%s"     https://launchpad.net/bugs/%s' % (lp_bug.title, bug_id)
                    bot.say(text)
                except:
                    # This must be a private bug
                    #
                    text = "LP: #%s may be private (I can't find it in LP)." % bug_id
                    bot.say(text)

@sopel.module.rule('.*(?i)(?:bugs?[ /]#?([0-9]+)|(?:^|\W)#([0-9]{5,})).*')
def rule1(bot, trigger):
    m = re.findall('(?i)(?:bugs?[ /]#?([0-9]+)|(?:^|\W)#([0-9]{5,}))', trigger)
    process_matches(bot, m)
