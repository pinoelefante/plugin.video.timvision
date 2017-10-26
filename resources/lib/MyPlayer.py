import xbmc
import threading
from resources.lib import utils

class MyPlayer(xbmc.Player):
    current_contentId = None
    current_item = None
    current_time = 0
    total_time = 0

    listen = False
    playback_thread_stop_event = None

    def setItem(self, url, contentId):
        self.current_item = url
        self.current_contentId = contentId
        utils.log_on_desktop_file("Setting item ("+self.current_contentId+"): "+url, filename=utils.LOG_PLAYER_FILE)

    def onPlayBackStarted(self):
        self.listen = self.current_item == self.getPlayingFile()
        if self.listen:
            utils.log_on_desktop_file("Listening ("+self.current_contentId+"): "+str(self.listen), filename=utils.LOG_PLAYER_FILE)
            utils.log_on_desktop_file("Started ("+self.current_contentId+")",utils.LOG_PLAYER_FILE)
            utils.call_timvision_service({"method":"keep_alive", "contentId": self.current_contentId})
            self.playback_thread_stop_event = threading.Event()
            check_thread = threading.Thread(target=self.check_time)
            check_thread.start()

    def onPlayBackEnded(self):
        #video terminato
        #se e' una serie, mostrare il prossimo episodio
        if self.listen:
            utils.log_on_desktop_file("Ended ("+self.current_contentId+")", filename=utils.LOG_PLAYER_FILE)
            self.playback_thread_stop_event.set()
            
    def onPlayBackPaused(self):
        if self.listen:
            utils.log_on_desktop_file("Paused ("+self.current_contentId+")", filename=utils.LOG_PLAYER_FILE)
            utils.call_timvision_service({"method":"pause_content", "contentId":self.current_contentId, "time":self.current_time})
    
    def onPlayBackStopped(self):
        if self.listen:
            utils.log_on_desktop_file("Stopped ("+self.current_contentId+")", filename=utils.LOG_PLAYER_FILE)
            self.playback_thread_stop_event.set()

    def check_time(self):
        self.total_time = self.getTotalTime()
        while not self.playback_thread_stop_event.isSet():
            last_time = self.current_time
            if self.isPlaying():
                self.current_time = self.getTime()
                if self.current_time > last_time:
                    utils.log_on_desktop_file("GetTime ("+self.current_contentId+"): "+str(self.current_time) + "/" + str(self.total_time), filename=utils.LOG_PLAYER_FILE)
                #TODO controllare la percentuale di completamento per proporre nuovo episodio
            self.playback_thread_stop_event.wait(5)

        complete_percentage = self.current_time * 100.0 / self.total_time
        utils.log_on_desktop_file("Stopping ("+self.current_contentId+") - "+str(complete_percentage)+"%", utils.LOG_PLAYER_FILE)
        if self.total_time > 0 and complete_percentage >= 99.0:
            utils.call_timvision_service({"method":"set_content_seen", "contentId":self.current_contentId})
        else:
            utils.call_timvision_service({"method":"stop_content", "contentId":str(self.current_contentId), "time":int(self.current_time)})

        self.current_item = None
        self.current_contentId = None
        self.current_time = 0
        self.total_time = 0
        self.listen = False