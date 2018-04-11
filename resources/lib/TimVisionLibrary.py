import os
import unicodedata
from resources.lib import utils, TimVisionObjects, Logger, Dialogs
import xbmc, xbmcvfs, xbmcgui
import xmltodict

invalidFilenameChars = "<>:\"/\\|/?*"
default_sources_xml = {"sources":{"programs":{"default":{"@pathversion":"1"}},"video":{"default":{"@pathversion":"1"}},"music":{"default":{"@pathversion":"1"}},"pictures":{"default":{"@pathversion":"1"}},"files":{"default":{"@pathversion":"1"}},"games":{"default":{"@pathversion":"1"}}}}

class TimVisionLibrary(object):
    movies_folder = "movies"
    tvshows_folder = "tvshows"

    def __init__(self):
        custom_path = utils.get_setting("lib_export_folder")
        if custom_path == None or len(custom_path) == 0:
            custom_path = utils.get_data_folder()
            utils.set_setting("lib_export_folder", custom_path)
        self.library_folder = os.path.join(custom_path, "timvision_library")
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
    
    def __run_library_update(self, label):
        path = os.path.join(self.library_folder, label)
        sources_xml_path = xbmc.translatePath("special://home/userdata/sources.xml")

        if not xbmcvfs.exists(sources_xml_path) or xbmcvfs.Stat(sources_xml_path).st_size() == 0:
            xml_file = open(sources_xml_path, "w")
            xmltodict.unparse(default_sources_xml, xml_file)
            xml_file.close()
        
        xml_file = open(sources_xml_path, "r")
        file_content = xml_file.read()
        xml_file.close()
        sources_xml = xmltodict.parse(file_content)
        
        if "source" not in sources_xml["sources"]["video"]: #si verifica quando non ci sono fonti video
            sources_xml["sources"]["video"]["source"] = []

        if not isinstance(sources_xml["sources"]["video"]["source"], list): #si verifica quando e' presente una sola fonte video
            source_zero = sources_xml["sources"]["video"]["source"]
            sources_xml["sources"]["video"]["source"]=[source_zero]
        
        to_add = True
        source_label = "timvision_%s" % label

        for source in sources_xml["sources"]["video"]["source"]:
            if str(source["name"]) == source_label:
                to_add = False
                source["path"]["#text"]
        
        if to_add:
            sources_xml["sources"]["video"]["source"].append({"name":source_label, "path":{"@pathversion":"1", "#text": path}, "allowsharing":"false"})
        
        xml_file = open(sources_xml_path, "w")
        xmltodict.unparse(sources_xml, xml_file)
        xml_file.close()
        xbmc.executebuiltin('Action(reloadsources)') 
        xbmc.executebuiltin("UpdateLibrary(video,%s)" % (path))
        
    def update(self):
        if not utils.get_setting("lib_export_enabled"):
            return
        self.__update_movies_library()
        self.__run_library_update(self.movies_folder)
        #self.__update_tvshows_library()
        #self.__run_library_update(self.tvshows_folder)
        #self.__run_cleanup()
        Dialogs.show_message("Library updated", xbmcgui.NOTIFICATION_INFO)

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