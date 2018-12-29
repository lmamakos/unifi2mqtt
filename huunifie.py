#!/usr/bin/env python3
# coding=utf-8
"""
Licensed under WTFPL.
http://www.wtfpl.net/about/
"""
__app_name__ = 'huunifie'
__version__ = '0.2'
__author__ = 'kurisuD'

import argparse
import logging
from logging import config
from logging.handlers import SysLogHandler, TimedRotatingFileHandler
from pathlib import Path

import requests
from requests.exceptions import ConnectionError
import json
import time
import urllib3
import configparser

__desc__ = """A Hue bridge and Unifi controller client.
Enables/disables specified Hue schedules in the presence/absence of specified wifi devices on the Unifi controller."""

__interval__ = 3
__config_path__ = Path("~/.config/huunifie.conf")
__log_path__ = Path("/tmp") / f'{__app_name__}.log'

__unifi_controller_host__ = "localhost"
__unifi_controller_port__ = 8443
__unifi_controller_user__ = "hue"
__unifi_controller_pwd__ = "hue_password!!"

__unifi_api_login__ = "/api/login"
__unifi_api_clients_stats__ = "/api/s/default/stat/sta"

__hue_hub_host__ = "hue"
__hue_hub_port__ = 80
__hue_key__ = "Your_40_alphanumeric_hue_api_key_please."

__wifi_clients_example__ = ["01:23:45:67:89:ab", "your_device_hostname"]
__schedules_names_example__ = ["A schedule name with spaces", "another_without"]

__LOGGING__ = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)7s] | %(module)s : %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %Z'
        },
        'simple': {
            'format': '%(asctime)s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %Z'
        },
    },
    'handlers': {
        'sysout': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        __app_name__: {
            'handlers': ['sysout'],
            'propagate': True,
            'level': 'INFO',
        }
    },
}


class HueClient:
    """
    Connects to the Hue hub, enable or disable the schedules.
    """

    def __init__(self, args):
        self.logger = logging.getLogger(__app_name__)
        self._url_prefix = f"http://{args.hue_host}:{args.hue_port}/api/{args.hue_key}"
        self._schedules_names = args.schedules_names

    def change_schedules(self, enabled=False):
        """
        Connects to the Hue hub, enable or disable the schedules.
        :param enabled:
        """
        status = "enabled" if enabled else "disabled"
        url = f"{self._url_prefix}/schedules"
        try:
            schedules_raw = requests.get(url)
            if schedules_raw.ok:
                for schedule_id, schedule in json.loads(schedules_raw.content).items():
                    if schedule["name"] in self._schedules_names:
                        msg = f'Schedule "{schedule["name"]}" (id={schedule_id}) is {schedule["status"]}.'
                        if schedule["status"] != status:
                            msg += f" Changing to {status}."
                            requests.put(f"{url}/{schedule_id}", data=json.dumps({'status': status}))
                            self.logger.warning(msg)
                        else:
                            self.logger.info(msg)
        except ConnectionError:
            self.logger.error(f"Unable to connect to hue bridge using {self._url_prefix}")


