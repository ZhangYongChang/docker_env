# -*- coding:utf-8 -*-

"""
generate fiberhome ne dev xsd from yang
"""
import pdb

import concurrent.futures
import logging
import re
import glob
import os
import pyang
from pyang.types import EnumerationTypeSpec, IntTypeSpec, StringTypeSpec, EnumTypeSpec, RangeTypeSpec, BooleanTypeSpec

from xgen import util
logger = logging.getLogger(__name__)


class YException(Exception):
    pass


def camelname(name):
    name = name.lower()
    name = name.replace('-', '_')
    camelName = ''
    for nm in name.split('_'):
        camelName += nm.capitalize()
    return camelName


class YWrapper:
    @staticmethod
    def type_spec(stmt):
        if stmt.keyword == 'type':
            type_stmt = stmt
        else:
            type_stmt = stmt.search_one('type')

        if hasattr(type_stmt, 'i_typedef') and type_stmt.i_typedef is not None:
            typedef_stmt = type_stmt.i_typedef
            return YWrapper.type_spec(typedef_stmt)
        elif hasattr(type_stmt, 'i_type_spec'):
            return type_stmt.i_type_spec
        else:
            return None

    @staticmethod
    def count_grouping_uses(stmt):
        for stmt_uses in stmt.search('uses'):
            #        if stmt_uses.i_module != stmt_uses.i_grouping.i_module:
            #            continue
            if hasattr(stmt_uses.i_grouping, 'x_refcount'):
                stmt_uses.i_grouping.x_refcount += 1
            else:
                stmt_uses.i_grouping.x_refcount = 1

        if hasattr(stmt, 'i_children'):
            for ch in stmt.i_children:
                YWrapper.count_grouping_uses(ch)

    @staticmethod
    def nodename(stmt):
        fname = stmt.arg
        renamestmt = stmt.search_one(('yymapping', 'rename'))
        if renamestmt:
            fname = renamestmt.arg
        return fname

    @staticmethod
    def keyseq(stmt):
        def attrsearch(tag, attr, list):
            for x in list:
                if getattr(x, attr) == tag:
                    return x
            return None

        keyi = 0
        if hasattr(stmt, 'parent') and stmt.parent.keyword == 'list':
            key = stmt.parent.search_one('key')
            if not key:
                return 0
            for x in key.arg.split():
                if x == '':
                    continue
                if x.find(":") == -1:
                    name = x
                else:
                    [prefix, name] = x.split(':', 1)
                keyi += 1
                ptr = attrsearch(name, 'arg', stmt.parent.i_children)
                if ptr is stmt:
                    return keyi
        return 0


