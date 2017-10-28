import sys
from resources.lib.Navigation import Navigation

plugin_dir = sys.argv[0]
plugin_handle = int(sys.argv[1])

navigation = Navigation(
    handle=plugin_handle,
    plugin=plugin_dir
)

if __name__ == '__main__':
    navigation.router(parameters=sys.argv[2])
