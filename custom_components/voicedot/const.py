"""Constants for the VoiceDot integration."""

DOMAIN = "voicedot"

# Where the firmware comes from, for the link on the update entity.
RELEASES_URL = "https://github.com/xCite1986/voicedot-waveshare/releases"

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
API_RADIO_PLAY = "/api/radio/play"
API_RADIO_STOP = "/api/radio/stop"
API_UPDATE_CHECK = "/api/update/check"
API_UPDATE_INSTALL = "/api/update/install"
API_ALARM = "/api/alarm"
API_TIMER = "/api/timer"
API_BRIEFING_TEST = "/api/alarm/briefing-test"

SERVICE_ANNOUNCE = "announce"
SERVICE_SET_ALARM = "set_alarm"
SERVICE_CLEAR_ALARM = "clear_alarm"
SERVICE_START_TIMER = "start_timer"
SERVICE_CLEAR_TIMER = "clear_timer"
SERVICE_SPEAK_BRIEFING = "speak_briefing"

SERVICES = (
    SERVICE_ANNOUNCE,
    SERVICE_SET_ALARM,
    SERVICE_CLEAR_ALARM,
    SERVICE_START_TIMER,
    SERVICE_CLEAR_TIMER,
    SERVICE_SPEAK_BRIEFING,
)

ATTR_TEXT = "text"
ATTR_TIME = "time"
ATTR_DAILY = "daily"
ATTR_DURATION = "duration"
