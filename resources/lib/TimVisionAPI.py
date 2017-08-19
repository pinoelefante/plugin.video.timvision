import json
import threading
import time
import urllib
from requests import session, cookies

RECOM_TOP_VIEW = "TOP_VIEWED"
RECOM_MOST_RECENT = "MOST_RECENT"
RECOM_FOR_YOU = "RECOM_FOR_YOU"
RECOM_EXPIRING = "EXPIRING"

class TimVisionSession:
    base_url = 'https://www.timvision.it/AVS'
    deviceType = 'WEB'
    service_name = 'CUBOVISION'
    service_channel = 'CUBOWEB'
    app_version = '10.0.47'
    api_endpoint = session()
    license_endpoint = session()
    user_http_header = "X-Avs-Username"
    widevine_proxy_url = "https://license.cubovision.it/WidevineManager/WidevineManager.svc/GetLicense/{ContentIdAVS}/{AssetIdWD}/{CpId}/{Type}/{ClientTime}/{Channel}/{DeviceType}"

    def __init__(self):
        self.api_endpoint.headers.update({
            'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept-Encoding' : 'gzip, deflate',
        })
        self.license_endpoint.headers.update({
            'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept-Encoding' : 'gzip, deflate',
            'Host' : 'license.timvision.it',
            'Origin' : 'https://www.timvision.it'
        })
        self.setup()

    def setup(self):
        return self.load_app_settings() and self.load_app_version()

    def load_app_version(self):
        r = self.api_endpoint.get("https://www.timvision.it/app_ver.js")
        if r.status_code == 200:
            str1 = r.text
            #str1 = str1.rsplit('{')[1].rsplit('}')[0]
            str1 = str1.rsplit('"')[1].rsplit('"')[0]
            self.app_version = str1
            return True
        return False
    def load_app_settings(self):
        url = '/PROPERTIES?deviceType='+self.deviceType+'&serviceName='+self.service_name
        data = self.api_send_request_tim(url)
        if data!=None:
            #self.license_acquisition_url = data['resultObj']['LICENSEACQUISITIONURL']
            self.user_http_header = data['resultObj']['USER_REQ_HEADER_NAME']
            #self.log_myfile("user_http_header = "+self.user_http_header)
            self.widevine_proxy_url = data['resultObj']['WV_PROXY_URL']
            return True
        self.log_myfile("Fail to load app_settings")
        return False
    def login(self, username, password):
        self.log_myfile("API_VERSION = "+self.app_version)
        data = {
            'username':username,
            'password':password,
            'customData':'{"customData":[{"name":"deviceType","value":'+self.deviceType+'},{"name":"deviceVendor","value":""},{"name":"accountDeviceModel","value":""},{"name":"FirmwareVersion","value":""},{"name":"Loader","value":""},{"name":"ResidentApp","value":""},{"name":"DeviceLanguage","value":"it"},{"name":"NetworkType","value":""},{"name":"DisplayDimension","value":""},{"name":"OSversion","value":"Windows 10"},{"name":"AppVersion","value":""},{"name":"DeviceRooted","value":""},{"name":"NetworkOperatoreName","value":""},{"name":"ServiceOperatorName","value":""},{"name":"Custom1","value":"Firefox"},{"name":"Custom2","value":54},{"name":"Custom3","value":"1920x1080"},{"name":"Custom4","value":"PC"},{"name":"Custom5","value":""},{"name":"Custom6","value":""},{"name":"Custom7","value":""},{"name":"Custom8","value":""},{"name":"Custom9","value":""}]}'
        }
        r = self.api_send_request("Login", method = 'POST', postData=data)
        if r!=None:
            self.api_endpoint.headers.__setitem__(self.user_http_header, r["resultObj"])
            self.sessionLoginHash = r["extObject"]["hash"]
            self.avs_cookie = self.api_endpoint.cookies.get("avs_cookie")
            self.license_endpoint.headers.__setitem__('AVS_COOKIE',self.avs_cookie)
            #self.stop_check_session = threading.Event()
            #check_thread = threading.Thread(target=self.check_session, args=(self.stop_check_session))
            #check_thread.start()
            return True
        return False
    def logout(self):
        r = self.api_send_request("Logout")
        if r!=None:
            self.api_endpoint.cookies.clear()
            self.sessionLoginHash = None
            self.api_endpoint.headers.pop(self.user_http_header, None)
            #self.stop_check_session.set()
            return True
        return False
    def is_logged(self):
        return self.sessionLoginHash != None
    def api_url(self, action, others = {}):
        query = ""
        if others!=None:
            for key,value in others:
                query += "&"+key+"="+value
        return self.base_url+"/besc?channel="+self.service_channel+"&providerName=TELECOMITALIA&serviceName="+self.service_name+"&action="+action+"&deviceType="+self.deviceType+query
    def api_send_request(self, action, method = 'GET', queryData=None, postData=None):
        url = self.api_url(action, queryData)
        r = None
        if method == "GET":
            r = self.api_endpoint.get(url)
        else:
            r = self.api_endpoint.post(url,postData)
        if r.status_code == 200:
            data = r.json()
            if data["resultCode"] == "OK":
                return data
        return None
    def api_send_request_tim(self, url, method="GET", data={}):
        if not url.startswith("https://"):
            url="https://www.timvision.it/TIM/"+self.app_version+"/PROD_WEB/IT/"+self.service_channel+"/ITALY"+url
        r = None
        if method == "GET":
            r = self.api_endpoint.get(url)
        else: 
            r = self.api_endpoint.post(url, data)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                data = data[0]
            if data["resultCode"]=="OK":
                return data
        return None
    def recommended_video(self, category):
        url = "/TRAY/RECOM?deviceType="+self.deviceType+"&serviceName="+self.service_name
        query = {
            "dataSet":"RICH",
            "orderBy":"year",
            "sortOrder":"desc",
            "area":"HOMEPAGE",
            "category":"HomePage",
            "recomType":category,
            "maxResults":"30"
        }
        url+="&"+urllib.urlencode(query)
        return self.__get_contents(url)
    def load_serie_seasons(self, serieId):
        url = "/DETAILS?contentId="+str(serieId)+"&type=SERIES&renderEngine=DELTA&deviceType="+self.deviceType+"&serviceName="+self.service_name
        return self.__get_contents(url)
    def load_serie_episodes(self, seasonId):
        url = "/DETAILS?renderEngine=DELTA&deviceType="+self.deviceType+"&serviceName="+self.service_name+"&contentId="+seasonId+"&type=SEASON"
        data = self.__get_contents(url)
        if data!=None:
            for cont in data:
                if cont["layout"] == "SEASON":
                    return cont["items"]
        return None
    def check_session(self, stop_event):
        while not stop_event.is_set():
            self.api_send_request("CheckSession")
            stop_event.wait(600)
        
    def get_license_info(self, contentId, videoType):
        mpdContent = self.get_mpd_file(contentId, videoType)
        if mpdContent != None:
            assetIdWd = self.get_assetIdWd(mpdContent["mpd"])
            return {
                'AVS_COOKIE':self.avs_cookie,
                "mpd_file":mpdContent["mpd"],
                "widevine_url":self.widevine_proxy_url.replace("{ContentIdAVS}",contentId).replace("{AssetIdWD}",assetIdWd).replace("{CpId}",mpdContent["cpId"]).replace("{Type}","VOD").replace("{ClientTime}",str(long(time.time()*1000))).replace("{Channel}",self.service_channel).replace("{DeviceType}","CHROME").replace('http://', 'https://')
            }
        return None
    def get_assetIdWd(self, mpdUrl):
        partial = mpdUrl[mpdUrl.find("DASH")+5:]
        partial = partial[0:partial.find("/")]
        return partial
    def get_mpd_file(self,contentId,videoType):
        url = "/PLAY?contentId="+contentId+"&deviceType=CHROME&serviceName="+self.service_name+"&type="+videoType
        data = self.api_send_request_tim(url)
        if data!=None:
            cpId = data["resultObj"]["cp_id"]
            mpd = data["resultObj"]["src"]
            return {"cpId": cpId, "mpd":mpd}
        return None
    def load_all_contents(self, category, begin=0, progress=49):
        end = int(begin)+progress
        url = "/TRAY/SEARCH/VOD?from="+str(begin)+"&to="+str(end)+"&sorting=order:title+asc&categoryName="+category+"&offerType=SVOD&deviceType="+self.deviceType+"&serviceName="+self.service_name
        data = self.api_send_request_tim(url)
        if data!=None:
            maxCount = data["resultObj"]["total"]
            movies = data["resultObj"]["containers"]
            if end<=maxCount:
                other_movie = self.load_all_contents(begin=end, category=category)
                if other_movie!=None:
                    movies.extend(other_movie)
            return movies
        return None
    def get_menu_categories(self):
        url = "/menu?deviceType="+self.deviceType+"&serviceName="+self.service_name
        return self.__get_contents(url)
    def get_page(self, page):
        url = "/PAGE/"+page+"?deviceType="+self.deviceType+"&serviceName="+self.service_name
        return self.__get_contents(url)
    def __get_contents(self, url,data={}):
        data = self.api_send_request_tim(url,data=data)
        if data!=None:
            return data["resultObj"]["containers"]
        return None
    def log_myfile(self, msg):
        f = open("C:\\Users\\pinoe\\Desktop\\timvision.log", "a")
        f.writelines(msg+"\n")
        f.close()