class YMGen(object):
    def __init__(self, inModule, inXsdFile, inExceptionOnDuplicate):
        self.m_module = inModule
        self.m_xsdfile = inXsdFile
        self.m_file = open(inXsdFile, "w+", encoding="utf-8")
        self.m_enums = {}
        self.m_groupings = []
        self.m_rpcs = {}
        self.m_complex_types = {}
        self.m_exception_on_duplicate = inExceptionOnDuplicate

        self.m_expand_default = False
        stmt = self.m_module.search_one(('yymapping', 'expanddefault'))
        if stmt:
            if stmt.arg == 'expand':
                self.m_expand_default = True
            elif stmt.arg == 'noexpand':
                self.m_expand_default = False

    def __del__(self):
        self.m_file.close()

    def gen(self):
        self.m_file.write(self.header())
        self.m_file.write(self.topgen())
        self.m_file.write(self.rpcgen())
        self.m_file.write(self.notificationgen())
        for name in sorted(self.m_complex_types.keys(), key=lambda d: d.upper()):
            self.m_file.write(self.m_complex_types[name])
        self.m_file.write(self.enumgen())
        self.m_file.write(self.footer())

    def header(self):
        text = """<?xml version="1.0" encoding="utf-8"?>
<!--auto generated by xgen toolkit, bug mail to zengmao@fiberhome.com -->

<xsd:schema xmlns:xdo="urn:pxp" xmlns:ms="urn:schemas-microsoft-com:xslt" xmlns:stack="urn:anything" xmlns:xdb="http://xmlns.oracle.com/xdb" xmlns:w="http://www.fiberhome.com.cn/board/control" xmlns:y="http://www.fiberhome.com.cn/ns/yang" xmlns:xsd="http://www.w3.org/2001/XMLSchema">

    <xsd:complexType name="YANGModules">
        <xsd:sequence>
"""

        text += '\t\t\t<xsd:element name="%s" type="%s"/>' % (
            self.m_module.arg, self.m_module.arg)

        text += """
        </xsd:sequence>
    </xsd:complexType>


"""

        rpcs = [ch for ch in self.m_module.i_children if ch.keyword == "rpc"]
        if len(rpcs):
            text += """
    <xsd:complexType name="YANGRpcs">
        <xsd:sequence>
"""
            for rpc in rpcs:
                text += '\t\t\t<xsd:element name="%s" y:ns="%s" ' % (
                    rpc.arg, self.m_module.search_one('namespace').arg)
                if rpc.search_one('input'):
                    text += 'y:input="%s-input" ' % (rpc.arg)

                if rpc.search_one('output'):
                    text += 'y:output="%s-output"' % (rpc.arg)
                text += '/>\n'
            text += """
        </xsd:sequence>
    </xsd:complexType>
"""
        notifys = [
            ch for ch in self.m_module.i_children if ch.keyword == "notification"]
        if len(notifys):
            text += """
    <xsd:complexType name="YANGNotifys">
        <xsd:sequence>
"""
            for notify in notifys:
                text += '\t\t\t<xsd:element name="%s" type="%s" y:ns="%s" ' % (
                    notify.arg, notify.arg, self.m_module.search_one('namespace').arg)
                text += '/>\n'
            text += """
        </xsd:sequence>
    </xsd:complexType>
"""
        return text

    def footer(self):
        text = """
    <xsd:simpleType name="string">
        <xsd:restriction base="xsd:string">
        </xsd:restriction>
    </xsd:simpleType>

    <xsd:simpleType name="int32">
        <xsd:restriction base="xsd:hexBinary">
            <xsd:length value="4"/>
        </xsd:restriction>
    </xsd:simpleType>

    <xsd:simpleType name="uint32">
        <xsd:restriction base="xsd:hexBinary">
            <xsd:length value="4"/>
        </xsd:restriction>
    </xsd:simpleType>

    <xsd:simpleType name="int64">
        <xsd:restriction base="xsd:hexBinary">
            <xsd:length value="8"/>
        </xsd:restriction>
    </xsd:simpleType>

    <xsd:simpleType name="uint64">
        <xsd:restriction base="xsd:hexBinary">
            <xsd:length value="8"/>
        </xsd:restriction>
    </xsd:simpleType>

    <xsd:simpleType name="boolean">
        <xsd:restriction base="xsd:hexBinary">
            <xsd:length value="1"/>
            <xsd:enumeration value="00" w:en="false" w:cn="false"/>
            <xsd:enumeration value="01" w:en="true" w:cn="false"/>
        </xsd:restriction>
    </xsd:simpleType>
</xsd:schema>
"""
        return text

    def topgen(self):
        text = '\t<xsd:complexType name="%s" y:ns="%s">\n' % (
            self.m_module.arg, self.m_module.search_one('namespace').arg)
        text += '\t\t<xsd:sequence>\n'
        for ch in self.children(self.m_module):
            text += self.fieldgen(ch, "/")
        text += '\t\t</xsd:sequence>\n'
        text += '\t</xsd:complexType>\n\n'
        return text

    def rpcgen(self):
        text = ''
        rpcs = [ch for ch in self.m_module.i_children if ch.keyword == "rpc"]
        for rpc in rpcs:
            rpc_input = rpc.search_one('input')
            if rpc_input:
                text += '\t<xsd:complexType name="%s-input">\n' % (rpc.arg)
                text += '\t\t<xsd:sequence>\n'
                for ch in rpc_input.i_children:
                    if ch.keyword in pyang.statements.data_definition_keywords:
                        text += self.fieldgen(ch, '')
                text += '\t\t</xsd:sequence>\n'
                text += '\t</xsd:complexType>\n\n'

            rpc_output = rpc.search_one('output')
            if rpc_output:
                text += '\t<xsd:complexType name="%s-output" y:ns="%s">\n' % (
                    rpc.arg, self.m_module.search_one('namespace').arg)
                text += '\t\t<xsd:sequence>\n'
                for ch in rpc_output.i_children:
                    if ch.keyword in pyang.statements.data_definition_keywords:
                        text += self.fieldgen(ch, '/')
                text += '\t\t</xsd:sequence>\n'
                text += '\t</xsd:complexType>\n\n'
        return text

    def enumgen(self):
        text = ''
        for (enumname, enumtype) in sorted(self.m_enums.items(), key=lambda e: e[0].upper()):
            text += '\t<xsd:simpleType name="%s">\n' % enumname
            text += '\t\t<xsd:restriction base="xsd:hexBinary">\n'
            text += '\t\t\t<xsd:length value="1"/>\n'
            for enum in enumtype.enums:
                hval = hex(int(enum[1])).replace("0x", "")
                hval = hval.upper()
                text += '\t\t\t\t<xsd:enumeration value="%s" w:en="%s" w:cn="%s"/>\n' % (
                    hval, enum[0], enum[0])
            text += '\t\t</xsd:restriction>\n'
            text += '\t</xsd:simpleType>\n\n'
        return text

    def nodegen(self, stmt):
        nname = YWrapper.nodename(stmt)
        text = '\t<xsd:complexType name="%s">\n' % (nname)
        text += '\t\t<xsd:sequence>\n'
        for ch in self.children(stmt):
            text += self.fieldgen(ch, "")
        text += '\t\t</xsd:sequence>\n'
        text += '\t</xsd:complexType>\n\n'

        if nname in self.m_complex_types and not stmt.search_one(('yymapping', 'override')):
            if self.m_exception_on_duplicate:
                raise YException("%s duplicate@ %s" %
                                 (nname, stmt.i_module.arg))
            else:
                logger.error("%s duplicate", nname)
        self.m_complex_types[nname] = text

    def fieldgen(self, stmt, ppath):
        text = ''
        if stmt.keyword == 'uses':
            text = self.usesgen(stmt)
        elif stmt.keyword == 'leaf':
            text = self.leafgen(stmt, ppath)
        elif stmt.keyword == 'container':
            text = self.containergen(stmt, ppath)
        elif stmt.keyword == 'list':
            text = self.listgen(stmt, ppath)
        elif stmt.keyword == 'leaf-list':
            text = self.leaflistgen(stmt, ppath)
        elif stmt.keyword == 'notification':
            text = self.notificationgen(stmt, ppath)
        return text

    def usesgen(self, stmt):
        gname = YWrapper.nodename(stmt.i_grouping)
        renamestmt = stmt.search_one(('yymapping', 'rename'))
        if renamestmt:
            fname = renamestmt.arg
        else:
            fname = gname

        text = '\t\t\t<xsd:element name="%s" type="%s"/>\n' % (fname, gname)
        return text

    def leafgen(self, stmt, ppath):
        text = '\t\t\t<xsd:element name="%s" ' % (YWrapper.nodename(stmt))

        if hasattr(stmt, 'i_augment'):
            b = stmt.i_module.search_one('belongs-to')
            if b is not None:
                ns = stmt.i_module.i_ctx.get_module(
                    b.arg).search_one('namespace')
            else:
                ns = stmt.i_module.search_one('namespace')

            text += 'y:ns="' + ns.arg + '" '

        typename = 'string'
        typespec = YWrapper.type_spec(stmt)

