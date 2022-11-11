from jico_utils import JiCoUtils
import credentials
import webbrowser
import logging
from datetime import datetime

class gumc():

    def __init__(self) -> None:
        self.logging = logging
        logging.basicConfig(filename='gumc_{}'.format(datetime.now().strftime("%Y%m%d_%H%M%S")),
                            encoding='utf-8', format='%(asctime)s - %(levelname)s - %(message)s',
                            level=logging.DEBUG)
