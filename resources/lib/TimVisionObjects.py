try:
    from urllib.parse import quote, quote_plus
except:
    from urllib import quote, quote_plus
import xbmcgui
from resources.lib import utils

PLUGIN_NAME = "plugin.video.timvision"

ITEM_TVSHOW = "TVSHOW"
ITEM_MOVIE = "MOVIE"
ITEM_EPISODE = "EPISODE"
ITEM_SEASON = "SEASON"
ITEM_COLLECTION = "COLLECTION"

def parse_collection(collection):
    content = []
    for container in collection:
        item_type = get_item_type(container["layout"])
        if item_type in [ITEM_TVSHOW, ITEM_EPISODE, ITEM_MOVIE]:
            content.append(parse_content(container, item_type))
        elif item_type == ITEM_SEASON:
            content.append(parse_season(container))
        elif item_type == ITEM_COLLECTION:
            content.append(parse_item_collection(container))
    return content

def get_item_type(value):
    if value == "EPISODE":
        return ITEM_EPISODE
    elif value in ["SERIES_ITEM", "SERIES_DETAILS"]:
        return ITEM_TVSHOW
    elif value in ["MOVIE_ITEM", "CONTENT_DETAILS"]:
        return ITEM_MOVIE
    elif value == "SEASON":
        return ITEM_SEASON
    #["COLLECTION_ITEM", "EDITORIAL_ITEM", "KIDS_ITEM"]
    return ITEM_COLLECTION

def parse_item_collection(container):
    title = container["metadata"]["title"]
    action_url = container["actions"][0]["uri"]
    content = TimVisionContent(action_url, title, ITEM_COLLECTION)
    content.poster = container["metadata"]["imageUrl"]
    content.plot = container["metadata"]["longDescription"].replace("Personaggi Second Screen ", "")
    content.plot_outline = container["metadata"]["shortDescription"]
    return content

def parse_content(item, mediatype):
    content_id = item["metadata"]["contentId"]
    title = item["metadata"]["title"]
    content = TimVisionContent(content_id, title, mediatype)

    content.year = int(item["metadata"]["year"]) if "year" in item["metadata"] else 0
    content.rating = float(item["metadata"]["rating"])*2 if "rating" in item["metadata"] else 0
    content.add_cast_simple(item["metadata"]["actors"] if "actors" in item["metadata"] else None)
    content.add_directors_simple(item["metadata"]["directors"] if "directors" in item["metadata"] else None)
    content.plot = item["metadata"]["longDescription"] if "longDescription" in item["metadata"] else None
    content.plot_outline = item["metadata"]["shortDescription"] if "shortDescription" in item["metadata"] else None
    content.duration = int(item["metadata"]["duration"]) if "duration" in item["metadata"] and item["metadata"]["duration"] != None else 0
    content.add_genres(item["metadata"]["genre"] if "genre" in item["metadata"] else None)

    content.fanart = item["metadata"]["bgImageUrl"] if "bgImageUrl" in item["metadata"] else None
    content.poster = item["metadata"]["imageUrl"] if "imageUrl" in item["metadata"] else None

    if mediatype in [ITEM_MOVIE, ITEM_EPISODE]:
        content.bookmark = int(item["metadata"]["bookmark"]) if "bookmark" in item["metadata"] else 0
        content.is_hd_available = "HD" in item["metadata"]["videoType"]

    if mediatype == ITEM_EPISODE:
        content.episode = int(item["metadata"]["episodeNumber"])
        content.season = int(item["metadata"]["season"])

    if mediatype == ITEM_TVSHOW and "watchNextObj" in item["metadata"]:
        series_name = item["metadata"]["watchNextObj"]["seriesName"]
        episode_title = item["metadata"]["watchNextObj"]["episodeTitle"]
        content.mediatype = ITEM_EPISODE
        content.content_id = item["metadata"]["watchNextObj"]["contentId"]
        content.episode = int(item["metadata"]["watchNextObj"]["episodeNumber"])
        content.season = int(item["metadata"]["watchNextObj"]["season"])
        content.duration = item["metadata"]["watchNextObj"]["duration"]
        content.bookmark = int(item["metadata"]["bookmark"]) if "bookmark" in item["metadata"] else 0
        content.title = "%s (%02dx%02d) - %s" % (series_name, content.season, content.episode, episode_title)
        content.is_hd_available = False

    return content

def parse_season(item):
    content_id = item["metadata"]["contentId"]
    season_no = item["metadata"]["season"]
    content = TimVisionContent(content_id, "Stagione %s" % (str(season_no)), ITEM_SEASON)
    content.fanart = item["metadata"]["bgImageUrl"]
    content.season = season_no
    return content

class TimVisionBaseObject(object):
    content_id = None
    title = None
    fanart = None
    poster = None
    def __init__(self, content_id, title):
        self.content_id = content_id
        self.title = title

    def get_list_item(self):
        list_item = xbmcgui.ListItem(label=self.title)
        list_item.setArt({"fanart": self.fanart, "poster": self.poster})
        is_folder = False
        url = ""
        return list_item, is_folder, url