#        if stmt.arg == 'prefix-ipv4':
#            pdb.set_trace()

        if typespec is not None:
            if isinstance(typespec, IntTypeSpec) or isinstance(typespec, RangeTypeSpec):
                if typespec.name in ('int8', 'int16', 'int32', 'uint8', 'uint16'):
                    typename = 'int32'
                elif typespec.name in ('uint32'):
                    typename = 'uint32'
                elif typespec.name in ('int64'):
                    typename = 'int64'
                elif typespec.name in ('uint64'):
                    typename = 'uint64'
                else:
                    typename = 'string'
            elif isinstance(typespec, StringTypeSpec):
                typename = 'string'
            elif isinstance(typespec, BooleanTypeSpec):
                typename = 'boolean'
            elif isinstance(typespec, EnumTypeSpec):
                typestmt = stmt.search_one('type')
                typename = typestmt.arg
                renamestmt = typestmt.search_one(('yymapping', 'rename'))
                if renamestmt:
                    typename = renamestmt.arg
                elif typename == 'enumeration':
                    typename = YWrapper.nodename(stmt)
                    typename = 'E' + typename
                elif typename.find(":") == -1:
                    prefix = None
                    if stmt.i_module is self.m_module:
                        typename = 'E' + camelname(typename)
                    else:
                        typename = 'E' + \
                            camelname(stmt.i_module.i_prefix) + \
                            '_' + camelname(typename)
                else:
                    [prefix, typename] = typename.split(':', 1)
                    typename = 'E' + \
                        camelname(prefix) + '_' + camelname(typename)

                if typename in self.m_enums:
                    if typespec is self.m_enums[typename]:
                        logger.debug('enum %s refed multi time' % (typename))
                    else:
                        raise YException('enum %s refined' % (typename))
                else:
                    self.m_enums[typename] = typespec
        text += 'type="%s" ' % (typename)

