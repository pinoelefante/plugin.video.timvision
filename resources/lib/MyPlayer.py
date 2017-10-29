import xbmc
import threading
import time
from resources.lib import utils, Logger

class MyPlayer(xbmc.Player):
    current_content_id = None
    current_item = None
    current_time = 0
    start_from = 0
    threshold = 0.0

    listen = False
    playback_thread_stop_event = None
    is_paused = False

    def setItem(self, url, content_id, start_point = 0.0):
        self.current_item = url
        self.current_content_id = content_id
        self.start_from = start_point
        Logger.log_on_desktop_file("Setting item ("+self.current_content_id+"): "+url, filename=Logger.LOG_PLAYER_FILE)

    def onPlayBackStarted(self):
        self.listen = self.current_item == self.getPlayingFile()
        if not self.listen:
            return
        if(self.start_from > 1):
            self.seekTime(float(self.start_from))
        Logger.log_on_desktop_file("Listening ("+self.current_content_id+"): "+str(self.listen), filename=Logger.LOG_PLAYER_FILE)
        Logger.log_on_desktop_file("Started ("+self.current_content_id+")",Logger.LOG_PLAYER_FILE)
        utils.call_service("keep_alive", {"contentId": self.current_content_id})
        self.playback_thread_stop_event = threading.Event()
        check_thread = threading.Thread(target=self.check_time)
        check_thread.start()
        threshold_thread = threading.Thread(target=self.threshold_calculation)
        threshold_thread.start()

    def onPlayBackEnded(self):
        #video terminato
        #se e' una serie, mostrare il prossimo episodio
        if not self.listen:
            return
        Logger.log_on_desktop_file("Ended ("+self.current_content_id+")", filename=Logger.LOG_PLAYER_FILE)
        self.playback_thread_stop_event.set()
            
    def onPlayBackPaused(self):
        if not self.listen:
            return
        Logger.log_on_desktop_file("Paused ("+self.current_content_id+")", filename=Logger.LOG_PLAYER_FILE)
        utils.call_service("pause_content", {"contentId":self.current_content_id, "time":int(self.current_time), "threshold":int(self.threshold)})
        self.is_paused = True
    
    def onPlayBackStopped(self):
        if not self.listen:
            return
        Logger.log_on_desktop_file("Stopped ("+self.current_content_id+")", filename=Logger.LOG_PLAYER_FILE)
        self.playback_thread_stop_event.set()

    def onPlayBackResumed(self):
        if not self.listen:
            return
        Logger.log_on_desktop_file("Resumed ("+self.current_content_id+")", filename=Logger.LOG_PLAYER_FILE)
        self.is_paused = False

    def check_time(self):
        total_time = self.getTotalTime()
        while not self.playback_thread_stop_event.isSet():
            last_time = self.current_time
            if self.isPlaying():
                self.current_time = self.getTime()
                if self.current_time > last_time:
                    Logger.log_on_desktop_file("GetTime ("+self.current_content_id+"): "+str(self.current_time) + "/" + str(total_time), filename=Logger.LOG_PLAYER_FILE)
                #TODO controllare la percentuale di completamento per proporre nuovo episodio
            self.playback_thread_stop_event.wait(5)

        complete_percentage = self.current_time * 100.0 / total_time
        Logger.log_on_desktop_file("Stopping ("+self.current_content_id+") - "+str(complete_percentage)+"%", Logger.LOG_PLAYER_FILE)
        if complete_percentage >= 99.0:
            utils.call_service("set_content_seen", {"contentId":self.current_content_id, "duration": int(total_time)})
        else:
            utils.call_service("stop_content", {"contentId":str(self.current_content_id), "time":int(self.current_time), "threshold": int(self.threshold)})
        self.current_item = None
        self.current_content_id = None
        self.current_time = 0
        self.threshold = 0
        self.start_from = 0
        self.listen = False
    
    def threshold_calculation(self):
        last_check = time.time()
        curr_check = last_check
        while not self.playback_thread_stop_event.isSet():
            self.playback_thread_stop_event.wait(1)
            curr_check = time.time()
            if not self.is_paused:
                diff_time = curr_check - last_check
                self.threshold+=diff_time
            last_check = curr_check