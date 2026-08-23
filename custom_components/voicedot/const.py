"""Constants for the VoiceDot integration."""

DOMAIN = "voicedot"

CONF_HOST = "host"

DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 10

# Endpoints exposed by the firmware.
API_STATUS = "/api/status"
API_CONFIG = "/api/config"
API_RUNTIME = "/api/runtime"
API_ANNOUNCE = "/api/announce"
API_VOLUME = "/api/volume"
API_ACK_TEST = "/api/ack/test"
API_ACK_BUILD = "/api/ack/build"
API_WAKE = "/api/assist/wake"
API_SPEAKER_TEST = "/api/audio/speaker-test"
API_REBOOT = "/api/system/reboot"

SERVICE_ANNOUNCE = "announce"
ATTR_TEXT = "text"
