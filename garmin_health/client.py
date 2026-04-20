import logging
import os
from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectTooManyRequestsError

logger = logging.getLogger(__name__)
TOKENSTORE_PATH = os.path.expanduser("~/.garmin_health_tokens")


class GarminHealthClient:
    def __init__(self, email: str, password: str):
        self._client = self._authenticate(email, password)

    def _authenticate(self, email: str, password: str) -> Garmin:
        if os.path.exists(TOKENSTORE_PATH):
            try:
                with open(TOKENSTORE_PATH) as f:
                    tokens = f.read()
                client = Garmin(email, password)
                client.garth.loads(tokens)
                client.login()
                self._save_tokens(client)
                logger.debug("Authenticated with cached tokens")
                return client
            except Exception:
                logger.debug("Cached tokens invalid, re-authenticating")

        client = Garmin(email, password)
        try:
            client.login()
        except GarminConnectAuthenticationError as e:
            raise SystemExit(f"Garmin auth failed: {e}\nCheck GARMIN_EMAIL and GARMIN_PASSWORD")
        self._save_tokens(client)
        return client

    def _save_tokens(self, client: Garmin):
        try:
            with open(TOKENSTORE_PATH, "w") as f:
                f.write(client.garth.dumps())
            os.chmod(TOKENSTORE_PATH, 0o600)
        except Exception as e:
            logger.debug(f"Could not save tokens: {e}")

    def get_sleep_data(self, date_str: str) -> dict:
        return self._call(self._client.get_sleep_data, date_str)

    def get_hrv_data(self, date_str: str) -> dict:
        return self._call(self._client.get_hrv_data, date_str)

    def get_rhr(self, date_str: str) -> dict:
        return self._call(self._client.get_rhr_day, date_str)

    def get_stats(self, date_str: str) -> dict:
        return self._call(self._client.get_stats, date_str)

    def get_activities(self, limit: int = 14) -> list:
        result = self._call(self._client.get_activities, 0, limit)
        return result if isinstance(result, list) else []

    def _call(self, method, *args):
        try:
            result = method(*args)
            return result if result is not None else {}
        except GarminConnectTooManyRequestsError:
            logger.warning("Rate limited by Garmin API")
            return {}
        except Exception as e:
            logger.debug(f"{method.__name__}: {e}")
            return {}
