import threading
import time
import urllib
from resources.lib import Logger, utils, TimVisionObjects, MyPlayer
from requests import session
from random import randint

AREA_FREE = "SVOD"
AREA_PAY = "TVOD"
AREA_FREE_PAY = "ALL"

TVSHOW_CONTENT_TYPE_SEASONS = "SERIES"
TVSHOW_CONTENT_TYPE_EPISODES = "SEASON"

DEVICE_TYPE = 'WEB'
SERVICE_NAME = 'CUBOVISION'
SERVICE_CHANNEL = 'CUBOWEB'
PROVIDER_NAME = "TELECOMITALIA"

class TimVisionSession(object):
    BASE_URL_TIM = "https://www.timvision.it/TIM/{appVersion}/{cluster}/IT/{channel}/ITALY"
    BASE_URL_AVS = "https://www.timvision.it/AVS"
    app_version = '10.4.11'
    api_endpoint = session()
    license_endpoint = session()
    user_http_header = "X-Avs-Username"
    user_cluster = "PROD"
    session_login_hash = None
    widevine_proxy_url = "https://license.cubovision.it/WidevineManager/WidevineManager.svc/GetLicense/{ContentIdAVS}/{AssetIdWD}/{CpId}/{Type}/{ClientTime}/{Channel}/{DeviceType}"
    player = MyPlayer.MyPlayer()
    last_time_request_received = 0
    favourites = None
    avs_cookie = None
    stop_check_session = None

    def __init__(self):
        self.api_endpoint.headers.update({
            'User-Agent': utils.get_user_agent(),
            'Accept-Encoding': 'gzip, deflate',
        })
        self.license_endpoint.headers.update({
            'User-Agent': utils.get_user_agent(),
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'license.timvision.it',
            'Origin': 'https://www.timvision.it'
        })
        self.init_ok = self.setup()

    def setup(self):
        return self.load_app_version() and self.load_app_settings()

    def load_app_version(self):
        response = self.api_endpoint.get("https://www.timvision.it/app_ver.js")
        if response.status_code == 200:
            version = response.text.rsplit('"')[1].rsplit('"')[0]
            self.app_version = version
            return True
        return False

    def load_app_settings(self):
        url = "/PROPERTIES?deviceType={deviceType}&serviceName={serviceName}"
        data = self.send_request(url, base_url=self.BASE_URL_TIM)
        if data != None:
            self.user_http_header = data['resultObj']['USER_REQ_HEADER_NAME']
            self.widevine_proxy_url = data['resultObj']['WV_PROXY_URL']
            self.user_cluster = data['resultObj']['USERCLUSTERNAME_ANONYMOUS']
            return True
        return False

    def login(self, username, password):
        deviceId = utils.get_setting("timvision_device_id")
        if deviceId == None or len(deviceId) < 38:
            deviceId = self.__random_device_id()
            utils.set_setting("timvision_device_id", deviceId)
        data = {
            'username': username,
            'password': password,
            'customData': '{"customData":[{"name":"deviceType","value":' + DEVICE_TYPE + '},{"name":"deviceVendor","value":""},{"name":"accountDeviceModel","value":""},{"name":"FirmwareVersion","value":""},{"name":"Loader","value":""},{"name":"ResidentApp","value":""},{"name":"DeviceLanguage","value":"it"},{"name":"NetworkType","value":""},{"name":"DisplayDimension","value":""},{"name":"OSversion","value":"Windows 10"},{"name":"AppVersion","value":""},{"name":"DeviceRooted","value":""},{"name":"NetworkOperatoreName","value":""},{"name":"ServiceOperatorName","value":""},{"name":"Custom1","value":"Firefox"},{"name":"Custom2","value":54},{"name":"Custom3","value":"1920x1080"},{"name":"Custom4","value":"PC"},{"name":"Custom5","value":""},{"name":"Custom6","value":""},{"name":"Custom7","value":""},{"name":"Custom8","value":""},{"name":"Custom9","value":""}]}'
        }
        url = "/besc?action=Login&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}&accountDeviceId=%s" % (deviceId)
        response = self.send_request(url=url, base_url=self.BASE_URL_AVS, method="POST", data=data)
        if response != None:
            self.api_endpoint.headers.__setitem__(self.user_http_header, response["resultObj"])
            self.session_login_hash = response["extObject"]["hash"]
            self.avs_cookie = self.api_endpoint.cookies.get("avs_cookie")
            self.license_endpoint.headers.__setitem__('AVS_COOKIE', self.avs_cookie)
            self.stop_check_session = threading.Event()
            check_thread = threading.Thread(target=self.check_session)
            check_thread.start()
            return True
        return False

    def __random_device_id(self):
        device_id = ""
        while len(device_id) < 38:
            chunk = randint(10, 99)
            device_id = device_id + str(chunk)
        return device_id

    def logout(self):
        """ deviceId not present (javascript localstorage)
        url = "/besc?action=Logout&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}"
        r = self.send_request(url, baseUrl=self.BASE_URL_AVS)
        if r != None:
            self.api_endpoint.cookies.clear()
            self.session_login_hash = None
            self.api_endpoint.headers.pop(self.user_http_header, None)
            if self.stop_check_session!=None:
                self.stop_check_session.set()
            return True
        return False
        """
        self.api_endpoint.cookies.clear()
        self.session_login_hash = None
        self.api_endpoint.headers.pop(self.user_http_header, None)
        if self.stop_check_session != None:
            self.stop_check_session.set()
        return True
    def is_logged(self):
        if not self.init_ok:
            self.init_ok = self.setup()
        return self.session_login_hash != None

    def __compile_url(self, url):
        return url.replace("{appVersion}", self.app_version).replace("{channel}", SERVICE_CHANNEL).replace("{serviceName}", SERVICE_NAME).replace("{deviceType}", DEVICE_TYPE).replace("{providerName}", PROVIDER_NAME).replace("{cluster}", self.user_cluster)

    def send_request(self, url, base_url, method="GET", data={}):
        if not url.startswith("https://"):
            url = utils.url_join(base_url, url)
        url = self.__compile_url(url)

        Logger.log_write("Sending "+method+" request to "+url, Logger.LOG_TIMVISION)
        response = self.api_endpoint.get(url, params=data) if method == "GET" else self.api_endpoint.post(url, data=data)
        Logger.log_write("Status Code: "+str(response.status_code), Logger.LOG_TIMVISION)
        if response.status_code == 200:
            data = response.json()
            Logger.log_write("Response: "+response.text, Logger.LOG_TIMVISION)
            if isinstance(data, list):
                Logger.log_write("JSON result is an array", Logger.LOG_TIMVISION)
                data = data[0]
            if data["resultCode"] == "OK":
                return data
        return None

    def get_show_content(self, content_id, content_type):
        url = "/DETAILS?contentId="+str(content_id)+"&type="+content_type+"&renderEngine=DELTA&deviceType={deviceType}&serviceName={serviceName}"
        response = self.get_contents(url)
        if response != None:
            content = []
            for container in response:
                if container["layout"] == "SEASON":
                    if content_type == TVSHOW_CONTENT_TYPE_SEASONS:
                        content.append(container)
                    elif content_type == TVSHOW_CONTENT_TYPE_EPISODES:
                        content = [item for item in container["items"] if item["layout"] == "EPISODE"]
            return content
        return None

    def check_session(self):
        url = "/besc?action=CheckSession&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}"
        while not self.stop_check_session.is_set():
            response = self.send_request(url=url, base_url=self.BASE_URL_AVS)
            if self.is_user_inactive() or (response != None and response["resultObj"]["sessionFlag"] == "N"):
                self.logout()
            self.stop_check_session.wait(600)

    def is_user_inactive(self):
        last_activity = max(self.last_time_request_received, self.player.get_last_time_activity())
        if time.time() - last_activity > 3600: #1 ora = 3600
            return True
        return False

    def get_license_info(self, content_id, video_type, has_hd=False):
        cp_id, mpd = self.get_mpd_file(content_id, video_type)
        if cp_id != None:
            asset_id_wd = TimVisionSession.get_asset_id_wd(mpd)
            if has_hd and utils.get_setting("prefer_hd"):
                mpd = mpd.replace("_SD", "_HD")
            wv_url = self.widevine_proxy_url.replace("{ContentIdAVS}", content_id).replace("{AssetIdWD}", asset_id_wd).replace("{CpId}", cp_id).replace("{Type}", "VOD").replace("{ClientTime}", str(long(time.time() * 1000))).replace("{Channel}", SERVICE_CHANNEL).replace("{DeviceType}", "CHROME").replace('http://', 'https://')
            '''
            major_version, _ = utils.get_kodi_version()
            if major_version < 18:
                wv_url = utils.url_join(utils.get_service_url(), "?action=get_license&license_url=%s" % (urllib.quote(wv_url)))
            '''
            return {
                "mpd_file": mpd,
                "avs_cookie":self.avs_cookie,
                "widevine_url": wv_url
            }
        return None

    @staticmethod
    def get_asset_id_wd(mpd_url):
        partial = mpd_url[mpd_url.find("DASH") + 5:]
        partial = partial[0:partial.find("/")]
        return partial

    def get_mpd_file(self, content_id, video_type):
        url = "/PLAY?contentId="+content_id+"&deviceType=CHROME&serviceName={serviceName}&type="+video_type
        data = self.send_request(url, base_url=self.BASE_URL_TIM)
        if data != None:
            cp_id = data["resultObj"]["cp_id"]
            mpd = data["resultObj"]["src"]
            return cp_id, mpd
        return None, None

    def load_all_contents(self, category, begin=0, progress=49):
        end = int(begin) + progress
        url = "/TRAY/SEARCH/VOD?from="+str(begin)+"&to="+str(end)+"&sorting=order:title+asc&categoryName="+category+"&offerType=SVOD&deviceType={deviceType}&serviceName={serviceName}"
        data = self.send_request(url, base_url=self.BASE_URL_TIM)
        if data != None:
            max_count = data["resultObj"]["total"]
            movies = data["resultObj"]["containers"]
            if end <= max_count:
                other_movie = self.load_all_contents(begin=end, category=category)
                if other_movie != None:
                    movies.extend(other_movie)
            return movies
        return None

    def get_menu_categories(self):
        url = "/menu?deviceType={deviceType}&serviceName={serviceName}"
        return self.get_contents(url)

    def get_page(self, page):
        url = "/PAGE/"+page+"?deviceType={deviceType}&serviceName={serviceName}"
        return self.get_contents(url)

    def get_contents(self, url, data={}):
        data = self.send_request(url, base_url=self.BASE_URL_TIM, data=data)
        if data != None:
            return data["resultObj"]["containers"]
        return None

    def get_cast(self, content_id):
        url = "/TRAY/CELEBRITIES?maxResults=50&deviceType={deviceType}&serviceName={serviceName}&contentId="+content_id
        return self.get_contents(url)

    def set_favorite(self, content_id, favorite, mediatype):
        choise = "Y" if favorite else "N"
        url = "/besc?action=SetFavorite&isFavorite="+choise+"&contentId="+content_id+"&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}"

        if mediatype == TimVisionObjects.ITEM_MOVIE:
            response = self.send_request(url, self.BASE_URL_AVS)
            if response is None or response["resultCode"] != "OK":
                return False

        if favorite:
            res_detail = self.get_details(content_id)
            if res_detail is None:
                res_detail = {"metadata":{"contentId":content_id, "title":"Content %s" % (content_id)}}
            self.favourites.append(res_detail)
        else:
            self.favourites = [x for x in self.favourites if int(x["metadata"]["contentId"]) != int(content_id)]
        utils.save_pickle(self.favourites, "favourites.pickle")
        return True

    def get_details(self, content_id):
        url = "/DETAILS?contentId=%s&deviceType=WEB&serviceName=CUBOVISION&type=VOD" % (str(content_id))
        response = self.get_contents(url)
        if response is None:
            return None
        detail = [x for x in response if x["layout"] == "CONTENT_DETAILS" or x["layout"] == "SERIES_DETAILS"][0]
        return detail

    def get_favourites(self):
        #rimuovere cache ?
        if self.favourites != None:
            return self.favourites
        #can use from-to instead of maxresults
        url = "/TRAY/FAVORITES?dataSet=RICH&area=ALL&category=ALL&maxResults=1000&deviceType={deviceType}&serviceName={serviceName}"
        result = self.get_contents(url)
        if result != None:
            self.favourites = self.__update_favourites_db(result)
        return self.favourites
    
    def __update_favourites_db(self, online_items):
        offline_items = utils.load_pickle("favourites.pickle", [])
        offline_tv_shows = [x for x in offline_items if x["layout"] in ["SERIES_ITEM", "SERIES_DETAILS"]]
        #online_items contiene solo film
        online_items.extend(offline_tv_shows)
        utils.save_pickle(online_items, "favourites.pickle")
        return online_items

    def is_favourite(self, content_id):
        if self.favourites is None and not self.get_favourites():
            return False
        for item in self.favourites:
            item_c_id = item["metadata"]["contentId"] if "contentId" in item["metadata"] else item["contentId"]
            if int(item_c_id) == int(content_id):
                return True
        return False

    def get_season_trailer(self, season_id):
        url = "/GETCDNFORSERIES?type=TRAILER&contentId="+season_id+"&contentType=SEASON&deviceType=CHROME&serviceName={serviceName}"
        response = self.send_request(url, self.BASE_URL_TIM)
        if response != None:
            return response["resultObj"]["src"]
        return None

    def get_movie_trailer(self, content_id):
        cp_id, _mpd = self.get_mpd_file(content_id, "MOVIE")
        if cp_id is None:
            return None
        url = "/besc?action=GetCDN&channel={channel}&type=TRAILER&asJson=Y&serviceName={serviceName}&providerName={providerName}&deviceType=CHROME&cp_id="+cp_id
        response = self.send_request(url, self.BASE_URL_AVS)
        if response != None:
            return response["resultObj"]["src"]
        return None

    def search(self, keyword, area=AREA_FREE):
        keyword = urllib.quote(keyword)
        url = "/TRAY/SEARCHRECOM?keyword="+keyword+"&from=0&to=100&area="+area+"&category=ALL&deviceType={deviceType}&serviceName={serviceName}"
        response = self.send_request(url, self.BASE_URL_TIM)
        if response != None:
            return response["resultObj"]["containers"][0]["items"] if response["resultObj"]["total"] > 0 else {}
        return None
    '''
    def get_widevine_response(self, widevine_request, widevine_url):
        for _ in range(0, 3):
            Logger.log_write("Trying to get widevine license", mode=Logger.LOG_WIDEVINE)
            resp = self.license_endpoint.post(widevine_url, data=widevine_request)
            Logger.log_write("Status code: "+str(resp.status_code), mode=Logger.LOG_WIDEVINE)
            if resp.status_code == 200:
                Logger.log_write("We get it! WOW", mode=Logger.LOG_WIDEVINE)
                return resp.content
        return None
    '''
    def set_playing_media(self, url, content_id, start_time, content_type, duration, paused=False):
        self.player.setItem(url, content_id, start_time, content_type, duration, paused)

    def keep_alive(self, content_id):
        url = "/besc?action=KeepAlive&channel={channel}&type={deviceType}&noRefresh=Y&providerName={providerName}&serviceName={serviceName}&contentId="+str(content_id)
        response = self.send_request(url, self.BASE_URL_AVS)
        return response

    def set_seen(self, content_id, duration):
        return self.stop_content(content_id, duration, duration)

    def pause_consumption(self, _content_id, pause_time, threshold):
        url = "/besc?action=PauseConsumption&channel={channel}&providerName={providerName}&serviceName={serviceName}&bookmark="+str(pause_time)+"&deltaThreshold="+str(threshold)
        response = self.send_request(url, self.BASE_URL_AVS)
        return response != None

    def stop_content(self, content_id, stop_time, threshold):
        url = "/besc?action=StopContent&channel={channel}&providerName={providerName}&serviceName={serviceName}&type=VOD&contentId="+str(content_id)+"&bookmark="+str(stop_time)+"&deltaThreshold="+str(threshold)+"&section=CATALOGUE"
        response = self.send_request(url, self.BASE_URL_AVS)
        return response != None

    def get_recommended_by_content_id(self, content_id):
        url = "/TRAY/RECOM?deviceType={deviceType}&serviceName={serviceName}&dataSet=RICH&recomType=MORE_LIKE_THIS&contentId="+content_id+"&maxResults=25"
        return self.get_contents(url)
