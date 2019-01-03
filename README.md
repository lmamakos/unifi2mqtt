# huunifie
A Hue bridge and Unifi controller client. Enables/disables specified Hue schedules in the presence/absence of specified wifi devices on the Unifi controller.

## Compatibility information

This code will only work with python 3.6 and above due to its use of f-strings.

It has only been tested under GNU/Linux with a Unify controller 5.9.29 and a hue bridge API version 1.28.0.

## Usage
```
you@computer:~$ huunifie.py --help
usage: huunifie.py [-h] [-uh UNIFI_HOST] [-up UNIFI_PORT] [-uu UNIFI_USERNAME]
                   [-uw UNIFI_PASSWORD] [-hh HUE_HOST] [-hp HUE_PORT]
                   [-hk HUE_KEY] [-wc WIFI_CLIENTS [WIFI_CLIENTS ...]]
                   [-sn SCHEDULES_NAMES [SCHEDULES_NAMES ...]] [-i INTERVAL]
                   [-c CONFIG_FILE] [-s] [-v] [-d] [-l LOG_FILE]
                   [-sh SYSLOG_HOST] [-sp SYSLOG_PORT]

A Hue bridge and Unifi controller client. Enables/disables specified Hue
schedules in the presence/absence of specified wifi devices on the Unifi
controller.

optional arguments:
  -h, --help            show this help message and exit
  -uh UNIFI_HOST, --unifi_host UNIFI_HOST
                        Unifi controller hostname (default: None)
  -up UNIFI_PORT, --unifi_port UNIFI_PORT
                        Unifi controller port (default: None)
  -uu UNIFI_USERNAME, --unifi_username UNIFI_USERNAME
                        Unifi controller username (default: None)
  -uw UNIFI_PASSWORD, --unifi_password UNIFI_PASSWORD
                        Unifi controller password (default: None)
  -hh HUE_HOST, --hue_host HUE_HOST
                        Hue hub hostname (default: None)
  -hp HUE_PORT, --hue_port HUE_PORT
                        Hue hub port (default: None)
  -hk HUE_KEY, --hue_key HUE_KEY
                        Hue hub API key (default: None)
  -wc WIFI_CLIENTS [WIFI_CLIENTS ...], --wifi_clients WIFI_CLIENTS [WIFI_CLIENTS ...]
                        Wifi clients (hostname or mac) to monitor. Clients
                        names are separated by spaces. (default: None)
  -sn SCHEDULES_NAMES [SCHEDULES_NAMES ...], --schedules_names SCHEDULES_NAMES [SCHEDULES_NAMES ...]
                        Schedules to respectively enable/disable based on the
                        wifi clients presence/absence. Schedule names with
                        space(s) to be double-quoted. Schedule names are
                        separated by spaces. (default: None)
  -i INTERVAL, --interval INTERVAL
                        Polling interval (default: None)
  -c CONFIG_FILE, --config_file CONFIG_FILE
                        Path to configuration file. A template can be created
                        by using the -s option below. (default:
                        ~/.config/huunifie.conf)
  -s, --save_config     Safe configuration given on the command line to the
                        configuration file. (default: False)
  -v, --verbose         Prints events information on the console. (default:
                        False)
  -d, --debug           Verbose mode. (default: False)
  -l LOG_FILE, --log_file LOG_FILE
                        Path to log file. (default: None)
  -sh SYSLOG_HOST, --syslog_host SYSLOG_HOST
                        Syslog hostname. If present, the logfile is not
                        written locally (default: None)
  -sp SYSLOG_PORT, --syslog_port SYSLOG_PORT
                        Syslog port. (default: 514)
```

## Configuration
You can create a template configuration file by running huunifie with only the -s flag.

You can also test values on one or more different arguments then, adding -s to update your configuration.
Only values specified on the command line will be update in the config file.

### Examples:
* Create a config file:

```
you@computer:~$ huunifie.py -s -v -c /tmp/test_huunifie.conf
2018-12-10 21:55:38 [WARNING] : Configuration file /tmp/test_huunifie.conf not found.
2018-12-10 21:55:38 [   INFO] : Configuration saved to /tmp/test_huunifie.conf
2018-12-10 21:55:38 [  ERROR] : Unable to connect to the Unifi controller using https://localhost:8443
^C
you@computer:~$  cat /tmp/test_huunifie.conf
[general]
interval = 3
wifi_clients = 01:23:45:67:89:ab,your_device_hostname
schedules_name = A schedule name with spaces,another_without

[unifi]
host = localhost
port = 8443
username = hue
password = hue_password!!

[hue]
host = hue
port = 80
key = Your_40_alphanumeric_hue_api_key_please.
```

* Update an existing config file

```
you@computer:~$ huunifie.py -hh hue -uh unifi -v -s -c /tmp/test_huunifie.conf
2018-12-10 21:59:06 [   INFO] : Configuration loaded from /tmp/test_huunifie.conf
2018-12-10 21:59:06 [   INFO] : Configuration saved to /tmp/test_huunifie.conf
2018-12-10 21:59:06 [  ERROR] : Unable to connect to the Unifi controller using https://unifi:8443
^C
you@computer:~$ cat /tmp/test_huunifie.conf
[general]
interval = 3
wifi_clients = 01:23:45:67:89:ab,your_device_hostname
schedules_name = A schedule name with spaces,another_without

[unifi]
host = unifi
port = 8443
username = hue
password = hue_password!!

[hue]
host = hue
port = 80
key = Your_40_alphanumeric_hue_api_key_please.

```
