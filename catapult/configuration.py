from collections import OrderedDict
import os
from pathlib import Path
import stat
import toml
from typing import Tuple

class Configuration:
    """
    Configuration singleton object; holds configurations of the application.
    """

    CATAPULT_HOME = Path(os.getenv("CATAPULT_HOME", Path.home() / ".catapult"))
    CATAPULT_CONFIG_FILE = CATAPULT_HOME / "catapult.toml"
    CATAPULT_CACHE_DB = CATAPULT_HOME / "cache.db"

    # application-specific config
    lrr_host: str = None
    lrr_api_key: str = None

    # upload folder-specific config
    multi_upload_folder_dir: str = None

    # nhentai archivist-specific config
    nhentai_archivist_db: str = None
    nhentai_archivist_folders: str = None

    # pixivutil2-specific config
    pixivutil2_db: str = None
    pixivutil2_folders: str = None

    def __init__(self):
        """
        Initialize configuration singleton.
        """
        self.CATAPULT_HOME.mkdir(parents=True, exist_ok=True)

        # load default file configuration.
        if self.CATAPULT_CONFIG_FILE.exists():
            with open(self.CATAPULT_CONFIG_FILE, 'r') as reader:
                curr_configuration = toml.load(reader)

                try:
                    self.lrr_host = curr_configuration['default']['lrr_host']
                except KeyError:
                    self.lrr_host = ""
                try:
                    self.lrr_api_key = curr_configuration['default']['lrr_api_key']
                except KeyError:
                    self.lrr_api_key = ""

        # load environment variable configuration.
        self.lrr_host = os.getenv('LRR_HOST', self.lrr_host)
        self.lrr_api_key = os.getenv('LRR_API_KEY', self.lrr_api_key)

        self.multi_upload_folder_dir = os.getenv('MULTI_UPLOAD_FOLDER', self.multi_upload_folder_dir)

        self.nhentai_archivist_db = os.getenv('NHENTAI_ARCHIVIST_DB', self.nhentai_archivist_db)
        self.nhentai_archivist_folders = os.getenv('NHENTAI_ARCHIVIST_FOLDER', self.nhentai_archivist_folders)

        self.pixivutil2_db = os.getenv('PIXIVUTIL2_DB', self.pixivutil2_db)
        self.pixivutil2_folders = os.getenv('PIXIVUTIL2_FOLDER', self.pixivutil2_folders)

    def save(self):
        """
        Save configuration to file.
        """
        configuration = OrderedDict([
            ('default', OrderedDict([
                ('lrr_host', self.lrr_host),
                ('lrr_api_key', self.lrr_api_key),
            ]))
        ])
        with open(self.CATAPULT_CONFIG_FILE, 'w') as writer:
            toml.dump(configuration, writer)
        self.CATAPULT_CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)

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
