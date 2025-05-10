import os

class ConfigPath:
    """
    Configuration class for PyJal.
    """

    def __init__(self):
        self.configRootPath = os.path.join(os.path.dirname(__file__), "ConfigFiles")
        self.nameconfigPath = os.path.join(self.configRootPath, "3DSMaxNamingConfig.json")
