import os

from lpltk.LaunchpadService import LaunchpadService

try:
    from launchpadlib.credentials import AuthorizeRequestTokenWithURL
except ImportError:
    from .launchpad_compat import AuthorizeRequestTokenWithURL
from .launchpad_cache import LaunchpadCache


# Launchpad
#
class Launchpad():
    '''
    A utility class for collecting together the basic launchpad objects that are used throughout
    the application.
    '''
    # __init__
    #
    def __init__(s, staging=False):
        s._staging = staging
        defaults = {}
        defaults['launchpad_client_name'] = 'kernel-team-sru-workflow-manager'
        s.production_service = LaunchpadService(defaults)  # Some things are only available on the production
                                                           # service.
        if staging:
            defaults['launchpad_services_root'] = 'qastaging'
        s.default_service = LaunchpadService(defaults)

    # bug_url
    #
    def bug_url(s, bug_id):
        '''
        Helper routine to return the correct URL for the specified bug. Takes use
        of the qastaging service into account.
        '''
        if s._staging:
            lpserver = 'bugs.qastaging.launchpad.net'
        else:
            lpserver = 'bugs.launchpad.net'
        retval = 'https://%s/bugs/%s' % (lpserver, bug_id)
        return retval


class LaunchpadDirect:

    @classmethod
    def login(cld, client_name='kernel-team-sru-workflow-manager'):
        creds = os.path.expanduser(os.path.join('~/.config', client_name, 'credentials-production'))
        return LaunchpadCache.login_with(client_name, 'production', version='devel',
            credentials_file=creds)

    @classmethod
    def login_application(cld, application, service_root='production'):
        cred_file = os.path.join(os.path.expanduser("~/.config"), application, "credentials-" + service_root)
        authorization_engine = AuthorizeRequestTokenWithURL(service_root=service_root, consumer_name=application)
        return LaunchpadCache.login_with(service_root=service_root, version='devel',
            authorization_engine=authorization_engine, credentials_file=cred_file)
