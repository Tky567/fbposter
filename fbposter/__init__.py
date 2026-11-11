# thuần HTTPS Facebook client — curl_cffi only, không browser.
from .client import FBClient, FBError
from .spec import DOC_IDS

__all__ = ("DOC_IDS", "FBClient", "FBError")
__version__ = "1.0.0"
