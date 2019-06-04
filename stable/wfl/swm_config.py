#
# swm_config -- expose the kernel-series swm_data
#
from datetime                   import datetime
import yaml

from wfl.errors                 import ShankError
from wfl.log                    import center, cleave, cinfo

# SwmConfigError
#
class SwmConfigError(ShankError):
    """
    Thrown when something goes wrong with the GCP bucket.
    """
    pass


# SwmConfig
#
class SwmConfig:
    """
    A helper class to handle SWM configuration data from kernel-series.
    """

    # __init__
    #
    def __init__(self, data):
        """
        :param data: swm raw data
        """
        center(self.__class__.__name__ + '.__init__')

        if isinstance(data, str):
            data = yaml.safe_load(data)
        if data == None:
            data = {}
        self._data = data

        # Parse and validate the deployment-blackout.
        self._blackouts = []
        blackout_list = self._data.get('deployment-blackout')
        if blackout_list is None:
            blackout_list = []
        for blackout in blackout_list:
            if len(blackout) != 2:
                raise SwmConfigError("bad blackout entry -- start and end dates required")
            try:
                start = datetime.strptime(blackout[0], '%Y-%m-%d %H:%M')
            except ValueError:
                raise SwmConfigError("bad blackout entry -- invalid start date")
            try:
                end = datetime.strptime(blackout[1], '%Y-%m-%d %H:%M')
            except ValueError:
                raise SwmConfigError("bad blackout entry -- invalid end date")
            self._blackouts.append([start, end])

        cleave(self.__class__.__name__ + '.__init__')

    @property
    def gke_nvidia_packages(self):
        return self._data.get('gke-nvidia-packages', None)

    def in_blackout(self, when):
        for blackout in self._blackouts:
            if when >= blackout[0] and when < blackout[1]:
                return True
        return False
