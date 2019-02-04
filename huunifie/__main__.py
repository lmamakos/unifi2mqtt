#!/usr/bin/env python3
# coding=utf-8
"""
Licensed under WTFPL.
http://www.wtfpl.net/about/
"""
from huunifie import Huunifie
import logging

if __name__ == '__main__':
    try:
        Huunifie().main()
    except KeyboardInterrupt:
        logging.info("User interrupted.")
        logging.shutdown()
