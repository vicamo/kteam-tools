from lpltk.LaunchpadService             import LaunchpadService

# Launchpad
#
class Launchpad():
    '''
    A utility class for collecting together the basic launchpad objects that are used throughout
    the application.
    '''
    # __init__
    #
    def __init__(s, staging=False, client='kernel-team-sru-workflow-manager'):
        s._staging = staging
        defaults = {}
        defaults['launchpad_client_name'] = client
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
