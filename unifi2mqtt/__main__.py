#!/usr/bin/env python3
# coding=utf-8
"""
Licensed under WTFPL.
http://www.wtfpl.net/about/
"""
from unifi2mqtt import UniFi2MQTT
import logging

if __name__ == '__main__':
    try:
        UniFi2MQTT().main()
    except KeyboardInterrupt:
        logging.info("User interrupted.")
        logging.shutdown()
