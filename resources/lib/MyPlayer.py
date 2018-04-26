import threading
import time
from resources.lib import utils, Logger, TimVisionObjects
import xbmc

class MyPlayer(xbmc.Player):
    current_content_id = None
    current_item = None
    current_time = 0
    total_time = 0
    start_from = 0
    threshold = 0.0
    current_video_type = ''
    listen = False
    playback_thread_stop_event = None
    is_paused = False
    keep_alive_limit = 600
    keep_alive_token = None
    last_time_end = 0

    def setItem(self, url, content_id, start_point=0.0, content_type='', total_time=0, paused=False):
        self.current_item = url
        self.current_content_id = content_id
        self.start_from = start_point
        self.current_video_type = content_type
        self.total_time = int(total_time)
        self.start_paused = paused
        Logger.log_write("Setting item (%s - %s) Duration (%d/%d): %s" % (content_id, content_type, self.start_from, self.total_time, url), mode=Logger.LOG_PLAYER)

    def onPlayBackStarted(self):
        if self.current_item != None and self.isPlaying():
            playing_file = self.getPlayingFile()
            self.listen = self.current_item == playing_file
        if not self.listen:
            Logger.log_write("%s is not setted item" % (playing_file), Logger.LOG_PLAYER)
            return
        if self.start_from >= 10:
            self.seekTime(float(self.start_from))
        Logger.log_write("Listening ("+self.current_content_id+"): "+str(self.listen), mode=Logger.LOG_PLAYER)
        Logger.log_write("Started ("+self.current_content_id+")", Logger.LOG_PLAYER)
        self.send_keep_alive()
        self.playback_thread_stop_event = threading.Event()
        check_thread = threading.Thread(target=self.check_time)
        check_thread.start()
        threshold_thread = threading.Thread(target=self.threshold_calculation)
        threshold_thread.start()
        if self.start_paused:
            self.start_paused = False
            self.pause()

    def onPlayBackEnded(self):
        if not self.listen:
            return
        Logger.log_write("Ended ("+self.current_content_id+")", mode=Logger.LOG_PLAYER)
        self.playback_thread_stop_event.set()

    def onPlayBackPaused(self):
        if not self.listen:
            return
        Logger.log_write("Paused ("+self.current_content_id+")", mode=Logger.LOG_PLAYER)
        utils.call_service("pause_content", {"contentId":self.current_content_id, "time":int(self.current_time), "threshold":int(self.threshold)})
        self.is_paused = True

    def onPlayBackStopped(self):
        if not self.listen:
            return
        Logger.log_write("Stopped ("+self.current_content_id+")", mode=Logger.LOG_PLAYER)
        self.playback_thread_stop_event.set()

    def onPlayBackResumed(self):
        if not self.listen:
            return
        Logger.log_write("Resumed ("+self.current_content_id+")", mode=Logger.LOG_PLAYER)
        self.is_paused = False
    
    def onCorrectTimeLoaded(self):
        if self.start_paused:
            while not self.is_paused:
                self.pause()
                xbmc.sleep(1000)
        
        while abs(self.getTime()-self.start_from) > 10:
            Logger.log_write("Trying to resume: %f" % (self.start_from), Logger.LOG_PLAYER)
            self.seekTime(self.start_from)
            xbmc.sleep(100)

    def check_time(self):
        time_elapsed = 0
        self.current_time = int(self.getTime())
        while self.current_time > self.total_time or self.current_time < 0:
            xbmc.sleep(200)
        self.onCorrectTimeLoaded()
        
        while not self.playback_thread_stop_event.isSet():
            # keep live check
            self.current_time = int(self.getTime())
            self.playback_thread_stop_event.wait(2)
            time_elapsed += 2
            if time_elapsed >= self.keep_alive_limit and self.send_keep_alive():
                time_elapsed = 0
        
        # out of while
        complete_percentage = self.current_time * 100.0 / self.total_time
        Logger.log_write("Stopping (%s) - %.3f%%" % (self.current_content_id, complete_percentage), Logger.LOG_PLAYER)
        if complete_percentage >= 97.5:
            utils.call_service("set_content_seen", {"contentId":self.current_content_id, "duration": int(self.total_time)})
        elif self.current_time > 10:
            utils.call_service("stop_content", {"contentId":str(self.current_content_id), "time":int(self.current_time), "threshold": int(self.threshold)})
        self.reset_player()

    def threshold_calculation(self):
        last_check = time.time()
        curr_check = last_check
        while not self.playback_thread_stop_event.isSet():
            self.playback_thread_stop_event.wait(1)
            curr_check = time.time()
            if not self.is_paused:
                diff_time = curr_check - last_check
                self.threshold += diff_time
            last_check = curr_check

    def get_last_time_activity(self):
        if self.isPlaying():
            return time.time()
        return self.last_time_end

    def send_keep_alive(self):
        ka_resp = utils.call_service("keep_alive", {"contentId": self.current_content_id})
        if ka_resp != None:
            Logger.log_write("Keep Alive OK!", Logger.LOG_PLAYER)
            self.keep_alive_limit = int(ka_resp["resultObj"]["keepAlive"])
            self.keep_alive_token = ka_resp["resultObj"]["token"]
            return True
        Logger.log_write("Keep Alive FAILED!", Logger.LOG_PLAYER)
        return False

    def reset_player(self):
        self.current_item = None
        self.current_content_id = None
        self.current_time = 0
        self.total_time = 0
        self.threshold = 0
        self.start_from = 0
        self.listen = False
        self.last_time_end = time.time()
        self.is_paused = False
        self.keep_alive_token = None
        self.keep_alive_limit = 600
        self.start_paused = False
