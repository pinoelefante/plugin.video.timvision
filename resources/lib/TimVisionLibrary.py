import os
import unicodedata
from resources.lib import utils, TimVisionObjects, Logger
import xbmc, xbmcvfs

invalidFilenameChars = "<>:\"/\\|/?*"

class TimVisionLibrary(object):
    movies_folder = "movies"
    tvshows_folder = "tvshows"

    def __init__(self):
        custom_path = utils.get_setting("lib_export_folder")
        if custom_path == None or len(custom_path) == 0:
            custom_path = os.path.join(utils.get_data_folder(), "library")
        self.library_folder = os.path.join(custom_path, "timvision")
        self.init_library_folders()

    def init_library_folders(self):
        self.__create_folder(self.library_folder, self.movies_folder)
        self.__create_folder(self.library_folder, self.tvshows_folder)

    def __create_folder(self, basepath, folder):
        new_folder = os.path.join(basepath, folder)
        if not xbmcvfs.exists(new_folder):
            xbmcvfs.mkdirs(new_folder)

    def write_strm(self, path, title, url):
        f = xbmcvfs.File(path, 'w')
        f.write('#EXTINF:-1,'+title.encode('utf-8')+'\n')
        f.write(url)
        f.close()
    
    def __empty_folder(self, library, folder=None):
        path = os.path.join(self.library_folder, library)
        if library == self.tvshows_folder:
            if folder != None:
                path = os.path.join(path, folder)
        dirs, files = xbmcvfs.listdir(path)
        for cur_file in files:
            xbmcvfs.delete(cur_file)
        for cur_dir in dirs:
            xbmcvfs.delete(cur_dir)

    def empty_movies_library(self):
        self.__empty_folder(self.movies_folder)

    def empty_tvshows_library(self):
        self.__empty_folder(self.tvshows_folder)

    def __run_cleanup(self):
        xbmc.executebuiltin("CleanLibrary(video)")
        pass

    def update(self):
        if not utils.get_setting("lib_export_enabled"):
            return
        self.__update_movies_library()
        self.__update_tvshows_library()
        self.__run_cleanup()

    def __update_movies_library(self):
        if not utils.get_setting("lib_export_movie"):
            return
        movies = utils.call_service("load_all_contents", {"begin": 0, "category": "Cinema"})
        if movies == None or len(movies) == 0:
            return
        self.empty_movies_library()
        items = TimVisionObjects.parse_collection(movies)
        for item in items:
            title = "%s (%d)" % (item.title, item.year)
            url = "plugin://plugin.video.timvision/?action=play_item&contentId=%s&videoType=%s&has_hd=%s&startPoint=%s&duration=%s" % (str(item.content_id), item.mediatype, str(item.is_hd_available), str(item.bookmark), str(item.duration))
            filename = os.path.join(self.library_folder, self.movies_folder, self.__normalize_path(title)+".strm")
            self.write_strm(filename, title, url)
    
    def __update_tvshows_library(self):
        #self.empty_movies_library()
        utils.call_service("load_all_contents", {"begin": 0, "category": "Serie"})
        pass

    def __normalize_path(self, filename):
        cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
        return ''.join(c for c in cleanedFilename if c not in invalidFilenameChars)