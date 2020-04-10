# -*- coding:utf-8 -*-

"""
fiberhome yang xsd parser which parse:
y:ns                yang module namespace, mark module namespace at xsd:complexType, mark container/list/leaf at xsd:element
y:parent            yang leaf/container/list parent path, container/list y:parent contains itself
y:nodeopr           yang leaf/container has operation field which name postfix _opr, list always has field listopr
y:nomap             donnot generate edit-config config for this field

y:leafprefix        yang leaf namespace prefix
y:leafname          yang leafname
y:leafmand          yang mandatory leaf

y:list              yang list
y:key               yang list element key

y:input             rpc input type
y:output            rpc output type
"""

from xml.etree import ElementTree
from xgen.util import *

import logging
logger = logging.getLogger(__name__)

XSDNS = {'xsd': 'http://www.w3.org/2001/XMLSchema',
         'w': 'http://www.fiberhome.com.cn/board/control',
         'y': 'http://www.fiberhome.com.cn/ns/yang'}
Y_NS = '{%s}ns' % XSDNS['y']
Y_LEAFNAME = '{%s}leafname' % XSDNS['y']
Y_LEAFPREFIX = '{%s}leafprefix' % XSDNS['y']
Y_LEAFMAND = '{%s}leafmand' % XSDNS['y']
Y_PATH = '{%s}path' % XSDNS['y']
Y_LIST = '{%s}list' % XSDNS['y']
Y_KEY = '{%s}key' % XSDNS['y']
Y_NOMAP = '{%s}nomap' % XSDNS['y']
Y_NODEOPR = '{%s}nodeopr' % XSDNS['y']
Y_INPUT = '{%s}input' % XSDNS['y']
Y_OUTPUT = '{%s}output' % XSDNS['y']
W_EN = '{%s}en' % XSDNS['w']
W_CN = '{%s}cn' % XSDNS['w']


class XException(Exception):
    pass


def nsparse(yns):
    nsDict = None
    for nsstr in yns.split():
        nslist = nsstr.split('|')
        ns = nslist[0]
        prefix = ''
        if len(nslist) == 2:
            prefix = nslist[1]
        if nsDict is None:
            nsDict = {prefix: ns}
        else:
            nsDict[prefix] = ns
    return nsDict


def pathlexical(path):
    if path[-1] == '/':
        return path[0:-1]
    else:
        return path


def rsubpath(path, count):
    i = 0
    end = len(path)
    while i < count:
        i = i+1
        end = path.rfind('/', 0, end)
        if end == -1 or end == 0:
            return None
        path = path[0:end]
    return path


def pathsplit(path):
    if path == '':
        return []
    plist = path.split('/')
    if plist[0] == '':
        plist[1] = '/' + plist[1]
        del plist[0]
    if plist[-1] == '':
        del plist[-1]
    return plist


class XEnum(object):
    """
    xsd simpleType/restriction/enumeration
    """

    def __init__(self, inValue, inEn=None, inCn=None, inFieldIndex=None):
        self.m_value = inValue
        self.m_en = inEn
        self.m_cn = inCn
        self.m_field_index = inFieldIndex


class XType(object):
    """
    base class of simpleType/complexType
    """

    def __init__(self, inName):
        self.m_name = inName
        self.m_root = None
        self.m_refed = False

    def parse(self, inXmlElement):
        pass

    def invalidate(self):
        """
        invalidate itself elements
        """
        logger.debug("%s invalidate" % (self.m_name))

    def invalidate_post_1(self):
        """
        generate cross object
        """
        logger.debug("%s invlidate post 1" % (self.m_name))
        pass

    def invalidate_post_2(self):
        """
        invalidate depend on cross object
        """
        logger.debug("%s invlidate post 2" % (self.m_name))
        pass

    def invalidate_post(self):
        logger.debug("%s invalidate post" % (self.m_name))
#        logger.debug("".join(traceback.format_stack()))
        self.invalidate_post_1()
        self.invalidate_post_2()


class XSimpleType(XType):
    def __init__(self, inName):
        super().__init__(inName)
        self.m_len = 0

    def parse(self, inXmlElement):
        super().parse(inXmlElement)

        restriction = inXmlElement.find(
            ".//xsd:restriction[@base='xsd:hexBinary']", XSDNS)
        if restriction is None:
            return

        length = restriction.find(".//xsd:length", XSDNS)
        if length is None:
            return

        self.m_len = int(length.attrib['value'])


class XSimpleTypeInt(XSimpleType):
    def __init__(self, inName):
        super().__init__(inName)


class XSimpleTypeString(XSimpleType):
    def __init__(self, inName):
        super().__init__(inName)


