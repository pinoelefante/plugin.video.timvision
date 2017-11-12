import threading
import time
from collections import deque
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

    def __init__(self):
        super(MyPlayer, self).__init__()
        self.playlist = deque()

    def enqueue(self, items):
        self.playlist.extend(items)

    def setItem(self, url, content_id, start_point=0.0, content_type='', total_time=0):
        self.current_item = url
        self.current_content_id = content_id
        self.start_from = start_point
        self.current_video_type = content_type
        self.total_time = int(total_time)
        Logger.log_on_desktop_file("Setting item (%s - %s) Duration (%d/%d): %s" % (content_id, content_type, self.start_from, self.total_time, url), filename=Logger.LOG_PLAYER_FILE)

    def onPlayBackStarted(self):
        self.listen = self.current_item == self.getPlayingFile()
        if not self.listen:
            return
        if self.start_from >= 10:
            self.seekTime(float(self.start_from))
        Logger.log_on_desktop_file("Listening ("+self.current_content_id+"): "+str(self.listen), filename=Logger.LOG_PLAYER_FILE)
        Logger.log_on_desktop_file("Started ("+self.current_content_id+")", Logger.LOG_PLAYER_FILE)
        self.send_keep_alive()
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
        proposed = False
        to_resume = self.start_from >= 10
        Logger.log_on_desktop_file("Is to resume: " + str(to_resume), Logger.LOG_PLAYER_FILE)
        time_elapsed = 0
        while not self.playback_thread_stop_event.isSet():
            if self.isPlaying():
                self.current_time = int(self.getTime())
                Logger.log_on_desktop_file("Time: %d/%d" % (self.current_time, self.total_time), Logger.LOG_PLAYER_FILE)
                if self.current_time > self.total_time: #happens at the beginning of the video
                    Logger.log_on_desktop_file("Invalid current_time", Logger.LOG_PLAYER_FILE)
                    continue
                while to_resume:
                    Logger.log_on_desktop_file("Trying to resume")
                    try:
                        Logger.log_on_desktop_file("Seek to %d" % (self.start_from), Logger.LOG_PLAYER_FILE)
                        self.seekTime(self.start_from)
                        if abs(self.getTime()-self.start_from) < 10:
                            to_resume = False
                    except:
                        Logger.log_on_desktop_file("Error trying to seek")
                        xbmc.sleep(100)
                remaining = self.total_time - self.current_time
                if self.current_video_type == TimVisionObjects.ITEM_MOVIE and remaining <= 120 and not proposed:
                    Logger.log_on_desktop_file("Proposing suggested movies", Logger.LOG_PLAYER_FILE)
                    proposed = True
                elif self.current_video_type == TimVisionObjects.ITEM_EPISODE and remaining <= 30 and not proposed and utils.get_setting("play_next_episode"):
                    Logger.log_on_desktop_file("Proposing next episode", Logger.LOG_PLAYER_FILE)
                    proposed = True
            self.playback_thread_stop_event.wait(5)
            time_elapsed += 5
            if time_elapsed >= self.keep_alive_limit and self.send_keep_alive():
                time_elapsed = 0
        
        # out of while
        complete_percentage = self.current_time * 100.0 / self.total_time
        Logger.log_on_desktop_file("Stopping (%s) - %.3f%%" % (self.current_content_id, complete_percentage), Logger.LOG_PLAYER_FILE)
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
            Logger.log_on_desktop_file("Keep Alive OK!", Logger.LOG_PLAYER_FILE)
            self.keep_alive_limit = int(ka_resp["resultObj"]["keepAlive"])
            self.keep_alive_token = ka_resp["resultObj"]["token"]
            return True
        Logger.log_on_desktop_file("Keep Alive FAILED!", Logger.LOG_PLAYER_FILE)
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
