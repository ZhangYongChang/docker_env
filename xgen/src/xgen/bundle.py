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


def load_config(filepath='bundle.json'):
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


def main(argv):
    filepath = "bundle.json"
    if (len(argv) == 2):
        filepath = argv[1]

    cmd_options = load_options(filepath)
    cmdmodules = {}
    xgendir = os.path.dirname(sys.modules['xgen'].__file__)
    for cmdfile in glob.glob(xgendir + '/cmd_*.py'):
        cmdmod = re.search('cmd_(\w+).py', cmdfile).group(1)
        try:
            module = __import__('xgen.cmd_' + cmdmod,
                                globals(), locals(), ['*'], 0)
        except Exception as e:
            print(e)
            pass
        else:
            if hasattr(module, 'makeoptions') and hasattr(module, 'run'):
                cmdmodules[cmdmod] = module
            else:
                pass

    for key, options in cmd_options.items():
        if options.logfile:
            fileHandler = logging.FileHandler(filename=options.logfile)
            fileHandler.setLevel(options.loglevel)
            fileHandler.setFormatter(logging.Formatter(
                fmt='[%(asctime)s][%(levelname)s][%(threadName)s][%(filename)s:%(funcName)s:%(lineno)s]%(message)s'))
            logger.addHandler(fileHandler)

        logger.info('xgenc command %s start for %s' %
                    (options.command, options.input))
        cmdmodules[options.command].run(options)
        logger.info('xgenc command %s end for %s' %
                    (options.command, options.input))


if __name__ == '__main__':
    main(sys.argv)
