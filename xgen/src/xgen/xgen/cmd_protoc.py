# -*- coding:utf-8 -*-

import os
import glob
import concurrent.futures
import sys

import os
import logging

logger = logging.getLogger(__name__)

cmddescription = 'compile all *.proto file under input directory into cpp/python... parallel'


def makeoptions(optparser):
    optparser.add_argument(
        "--protoc",
        type=str,
        default='protoc.exe',
        help="protoc.exe")

    optparser.add_argument(
        "-p", "--path",
        dest="path",
        default=[],
        action="append",
        help="proto include path")

    optparser.add_argument(
        "--excludefile",
        default=[],
        action="append",
        help="proto exclude file list")

    optparser.add_argument(
        "--format",
        type=str,
        default='cpp',
        choices=['cpp', 'python'],
        help="compiled format")


def run(options):
    if os.path.exists(options.output) is False:
        os.mkdir(options.output)

    pfiles = ''
    ipath = ''
    for p in options.path:
        ipath += '-I' + p + ' '

    path = options.input + '/*.proto'
    logger.info('protoc for %s start' % (path))

    if options.format == 'cpp':
        commandprefix = options.protoc + ' --cpp_out=' + options.output + ' ' + ipath
    elif options.format == 'python':
        commandprefix = options.protoc + ' --python_out=' + options.output + ' ' + ipath

    commands = []
    for proto in glob.glob(path):
        if os.path.basename(proto) in options.excludefile:
            continue
        pfiles += proto + ' '
        if len(pfiles) > 0x400:
            command = commandprefix + pfiles
            logger.info(command)
            commands.append(command)
            pfiles = ''

    if pfiles != '':
        command = commandprefix + pfiles
        logger.info(command)
        commands.append(command)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.map(os.system, commands)
