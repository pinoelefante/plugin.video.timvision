import sys
from resources.lib.KodiHelper import KodiHelper
from resources.lib.Navigation import Navigation

plugin_dir = sys.argv[0]
plugin_handle = int(sys.argv[1])

kodi_helper = KodiHelper(
    plugin_handle=plugin_handle,
    base_url=plugin_dir
)

navigation = Navigation(
    handle=plugin_handle,
    plugin=plugin_dir,
    kodi_helper=kodi_helper
)

if __name__ == '__main__':
    navigation.router(parameters=sys.argv[2])