class UnifiClient:
    """
    Connects to the unifi controller, retrieves the wifi clients information, updates Hue schedules.
    """

    def __init__(self, args):
        self.logger = logging.getLogger(__app_name__)
        self._url_prefix = f"https://{args.unifi_host}:{args.unifi_port}"
        self._auth_json = {"username": args.unifi_username, "password": args.unifi_password, "strict": True}
        self._unifi_session = requests.session()
        self._logged_in = False
        self._current_wifi_clients = []
        self._wifi_clients = args.wifi_clients
        self._someone_home = False
        self._interval = args.interval
        self.hc = HueClient(args)

    @property
    def someone_home(self) -> bool:
        """
        True when a device to monitor is found connected to the unifi system.
        """
        return self._someone_home

    @someone_home.setter
    def someone_home(self, value: bool):
        self._someone_home = value
        self.hc.change_schedules(self._someone_home)

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
        url = f"{self._url_prefix}{__unifi_api_login__}"
        auth_data = json.dumps(self._auth_json)
        self.logger.debug(auth_data)
        try:
            login_response = self._unifi_session.post(url=url, verify=False, data=auth_data)
        except ConnectionError:
            self.logger.error(f"Unable to connect to the Unifi controller using {self._url_prefix}")
            return False
        self.logged_in = login_response.ok
        return self.logged_in

    def _get_clients_info(self) -> str:
        while not self.logged_in:
            self._login()
            time.sleep(self._interval)
        url = f"{self._url_prefix}{__unifi_api_clients_stats__}"
        get_response = self._unifi_session.get(url=url, verify=False)
        if get_response.status_code == 200:
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
                for prop in ["mac", "name", "hostname"]:
                    if prop in client:
                        wc[prop] = client[prop]
                self._current_wifi_clients.append(wc)
        self.logger.debug(self._current_wifi_clients)

    def _eval_is_someone_home(self):
        rtn = 0
        for c in self._current_wifi_clients:
            self.logger.debug(c.values())
            self.logger.debug(self._wifi_clients)
            self.logger.debug(set(self._wifi_clients).intersection(c.values()))
            rtn += len(set(self._wifi_clients).intersection(c.values()))
        self.someone_home = bool(rtn)

    def current_wifi_clients(self) -> list:
        """
        List of devices connected to Unifi. Each device is a dictionnary with at least the mac address.
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


class Huunifie:
    """
    Main class
    """

    def __init__(self):
        self.arguments = self._read_cli_arguments()
        self.logger = None
        self._setup_logger()
        self.config_file = Path(self.arguments.config_file).expanduser()
        if self.config_file.exists():
            self.load_config()
        else:
            self.logger.warning(f"Configuration file {str(self.config_file)} not found.")

        if self.arguments.save_config:
            self.save_config()

        urllib3.disable_warnings()

    def save_config(self):
        """
        Save current settings to configuration file
        """

        hconfig = configparser.ConfigParser()
        hconfig["general"] = {}
        if not self.arguments.interval:
            self.arguments.interval = __interval__
        hconfig["general"]["interval"] = f"{self.arguments.interval}"
        if not self.arguments.wifi_clients:
            self.arguments.wifi_clients = __wifi_clients_example__
        hconfig["general"]["wifi_clients"] = ",".join(self.arguments.wifi_clients)
        if not self.arguments.schedules_names:
            self.arguments.schedules_names = __schedules_names_example__
        hconfig["general"]["schedules_name"] = ",".join(self.arguments.schedules_names)
        hconfig["unifi"] = {}
        if not self.arguments.unifi_host:
            self.arguments.unifi_host = __unifi_controller_host__
        hconfig["unifi"]["host"] = self.arguments.unifi_host
        if not self.arguments.unifi_port:
            self.arguments.unifi_port = __unifi_controller_port__
        hconfig["unifi"]["port"] = f"{self.arguments.unifi_port}"
        if not self.arguments.unifi_username:
            self.arguments.unifi_username = __unifi_controller_user__
        hconfig["unifi"]["username"] = self.arguments.unifi_username
        if not self.arguments.unifi_password:
            self.arguments.unifi_password = __unifi_controller_pwd__
        hconfig["unifi"]["password"] = self.arguments.unifi_password
        hconfig["hue"] = {}
        if not self.arguments.hue_host:
            self.arguments.hue_host = __hue_hub_host__
        hconfig["hue"]["host"] = self.arguments.hue_host
        if not self.arguments.hue_port:
            self.arguments.hue_port = __hue_hub_port__
        hconfig["hue"]["port"] = f"{self.arguments.hue_port}"
        if not self.arguments.hue_key:
            self.arguments.hue_key = __hue_key__
        hconfig["hue"]["key"] = self.arguments.hue_key
        with self.config_file.open(mode='w') as configfile:
            hconfig.write(configfile)
        self.logger.info(f"Configuration saved to {str(self.config_file)}")

    def load_config(self):
        """
        Load settings from configuration file, unless otherwise provided on the command line.
        """
        hconfig = configparser.ConfigParser()
        with self.config_file.open() as configfile:
            hconfig.read_file(configfile)

        if not self.arguments.interval:
            self.arguments.interval = int(hconfig["general"]["interval"])
        if not self.arguments.wifi_clients:
            self.arguments.wifi_clients = hconfig["general"]["wifi_clients"].split(",")
        if not self.arguments.schedules_names:
            self.arguments.schedules_names = hconfig["general"]["schedules_name"].split(",")
        if not self.arguments.unifi_host:
            self.arguments.unifi_host = hconfig["unifi"]["host"]
        if not self.arguments.unifi_port:
            self.arguments.unifi_port = int(hconfig["unifi"]["port"])
        if not self.arguments.unifi_username:
            self.arguments.unifi_username = hconfig["unifi"]["username"]
        if not self.arguments.unifi_password:
            self.arguments.unifi_password = hconfig["unifi"]["password"]
        if not self.arguments.hue_host:
            self.arguments.hue_host = hconfig["hue"]["host"]
        if not self.arguments.hue_port:
            self.arguments.hue_port = int(hconfig["hue"]["port"])
        if not self.arguments.hue_key:
            self.arguments.hue_key = hconfig["hue"]["key"]
        self.logger.info(f"Configuration loaded from {str(self.config_file)}")
        self.logger.debug(self.arguments)

    def main(self):
        """
        Entry point.
        """
        uc = UnifiClient(self.arguments)
        uc.run()

    @staticmethod
    def _read_cli_arguments():
        parser = argparse.ArgumentParser(description=__desc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument("-uh", "--unifi_host", help="Unifi controller hostname", type=str)
        parser.add_argument("-up", "--unifi_port", help="Unifi controller port", type=int)
        parser.add_argument("-uu", "--unifi_username", help="Unifi controller username", type=str)
        parser.add_argument("-uw", "--unifi_password", help="Unifi controller password", type=str)

        parser.add_argument("-hh", "--hue_host", help="Hue hub hostname", type=str)
        parser.add_argument("-hp", "--hue_port", help="Hue hub port", type=int)
        parser.add_argument("-hk", "--hue_key", help="Hue hub API key", type=str)

        parser.add_argument("-wc", "--wifi_clients",
                            help="Wifi clients (hostname or mac) to monitor. Clients names are separated by spaces.",
                            nargs="+", type=str)

        parser.add_argument("-sn", "--schedules_names",
                            help="""Schedules to respectively enable/disable based on the wifi clients presence/absence.
                                Schedule names with space(s) to be double-quoted.
                                Schedule names are separated by spaces.""",
                            nargs="+", type=str)

        parser.add_argument("-i", "--interval", help="Polling interval", type=int)

        parser.add_argument("-c", "--config_file",
                            help="Path to configuration file. A template can be created by using the -s option below.",
                            default=__config_path__, type=Path)

        parser.add_argument("-s", "--save_config",
                            help="Safe configuration given on the command line to the configuration file.",
                            action="store_true")

        parser.add_argument("-v", "--verbose", help="Prints events information on the console.", action="store_true")
        parser.add_argument("-d", "--debug", help="Verbose mode.", action="store_true")

        parser.add_argument("-l", "--log_file", help="Path to log file.", default=__log_path__, type=Path)

        parser.add_argument("-sh", "--syslog_host",
                            help="Syslog hostname. If present, the logfile is not written locally", type=str)
        parser.add_argument("-sp", "--syslog_port", help="Syslog port.", type=int, default=514)

        return parser.parse_args()

    @staticmethod
    def _get_formatter_from_dict(format_name):
        fmt_from_dict = __LOGGING__['formatters'][format_name]
        return logging.Formatter(fmt=fmt_from_dict['format'], datefmt=fmt_from_dict['datefmt'])

    def _update_sysout_formatter(self):
        sysout_fmt_name = 'verbose' if (self.arguments.verbose or self.arguments.debug) else 'simple'
        sysout_fmt = self._get_formatter_from_dict(sysout_fmt_name)
        try:
            assert (len(self.logger.handlers) == 1)
            self.logger.handlers[0].setFormatter(sysout_fmt)
        except AssertionError:
            print(f"_update_sysout_formatter is to be called before any handlers are added")

    def _add_syslog_handler(self):
        """Adds a SysLogHandler, with minimum logging set to WARNING and a 'verbose' format"""
        level = logging.DEBUG if self.arguments.debug else logging.WARNING
        syslog_hdlr = SysLogHandler(address=(self.arguments.syslog_host, self.arguments.syslog_port))
        syslog_hdlr.setLevel(level)
        syslog_hdlr.setFormatter(self._get_formatter_from_dict('verbose'))
        self.logger.addHandler(syslog_hdlr)

    def _add_logfile_handler(self):
        """Adds a TimedRotatingFileHandler, with minimum logging set to WARNING and a 'verbose' format"""
        level = logging.DEBUG if self.arguments.debug else logging.WARNING
        logfile_hdlr = TimedRotatingFileHandler(filename=self.arguments.log_file, when='D', backupCount=15)
        logfile_hdlr.setLevel(level)
        logfile_hdlr.setFormatter(self._get_formatter_from_dict('verbose'))
        self.logger.addHandler(logfile_hdlr)

    def _setup_logger(self):
        level = logging.INFO if self.arguments.verbose else logging.WARNING
        level = logging.DEBUG if self.arguments.debug else level
        logging.config.dictConfig(__LOGGING__)
        self.logger = logging.getLogger(__app_name__)
        self._update_sysout_formatter()
        self.logger.setLevel(level)
        if self.arguments.syslog_host:
            self._add_syslog_handler()
        elif self.arguments.log_file:
            self._add_logfile_handler()
        level_name = logging.getLevelName(self.logger.getEffectiveLevel())
        self.logger.info(f"Logging activated with level {level_name}")


if __name__ == '__main__':
    try:
        Huunifie().main()
    except KeyboardInterrupt:
        logging.info("User interrupted.")
