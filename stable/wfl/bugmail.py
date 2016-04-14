import os
from sys                                import argv
import yaml
from email.mime.text                    import MIMEText
from smtplib                            import SMTP
from .log                               import center, cleave, cdebug


# BugMailConfigFileMissing
#
class BugMailConfigFileMissing(Exception):
    '''
    '''
    # __init__
    #
    def __init__(s, msg):
        s.message = msg

    def __str__(s):
        return s.message


# A class for sending email
#
class BugMail:

    smtp_user = None
    smtp_password = None
    smtp_port = 587

    # load_config
    #
    @classmethod
    def load_config(c, cfg_file):
        if os.path.exists(cfg_file):
            with open(cfg_file, 'r') as f:
                cfg = yaml.safe_load(f)
        elif os.path.exists(os.path.join(os.path.dirname(argv[0]), cfg_file)):
            with open(os.path.join(os.path.dirname(argv[0]), cfg_file), 'r') as f:
                cfg = yaml.safe_load(f)
        else:
            msg = 'Unable to find the file (%s). This file is required for the SRU Workflow Manager to operate correctly.' % cfg_file
            raise BugMailConfigFileMissing(msg)

        for k in cfg:
            setattr(c, k, cfg[k])

    # send
    #
    @classmethod
    def send(c, subject, body):
        """
        Send email. Uses the smtp server info already initialized.
        """
        center(c.__class__.__name__ + '.send')

        cdebug('send_email: from=<%s>, to=<%s>, subject=<%s>, body=<%s>' % (c.from_address, c.to_address, subject, body))

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = c.from_address
        msg['To'] = c.to_address

        # If to_address contains multiple addresses, we must pass it as
        # a python list to sendemail
        #
        to_list = c.to_address.split(',')

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        #
        smtp = SMTP(c.smtp_server, c.smtp_port)
        smtp.ehlo()
        smtp.starttls()
        if c.smtp_user is not None and c.smtp_password is not None:
            smtp.login(c.smtp_user, c.smtp_password)
        smtp.sendmail(c.from_address, to_list, msg.as_string())
        smtp.quit()

        cleave(c.__class__.__name__ + '.send')
        return

# vi:set ts=4 sw=4 expandtab:
