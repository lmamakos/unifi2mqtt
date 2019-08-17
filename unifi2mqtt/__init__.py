# coding=utf-8
"""
Licensed under WTFPL.
http://www.wtfpl.net/about/
"""
import argparse
import configparser
import json
import logging
from datetime import datetime

from pathlib import Path
import requests
from requests.exceptions import ConnectionError
import time
import urllib3

__app_name__ = 'unifi2mqtt'
__version__ = '0.0'

__desc__ = """A Unifi controller client.
Enables/disables specified Hue schedules in the presence/absence of specified wifi devices on the Unifi controller."""

__interval__ = 3
__config_path__ = Path(".unifi2mqtt.conf").expanduser()

__latitude__ =  0.0
__longitude__ = 0.0

__unifi_controller_host__ = "localhost"
__unifi_controller_port__ = 8443
__unifi_controller_user__ = "unifiuser"
__unifi_controller_pwd__ = "unifi_password!!"

__unifi_api_login__ = "/api/login"
__unifi_api_clients_stats__ = "/api/s/default/stat/sta"

__wifi_clients_example__ = ["01:23:45:67:89:ab", "your_device_hostname"]
__grace_period__ = 15

import paho.mqtt.client as mqtt
__mqttbroker__   = '10.200.0.100'
__mqttport__     = 1883
__mqttuser__     = ""
__mqttpassword__ = ""
__mqttprefix__   = '19916/unifi-clients'
__mqttqos__      = 0

class UnifiClient:
    """
    Connects to the Unifi controller, retrieves the wifi clients information, updates Hue schedules.
    """

    def __init__(self, args):
        for mandatory_value in ["unifi_host", "unifi_port", "unifi_username", "unifi_password"]:
            if mandatory_value not in args or vars(args)[mandatory_value] is None:
                raise ValueError("{} not specified in the config file nor on the command line.".format(mandatory_value))

        self._url_prefix = "https://{}:{}".format(args.unifi_host, args.unifi_port)
        self._auth_json = {"username": args.unifi_username, "password": args.unifi_password, "strict": True}
        self._unifi_session = requests.session()
        self._logged_in = False
        self._current_wifi_clients = []
        self._wifi_clients = args.wifi_clients
        self._tracked = {}
        self._grace_period = args.grace_period
        self._interval = args.interval
        self._longitude = args.longitude
        self._latitude = args.latitude
        self._mqttc = mqtt.Client(client_id=None,
                                  clean_session=True, userdata=self)
        self._mqtt_prefix = args.mqtt_prefix
        self._mqtt_qos = args.mqtt_qos
        self._mqtt_retain = False
        if args.mqtt_user and args.mqtt_user != "":
            self._mqttc.username_pw_set(args.mqtt_user, args.mqtt_password)
        self._mqttc.loop_start()
        self._mqttc.connect(args.mqtt_broker, args.mqtt_port)

    @property
    def logged_in(self) -> bool:
        """
        Our connection status to unifi.
        """
        return self._logged_in

    @logged_in.setter
    def logged_in(self, value: bool):
        self._logged_in = value

    def _login(self) -> bool:
        auth_data = json.dumps(self._auth_json)
        try:
            login_response = self._unifi_session.post(url="{}{}".format(self._url_prefix, __unifi_api_login__),
                                                      verify=False,
                                                      data=auth_data)
        except ConnectionError:
            logging.critical("Unable to connect to the Unifi controller using {}".format(self._url_prefix))
            return False
        self.logged_in = login_response.ok
        return self.logged_in

    def _get_clients_info(self) -> str:
        while not self.logged_in:
            self._login()
            time.sleep(self._interval)
        get_response = self._unifi_session.get(url="{}{}".format(self._url_prefix, __unifi_api_clients_stats__),
                                               verify=False)
        if get_response.status_code == 200:
            if isinstance(get_response.content, bytes):
                return get_response.content.decode()
            else:
                return get_response.content
        else:
            self.logged_in = False
            return ""

    def _parse_clients_info(self):
        self._current_wifi_clients = []
        clients = json.loads(self._get_clients_info())
        for client in clients["data"]:
            if not client["is_wired"]:
                wc = {}
                # 'site_id': '59407ecc3004bcd21cb1704c', 'assoc_time': 1564358306,
                #  'latest_assoc_time': 1565555777, 'oui': 'Roku', 
                # 'user_id': '5b89e3be3717860019f17fe7', '_id': '5b89e3be3717860019f17fe7', 
                # 'mac': 'c8:3a:6b:59:5a:5d', 'is_guest': False, 
                # 'first_seen': 1535763390, 'last_seen': 1565567414, 'is_wired': False, 
                # 'hostname': 'KitchenRokuStick', '_uptime_by_uap': 11637, '_last_seen_by_uap': 1565567414, 
                # '_is_guest_by_uap': False, 
                # 'ap_mac': 'f0:9f:c2:26:1e:ca', 'channel': 149, 'radio': 'na', 'radio_name': 'wifi1', 
                # 'essid': 'Mamakos5N', 'bssid': 'f2:9f:c2:28:1e:ca', 
                # 'powersave_enabled': False, 'is_11r': False, 'ccq': 333, 
                # 'rssi': 25, 'noise': -100, 'signal': -71, 'tx_rate': 78000, 'rx_rate': 117000, 
                # 'tx_power': 44, 'idletime': 2, 'ip': '10.200.20.2', 'dhcpend_time': 270, 
                # 'satisfaction': 94, 'anomalies': 0, 'vlan': 0, 'radio_proto': 'ac', 
                # 'uptime': 1209108, 
                # 'tx_bytes': 13334603717, 'rx_bytes': 703579508, 'tx_packets': 9703150, 
                # 'tx_retries': 5987874, 'wifi_tx_attempts': 15682821, 'rx_packets': 3744995, 
                # 'bytes-r': 435, 'tx_bytes-r': 48, 'rx_bytes-r': 386, 'authorized': True, 
                # 'qos_policy_applied': True, 'roam_count': 2}
                for prop in ["mac", "name", "hostname", "last_seen", "ap_mac", "bssid", "ip"]:
                    if prop in client:
                        wc[prop] = client[prop]
                wc["msg_ts"] = int(datetime.now().timestamp())
                self._current_wifi_clients.append(wc)

        logging.debug("clients: " + str(self._current_wifi_clients))

    def _publish_tracked_clients(self):
        "For each tracked client, publish current home/not_home state"
        now = int(datetime.now().timestamp())
        for _,client in self._tracked.items():
            payload = "home" if ((client["last_seen"] + self._grace_period) > now) else "not_home"

            self._mqttc.publish(self._mqtt_prefix + '/' + client['mac'] + '/home',
                                payload=payload,
                                qos=self._mqtt_qos,
                                retain=self._mqtt_retain)
            logging.debug("publish {} / {} is {} last seen={} limit={} now={}".format(
                    client["mac"], client["hostname"], payload,
                    client["last_seen"], client["last_seen"]+self._grace_period, now))
            
    def _publish_client(self, client):
        # strip out timestamps to avoid constantly changing metadata
        msg = {k : client[k] for k in client.keys() if k not in ['last_seen', 'msg_ts'] }
        msg['latitude']  = self._latitude
        msg['longitude'] = self._longitude
        msg['gps_accuracy'] = 20
        logging.info("PUBLISH: {} {}".format(client["mac"], json.dumps(msg)))
        self._mqttc.publish(self._mqtt_prefix + '/' + msg['mac'],
                            payload=json.dumps(msg), qos=self._mqtt_qos, retain=self._mqtt_retain)

    def _eval_is_someone_home(self):
        for c in self._current_wifi_clients:
            logging.debug(c.values())
            logging.debug(self._wifi_clients)
            set_wifi = set(self._wifi_clients).intersection(c.values())
            if len(set_wifi):
                self._tracked[c["mac"]] = c
                self._publish_client(c)

        # now we'll publish an updated for all the tracked clients
        self._publish_tracked_clients()

    def current_wifi_clients(self) -> list:
        """
        List of devices connected to Unifi. Each device is a dictionary with at least the mac address.
        """
        self._parse_clients_info()
        return self._current_wifi_clients

    def run(self):
        """
        Loops on getting client information from Unifi, updating the schedules accordingly.
        """
        while True:
            self.current_wifi_clients()
            self._eval_is_someone_home()
            time.sleep(self._interval)


class UniFi2MQTT:
    """
    Main class
    """

    def __init__(self):
        self.configuration = self._read_cli_arguments()
        if self.configuration.debug:
            logging.basicConfig(level=logging.DEBUG)

        self.config_file = Path(self.configuration.config_file)
        if self.config_file.exists():
            self.load_config()
        else:
            logging.warning("Configuration file {} not found.".format(str(self.config_file)))

        if self.configuration.save_config:
            self.save_config()

        if self.configuration.debug:
                logging.basicConfig(level=logging.DEBUG)

        urllib3.disable_warnings()

    def save_config(self):
        """
        Save current settings to configuration file
        """

        h_config = configparser.ConfigParser()

        h_config["general"] = {}
        if not self.configuration.interval:
            self.configuration.interval = __interval__
        h_config["general"]["interval"] = str(self.configuration.interval)

        if not self.configuration.longitude:
            self.configuration.longitude = __longitude__
        h_config["general"]["longitude"] = str(self.configuration.longitude)

        if not self.configuration.latitude:
            self.configuration.latitude = __latitude__
        h_config["general"]["longitude"] = str(self.configuration.latitude)
              
        if not self.configuration.wifi_clients:
            self.configuration.wifi_clients = __wifi_clients_example__
        h_config["general"]["wifi_clients"] = ",".join(self.configuration.wifi_clients)

        if not self.configuration.grace_period:
            self.configuration.grace_period = __grace_period__
        h_config["general"]["wifi_clients"] = str(self.configuration.grace_period)

        h_config["unifi"] = {}
        if not self.configuration.unifi_host:
            self.configuration.unifi_host = __unifi_controller_host__
        h_config["unifi"]["host"] = self.configuration.unifi_host
        if not self.configuration.unifi_port:
            self.configuration.unifi_port = __unifi_controller_port__
        h_config["unifi"]["port"] = str(self.configuration.unifi_port)
        if not self.configuration.unifi_username:
            self.configuration.unifi_username = __unifi_controller_user__
        h_config["unifi"]["username"] = self.configuration.unifi_username
        if not self.configuration.unifi_password:
            self.configuration.unifi_password = __unifi_controller_pwd__
        h_config["unifi"]["password"] = self.configuration.unifi_password

        h_config["mqtt"] = {}
        if not self.configuration.mqtt_broker:
            self.configuration.mqtt_broker = __mqttbroker__
        h_config["mqtt"]["broker"] = self.configuration.mqtt_broker

        if not self.configuration.mqtt_port:
            self.configuration.mqtt_port = __mqttport__
        h_config["mqtt"]["port"] = str(self.configuration.mqtt_port)

        if not self.configuration.mqtt_user:
            self.configuration.mqtt_user = __mqttuser__            
        h_config["mqtt"]["user"] = self.configuration.mqtt_user

        if not self.configuration.mqtt_password:
            self.configuration.mqtt_password = __mqttpassword__
        h_config["mqtt"]["password"] = self.configuration.mqtt_password

        if not self.configuration.mqtt_qos:
            self.configuration.mqtt_qos = __mqttqos__
        h_config["mqtt"]["qos"] = str(self.configuration.mqtt_qos)

        if not self.configuration.mqtt_prefix:
            self.configuration.mqtt_prefix = __mqttprefix__
        h_config["mqtt"]["prefix"] = self.configuration.mqtt_prefix

        with self.config_file.open(mode='w') as configfile:
            h_config.write(configfile)
        logging.info("Configuration saved to {}".format(str(self.config_file)))

    def load_config(self):
        """
        Load settings from configuration file, unless otherwise provided on the command line.
        """
        h_config = configparser.ConfigParser()
        with self.config_file.open() as configfile:
            h_config.read_file(configfile)
        if not ("general" in h_config.keys() and "unifi" in h_config.keys()):
            logging.warning("Configuration file {} is invalid.".format(self.config_file))
            return
        if not self.configuration.interval:
            self.configuration.interval = int(h_config["general"]["interval"])
        if not self.configuration.longitude:
            self.configuration.longitude = float(h_config["general"]["longitude"])
        if not self.configuration.latitude:
            self.configuration.latitude = float(h_config["general"]["latitude"])
        if not self.configuration.wifi_clients:
            self.configuration.wifi_clients = h_config["general"]["wifi_clients"].split(",")
        if not self.configuration.grace_period:
            self.configuration.grace_period = int(h_config["general"]["grace_period"])
        if not self.configuration.unifi_host:
            self.configuration.unifi_host = h_config["unifi"]["host"]
        if not self.configuration.unifi_port:
            self.configuration.unifi_port = int(h_config["unifi"]["port"])
        if not self.configuration.unifi_username:
            self.configuration.unifi_username = h_config["unifi"]["username"]
        if not self.configuration.unifi_password:
            self.configuration.unifi_password = h_config["unifi"]["password"]

        if not self.configuration.mqtt_broker:
            self.configuration.mqtt_broker = h_config["mqtt"]["broker"]
        if not self.configuration.mqtt_port:
            self.configuration.mqtt_port = int(h_config["mqtt"]["port"])
        if not self.configuration.mqtt_user:
            self.configuration.mqtt_user = h_config["mqtt"]["user"]
        if not self.configuration.mqtt_password:
            self.configuration.mqtt_password = h_config["mqtt"]["password"]
        if not self.configuration.mqtt_qos:
            self.configuration.mqtt_qos = int(h_config["mqtt"]["qos"])
        if not self.configuration.mqtt_prefix:
            self.configuration.mqtt_prefix = h_config["mqtt"]["prefix"]
    
        logging.info("Configuration loaded from {}".format(str(self.config_file)))
        logging.debug(self.configuration)

    def main(self):
        """
        Entry point.
        """
        try:
            uc = UnifiClient(self.configuration)
            uc.run()
        except ValueError:
            logging.info("One or mandatory argument is missing.")

    @staticmethod
    def _read_cli_arguments():
        parser = argparse.ArgumentParser(description=__desc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter, epilog=__desc__)

        parser.add_argument("-uh", "--unifi_host", help="Unifi controller hostname", type=str)
        parser.add_argument("-up", "--unifi_port", help="Unifi controller port", type=int)
        parser.add_argument("-uu", "--unifi_username", help="Unifi controller username", type=str)
        parser.add_argument("-uw", "--unifi_password", help="Unifi controller password", type=str)

        parser.add_argument("-mb", "--mqtt_broker", help="MQTT Broker", type=str)
        parser.add_argument("-mp", "--mqtt_port", help="MQTT Port", type=int)
        parser.add_argument("-mu", "--mqtt_user", help="MQTT user", type=str)
        parser.add_argument("-mw", "--mqtt_password", help="MQTT password", type=str)
        parser.add_argument("-mq", "--mqtt_qos", help="MQTT Publish QoS", type=int, choices=[0,1,2])
        parser.add_argument("-mt", "--mqtt_prefix", help="MQTT topic prefix", type=str)

        parser.add_argument("-wc", "--wifi_clients",
                            help="Wifi clients (hostname or mac) to monitor. Clients names are separated by spaces.",
                            nargs="+", type=str)
        parser.add_argument("-g", "--grace_period", 
                            help="Period in seconds before client is declared not home", type=int)

        parser.add_argument("-i", "--interval", help="Polling interval", type=int)
        parser.add_argument("--latitude", help="latitude of the site", type=float)
        parser.add_argument("--longitude", help="longitude of the site", type=float)

        parser.add_argument("-c", "--config_file",
                            help="Path to configuration file. A template can be created by using the -s option below.",
                            default=__config_path__, type=Path)

        parser.add_argument("-s", "--save_config",
                            help="Safe configuration given on the command line to the configuration file.",
                            action="store_true")

        parser.add_argument("-v", "--verbose", help="Prints events information on the console.", action="store_true")
        parser.add_argument("-d", "--debug", help="Verbose mode.", action="store_true")

        parser.add_argument("-l", "--log_file", help="Path to log file.", type=Path)

        return parser.parse_args()


__all__ = ["Uni2MQTT"]
