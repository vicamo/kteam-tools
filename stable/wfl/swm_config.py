#
# swm_config -- expose the kernel-series swm_data
#
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

        cleave(self.__class__.__name__ + '.__init__')

    @property
    def gcp_nvidia_packages(self):
        return self._data.get('gcp-nvidia-packages', False)
