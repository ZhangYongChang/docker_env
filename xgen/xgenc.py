# -*- coding:utf-8 -*-

#! /usr/bin/python
#

import sys
from argparse import ArgumentParser
import os
import logging
import itertools
import glob
import re
import xgen
import json

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
streamHandler.setLevel(logging.INFO)
logger.addHandler(streamHandler)


def load_config(filepath='config.json'):
    with open(filepath, 'r') as f:
        options = json.load(f)
        return options
    return []


class Option(object):
    def to_json_string(self):
        return json.dumps(self, default=lambda obj: obj.__dict__)

    def from_json_string(self, json_string):
        data = json.loads(json_string)
        for key, val in data.items():
            setattr(self, key, val)


def load_options(filepath):
    cmd_options = {}
    options = load_config(filepath)
    for item in options:
        option = Option()
        option.from_json_string(json.dumps(item))
        cmd_options[option.command] = option
    return cmd_options

def config_logger(options):
    fileHandler = logging.FileHandler(filename=options.logfile)
    fileHandler.setLevel(options.loglevel)
    fileHandler.setFormatter(logging.Formatter(
        fmt='[%(asctime)s][%(levelname)s][%(threadName)s][%(filename)s:%(funcName)s:%(lineno)s]%(message)s'))
    logger.addHandler(fileHandler)


def main(argv):
    filepath = "config.json"
    if (len(argv) == 2):
        filepath = argv[1]

    cmd_options = load_options(filepath)
    cmdmodules = {}
    for key, options in cmd_options.items():
        if options.logfile:
            config_logger(options)

        try:
            module = __import__('xgen.cmd_' + options.command, globals(), locals(), ['*'], 0)
        except Exception as e:
            logger.error('can not import subcommand (%s)' % options.command)
            logger.error('exception: (%s)' % e)
            pass
        else:
            if hasattr(module, 'makeoptions') and hasattr(module, 'run'):
                cmdmodules[options.command] = module
            else:
                pass        

        logger.info('xgenc command %s start for %s' % (options.command, options.input))
        cmdmodules[options.command].run(options)
        logger.info('xgenc command %s end for %s' % (options.command, options.input))


if __name__ == '__main__':
    main(sys.argv)
