"""Constants for VirtuHome Pro."""

DOMAIN = "virtuhome_pro"
# VirtuHome, whose extension sources this integration's frontend module registers with
CORE_DOMAIN = "virtuhome"
# the first VirtuHome with extension sources and no licence code of its own
CORE_MIN_VERSION = "0.18.0"

# this integration's frontend module, loaded on every page; the version query busts browser caches
URL_BASE = "/virtuhome_pro_static"
MODULE_FILE = "virtuhome-pro.js"

STORAGE_VERSION = 1

# extensions: unlocked by a licence key, downloaded from the licence server, served from here
EXT_URL_BASE = "/virtuhome_ext"
# the store VirtuHome kept the licence in up to 0.17, so keys and trials from then carry on
LICENCE_KEY_STORE = "virtuhome.licence"
DEFAULT_LICENCE_SERVER = "https://license.virtumaps.com"
# the first address: tried when the other can't be reached, and what older installs have stored
OLD_LICENCE_SERVER = "https://virtuhome-license.virtumaps.workers.dev"
CONF_LICENCE_SERVER = "licence_server"
