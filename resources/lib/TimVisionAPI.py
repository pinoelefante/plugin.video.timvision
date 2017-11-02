import json
import threading
import time
import urllib
from resources.lib import Logger, utils, TimVisionObjects
from requests import session, cookies
from resources.lib.MyPlayer import MyPlayer

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
    BASE_URL_TIM = "https://www.timvision.it/TIM/{appVersion}/PRODSVOD_WEB/IT/{channel}/ITALY"
    BASE_URL_AVS = "https://www.timvision.it/AVS"
    app_version = '10.4.11'
    api_endpoint = session()
    license_endpoint = session()
    user_http_header = "X-Avs-Username"
    session_login_hash = None
    widevine_proxy_url = "https://license.cubovision.it/WidevineManager/WidevineManager.svc/GetLicense/{ContentIdAVS}/{AssetIdWD}/{CpId}/{Type}/{ClientTime}/{Channel}/{DeviceType}"
    player = None
    last_time_request_received = 0
    favourites = None

    def __init__(self):
        self.player = MyPlayer()
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
        r = self.api_endpoint.get("https://www.timvision.it/app_ver.js")
        if r.status_code == 200:
            version = r.text.rsplit('"')[1].rsplit('"')[0]
            self.app_version = version
            return True
        return False

    def load_app_settings(self):
        url = "/PROPERTIES?deviceType={deviceType}&serviceName={serviceName}"
        data = self.send_request(url,baseUrl=self.BASE_URL_TIM)
        if data != None:
            self.user_http_header = data['resultObj']['USER_REQ_HEADER_NAME']
            self.widevine_proxy_url = data['resultObj']['WV_PROXY_URL']
            return True
        return False

    def login(self, username, password):
        data = {
            'username': username,
            'password': password,
            'customData': '{"customData":[{"name":"deviceType","value":' + DEVICE_TYPE + '},{"name":"deviceVendor","value":""},{"name":"accountDeviceModel","value":""},{"name":"FirmwareVersion","value":""},{"name":"Loader","value":""},{"name":"ResidentApp","value":""},{"name":"DeviceLanguage","value":"it"},{"name":"NetworkType","value":""},{"name":"DisplayDimension","value":""},{"name":"OSversion","value":"Windows 10"},{"name":"AppVersion","value":""},{"name":"DeviceRooted","value":""},{"name":"NetworkOperatoreName","value":""},{"name":"ServiceOperatorName","value":""},{"name":"Custom1","value":"Firefox"},{"name":"Custom2","value":54},{"name":"Custom3","value":"1920x1080"},{"name":"Custom4","value":"PC"},{"name":"Custom5","value":""},{"name":"Custom6","value":""},{"name":"Custom7","value":""},{"name":"Custom8","value":""},{"name":"Custom9","value":""}]}'
        }
        url = "/besc?action=Login&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}"
        r = self.send_request(url=url, baseUrl=self.BASE_URL_AVS, method="POST", data=data)
        if r != None:
            self.api_endpoint.headers.__setitem__(self.user_http_header, r["resultObj"])
            self.session_login_hash = r["extObject"]["hash"]
            self.avs_cookie = self.api_endpoint.cookies.get("avs_cookie")
            self.license_endpoint.headers.__setitem__('AVS_COOKIE', self.avs_cookie)
            self.stop_check_session = threading.Event()
            check_thread = threading.Thread(target=self.check_session)
            check_thread.start()
            return True
        return False

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
        if self.stop_check_session!=None:
            self.stop_check_session.set()
        return True
    def is_logged(self):
        if not self.init_ok:
            self.init_ok = self.setup()
        return self.session_login_hash != None

    def __compile_url(self, url):
        return url.replace("{appVersion}", self.app_version).replace("{channel}", SERVICE_CHANNEL).replace("{serviceName}", SERVICE_NAME).replace("{deviceType}", DEVICE_TYPE).replace("{providerName}", PROVIDER_NAME)

    def send_request(self, url, baseUrl, method="GET", data={}):
        if not url.startswith("https://"):
            url = utils.url_join(baseUrl, url)
        url = self.__compile_url(url)
        
        Logger.log_on_desktop_file("Sending "+method+" request to "+url)
        r = self.api_endpoint.get(url, params=data) if method == "GET" else self.api_endpoint.post(url, data=data)
        Logger.log_on_desktop_file("Status Code: "+str(r.status_code))
        if r.status_code == 200:
            data = r.json()
            Logger.log_on_desktop_file(msg=("Response: "+r.text))
            if isinstance(data, list):
                Logger.log_on_desktop_file("JSON result is an array")
                data = data[0]
            if data["resultCode"] == "OK":
                return data
        return None
    
    def get_show_content(self, content_id, content_type):
        url = "/DETAILS?contentId="+str(content_id)+"&type="+content_type+"&renderEngine=DELTA&deviceType={deviceType}&serviceName={serviceName}"
        response = self.get_contents(url)
        if response != None:
            content = []
            for s in response:
                if s["layout"]=="SEASON":
                    if content_type == TVSHOW_CONTENT_TYPE_SEASONS:
                        content.append(s)
                    elif content_type == TVSHOW_CONTENT_TYPE_EPISODES:
                        content = [item for item in s["items"] if item["layout"] == "EPISODE"]
            return content
        return None
    
    def check_session(self):
        url = "/besc?action=CheckSession&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}"
        while not self.stop_check_session.is_set():
            r = self.send_request(url=url, baseUrl=self.BASE_URL_AVS)
            if self.is_user_inactive() or (r != None and r["resultObj"]["sessionFlag"] == "N"):
                self.logout()
            self.stop_check_session.wait(600)

    def is_user_inactive(self):
        last_activity = max(self.last_time_request_received, self.player.get_last_time_activity())
        if time.time() - last_activity > 3600: #1 ora = 3600
            return True
        return False
    
    def get_license_info(self, content_id, videoType, has_hd=False):
        cp_id,mpd = self.get_mpd_file(content_id, videoType)
        if cp_id != None:
            assetIdWd = self.get_assetIdWd(mpd)
            if has_hd and utils.get_setting("prefer_hd"):
                mpd=mpd.replace("_SD.mpd", "_HD.mpd")
            wv_url = self.widevine_proxy_url.replace("{ContentIdAVS}", content_id).replace("{AssetIdWD}", assetIdWd).replace("{CpId}", cp_id).replace("{Type}", "VOD").replace("{ClientTime}", str(long(time.time() * 1000))).replace("{Channel}", SERVICE_CHANNEL).replace("{DeviceType}", "CHROME").replace('http://', 'https://')
            if utils.get_setting("inputstream_kodi17"):
                wv_url = utils.url_join(utils.get_service_url(), "?action=get_license&license_url=%s" % (urllib.quote(wv_url)))
            return {
                "mpd_file": mpd,
                "avs_cookie":self.avs_cookie,
                "widevine_url": wv_url
            }
        return None

    def get_assetIdWd(self, mpdUrl):
        partial = mpdUrl[mpdUrl.find("DASH") + 5:]
        partial = partial[0:partial.find("/")]
        return partial

    def get_mpd_file(self, content_id, videoType):
        url = "/PLAY?contentId="+content_id+"&deviceType=CHROME&serviceName={serviceName}&type="+videoType
        data = self.send_request(url, baseUrl=self.BASE_URL_TIM)
        if data != None:
            cpId = data["resultObj"]["cp_id"]
            mpd = data["resultObj"]["src"]
            return cpId, mpd
        return None,None

    def load_all_contents(self, category, begin=0, progress=49):
        end = int(begin) + progress
        url = "/TRAY/SEARCH/VOD?from="+str(begin)+"&to="+str(end)+"&sorting=order:title+asc&categoryName="+category+"&offerType=SVOD&deviceType={deviceType}&serviceName={serviceName}"
        data = self.send_request(url, baseUrl=self.BASE_URL_TIM)
        if data != None:
            maxCount = data["resultObj"]["total"]
            movies = data["resultObj"]["containers"]
            if end <= maxCount:
                other_movie = self.load_all_contents(
                    begin=end, category=category)
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
        data = self.send_request(url, baseUrl=self.BASE_URL_TIM, data=data)
        if data != None:
            return data["resultObj"]["containers"]
        return None
        
    def getCast(self, content_id):
        url = "/TRAY/CELEBRITIES?maxResults=50&deviceType={deviceType}&serviceName={serviceName}&contentId="+content_id
        return self.get_contents(url)

    def setFavorite(self, content_id, favorite, mediatype):
        f = "Y" if favorite else "N"
        url = "/besc?action=SetFavorite&isFavorite="+f+"&contentId="+content_id+"&channel={channel}&providerName={providerName}&serviceName={serviceName}&deviceType={deviceType}"
        r = self.send_request(url, self.BASE_URL_AVS)
        if r!=None and r["resultCode"]=="OK":
            if favorite:
                res_detail = self.get_details(content_id)
                if res_detail is None:
                    self.favourites.append(TimVisionObjects.TimVisionBaseObject(content_id, '!!!TITLE ERROR!!!'))
                    return True
                content = TimVisionObjects.parse_content(res_detail, mediatype)
                self.favourites.append(content)
            else:
                self.favourites = [x for x in self.favourites if x.content_id != content_id]
            return True
        return False

    def get_details(self, content_id):
        url = "/DETAILS?contentId=%s&deviceType=WEB&serviceName=CUBOVISION&type=VOD" % (str(content_id))
        response = self.get_contents(url)
        if response is None:
            return None
        detail = [x for x in response if x["layout"]=="CONTENT_DETAILS"][0]
        return detail

    def get_favourites(self):
        #can use from-to instead of maxresults
        url = "/TRAY/FAVORITES?dataSet=RICH&area=ALL&category=ALL&maxResults=1000&deviceType={deviceType}&serviceName={serviceName}"
        result = self.get_contents(url)
        if result != None:
            self.favourites = TimVisionObjects.parse_collection(result)
            return True
        return False

    def is_favourite(self, content_id):
        if self.favourites is None and not self.get_favourites():
            return False
        for item in self.favourites:
            if item.content_id == content_id:
                return True
        return False

    def get_season_trailer(self, season_id, contentType="SEASON"):
        url = "/GETCDNFORSERIES?type=TRAILER&contentId="+season_id+"&contentType=SEASON&deviceType=CHROME&serviceName={serviceName}"
        r = self.send_request(url, self.BASE_URL_TIM)
        if r != None:
            return r["resultObj"]["src"]
        return None

    def get_movie_trailer(self, contentId):
        cp_id, mpd = self.get_mpd_file(contentId, "MOVIE")
        if cp_id == None:
            return None
        url = "/besc?action=GetCDN&channel={channel}&type=TRAILER&asJson=Y&serviceName={serviceName}&providerName={providerName}&deviceType=CHROME&cp_id="+cp_id
        r = self.send_request(url, self.BASE_URL_AVS)
        if r != None:
            return r["resultObj"]["src"]
        return None
    
    def search(self, keyword, area = AREA_FREE):
        url = "/TRAY/SEARCHRECOM?keyword="+keyword+"&from=0&to=100&area="+area+"&category=ALL&deviceType={deviceType}&serviceName={serviceName}"
        r = self.send_request(url, self.BASE_URL_TIM)
        if r!=None:
            return r["resultObj"]["containers"][0]["items"] if r["resultObj"]["total"] > 0 else {}
        return None

    def get_widevine_response(self, widevineRequest, widevine_url):
        for count in range(0,3):
            Logger.log_on_desktop_file("Trying to get widevine license", filename=Logger.LOG_WIDEVINE_FILE)
            resp = self.license_endpoint.post(widevine_url, data=widevineRequest)
            Logger.log_on_desktop_file("Status code: "+str(resp.status_code), filename=Logger.LOG_WIDEVINE_FILE)
            if resp.status_code == 200:
                Logger.log_on_desktop_file("We get it! WOW", filename=Logger.LOG_WIDEVINE_FILE)
                return resp.content
        return None

    def set_playing_media(self, url, contentId, start_time, content_type, duration):
        self.player.setItem(url, contentId, start_time, content_type, duration)

    def keep_alive(self, contentId):
        url = "/besc?action=KeepAlive&channel={channel}&type={deviceType}&noRefresh=Y&providerName={providerName}&serviceName={serviceName}&contentId="+str(contentId)
        r = self.send_request(url, self.BASE_URL_AVS)
        if r!=None:
            return True
        return False

    def set_seen(self, contentId, duration):
        return self.stop_content(contentId, duration, duration)

    def pause_consumption(self, contentId, time, threshold):
        url = "/besc?action=PauseConsumption&channel={channel}&providerName={providerName}&serviceName={serviceName}&bookmark="+str(time)+"&deltaThreshold="+str(threshold)
        r = self.send_request(url, self.BASE_URL_AVS)
        if r != None:
            return True
        return False

    def stop_content(self, contentId, time, threshold):
        url = "/besc?action=StopContent&channel={channel}&providerName={providerName}&serviceName={serviceName}&type=VOD&contentId="+str(contentId)+"&bookmark="+str(time)+"&deltaThreshold="+str(threshold)+"&section=CATALOGUE"
        r = self.send_request(url, self.BASE_URL_AVS)
        if r!=None:
            return True
        return False

    def get_recommended_by_content_id(self, content_id):
        url = "/TRAY/RECOM?deviceType={deviceType}&serviceName={serviceName}&dataSet=RICH&recomType=MORE_LIKE_THIS&contentId="+content_id+"&maxResults=25"
        return self.get_contents(url)