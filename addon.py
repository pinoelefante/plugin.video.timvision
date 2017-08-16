import sys
from TimVisionAPI import TimVisionSession

plugin_handle = int(sys.argv[1])
usernameTest = ""
passwordTest = ""
tim = TimVisionSession(plugin_handle)
if tim.setup() and tim.login(usernameTest, passwordTest):

    pass
