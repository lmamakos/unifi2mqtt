# unifi2mqtt - the result of hunifie as an organ donor

I've ruthlessly hacked on the guts of `hunnifie`, ripped asunder the Hue bridge and 0MQ/ZMQ logic
and replaced it with some hot MQTT publishing action.  It fit in there OK once I had a running start.

## why

The general idea here is to use this platform to implement [Home Assistant](https://home-assistant.io) 
`device_tracker` entities using the [JSON MQTT Device Tracker](https://www.home-assistant.io/components/mqtt_json/)
platform, one of many types of [Presence Detection](https://www.home-assistant.io/components/#presence-detection) 
integrations.  It queries the UniFi manager application of a list of devices, and will publish updates via MQTT 
with a JSON payload for *only* those devices that you specify.

This is intended as a workaround for the recently updated 
[UniFi integration](https://www.home-assistant.io/components/unifi/) which has lost the ability
to selectively allow only specific devices to have their presence known by creating `device_tracker`
entities.

## how

### unifi2mqtt operation

You can select which devices selected by specifing the MAC address or the hostname.  Please note
that the matches are simple, case senstive textual matches.  So the mac address you specify ought to
be in lower case to match the JSON payload from UniFi.  If you want to use the Hostname, ensure that
the case matches.  

You could also match on the IP address, though honestly, I'm not sure how UniFi 
figures that out -- on my system, the DHCP server isn't on a UniFi managed device, so it must
wiretap the traffic, maybe look at ARP responses or something?

This software, when a desired device is detected, will publish an MQTT payload like this:

```
 {"mac": "70:ef:00:06:be:ef", "hostname": "iPhone", 
  "ap_mac": "f0:9f:c2:26:1e:ca", "bssid": "f2:9f:c2:28:1e:ca", "ip": "10.0.1.42",
  "latitude": 44.4200, "longitude": -78.1234, "gps_accuracy": 20}
```

to a topic constructed by a prefix you specify, appened with the MAC address, such as:

```
19916/unifi-clients/70:ef:00:06:be:ef: 
```

The latitude and logitude are also specified as options (or in from the configuration file), and probably should
match the latitude and logitude of your Home Assistant installation so that devices are considered "home".  Note
that presently, the "gps accuracy" is fixed at 20 meters.

There's nothing fancy here to select by Wi-Fi network name or site or anything like that.  I'm not even
sure how the API is supposed work... remember, this is just a drive-by shooting and kidnapping of some
existing code.  I didn't look too hard at the parts that seemed to work Just Fine to figure out why
they worked like they did.  Just a hack, both quick and dirty.

### Home Assistant configuration

The Home Assistant configuration would look something like this:

```
device_tracker:
  - platform: mqtt_json
    qos: 0
    devices:
      iphone: 19916/unifi-clients/70:ef:00:06:be:ef
```

## Epilog and apology

As part of the process, I've renamed it so that the original's reputation won't suffer from the
poor reputation of this effort.   As a tribute, I've left the original README.md file below.  While
the options have changed around a bit, the general approach of managing configuration data, options
and the like are preserved, though some of the defaults are changed here and there.

Please, for the love of DOG and all that is holy, do not bother the original author of `huunifie` 
with questions that might come from using these changes that I slammed into his code.  I apologize.


# huunifie
A Hue bridge and Unifi controller client. Enables/disables specified Hue schedules in the presence/absence of specified wifi devices on the Unifi controller.

## Installation

huunifie can be installed with the following command:

`python3 -m pip install huunifie`

## Compatibility information

This code was only tested with python 3.5 and above under GNU/Linux with a Unify controller 5.9.29 and a hue bridge API version 1.28.0.

## Usage
```
you@computer:~$ python3 -m huunifie --help
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
  --no_pub              Disables zmq publication
  --pub                 Enables zmq publication
  --pub_host PUB_HOST   Host for zmq publication (default: *)
  --pub_port PUB_PORT   Port for zmq publication (default: 12168)
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

A Hue bridge and Unifi controller client. Enables/disables specified Hue
schedules in the presence/absence of specified wifi devices on the Unifi
controller.
```

## Configuration
You can create a template configuration file by running huunifie with only the -s flag.

You can also test values on one or more different arguments then, adding -s to update your configuration.
Only values specified on the command line will be update in the config file.

### Examples:
* Create a config file:

```
you@computer:~$ python3 -m huunifie -s -v -c /tmp/test_huunifie.conf
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
you@computer:~$ python3 -m huunifie -hh hue -uh unifi -v -s -c /tmp/test_huunifie.conf
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