class XSimpleTypeEnum(XSimpleType):
    def __init__(self, inName):
        super().__init__(inName)
        self.m_enums = {}

    def parse(self, inXmlElement):
        super().parse(inXmlElement)

        for enum in inXmlElement.iterfind(".//xsd:restriction/xsd:enumeration", XSDNS):
            value = int(enum.attrib["value"], base=16)
            en = enum.attrib[W_EN]

            cn = None
            if W_CN in enum.attrib:
                cn = enum.attrib[W_CN]
            else:
                logger.warning(
                    "enumeration simpleType %s:%d has no w:cn attribute", self.m_name, value)

            xenum = XEnum(value, inEn=en, inCn=cn,
                          inFieldIndex=enum.attrib["field_index"])
            self.enum_add(xenum)

    def enum_add(self, inEnum):
        if inEnum.m_value in self.m_enums:
            raise XException("enumeration simpleType %s value %d duplicate" % (
                self.m_name, inEnum.m_value))
        if inEnum.m_en in [x.m_en for x in self.m_enums.values()]:
            raise XException("enumeration simpleType %s w:en %s duplicate" % (
                self.m_name, inEnum.m_en))
#        if inEnum.m_cn in [x.m_cn for x in self.m_enums.values()]:
#            raise XException("enumeration simpleType %s w:cn %s duplicate" % (self.m_name, inEnum.m_cn))
        self.m_enums[inEnum.m_value] = inEnum


class ElementField(object):
    def __init__(self, inName, inType, inLeafName=None, inLeafPrefix=None, inFieldNum=None):
        self.m_name = inName
        self.m_type = inType
        self.m_field_index = inFieldNum

        self.m_leaf = False
        self.m_list = False
        self.m_nomap = False
        self.m_nodeopr = None
        self.m_path = None
        self.m_key = -1
        self.m_mandatory = False
        self.m_namespaces = {}

        if inLeafName is None:
            self.m_leafname = inName
        else:
            self.m_leafname = inLeafName
        if inLeafPrefix is not None:
            self.m_leafname = inLeafPrefix + ':' + self.m_leafname
        self.m_pbname = pbname(inName)
        self.m_pbtype = pbname(inType)
        self.m_pboption = 'optional'
        self.m_typename = 'int32'
        self.m_path_shared = []
        self.m_path_priv = []
        self.m_path_priv_list = ''

        self.m_type_obj = None


class ElementRpc(object):
    def __init__(self, inName):
        self.m_name = inName
        self.m_input = None
        self.m_output = None
        self.m_namespace = None

    def parse(self, inXmlElement):
        if Y_INPUT in inXmlElement.attrib:
            self.m_input = inXmlElement.attrib[Y_INPUT]

        if Y_OUTPUT in inXmlElement.attrib:
            self.m_output = inXmlElement.attrib[Y_OUTPUT]

        if Y_NS in inXmlElement.attrib:
            self.m_namespace = inXmlElement.attrib[Y_NS]


class ElementNotify(object):
    def __init__(self, inName):
        self.m_name = inName
        self.m_type = None
        self.m_namespace = None

    def parse(self, inXmlElement):
        self.m_type = inXmlElement.attrib['type']
        self.m_namespace = inXmlElement.attrib[Y_NS]


class XNode(object):
    def __init__(self, inXName=''):
        self.m_xname = inXName
        self.m_xname_parent = ''
        self.m_xnodes = {}
        self.m_fields = []


class XTree(object):
    def __init__(self):
        self.m_xnodes = {}

    def build(self, element):
        if element.m_path_shared == '':
            return

        xnode = XNode()
        pathlist = element.m_path_shared
        parent = ''
        i = 0
        while i < len(pathlist):
            path = pathlist[i]
            if i == 0:
                if path in self.m_xnodes:
                    xnode = self.m_xnodes[path]
                else:
                    self.m_xnodes[path] = XNode(path)
                    xnode = self.m_xnodes[path]
                    xnode.m_xname_parent = 'yNode'
            else:
                if path in xnode.m_xnodes:
                    xnode = xnode.m_xnodes[path]
                else:
                    xnode.m_xnodes[path] = XNode(path)
                    xnode = xnode.m_xnodes[path]
                    xnode.m_xname_parent = parent

            parent = path
            i = i + 1
            if i == len(pathlist):
                xnode.m_fields.append(element)
        return


