"""Constants for spaceapi_endpoint_client."""

from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "spaceapi_endpoint_client"
ATTRIBUTION = "Data provided by SpaceAPI"
CONF_HOST = "host"
CONF_API_KEY = "api_key"

SCAN_INTERVAL = timedelta(minutes=1)

# Window we wait between POSTing a state change and re-polling, so the
# SpaceAPI server has time to commit the write before our refresh reads it.
API_SETTLE_DELAY = 0.5
