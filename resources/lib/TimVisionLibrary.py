import os
import unicodedata
from resources.lib import utils, TimVisionObjects, Logger, Dialogs, TimVisionAPI
import xbmc, xbmcvfs, xbmcgui
import xmltodict
import sqlite3

invalidFilenameChars = "<>:\"/\\|/?*"
default_sources_xml = {"sources":{"programs":{"default":{"@pathversion":"1"}},"video":{"default":{"@pathversion":"1"}},"music":{"default":{"@pathversion":"1"}},"pictures":{"default":{"@pathversion":"1"}},"files":{"default":{"@pathversion":"1"}},"games":{"default":{"@pathversion":"1"}}}}

class TimVisionLibrary(object):
    movies_folder = "movies"
    tvshows_folder = "tvshows"
    database_path = None

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
    
    def __add_folder_to_sources(self, label):
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
        
    def update(self):
        if not utils.get_setting("lib_export_enabled"):
            return
        if utils.get_setting("lib_export_movie"):
            self.__update_movies_library()
            self.__add_folder_to_sources(self.movies_folder)
            self.__insert_folder_database(self.movies_folder)

        if utils.get_setting("lib_export_tvshow"):
            self.__update_tvshows_library()
            self.__add_folder_to_sources(self.tvshows_folder)
            self.__insert_folder_database(self.tvshows_folder)
        
        xbmc.executebuiltin('Action(ReloadSources)')
        xbmc.executebuiltin("UpdateLibrary(video)")
        #self.__run_cleanup()
        
        Dialogs.show_message("Libraria aggiornata", "TIMVISION", xbmcgui.NOTIFICATION_INFO)

    def __update_movies_library(self):
        movies = utils.call_service("load_all_contents", {"begin": 0, "category": "Cinema"})
        if movies == None or len(movies) == 0:
            return
        self.empty_movies_library()
        items = TimVisionObjects.parse_collection(movies)
        folder_movies = os.path.join(self.library_folder, self.movies_folder)
        for item in items:
            title = "%s (%d)" % (item.title, item.year)
            url = "plugin://plugin.video.timvision/?action=play_item&contentId=%s&videoType=%s&has_hd=%s&startPoint=%s&duration=%s" % (str(item.content_id), item.mediatype, str(item.is_hd_available), str(item.bookmark), str(item.duration))
            filename = os.path.join(folder_movies, self.__normalize_path(title)+".strm")
            self.write_strm(filename, title, url)
    
    def __update_tvshows_library(self):
        tvshows = utils.call_service("load_all_contents", {"begin": 0, "category": "Serie"})
        if tvshows == None or len(tvshows) == 0:
            return
        self.empty_tvshows_library()
        base_series_folder = os.path.join(self.library_folder, self.tvshows_folder)
        items = TimVisionObjects.parse_collection(tvshows)
        for tvshow in items:
            normalized_show_name = "%s (%d)" % (self.__normalize_path(tvshow.title), tvshow.year)
            show_folder = os.path.join(base_series_folder, normalized_show_name)
            xbmcvfs.mkdir(show_folder)
            seasons_json = utils.call_service("get_show_content", {"contentId": tvshow.content_id, "contentType": TimVisionAPI.TVSHOW_CONTENT_TYPE_SEASONS})
            seasons = TimVisionObjects.parse_collection(seasons_json)
            for season in seasons:
                episodes_json = utils.call_service("get_show_content", {"contentId": season.content_id, "contentType": TimVisionAPI.TVSHOW_CONTENT_TYPE_EPISODES})
                episodes = TimVisionObjects.parse_collection(episodes_json)
                for episode in episodes:
                    filename = "%s S%02dE%02d" % (normalized_show_name, episode.season, episode.episode)
                    url = "plugin://plugin.video.timvision/?action=play_item&contentId=%s&videoType=%s&has_hd=%s&startPoint=%s&duration=%s" % (str(episode.content_id), episode.mediatype, str(episode.is_hd_available), str(episode.bookmark), str(episode.duration))
                    self.write_strm(os.path.join(show_folder, filename+".strm"), filename, url)

    def __normalize_path(self, filename):
        cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
        newName = ''.join(c for c in cleanedFilename if c not in invalidFilenameChars)
        if len(newName) == 0:
            return xbmc.makeLegalFilename(filename)
        return newName
    
    def __check_database(self, folder):
        path_found = False
        db_path = self.__get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM path WHERE strPath = ?", [folder])
        if cursor.fetchone() != None:
            path_found = True
        cursor.close()
        conn.close()
        return path_found

    def __insert_folder_database(self, label):
        folder = os.path.join(self.library_folder, label)+os.sep
        if self.__check_database(folder):
            return False
        if label == self.movies_folder:
            strScraper = "metadata.themoviedb.org"
            strSettings = '<settings version="2"><setting id="certprefix" default="true">Rated </setting><setting id="fanart">true</setting><setting id="imdbanyway" default="true">false</setting><setting id="keeporiginaltitle" default="true">false</setting><setting id="language">it</setting><setting id="RatingS">IMDb</setting><setting id="tmdbcertcountry">it</setting><setting id="trailer">true</setting></settings>'
        else:
            strScraper = "metadata.tvdb.com"
            strSettings = '<settings version="2"><setting id="absolutenumber" default="true">false</setting><setting id="alsoimdb" default="true">false</setting><setting id="dvdorder" default="true">false</setting><setting id="fallback" default="true">true</setting><setting id="fallbacklanguage" default="true">en</setting><setting id="fanart">true</setting><setting id="language">it</setting><setting id="RatingS">IMDb</setting><setting id="usefallbacklanguage1">true</setting></settings>'
        db_path = self.__get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO path (strPath, strContent, strScraper, scanRecursive, useFolderNames, strSettings, noUpdate, exclude) VALUES (?,?,?,0,0,?,0,0)", [folder, label, strScraper, strSettings])
        conn.commit()
        cursor.close()
        conn.close()

    def __get_database_path(self):
        if self.database_path!=None:
            return self.database_path
        db_folder = xbmc.translatePath("special://home/userdata/Database")
        file_list = os.listdir(db_folder)
        for f in file_list:
            if f.startswith("MyVideos"):
                self.database_path = os.path.join(db_folder, f)
                return self.database_path
        return None