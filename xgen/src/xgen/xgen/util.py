import re
import logging
import shutil
import os

logger = logging.getLogger(__name__)

cppkeyword = ('alignas',   'continue',     'friend',   'register',         'true',
              'alignof',   'decltype'      'goto',     'reinterpret_cast', 'try',
              'asm',       'default',      'if',       'return',           'typedef',
              'auto',      'delete',       'inline',   'short',            'typeid',
              'bool',      'do',           'int',      'signed',           'typename',
              'break',     'double',       'long',     'sizeof',           'union',
              'case',      'dynamic_cast', 'mutable',  'static',           'unsigned',
              'catch',     'else',         'namespace', 'static_assert',    'using',
              'char',      'enum',         'new',      'static_cast',      'virtual',
              'char16_t',  'explicit',     'noexcept', 'struct',           'void',
              'char32_t',  'export',       'nullptr',  'switch',           'volatile',
              'class',     'extern',       'operator', 'template',         'wchar_t',
              'const',     'false',        'private',  'this',             'while',
              'constexpr', 'float',        'protected', 'thread_local',
              'const_cast', 'for',          'public',   'throw')

cppconst = ('NULL', 'TRUE', 'FALSE', 'True', 'False')

appconst = ('IN', 'OUT', 'interface')


def camel_name(name):
    name = name.lower()
    name = name.replace('-', '_')
    camelName = ''
    for nm in name.split('_'):
        camelName = camelName + nm.capitalize()
    return camelName


def lower_name(name):
    name = name.replace('-', '_')
    name = name.lower()
    return name


def pbname(name):
    name = name.replace('-', '_')
    name = name.lower()
    if name in cppkeyword:
        name += '_'
    return name


def cppname(name):
    name = name.lower()
    name = name.replace('-', '_')
    camelName = ''
    for nm in name.split('_'):
        camelName = camelName + nm.capitalize()
    return camelName


def cppnormalize(name):
    name = re.sub('\s*<\s*', '_LT_', name)
    name = re.sub('\s*<=\s*', '_LE_', name)
    name = re.sub('\s*>\s*', '_GT_', name)
    name = re.sub('\s*>=\s*', '_GE_', name)
    name = re.sub('\s*=\s*', '_EQ_', name)
    name = re.sub('\s*\+\s*', '_PS_', name)
    name = re.sub('\s+', '_', name)
    if name[0] in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
        name = '_' + name
    name = re.sub('[^a-zA-Z0-9_]', '_', name)

    if name in cppkeyword:
        name += '_'
    elif name in cppconst:
        name += '_'
    elif name in appconst:
        name += '_'

    return name


def allzero(default):
    for ch in default:
        if ch != '0':
            return False
    return True


def ipv4str(i):
    ipstr = "%d.%d.%d.%d" % (i & 0xFF, i >> 8 & 0xFF,
                             i >> 16 & 0xFF, i >> 32 & 0xFF)
    return ipstr


def mkdir(inDir, inRemove=False):
    dir = os.path.dirname(inDir)
    if dir == '':
        return

    if inRemove and os.path.exists(dir):
        shutil.rmtree(inDir)

    if os.path.exists(dir):
        logger.debug('%s already exist', dir)
    else:
        os.makedirs(dir)
        logger.debug('makedirs %s', dir)


# Lookup table for non-utf8, with necessary escapes at (o >= 127 or o < 32)
_cescape_byte_to_str = ([r'%02X' % i for i in range(0, 32)] +
                        [r'%2s' % chr(i) for i in range(32, 127)] +
                        [r'%02X' % i for i in range(127, 256)])
_cescape_byte_to_str_hex = ([r'\%02X' % i for i in range(0, 256)])


def cescape(text, hexed=False):
    if hexed:
        return ''.join(_cescape_byte_to_str_hex[ord(c)] for c in text)
    else:
        return ''.join(_cescape_byte_to_str[ord(c)] for c in text)


class EncodeUtil(object):
    @staticmethod
    def DecodeBigEndian32(buffer):
        i = 1
        result = ord(buffer[0])
        while i < 4:
            result = result * 256 + ord(buffer[i])
            i = i + 1
        return result

    @staticmethod
    def DecodeLittleEndian32(buffer):
        i = 4
        result = ord(buffer[3])
        while i > 1:
            i -= 1
            result = result * 256 + ord(buffer[i - 1])
        return result

    @staticmethod
    def EncodeLittleEndian32(i):
        buffer = bytearray(4)
        buffer[0] = i & 0xFF
        buffer[1] = i >> 8 & 0xFF
        buffer[2] = i >> 16 & 0xFF
        buffer[3] = i >> 24 & 0xFF
        return buffer
