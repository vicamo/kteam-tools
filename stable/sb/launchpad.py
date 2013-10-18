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
    def __init__(s, staging):
        defaults = {}
        defaults['launchpad_client_name'] = 'kernel-team-sru-workflow-manager'
        s.production_service = LaunchpadService(defaults)  # Some things are only available on the production
                                                        # service.
        if staging:
            defaults['launchpad_services_root'] = 'qastaging'
        s.default_service = LaunchpadService(defaults)