#        if hasattr(stmt, 'i_is_key'):
#            keyi = 1
#            for ptr in stmt.parent.i_key:
#                if ptr is stmt:
#                    break
#                keyi += 1
        keyi = YWrapper.keyseq(stmt)
        if keyi > 0:
            text += 'y:key="%s" ' % keyi
        elif stmt.search_one('mandatory'):
            if stmt.search_one('mandatory').arg != 'false':
                text += 'y:leafmand="" '

        if YWrapper.nodename(stmt) != stmt.arg:
            text += 'y:leafname="%s " ' % (stmt.arg)

        if ppath != "":
            text += 'y:path="' + ppath + '" '

        if not hasattr(stmt, 'i_is_key'):
            if stmt.search_one(('yymapping', 'nodeopr')) or stmt.search_one('must'):
                text += 'y:nodeopr="" '

        text += '/>\n'
        return text

    def leaflistgen(self, stmt, ppath):
        # self.nodegen(stmt)
        nname = YWrapper.nodename(stmt)
        typespec = YWrapper.type_spec(stmt)
        typename = "string"
        if typespec is not None:
            if isinstance(typespec, IntTypeSpec) or isinstance(typespec, RangeTypeSpec):
                if typespec.name in ('int8', 'int16', 'int32', 'uint8', 'uint16'):
                    typename = 'int32'
                elif typespec.name in ('uint32'):
                    typename = 'uint32'
                elif typespec.name in ('int64'):
                    typename = 'int64'
                elif typespec.name in ('uint64'):
                    typename = 'uint64'
                else:
                    typename = 'string'
            elif isinstance(typespec, StringTypeSpec):
                typename = 'string'
            elif isinstance(typespec, BooleanTypeSpec):
                typename = 'boolean'
            elif isinstance(typespec, EnumTypeSpec):
                typestmt = stmt.search_one('type')
                typename = typestmt.arg
                renamestmt = typestmt.search_one(('yymapping', 'rename'))
                if renamestmt:
                    typename = renamestmt.arg
                elif typename == 'enumeration':
                    typename = YWrapper.nodename(stmt)
                    typename = 'E' + typename
                elif typename.find(":") == -1:
                    prefix = None
                    if stmt.i_module is self.m_module:
                        typename = 'E' + camelname(typename)
                    else:
                        typename = 'E' + \
                            camelname(stmt.i_module.i_prefix) + \
                            '_' + camelname(typename)
                else:
                    [prefix, typename] = typename.split(':', 1)
                    typename = 'E' + \
                        camelname(prefix) + '_' + camelname(typename)

                if typename in self.m_enums:
                    if typespec is self.m_enums[typename]:
                        logger.debug('enum %s refed multi time' % (typename))
                    else:
                        raise YException('enum %s refined' % (typename))
                else:
                    self.m_enums[typename] = typespec

        text = '\t\t\t<xsd:element name="%s" type="%s" y:list="" y:path="%s"' % (
            nname, typename, ppath + stmt.arg)
        if hasattr(stmt, 'i_augment'):
            b = stmt.i_module.search_one('belongs-to')
            if b is not None:
                ns = stmt.i_module.i_ctx.get_module(
                    b.arg).search_one('namespace')
            else:
                ns = stmt.i_module.search_one('namespace')

            text += ' y:ns="' + ns.arg + '" '

        text += "/>\n"
        return text

    def notificationgen(self):
        # if stmt.i_children:
        #     self.nodegen(stmt)
        # nname = YWrapper.nodename(stmt)
        # text = '\t\t\t<xsd:element name="%s" type="%s" y:notification=""' % (nname, nname)
        text = ''
        notifications = [
            ch for ch in self.m_module.i_children if ch.keyword == "notification"]
        for notification in notifications:
            text += '\t<xsd:complexType name="%s">\n' % (notification.arg)
            text += '\t\t<xsd:sequence>\n'
            for ch in notification.i_children:
                if ch.keyword in pyang.statements.data_definition_keywords:
                    text += self.fieldgen(ch, '')
            text += '\t\t</xsd:sequence>\n'
            text += '\t</xsd:complexType>\n\n'
        return text

    def listgen(self, stmt, ppath):
        self.nodegen(stmt)
        nname = YWrapper.nodename(stmt)
        text = '\t\t\t<xsd:element name="%s" type="%s" y:list=""  y:path="%s"' % (
            nname, nname, ppath + stmt.arg)

        if hasattr(stmt, 'i_augment'):
            b = stmt.i_module.search_one('belongs-to')
            if b is not None:
                ns = stmt.i_module.i_ctx.get_module(
                    b.arg).search_one('namespace')
            else:
                ns = stmt.i_module.search_one('namespace')

            text += ' y:ns="' + ns.arg + '" '

        text += "/>\n"

        return text

    def containergen(self, stmt, ppath):
        nname = YWrapper.nodename(stmt)
        text = '\t\t\t<xsd:element name="%s" type="%s" ' % (nname, nname)

        expand = self.m_expand_default
        if hasattr(stmt, 'i_augment'):
            b = stmt.i_module.search_one('belongs-to')
            if b is not None:
                ns = stmt.i_module.i_ctx.get_module(
                    b.arg).search_one('namespace')
            else:
                ns = stmt.i_module.search_one('namespace')

            text += 'y:ns="' + ns.arg + '" '
            expand = False

        if stmt.search_one(('yymapping', 'nodeopr')) or stmt.search_one('must'):
            text += ' y:nodeopr="" '
            expand = False
        elif stmt.search_one(('yymapping', 'noexpand')):
            expand = False
        elif stmt.search_one(('yymapping', 'expand')):
            expand = True
        elif ppath == '/':
            expand = False
        elif stmt.search_one('when'):
            expand = False
        else:
            for c in stmt.i_children:
                if c.keyword == 'leaf':
                    m = c.search_one('mandatory')
                    if m and m.arg != 'false':
                        expand = False
                        break

        if expand:
            text = ''
            for ch in stmt.i_children:
                text += self.fieldgen(ch, ppath + stmt.arg + '/')
        else:
            text += 'y:path="' + ppath + stmt.arg + '"/>\n'
            self.nodegen(stmt)
        return text

    def children(self, stmt):
        """
        return uses,   leaf,leaflist,container,list statment list, same order as they appear in yang file
        """
        chs = []
        if hasattr(stmt, 'i_children'):
            usess = []
            if stmt.keyword != 'module':
                for uses in stmt.search('uses'):
                    if not uses.i_grouping.search_one(('yymapping', 'noexpand')):
                        if not hasattr(uses.i_grouping, 'x_refcount'):
                            continue

                        if uses.i_grouping.x_refcount < 2 or len(uses.i_grouping.i_children) < 10:
                            continue

                    if uses.search_one(('yymapping', 'expand')):
                        continue

                    usess.append(uses)
                    logger.debug('uses %s as bundle @%s',
                                 uses.i_grouping.arg, uses.pos)

                    if uses.i_grouping not in self.m_groupings:
                        self.m_groupings.append(uses.i_grouping)
                        self.nodegen(uses.i_grouping)

            gchs = []
            for uses in usess:
                gchs.extend([s.arg for s in uses.i_grouping.i_children])

            if len(usess):
                logger.debug("%s grouping children %s", stmt.arg, gchs)

            gchsshot = []
            for ch in stmt.i_children:
                if ch.keyword not in pyang.statements.data_definition_keywords:
                    continue

                if ch.arg in gchs:
                    # grouping child
                    if ch.arg not in gchsshot:
                        for uses in usess:
                            if ch.arg in [s.arg for s in uses.i_grouping.i_children]:
                                gchsshot.extend(
                                    [s.arg for s in uses.i_grouping.i_children])
                                chs.append(uses)
                                logger.debug("%s shot grouping %s",
                                             stmt.arg, uses.i_grouping.arg)
                                break
                            else:
                                logger.debug("%s not in grouping %s %s", ch.arg, uses.i_grouping.arg, [
                                             s.arg for s in uses.i_grouping.i_children])
                    else:
                        #                        logger.debug("%s %s's grouping already shot", stmt.arg, ch.arg)
                        pass
                else:
                    chs.append(ch)

        return chs