class TimVisionContent(TimVisionBaseObject):
    year = None
    rating = 0.0
    actors = []
    directors = []
    plot = None
    plot_outline = None
    duration = 0
    genres = []
    season = 0
    episode = 0
    bookmark = 0
    is_hd_available = False

    def __init__(self, content_id, title, mediatype):
        super(TimVisionContent, self).__init__(content_id, title)
        self.mediatype = mediatype

    def get_list_item(self):
        list_item, is_folder, url = super(TimVisionContent, self).get_list_item()
        is_folder = True if self.mediatype in [ITEM_TVSHOW, ITEM_SEASON, ITEM_COLLECTION] else False

        if self.mediatype == ITEM_TVSHOW:
            url = "?action=apri_serie&id_serie=%s&serieNome=%s" % (str(self.content_id), quote(self.title.encode("utf-8")))
        elif self.mediatype == ITEM_SEASON:
            url = "?action=apri_stagione&seasonNo=%s&id_stagione=%s" % (str(self.season), str(self.content_id))
        elif self.mediatype == ITEM_COLLECTION:
            url = "?action=open_page&uri=" + quote_plus(self.content_id)
        elif self.mediatype in [ITEM_MOVIE, ITEM_EPISODE]:
            url = "?action=play_item&contentId=%s&videoType=%s&has_hd=%s&startPoint=%s&contentType=%s&duration=%s" % (str(self.content_id), self.mediatype, str(self.is_hd_available), str(self.bookmark), self.mediatype, str(self.duration))
            list_item.setProperty("isPlayable", "true")
            list_item.addStreamInfo("video", {'width': '768', 'height': '432'} if not self.is_hd_available else {'width': '1920', 'height': '1080'})

        list_item.setInfo("video", {
            "year": str(self.year),
            "rating": str(self.rating),
            "cast": self.actors,
            "director": utils.list_to_string(self.directors),
            "plot": self.plot,
            "plotoutline": self.plot_outline,
            "title": self.title,
            "duration": str(self.duration),
            "genre": utils.list_to_string(self.genres),
            "mediatype": self.mediatype.lower()
        })
        if self.mediatype == ITEM_EPISODE:
            list_item.setInfo("video", {
                "episode": str(self.episode),
                "season": str(self.season)
            })
        list_item = self.create_context_menu(list_item)
        return list_item, is_folder, url

    def create_context_menu(self, list_item):
        actions = []
        if self.mediatype in [ITEM_MOVIE, ITEM_TVSHOW]:
            is_fav = utils.call_service("is_favourite", {"contentId":self.content_id})
        if self.mediatype == ITEM_MOVIE:
            actions.extend([("Play Trailer", "RunPlugin(plugin://"+PLUGIN_NAME+"/?action=play_trailer&contentId="+self.content_id+"&type=MOVIE)")])
            #actions.extend([("Gia' Visto", "RunPlugin("+self.plugin_dir+"?action=set_seen&contentId="+content_id+"&duration="+str(container["metadata"]["duration"])+")")])
            if is_fav:
                actions.extend([("Rimuovi da preferiti", "RunPlugin(plugin://"+PLUGIN_NAME+"/?action=toogle_favourite&value=False&contentId=%s&mediatype=%s)" % (str(self.content_id), self.mediatype))])
            else:
                actions.extend([("Aggiungi a preferiti", "RunPlugin(plugin://"+PLUGIN_NAME+"/?action=toogle_favourite&value=True&contentId=%s&mediatype=%s)" % (str(self.content_id), self.mediatype))])
        elif self.mediatype == ITEM_EPISODE:
            actions.extend([("Play Trailer della Stagione", "RunPlugin(plugin://"+PLUGIN_NAME+"/?action=play_trailer&contentId="+self.content_id+"&type=TVSHOW)")])
            #actions.extend([("Gia' Visto", "RunPlugin(plugin://"+PLUGIN_NAME+"/?action=play_item&contentId="+self.content_id+"&duration="+str(self.duration)+"&video_type=VOD&has_hd=False&startPoint="+str(int(self.duration)-1)+")")])
        elif  self.mediatype == ITEM_TVSHOW:
            if is_fav:
                actions.extend([("Rimuovi da preferiti (locale)", "RunPlugin(plugin://"+PLUGIN_NAME+"/?action=toogle_favourite&value=False&contentId=%s&mediatype=%s)" % (str(self.content_id), self.mediatype))])
            else:
                actions.extend([("Aggiungi a preferiti (locale)", "RunPlugin(plugin://"+PLUGIN_NAME+"/?action=toogle_favourite&value=True&contentId=%s&mediatype=%s)" % (str(self.content_id), self.mediatype))])
        elif  self.mediatype == ITEM_SEASON:
            actions.extend([("Play Trailer", "RunPlugin(plugin://"+PLUGIN_NAME+"/?action=play_trailer&contentId="+self.content_id+"&type=TVSHOW)")])
        list_item.addContextMenuItems(items=actions)
        return list_item

    def add_cast_simple(self, cast):
        if cast is None:
            return
        if isinstance(cast, str):
            cast = utils.string_to_list(cast, ',')
        self.actors = cast

    def add_directors_simple(self, dirs):
        if dirs is None:
            return
        if isinstance(self, str):
            dirs = utils.string_to_list(dirs, ',')
        self.directors = dirs

    def add_genres(self, gens):
        if gens is None:
            return
        self.genres = utils.string_to_list(gens, ',')
