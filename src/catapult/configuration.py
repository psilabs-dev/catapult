from collections import OrderedDict
import os
from pathlib import Path
import stat
import toml
from typing import Tuple

from catapult.constants import CATAPULT_CONFIG_FILE, CATAPULT_HOME

class Configuration:
    """
    Configuration singleton object; holds configurations of the application.
    """

    # application-specific config
    lrr_host: str = None
    lrr_api_key: str = None

    # upload folder-specific config
    upload_folder: str = None

    # nhentai archivist-specific config
    nhentai_archivist_db: str = None
    nhentai_archivist_content_folder: str = None

    def __init__(self):
        """
        Initialize configuration singleton.
        """
        # load default file configuration.
        if CATAPULT_CONFIG_FILE.exists():
            with open(CATAPULT_CONFIG_FILE, 'r') as reader:
                curr_configuration = toml.load(reader)
                self.lrr_host = curr_configuration['default']['lrr_host']
                self.lrr_api_key = curr_configuration['default']['lrr_api_key']

        # load environment variable configuration.
        self.lrr_host = os.getenv('LRR_HOST', self.lrr_host)
        self.lrr_api_key = os.getenv('LRR_API_KEY', self.lrr_api_key)
    
        self.upload_folder = os.getenv('UPLOAD_FOLDER', self.upload_folder)

        self.nhentai_archivist_db = os.getenv('NHENTAI_ARCHIVIST_DB', self.nhentai_archivist_db)
        self.nhentai_archivist_content_folder = os.getenv('NHENTAI_ARCHIVIST_CONTENTS', self.nhentai_archivist_content_folder)

    def save(self):
        """
        Save configuration to file.
        """
        CATAPULT_HOME.mkdir(parents=True, exist_ok=True)
        configuration = OrderedDict([
            ('default', OrderedDict([
                ('lrr_host', self.lrr_host),
                ('lrr_api_key', self.lrr_api_key),
            ]))
        ])
        with open(CATAPULT_CONFIG_FILE, 'w') as writer:
            toml.dump(configuration, writer)
        CATAPULT_CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def is_valid(self) -> Tuple[bool, str]:
        """
        Validate configurations.
        """
        if not self.lrr_host:
            return False, "No LRR host!"
        if not self.lrr_host.startswith('http://') and not self.lrr_host.startswith('https://'):
            return False, f"URL {self.lrr_host} does not include protocol!"
        return True, "success"

config = Configuration()
