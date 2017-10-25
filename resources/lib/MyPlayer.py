import xbmc
from resources.lib import utils as logger

class MyPlayer(xbmc.Player):
    current_item = None
    listen = False

    def setItem(self, url):
        self.current_item = url

    def onPlayBackEnded(self):
        #video terminato
        #se e' una serie, mostrare il prossimo episodio
        if self.listen:
            logger.log_on_desktop_file("Playback ended", filename="player.log")
            self.current_item = None
        pass

    def onPlayBackPaused(self):
        if self.listen:
            logger.log_on_desktop_file("Playback paused", filename="player.log")
    
    def onPlayBackStarted(self):
        item = self.getPlayingFile()
        logger.log_on_desktop_file("Playback started = "+item+" - Item setted = "+self.current_item, filename="player.log")
        self.listen = self.current_item == self.getPlayingFile()
    
    def onPlayBackStopped(self):
        if self.listen:
            logger.log_on_desktop_file(self.current_item+" stopped", filename="player.log")    
        #logger.log_on_desktop_file("Playback stopped", filename="player.log")