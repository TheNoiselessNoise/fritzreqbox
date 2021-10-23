import sys
import json
import hashlib
import requests as r
from bs4 import BeautifulSoup


class StaticPages:
    def __init__(self):
        self.login_sid = "/login_sid.lua"
        self.index = "/index.lua"
        self.data = "/data.lua"


class Funcs:
    @staticmethod
    def get_host(h):
        if h:
            if h.startswith("http://") or h.startswith("https://"):
                return h
            return "http://" + h
        return None

    @staticmethod
    def find_xml(text, tag):
        soup = BeautifulSoup(text, "xml")
        return soup.find(tag).getText().strip()

    @staticmethod
    def decode_unicode(txt):
        enc = txt.encode("ascii", "ignore")
        return enc.decode("utf-8").strip()

    @staticmethod
    def error(msg):
        print(msg)
        sys.exit();


class FritzReqBox:
    def __init__(self, x):
        self.username = x["user"] if "user" in x.keys() else ""
        self.password = x["pass"] if "pass" in x.keys() else ""
        self.host = Funcs.get_host(x["host"]) or ""
        self.session = r.Session()
        self.pages = StaticPages()
        self.sid = self.get_sid()

        if not self.sid:
            Funcs.error("Couldn't generate sid! Did you mistype anything?")


    def get_general_information(self):
        overview_json = self.get_data_dict("overview")
        netdev_json = self.get_data_dict("netDev")
        fritzos = overview_json["data"]["fritzos"]
        internet = overview_json["data"]["internet"]
        devices = overview_json["data"]["net"]["devices"]
        gen_info = {
            "Product": {
                "Name": fritzos["Productname"],
                "Firmware": {
                    "Version": fritzos["nspver"],
                    "UpdateAvailable": fritzos["isUpdateAvail"]
                },
                "Lan": {
                    "IP": netdev_json["data"]["fbox"][0]["ipv4"],
                    "MAC": netdev_json["data"]["fbox"][0]["mac"]
                }
            },
            "Internet": {
                "Provider": internet["txt"][0].split(": ")[1],
                "Since": internet["txt"][1][-17:],
                "Upload": Funcs.decode_unicode(internet["up"]),
                "Download": Funcs.decode_unicode(internet["down"])
            },
            "ConnectedDevices": [x["name"] for x in devices]
        }

        return json.dumps(gen_info, indent=4)

    def get_all_devices(self):
        conn_info = {
            "ConnectedDevices": self.get_connected_devices(),
            "HistoryDevices": self.get_not_connected_devices()
        }

        return json.dumps(conn_info, indent=4)

    def get_connected_devices(self):
        netdev_json = self.get_data_dict("netDev")
        active_devices = netdev_json["data"]["active"]
        conn_info = [self.get_device_info("name", x["name"], active_devices) for x in active_devices]
        return json.dumps(conn_info, indent=4)

    def get_not_connected_devices(self):
        netdev_json = self.get_data_dict("netDev")
        history_devices = netdev_json["data"]["passive"]
        conn_info = [self.get_device_info("name", x["name"], history_devices) for x in history_devices]
        return json.dumps(conn_info, indent=4)

    def get_device_info(self, key, value, jsn=None):
        device_json = self.get_device_json(key, value, jsn)

        if not device_json:
            return None

        return {
            "Name": device_json["name"],
            "IP": device_json["ipv4"],
            "MAC": device_json["mac"]
        }

    def get_device_json(self, key, value, jsn=None):
        if not jsn:
            jsn = self.get_data_dict("netDev")

        if type(jsn) is list:
            devices = jsn
        else:
            if "data" in jsn.keys():
                devices = jsn["data"]["active"] + jsn["data"]["passive"]
            else:
                devices = jsn

        for device in devices:
            if device[key] == value:
                return device

        return None

    def get_data_dict(self, name, headers=None, usepost=True):
        if not headers:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = self.get_data_text(name, headers=headers, usepost=usepost)
        return json.loads(data)

    def get_data_text(self, name, headers=None, usepost=True):
        if not headers:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
        # xhr=1&sid=1685383074749b30&lang=en&page=netDev&xhrId=cleanup&useajax=1&no_sidrenew=
        return self.get_text(self.host + self.pages.data, {
            "xhr": 1,
            "sid": self.sid,
            "page": name,
            "lang": "en",
            "xhrId": "all"
        }, headers=headers, usepost=usepost)

    def get_page_text(self, name, params=None):
        page = self.get_page(name)

        if not params:
            params = {}

        if page and "lua" in page.keys():
            return self.get_text(self.host + "/" + page["lua"], params)

        return None

    def get_page(self, name):
        pages = self.get_available_pages()

        if name in pages.keys():
            return pages[name]

        return None

    def get_available_pages(self):
        pagestxt = self.get_text(self.host + self.pages.index, {
            "sid": self.sid,
            "lp": "overview"
        })
        pagesjson = self.get_json(pagestxt)
        pagesdict = json.loads(pagesjson)

        if "pages" in pagesdict.keys():
            return pagesdict["pages"]
        return None

    @staticmethod
    def get_md5(challenge, password):
        hash_text = (challenge + "-" + password).encode("UTF-16LE")
        hashed = hashlib.md5(hash_text).hexdigest()
        return challenge + "-" + hashed

    def get_text(self, url, params=None, headers=None, usepost=False):
        if not params:
            params = {}
        if usepost:
            return self.session.post(url, data=params, headers=headers).text.strip()
        return self.session.get(url, params=params, headers=headers).text.strip()

    def get_sid(self):
        try:
            sidtext = self.get_text(self.host + self.pages.login_sid)
            sid = Funcs.find_xml(sidtext, "SID")
            challenge = Funcs.find_xml(sidtext, "Challenge")

            if sid == "0000000000000000":
                gensidtext = self.get_text(self.host + self.pages.login_sid, {
                    "username": self.username,
                    "response": self.get_md5(challenge, self.password)
                })
                return Funcs.find_xml(gensidtext, "SID")

            return None
        except:
            return None

    @staticmethod
    def get_json(txt):
        soup = BeautifulSoup(txt, "html.parser")
        scripts = soup.find_all("script")
        mscr = scripts[-1].getText().strip()
        mainscr = mscr.split("main.init(")[1].split(");")[0]
        return mainscr
