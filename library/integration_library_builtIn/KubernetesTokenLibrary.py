import os
import threading

from robot.api import logger

# Audience is used for m2m communication between microservices in the same namespace
AUDIENCE_NETCRACKER = "netcracker"
# Audience is used for sending requests to DBaaS infra service
AUDIENCE_DBAAS = "dbaas"
# Audience is used for sending requests to MaaS infra service
AUDIENCE_MAAS = "maas"

# Default directory of Kubernetes tokens with custom audience
DEFAULT_AUDIENCE_TOKENS_DIR = "/var/run/secrets/tokens"
# Default Kubernetes service account directory
DEFAULT_SERVICE_ACCOUNT_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"


class KubernetesTokenLibrary(object):
    """
    Kubernetes token library for Robot Framework.
    Provides Kubernetes service account token and tokens with custom audience for services interaction.
    Tokens are read from projected volume files located at `/var/run/secrets/tokens/<audience>/token`,
    the default service account token is read from `/var/run/secrets/kubernetes.io/serviceaccount/token`.
    The library is a singleton, so Robot Framework imports and Python libraries share the same tokens cache.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._token_source = TokenSource()
                cls._instance = instance
            return cls._instance

    def get_audience_token(self, audience):
        """
        Returns Kubernetes token with the given audience.
        *Args:*\n
            _audience_ - token audience, for example `netcracker`, `dbaas` or `maas`;\n
        *Returns:*\n
            str - token
        *Example:*\n
            | Get Audience Token | dbaas |
        """
        return self._token_source.get_audience_token(audience)

    def get_service_account_token(self):
        """
        Returns default Kubernetes service account token.
        *Returns:*\n
            str - token
        *Example:*\n
            | Get Service Account Token |
        """
        return self._token_source.get_service_account_token()

    def get_audience_token_headers(self, audience):
        """
        Returns HTTP headers with bearer authorization by Kubernetes token with the given audience.
        *Args:*\n
            _audience_ - token audience, for example `netcracker`, `dbaas` or `maas`;\n
        *Returns:*\n
            dict - HTTP headers
        *Example:*\n
            | Get Audience Token Headers | maas |
        """
        return {"Authorization": f"Bearer {self.get_audience_token(audience)}"}


class TokenSource(object):
    """
    Reads Kubernetes projected volume tokens. Kubernetes rotates tokens by switching the `..data` symlink
    to a new directory, so the token is re-read only when the file behind the token path changes.
    """

    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get_audience_token(self, audience):
        if not audience:
            raise ValueError("audience is empty")
        if not os.path.isdir(DEFAULT_AUDIENCE_TOKENS_DIR):
            raise RuntimeError(f"audience tokens dir {DEFAULT_AUDIENCE_TOKENS_DIR} does not exist")
        token_path = os.path.join(DEFAULT_AUDIENCE_TOKENS_DIR, audience, "token")
        if not os.path.isfile(token_path):
            raise RuntimeError(f"token with audience {audience} was not found")
        try:
            return self._read_token(token_path)
        except OSError as e:
            raise RuntimeError(f"failed to get token by audience: {audience}: {e}") from e

    def get_service_account_token(self):
        token_path = os.path.join(DEFAULT_SERVICE_ACCOUNT_DIR, "token")
        try:
            return self._read_token(token_path)
        except OSError as e:
            raise RuntimeError(f"failed to get default kubernetes service account token: {e}") from e

    def _read_token(self, token_path):
        # the symlinked path is opened directly, so the file can't be removed by rotation between check and read
        with self._lock, open(token_path, "r") as f:
            stat = os.fstat(f.fileno())
            version = (stat.st_dev, stat.st_ino, stat.st_mtime_ns, stat.st_size)
            cached = self._cache.get(token_path)
            if cached and cached[0] == version:
                return cached[1]
            token = f.read().strip()
            self._cache[token_path] = (version, token)
        logger.debug(f"k8s token at path {token_path} refreshed")
        return token