class XComplexType(XType):
    def __init__(self, inName):
        super().__init__(inName)
        self.m_name_pb = pbname(inName)
        self.m_name_cpp = cppname(inName)
        self.m_modname = None
        self.m_fields_key = {}
        self.m_fields_mandatory = []
        self.m_fields_noshared = []
        self.m_xtree = XTree()
        self.m_namespaces = {}
        self.m_fields = []

    def parse(self, inXmlElement):
        super().parse(inXmlElement)
        if self.m_name == self.m_root.m_modtype:
            self.m_modname = self.m_root.m_modname

        if Y_NS in inXmlElement.attrib:
            #            if self.m_name != self.m_root.m_modtype and self.m_name not in self.m_root.m_rpcs:
            #                raise XException('only module complex type has y:ns attrib')
            self.m_namespaces = nsparse(inXmlElement.attrib[Y_NS])

        for element in inXmlElement.iterfind(".//xsd:sequence/xsd:element", XSDNS):
            leafname = None
            leafprefix = None
            if Y_LEAFNAME in element.attrib:
                leafname = element.attrib[Y_LEAFNAME]

            if Y_LEAFPREFIX in element.attrib:
                leafprefix = element.attrib[Y_LEAFPREFIX]

            field = ElementField(
                element.attrib['name'], element.attrib['type'], leafname, leafprefix, element.attrib['field_index'])

            if Y_PATH in element.attrib:
                field.m_path = pathlexical(element.attrib[Y_PATH])

            ftype = element.attrib['type']
            if ftype in self.m_root.m_simple_type_dict:
                field.m_leaf = True
                stype = self.m_root.m_simple_type_dict[ftype]
                if isinstance(stype, XSimpleTypeInt):
                    field.m_pbtype = ftype
                    field.m_typename = ftype
                elif isinstance(stype, XSimpleTypeString):
                    field.m_pbtype = 'bytes'
                    field.m_typename = 'string'
                elif isinstance(stype, XSimpleTypeEnum):
                    field.m_pbtype = 'int32'
                    field.m_typename = 'enum'
                else:
                    raise XException('unsupport element type %s ' %
                                     element.attrib['type'])
            else:
                field.m_leaf = False
                field.m_pbtype = pbname(element.attrib['type'])
                if leafname or leafprefix:
                    raise XException('%s:%s is not leaf, only leaf has y:leafname, y:leafprefix attrib', (
                        self.m_name, element.attrib['name']))

            if Y_LIST in element.attrib:
                field.m_list = True
                field.m_pboption = 'repeated'
                # if field.m_leaf:
                # raise XException('leaf type cannot has y:list attribute')
            elif Y_KEY in element.attrib:
                ystr = element.attrib[Y_KEY]
                field.m_key = int(ystr)
                field.m_pboption = 'required'
                field.m_list = False
                if not field.m_leaf:
                    raise XException('only leaf type has y:key attribute')
            elif Y_LEAFMAND in element.attrib:
                field.m_mandatory = True
                field.m_pboption = 'required'
                field.m_list = False
                if not field.m_leaf:
                    raise XException('only leaf type has y:leafmand attribute')

            if Y_NOMAP in element.attrib:
                field.m_nomap = True
            else:
                field.m_nomap = False

            if Y_NODEOPR in element.attrib:
                field.m_nodeopr = pbname(field.m_name + "_opr")

            if Y_NS in element.attrib:
                ystr = element.attrib[Y_NS]
                if ystr.startswith('/') and self.m_name != self.m_modtype:
                    raise XException(
                        'only module complex type has y:ns attrib which start with "/"')
                field.m_namespaces = nsparse(ystr)

            self.m_fields.append(field)
            logger.debug("parsed complexType %s", self.m_name)

    def parentpathsplit(self):
        index = 0
        # while index < len(self.m_fields):
        for element in self.m_fields:
            #element = self.m_fields[index]
            if element.m_nomap:
                index = index + 1
                continue

            shared = element.m_path
            if shared is None:
                index = index + 1
                continue

            slashn = 0
            while True:
                shared = rsubpath(element.m_path, slashn)
                slashn = slashn + 1
                if shared is None:
                    break

                matched = 0
                for element2 in self.m_fields:
                    if element2.m_nomap:
                        continue

                    if element2.m_path is None:
                        continue
                    path = element2.m_path + '/'
                    if path.startswith(shared + '/'):
                        matched = matched + 1
                        logger.debug("complexType %s field %s & field %s shared part with %s",
                                     self.m_name, element.m_name, element2.m_name, shared)
                if matched >= 2:
                    break

            logger.debug("complexType %s field %s parent %s shared part %s",
                         self.m_name, element.m_name, element.m_path, shared)
            if shared is not None:
                element.m_path_shared = pathsplit(shared)
                element.m_path_priv = pathsplit(element.m_path[len(shared)+1:])
            else:
                element.m_path_priv = pathsplit(element.m_path)
            if element.m_list:
                element.m_path_priv_list = element.m_path_priv.pop()

            #self.m_fields[index] = element
            #index = index + 1

    def build(self):
        self.parentpathsplit()
        for element in self.m_fields:
            if element.m_nomap:
                continue

            if element.m_key > 0:
                self.m_fields_key[element.m_key] = element
                continue
            elif element.m_mandatory:
                self.m_fields_mandatory.append(element)
                continue

            if not element.m_path_shared:
                self.m_fields_noshared.append(element)
                continue

            self.m_xtree.build(element)

    def invalidate_post_1(self):
        super().invalidate_post_1()
        for field in self.m_fields:
            # invalidate type and generate m_type_obj
            ftype = None
            if field.m_type in self.m_root.m_simple_type_dict:
                ftype = self.m_root.m_simple_type_dict[field.m_type]
                ftype.m_refed = True
            elif field.m_type in self.m_root.m_complex_type_dict:
                ftype = self.m_root.m_complex_type_dict[field.m_type]
                if not ftype.m_refed:
                    ftype.invalidate_post()
                    ftype.m_refed = True
            field.m_type_obj = ftype


