import sys
from resources.lib.Navigation import Navigation

PLUGIN_DIR = sys.argv[0]
PLUGIN_HANDLE = int(sys.argv[1])

NAVIGATION = Navigation(handle=PLUGIN_HANDLE, plugin=PLUGIN_DIR)

if __name__ == '__main__':
    NAVIGATION.router(parameters=sys.argv[2])
