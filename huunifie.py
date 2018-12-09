#!/usr/bin/env python3
# coding=utf-8
"""
Licensed under WTFPL.
http://www.wtfpl.net/about/
"""
__version__ = '0.1'
__author__ = 'kurisuD'

import argparse
import logging
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


class HueClient:
    """
    Connects to the Hue hub, enable or disable the schedules.
    """

    def __init__(self, args):
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
                        logging.info(msg)
        except ConnectionError:
            logging.error(f"Unable to connect to hue bridge using {self._url_prefix}")


class UnifiClient:
    """
    Connects to the unifi controller, retrieves the wifi clients information, updates Hue schedules.
    """

    def __init__(self, args):
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
        logging.debug(auth_data)
        try:
            login_response = self._unifi_session.post(url=url, verify=False, data=auth_data)
        except ConnectionError:
            logging.error(f"Unable to connect to the Unifi controller using {self._url_prefix}")
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
        logging.debug(self._current_wifi_clients)

    def _eval_is_someone_home(self):
        rtn = 0
        for c in self._current_wifi_clients:
            logging.debug(c.values())
            logging.debug(self._wifi_clients)
            logging.debug(set(self._wifi_clients).intersection(c.values()))
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


def save_config(config_file: Path, args: argparse):
    """
    Save current settings to config
    """

    config = configparser.ConfigParser()
    config["general"] = {}
    if not args.interval:
        args.interval = __interval__
    config["general"]["interval"] = f"{args.interval}"
    if not args.wifi_clients:
        args.wifi_clients = __wifi_clients_example__
    config["general"]["wifi_clients"] = ",".join(args.wifi_clients)
    if not args.schedules_names:
        args.schedules_names = __schedules_names_example__
    config["general"]["schedules_name"] = ",".join(args.schedules_names)
    config["unifi"] = {}
    if not args.unifi_host:
        args.unifi_host = __unifi_controller_host__
    config["unifi"]["host"] = args.unifi_host
    if not args.unifi_port:
        args.unifi_port = __unifi_controller_port__
    config["unifi"]["port"] = f"{args.unifi_port}"
    if not args.unifi_username:
        args.unifi_username = __unifi_controller_user__
    config["unifi"]["username"] = args.unifi_username
    if not args.unifi_password:
        args.unifi_password = __unifi_controller_pwd__
    config["unifi"]["password"] = args.unifi_password
    config["hue"] = {}
    if not args.hue_host:
        args.hue_host = __hue_hub_host__
    config["hue"]["host"] = args.hue_host
    if not args.hue_port:
        args.hue_port = __hue_hub_port__
    config["hue"]["port"] = f"{args.hue_port}"
    if not args.hue_key:
        args.hue_key = __hue_key__
    config["hue"]["key"] = args.hue_key
    with config_file.open(mode='w') as configfile:
        config.write(configfile)
    logging.info(f"Configuration saved to {str(config_file)}")


def load_config(config_file: Path, args: argparse):
    """
    Load settings from config, unless otherwise provided on the command line.
    """
    config = configparser.ConfigParser()
    with config_file.open() as configfile:
        config.read_file(configfile)

    if not args.interval:
        args.interval = int(config["general"]["interval"])
    if not args.wifi_clients:
        args.wifi_clients = config["general"]["wifi_clients"].split(",")
    if not args.schedules_names:
        args.schedules_names = config["general"]["schedules_name"].split(",")
    if not args.unifi_host:
        args.unifi_host = config["unifi"]["host"]
    if not args.unifi_port:
        args.unifi_port = int(config["unifi"]["port"])
    if not args.unifi_username:
        args.unifi_username = config["unifi"]["username"]
    if not args.unifi_password:
        args.unifi_password = config["unifi"]["password"]
    if not args.hue_host:
        args.hue_host = config["hue"]["host"]
    if not args.hue_port:
        args.hue_port = int(config["hue"]["port"])
    if not args.hue_key:
        args.hue_key = config["hue"]["key"]
    logging.info(f"Configuration loaded from {str(config_file)}")
    if args.verbose:
        logging.info(args)


def main():
    """
    Entry point.
    """
    arguments = _read_cli_arguments()
    _setup_logger(arguments)
    config_file = Path(arguments.config_file).expanduser()
    if config_file.exists():
        load_config(config_file, arguments)
    else:
        logging.warning(f"Configuration file {str(config_file)} not found.")

    if arguments.save_config:
        save_config(config_file, arguments)

    urllib3.disable_warnings()
    uc = UnifiClient(arguments)
    uc.run()


def _read_cli_arguments():
    parser = argparse.ArgumentParser(description=__desc__,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-uh", "--unifi_host",
                        help="Unifi controller hostname",
                        type=str)
    parser.add_argument("-up", "--unifi_port",
                        help="Unifi controller port",
                        type=int)
    parser.add_argument("-uu", "--unifi_username",
                        help="Unifi controller username",
                        type=str)
    parser.add_argument("-uw", "--unifi_password",
                        help="Unifi controller password",
                        type=str)

    parser.add_argument("-hh", "--hue_host",
                        help="Hue hub hostname",
                        type=str)
    parser.add_argument("-hp", "--hue_port",
                        help="Hue hub port",
                        type=int)
    parser.add_argument("-hk", "--hue_key",
                        help="Hue hub API key",
                        type=str)

    parser.add_argument("-wc", "--wifi_clients",
                        help="Wifi clients (hostname or mac) to monitor. Clients names are separated by spaces.",
                        nargs="+",
                        type=str)

    parser.add_argument("-sn", "--schedules_names",
                        help="""Schedules to respectively enable/disable based on the wifi clients presence/absence.
                            Schedule names with space(s) to be double-quoted.
                            Schedule names are separated by spaces.""",
                        nargs="+",
                        type=str)

    parser.add_argument("-i", "--interval",
                        help="Polling interval",
                        type=int)

    parser.add_argument("-v", "--verbose",
                        help="Prints events information on the console.",
                        action="store_true")
    parser.add_argument("-d", "--debug",
                        help="Verbose mode.",
                        action="store_true")

    parser.add_argument("-c", "--config_file",
                        help="Path to configuration file. A template can be created by using the -s option below.",
                        default=__config_path__,
                        type=Path)

    parser.add_argument("-s", "--save_config",
                        help="Safe configuration given on the command line to the configuration file.",
                        action="store_true")

    return parser.parse_args()


def _setup_logger(args):
    level = logging.WARNING
    if args.verbose:
        level = logging.INFO

    if args.debug:
        level = logging.DEBUG

    logging.basicConfig(level=level,
                        format='%(asctime)s [%(levelname)7s] : %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info("User interrupted.")