class YModule(object):
    def __init__(self, inXsdName):
        self.m_xsd_name = os.path.basename(inXsdName)
        self.m_xsd_tree = ElementTree.parse(inXsdName)
        self.m_xsd_root = self.m_xsd_tree.getroot()
        self.m_modname = ''
        self.m_modtype = ''
        self.m_namespaces = {}

        self.m_simple_types = []
        self.m_simple_type_dict = {}

        self.m_complex_types = []
        self.m_complex_type_dict = {}
        self.m_rpcs = {}
        self.m_notifys = {}

    @property
    def namespace(self):
        if '' in self.m_namespaces:
            return self.m_namespaces['']
        raise XException('there is no module namespace')

    def parse(self):
        logger.debug("begin parse %s", self.m_xsd_name)
        self.load_root()
        self.load_simple_types()
        self.load_complex_types()
        self.load_complex_types_post()

    def load_root(self):
        modules = self.m_xsd_root.findall(
            ".//xsd:complexType[@name='YANGModules']/xsd:sequence/xsd:element", XSDNS)
        if len(modules) != 1:
            raise XException('only support one xsd one yang module')
        self.m_modname = modules[0].attrib['name']
        self.m_modtype = modules[0].attrib['type']

        for element in self.m_xsd_root.iterfind(".//xsd:complexType[@name='YANGRpcs']/xsd:sequence/xsd:element", XSDNS):
            name = element.attrib['name']
            rpc = ElementRpc(name)
            rpc.parse(element)
            self.m_rpcs[name] = rpc

        for element in self.m_xsd_root.iterfind(".//xsd:complexType[@name='YANGNotifys']/xsd:sequence/xsd:element", XSDNS):
            name = element.attrib['name']
            notify = ElementNotify(name)
            notify.parse(element)
            self.m_notifys[name] = notify

    def load_simple_types(self):
        for simple in self.m_xsd_root.iterfind(".//xsd:simpleType", XSDNS):
            name = simple.attrib['name']

            simpleType = None
            if simple.findall(".//xsd:restriction/xsd:enumeration", XSDNS):
                simpleType = XSimpleTypeEnum(name)
            elif name in ('int32', 'uint32', 'int64', 'uint64'):
                simpleType = XSimpleTypeInt(name)
            else:
                simpleType = XSimpleTypeString(name)
            simpleType.parse(simple)
            self.type_add(simpleType)

    def load_complex_types(self):
        for complex in self.m_xsd_root.iterfind(".//xsd:complexType", XSDNS):
            name = complex.attrib['name']
            if name in ('YANGModules', 'YANGRpcs', 'YANGNotifys'):
                continue
            complexType = XComplexType(name)
            self.type_add(complexType)
            complexType.parse(complex)

    def load_complex_types_post(self):
        for complexType in self.m_complex_types:
            complexType.build()
            complexType.invalidate_post()
        self.m_namespaces = self.m_complex_type_dict[self.m_modtype].m_namespaces

    def type_add(self, inType):
        if isinstance(inType, XSimpleType):
            if inType.m_name in self.m_simple_type_dict:
                raise XException("simpleType %s duplicate!!" % inType.m_name)
            self.m_simple_types.append(inType)
            self.m_simple_type_dict[inType.m_name] = inType
#            logger.debug("add simpleType %s", (inType.m_name))
        elif isinstance(inType, XComplexType):
            if inType.m_name in self.m_complex_type_dict:
                raise XTypeException(
                    "complexType %s duplicate!!" % inType.m_name)
            self.m_complex_types.append(inType)
            self.m_complex_type_dict[inType.m_name] = inType
#            logger.debug("add complexType %s", (inType.m_name))
        else:
            raise XTypeException(
                'unkown simpleType/complexType %s', inType.m_name)
        inType.m_root = self


def isXSimpleTypeEnum(inSimpleType):
    if isinstance(inSimpleType, XSimpleTypeEnum):
        return True
    else:
        return False