class CmdYXsd(object):
    def __init__(self, inDir, inPath, inExceptionOnDuplicate, inWithWarning):
        repos = pyang.FileRepository(inPath, no_path_recurse=True)
        self.m_ctx = pyang.Context(repos)
        self.m_modules = []
        self.m_filenames = []
        self.m_modulenames = []
        self.m_expanddefault = False
        self.m_exception_on_duplicate = inExceptionOnDuplicate
        self.m_with_warning = inWithWarning

        path = inDir + '/*.yang'
        r = re.compile(r"^(.*?)(\@(\d{4}-\d{2}-\d{2}))?\.(yang|yin)$")
        for filename in glob.glob(path):
            fd = open(filename, "r", encoding="utf-8")
            text = fd.read()

            m = r.search(filename)
            self.m_ctx.yin_module_map = {}
            if m is not None:
                (name, _dummy, rev, format) = m.groups()
                name = os.path.basename(name)
                module = self.m_ctx.add_module(filename, text, format, name, rev,
                                               expect_failure_error=False)
            else:
                module = self.m_ctx.add_module(filename, text)

            if module and not module.search_one('belongs-to'):
                chs = [ch for ch in module.i_children
                       if ch.keyword in pyang.statements.data_definition_keywords or ch.keyword in ('rpc', 'notification')]

                if len(chs):
                    self.m_modules.append(module)
                    self.m_modulenames.append(module.arg)
                    self.m_filenames.append(filename)

        self.m_ctx.validate()

        def keyfun(e):
            if e[0].ref == self.m_filenames[0]:
                return 0
            else:
                return 1

        self.m_ctx.errors.sort(key=lambda e: (e[0].ref, e[0].line))
        if len(self.m_filenames) > 0:
            # first print error for the first filename given
            self.m_ctx.errors.sort(key=keyfun)

        haserror = False
        for (epos, etag, eargs) in self.m_ctx.errors:
            if (self.m_ctx.implicit_errors == False and
                hasattr(epos.top, 'i_modulename') and
                epos.top.arg not in self.m_modulenames and
                epos.top.i_modulename not in self.m_modulenames and
                    epos.ref not in self.m_filenames):
                # this module was added implicitly (by import); skip this error
                # the code includes submodules
                continue
            elevel = pyang.error.err_level(etag)
            if pyang.error.is_warning(elevel):
                kind = "warning"
                if self.m_with_warning:
                    logger.error(str(epos) + ': %s: ' % kind +
                                 pyang.error.err_to_str(etag, eargs) + '\n')
            else:
                kind = "error"
                haserror = True
                logger.error(str(epos) + ': %s: ' % kind +
                             pyang.error.err_to_str(etag, eargs) + '\n')

        if haserror:
            raise YException(
                'some errors occur in yang modules, error details refer to log please')

        for module in self.m_modules:
            YWrapper.count_grouping_uses(module)

    def run(self, inDir):
        if os.path.exists(inDir) is False:
            os.mkdir(inDir)

        self.emit(self.m_modules, inDir)

    def emit(self, modules, xsddir):
        for module in modules:
            # yxsdfile = xsddir + module.arg + ".xsd"
            yxsdfile = os.path.join(xsddir, module.arg + ".xsd")
            fd = open(yxsdfile, "w+", encoding="utf-8")

            logger.info('generate %s', yxsdfile)

            yGen = YMGen(module, yxsdfile, self.m_exception_on_duplicate)
            yGen.gen()


cmddescription = 'generate fiberhome dev ne xsd model from yang'


def makeoptions(optpartser):
    optpartser.add_argument(
        "-p", "--path",
        dest="path",
        default=[],
        action="append",
        help=os.pathsep + "-separated search path for yang modules")

    optpartser.add_argument(
        "--with-warning",
        action='store_true',
        default=False,
        help="log warning info for yang invalidation")

    optpartser.add_argument(
        "--exception-on-duplicate",
        action='store_true',
        default=False,
        help="raise exception when complexType duplicate")


def run(options):
    options.path = os.pathsep.join(options.path)
    if len(options.path) == 0:
        options.path = "."
    else:
        options.path += os.pathsep + "."

    cmd = CmdYXsd(options.input, options.input + os.pathsep + options.path,
                  options.exception_on_duplicate, options.with_warning)
    cmd.run(options.output)
