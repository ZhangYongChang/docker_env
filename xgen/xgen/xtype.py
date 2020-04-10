#! /usr/bin/python
#

"""
fiberhome xsd file parser which parse:
w:pbout          mark a complexType as a ne config block type
w:pbinc          mark a complexType as a ne config block list item type
w:pbcommon       mark a complexType as common type
w:en             field english name
w:cn             field chinese name
w:index          field index which equal with protobuf message field no
w:if             mark field type is a block complexType, and its id
w:nopb           mark field donnot seriealized to protobuf message
w:while          mark field as list
w:key            mark field as list key
w:range          mark field value range
w:show           mark field show pattern
w:hide           mark field not show
w:bittype        mark field bittype
"""

from xml.etree import ElementTree
import re
import logging
import traceback
from . import util

XSDNS = {'xsd': 'http://www.w3.org/2001/XMLSchema',
         'w': 'http://www.fiberhome.com.cn/board/control',
         'y': 'http://www.fiberhome.com.cn/ns/yang'}

W_PBOUT = '{%s}pbout' % XSDNS['w']
W_PBINC = '{%s}pbinc' % XSDNS['w']
W_PBCOMMON = '{%s}pbcommon' % XSDNS['w']
W_EN = '{%s}en' % XSDNS['w']
W_CN = '{%s}cn' % XSDNS['w']
W_INDEX = '{%s}index' % XSDNS['w']
W_NOPB = '{%s}nopb' % XSDNS['w']
W_WHILE = '{%s}while' % XSDNS['w']
W_KEY = '{%s}key' % XSDNS['w']
W_RANGE = '{%s}range' % XSDNS['w']
W_SHOW = '{%s}show' % XSDNS['w']
W_HIDE = '{%s}hide' % XSDNS['w']
W_IF = '{%s}if' % XSDNS['w']
W_BITTYPE = '{%s}bittype' % XSDNS['w']

logger = logging.getLogger(__name__)


class XTypeException(Exception):
    pass


class XEnum(object):
    """
    xsd simpleType/restriction/enumeration
    """

    def __init__(self, inValue, inEn=None, inCn=None):
        self.m_value = inValue
        self.m_en = inEn
        self.m_cn = inCn


class XElement(object):
    """
    xsd complexType/sequence/element
    """

    def __init__(self):
        self.m_name = ''
        self.m_type = ''
        self.m_en = ''
        self.m_cn = ''
        self.m_nopb = False

        self.m_type_obj = None
        self.m_parent = None

    def parse(self, inXmlElement):
        self.m_name = inXmlElement.attrib['name']
        self.m_type = inXmlElement.attrib['type']

        if W_EN in inXmlElement.attrib:
            self.m_en = inXmlElement.attrib[W_EN]

        if W_CN in inXmlElement.attrib:
            self.m_cn = inXmlElement.attrib[W_CN]

        if W_NOPB in inXmlElement.attrib:
            self.m_nopb = True


class XElementBlock(XElement):
    """
    xsd complexType[@name = DataBlockConfig]/sequence/element
    """

    def __init__(self):
        super().__init__()
        self.m_no = None

    def parse(self, inXmlElement):
        super().parse(inXmlElement)
        self.parse_block_id(inXmlElement)

    def parse_block_id(self, inXmlElement):
        if W_IF in inXmlElement.attrib:
            strid = inXmlElement.attrib[W_IF]
            hexid = re.search(".*Index.*\'([a-zA-Z0-9]*)\'.*", strid).group(1)
            self.m_no = int(hexid, base=16)


class XElementField(XElement):
    """
    xsd complexType[@pbcommon or @pbinc or @pbout]/sequence/element
    """

    def __init__(self):
        super().__init__()
        self.m_default = None
        self.m_range = None
        self.m_show = None
        self.m_key = 0
        self.m_hide = False
        self.m_index = None
        self.m_while = None
        self.m_bittype = None

        self.m_while_for = None
        self.m_child_has_key = False

    def parse(self, inXmlElement):
        super().parse(inXmlElement)
        if 'default' in inXmlElement.attrib:
            self.m_default = inXmlElement.attrib['default']

        if W_RANGE in inXmlElement.attrib:
            self.m_range = inXmlElement.attrib[W_RANGE]

        if W_SHOW in inXmlElement.attrib:
            self.m_show = inXmlElement.attrib[W_SHOW]

        if W_KEY in inXmlElement.attrib:
            #            print(inXmlElement.items())
            try:
                self.m_key = int(inXmlElement.attrib[W_KEY])
            except Exception as exc:
                self.m_key = 1

            if self.m_key < 1:
                raise XTypeException(
                    "field %s's w:key attribute must > 0" % (self.m_name))

        if W_HIDE in inXmlElement.attrib:
            #            print(inXmlElement.items())
            self.m_hide = True

        if W_INDEX in inXmlElement.attrib:
            #            print(inXmlElement.items())
            self.m_index = int(inXmlElement.attrib[W_INDEX])

        if W_WHILE in inXmlElement.attrib:
            self.m_while = inXmlElement.attrib[W_WHILE]
            if re.match('^\.\./[a-zA-Z_][a-zA-Z0-9_]*$', self.m_while) is None and re.match('^[1-9][0-9]*$', self.m_while) is None:
                raise XTypeException(
                    "complexType %s field %s attribute w:while invalid, must be '../fieldname'" % (self.m_parent.m_name, self.m_name))

        if self.m_while and self.m_key:
            raise XTypeException("complexType %s field %s with w:key should be normal field(without w:while)" % (
                self.m_parent.m_name, self.m_name))

        if W_BITTYPE in inXmlElement.attrib:
            self.m_bittype = inXmlElement.attrib[W_BITTYPE]


class XType(object):
    """
    base class of simpleType/complexType
    """

    def __init__(self, inName):
        if not re.match('^[a-zA-Z0-9_]*$', inName):
            raise XTypeException(
                'simpleType/complexType name "%s" invalid' % (inName))
        self.m_name = inName
        self.m_refcnt = 0
        self.m_root = None
        self.m_refedby = []

    def ref(self, refedby):
        self.m_refcnt += 1
        if refedby is not self:
            self.m_refedby.append(refedby)
            logger.debug("%s refed by %s" % (self.m_name, refedby.m_name))

    def refed(self):
        return self.m_refcnt > 0

    def refcnt(self):
        return self.m_refcnt

    def parse(self, inXmlElement):
        logger.debug("%s parse" % (self.m_name))
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
            #            raise XTypeException("simpleType must has length info except enumeration, error simpleType %s" % name)
            return

        self.m_len = int(length.attrib['value'])


class XSimpleTypeEnum(XSimpleType):
    def __init__(self, inName):
        super().__init__(inName)
        self.m_enums = {}

    def parse(self, inXmlElement):
        super().parse(inXmlElement)

        enums = list(inXmlElement.iterfind(
            ".//xsd:restriction/xsd:enumeration", XSDNS))
        for enum in enums:
            value = int(enum.attrib["value"], base=16)
            en = enum.attrib[W_EN]

            cn = None
            if W_CN in enum.attrib:
                cn = enum.attrib[W_CN]
            else:
                logger.warning(
                    "enumeration simpleType %s:%d has no w:cn attribute", self.m_name, value)

            enumElement = XEnum(value, inEn=en, inCn=cn)
            self.enum_add(enumElement)

    def enum_add(self, inEnum):
        if inEnum.m_value in self.m_enums:
            raise XTypeException("enumeration simpleType %s value %d duplicate" % (
                self.m_name, inEnum.m_value))
        if inEnum.m_en in [x.m_en for x in self.m_enums.values()]:
            raise XTypeException(
                "enumeration simpleType %s w:en %s duplicate" % (self.m_name, inEnum.m_en))
        if inEnum.m_cn in [x.m_cn for x in self.m_enums.values()]:
            raise XTypeException(
                "enumeration simpleType %s w:cn %s duplicate" % (self.m_name, inEnum.m_cn))
        self.m_enums[inEnum.m_value] = inEnum


class XComplexType(XType):
    def __init__(self, inName):
        super().__init__(inName)
        self.m_elements = []

    def element_add(self, inElement):
        self.m_elements.append(inElement)
        inElement.m_parent = self

    def invalidate(self):
        super().invalidate()
        if len(self.m_elements) == 0:
            raise XTypeException("complexType %s has no field", (self.m_name))

        fnames = []
        for field in self.m_elements:
            if not re.match('^[a-zA-Z0-9_]*$', field.m_name):
                raise XTypeException(
                    'complexTpe %s field "%s" name invalid' % (self.m_name, field.m_name))
            fname = field.m_name.upper()
            if fname in fnames:
                raise XTypeException(
                    "complexType %s field %s name duplicate" % (self.m_name, field.m_name))
            fnames.append(fname)

    def invalidate_post_1(self):
        super().invalidate_post_1()
        for field in self.m_elements:
            # invalidate type and generate m_type_obj
            ftype = None
            if field.m_type in self.m_root.m_simple_type_dict:
                ftype = self.m_root.m_simple_type_dict[field.m_type]
            elif field.m_type in self.m_root.m_complex_type_dict:
                ftype = self.m_root.m_complex_type_dict[field.m_type]
                if not ftype.refed():
                    #                    logger.debug("post 1 invalidate complexType %s" % (field.m_type))
                    ftype.invalidate_post()
            else:
                raise XTypeException("complexType %s field %s's type %s not defined" % (
                    self.m_name, field.m_name, field.m_type))
            ftype.ref(self)
            field.m_type_obj = ftype

    def dependency(self, depends):
        for field in self.m_elements:
            if field.m_type_obj in depends:
                continue
            depends.append(field.m_type_obj)

            if isinstance(field.m_type_obj, XComplexType):
                field.m_type_obj.dependency(depends)


class XComplexTypePB(XComplexType):
    def __init__(self, inName):
        super().__init__(inName)
        self.m_has_key_field = False

    def parse(self, inXmlElement):
        elements = list(inXmlElement.iterfind(
            ".//xsd:sequence/xsd:element", XSDNS))
        for element in elements:
            xelement = XElementField()
            self.element_add(xelement)
            xelement.parse(element)

    def invalidate(self):
        super().invalidate()

        # invalidate index
        indexFirst = self.m_elements[0].m_index
        indexs = {}
        for field in self.m_elements:
            if (indexFirst is not None and field.m_index is None) or (indexFirst is None and field.m_index is not None):
                #                print(field.m_index, indexFirst)
                raise XTypeException("complexType %s field must all have w:index attribute, or no one field has w:index attribute, please check field %s first!" % (
                    self.m_name, field.m_name))

            if field.m_index:
                if field.m_index in indexs:
                    raise XTypeException("complexType %s field %s w:index duplicate with field %s!" % (
                        self.m_name, field.m_name, indexs[field.m_index].m_name))
                indexs[field.m_index] = field

            if field.m_key and not field.m_nopb:
                self.m_has_key_field = True

        index = 1
        if indexFirst is None:
            for field in self.m_elements:
                field.m_index = index
                index += 1
#                print(field.m_index, index)

    def invalidate_post_1(self):
        super().invalidate_post_1()

        for field in self.m_elements:
            if field.m_bittype:
                if field.m_bittype in self.m_root.m_simple_type_dict:
                    ftype = self.m_root.m_simple_type_dict[field.m_bittype]
                elif field.m_bittype in self.m_root.m_complex_type_dict:
                    ftype = self.m_root.m_complex_type_dict[field.m_bittype]
                else:
                    raise XTypeException("complexType %s field %s's bittype %s not defined" % (
                        self.m_name, field.m_name, field.m_bittype))
                ftype.ref(self)

            # invlidate while and generate m_while_for; and determine m_key_child
            if field.m_while:
                match = re.search(
                    "^../([a-zA-Z_][a-zA-Z0-9_]*)$", field.m_while)
                if match is None:
                    continue
                gotit = False
                for wfield in self.m_elements:
                    if wfield.m_name == match.group(1):
                        wfield.m_while_for = field
                        field.m_while_field = wfield
                        gotit = True
                        break
                if not gotit:
                    raise XTypeException("complexType %s while field %s not exist" % (
                        self.m_name, match.group(1)))

                if not isinstance(field.m_type_obj, XComplexType):
                    raise XTypeException("complexType %s w:while field %s's type %s must be complexType" % (
                        self.m_name, field.m_name, field.m_type))
            elif isinstance(field.m_type_obj, XComplexType) and field.m_type_obj.m_has_key_field:
                field.m_child_has_key = True
                self.m_has_key_field = True

            # m_default invalidate
            if field.m_default:
                if not isinstance(field.m_type_obj, XSimpleType):
                    raise XTypeException("complexType %s field %s's type %s is not simpleType, only simpleType field has default attribute" % (
                        self.m_name, field.m_name, field.m_type))
                if len(field.m_default)/2 > field.m_type_obj.m_len:
                    raise XTypeException("complexType %s field %s's default value length %d > %s's len %d" % (
                        self.m_name, field.m_name, len(field.m_default)/2, field.m_type_obj.m_name, field.m_type_obj.m_len))
                if field.m_type_obj.m_len in (1, 2, 4):
                    field.m_default_value = int(field.m_default, base=16)
                    if isinstance(field.m_type_obj, XSimpleTypeEnum) and field.m_default_value not in field.m_type_obj.m_enums:
                        raise XTypeException("complexType %s field %s's default value %d is not in enum %s" % (
                            self.m_name, field.m_name, field.m_default_value, field.m_type_obj.m_enums.keys()))

    def invalidate_post_2(self):
        super().invalidate_post_2()
        for field in self.m_elements:
            if not field.m_while_for:
                continue

            if isinstance(field.m_type_obj, XSimpleType) and field.m_type_obj.m_len in (1, 2, 4):
                continue

            raise XTypeException("complexType %s field %s's type must be BYTE,WORD,DWORD which w:whiled by element %s" % (
                self.m_name, field.m_name, field.m_while_for.m_name))


class XComplexTypeCommon(XComplexTypePB):
    def __init__(self, inName):
        super().__init__(inName)

    def invlidate_post_1(self):
        super().invlidate_post_1()
        for field in self.m_elements:
            if isinstance(field.m_type_obj, XComplexType) and not isinstance(field.m_type_obj, XComplexTypeCommon):
                raise XTypeException("complexType %s field %s's type %s must has w:pbcommon attribute", (
                    self.m_name, field.m_name, field.m_type))


class XComplexTypeInc(XComplexTypePB):
    def __init__(self, inName):
        super().__init__(inName)

    def invlidate_post_1(self):
        super().invlidate_post_1()
        for field in self.m_elements:
            if isinstance(field.m_type_obj, XComplexType) and not isinstance(field.m_type_obj, XComplexTypeCommon):
                raise XTypeException("complexType %s field %s's type %s must has w:pbcommon attribute", (
                    self.m_name, field.m_name, field.m_type))


class XComplexTypeOut(XComplexTypePB):
    def __init__(self, inName):
        super().__init__(inName)
        self.m_item_type = None

    def invalidate(self):
        super().invalidate()
        fieldw = None
        for field in self.m_elements:
            if field.m_while:
                if fieldw is not None:
                    raise XTypeException(
                        "w:pbout complexType %s must have only one element with w:while attribute" % (self.m_name))
                fieldw = field
#                logger.debug(fieldw)
        if fieldw is None:
            raise XTypeException(
                "w:pbout complexType %s must have one element with w:while attribute" % (self.m_name))

        if not fieldw.m_type.endswith("_Item") and not fieldw.m_type.endswith("_item"):
            logger.warning("w:pbout complexType %s's item type %s suggest endswith '_Item' or '_item'" % (
                self.m_name, fieldw.m_type))

        self.m_item_type = fieldw.m_type

    def invalidate_post_1(self):
        super().invalidate_post_1()

        for field in self.m_elements:
            if field.m_while:
                self.m_item_type = self.m_root.m_complex_type_dict[self.m_item_type]
                if not isinstance(self.m_item_type, XComplexTypeInc):
                    raise XTypeException("w:pbout complexType %s's item type %s has no attribute w:pbinc" % (
                        self.m_name, self.m_item_type.m_name))
                break


class XComplexTypeRoot(XComplexType):
    def __init__(self, inName):
        super().__init__(inName)

    def parse(self, inXmlElement):
        elements = list(inXmlElement.iterfind(
            ".//xsd:sequence/xsd:element", XSDNS))
        for element in elements:
            xelement = XElementBlock()
            xelement.parse(element)
            for block in self.m_elements:
                if xelement.m_no == block.m_no:
                    raise XTypeException("w:pbout complexType %s's no %X duplicate with %s" % (
                        xelement.m_type, xelement.m_no, block.m_type))
            self.element_add(xelement)
            if xelement.m_no:
                logger.debug('blockdataconfig element item %s(%X)' %
                             (xelement.m_name, xelement.m_no))
            else:
                logger.debug('blockdataconfig element item %s' %
                             (xelement.m_name, ))

    def invalidate(self):
        super().invalidate()

    def invalidate_post_1(self):
        super().invalidate_post_1()
        for field in self.m_elements:
            if isinstance(field.m_type_obj, XComplexType) and not isinstance(field.m_type_obj, XComplexTypeOut):
                raise XTypeException("block %s's type %s must has w:pbout attribute!!" % (
                    field.m_name, field.m_type))
        self.ref(self)

    def invalidate_post_2(self):
        pass


class XXsdTree(object):
    def __init__(self, inXsdFile):
        self.m_xsd_file = inXsdFile
        self.m_xsd_name = inXsdFile.split('\\')[-1]
        self.m_xsd_root = ElementTree.parse(self.m_xsd_file).getroot()

        self.m_complex_root = None

        self.m_simple_types = []
        self.m_simple_type_dict = {}

        self.m_complex_types = []
        self.m_complex_type_dict = {}

        self.m_meta_complex_types = ['BlockTableItem', 'AllConfig']

    def meta_complex_add(self, inName):
        self.m_meta_complex_types.append(inName)

    def simple_types_unrefed(self):
        return [type.m_name for type in self.m_simple_types if not type.refed()]

    def complex_types_unrefed(self):
        return [type.m_name for type in self.m_complex_types if not type.refed()]

    def type_add(self, inType):
        if isinstance(inType, XSimpleType):
            if inType.m_name in self.m_simple_type_dict:
                raise XTypeException(
                    "simpleType %s duplicate!!" % inType.m_name)
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

    def parse(self):
        self.load_complex_root()
        self.load_simple_types()
        self.load_complex_types()
        self.m_complex_root.invalidate_post()
        self.dagsort()

        for complex in self.m_complex_types:
            if complex is not self.m_complex_type_dict[complex.m_name]:
                #                raise XTypeException("%s id(list) %d != id(dict) %d" % (complex.m_name, id(complex), id(self.m_complex_type_dict[complex.m_name])))
                pass
            logger.debug("%s id(list) %d, id(dict) %d", complex.m_name, id(
                complex), id(self.m_complex_type_dict[complex.m_name]))

    def load_complex_root(self):
        element = self.m_xsd_root.find("xsd:element", XSDNS)
        self.m_complex_root = XComplexTypeRoot(element.attrib['type'])
        logger.debug("root complexType %s" % (self.m_complex_root.m_name))
        self.meta_complex_add(self.m_complex_root.m_name)

        element = self.m_xsd_root.find(
            ".//xsd:complexType[@name='" + self.m_complex_root.m_name + "']", XSDNS)
        self.m_complex_root.parse(element)

        self.type_add(self.m_complex_root)
        self.m_complex_root.invalidate()

    def load_simple_types(self):
        for simple in list(self.m_xsd_root.iterfind(".//xsd:simpleType", XSDNS)):
            name = simple.attrib['name']

            simpleType = None
            if simple.findall(".//xsd:restriction/xsd:enumeration", XSDNS):
                simpleType = XSimpleTypeEnum(name)
            else:
                simpleType = XSimpleType(name)
            simpleType.parse(simple)
            self.type_add(simpleType)
            simpleType.invalidate()

    def load_complex_types(self):
        for complex in list(self.m_xsd_root.iterfind(".//xsd:complexType", XSDNS)):
            name = complex.attrib['name']

            complexType = None
            if W_PBOUT in complex.attrib:
                complexType = XComplexTypeOut(name)
            elif W_PBINC in complex.attrib:
                complexType = XComplexTypeInc(name)
            elif W_PBCOMMON in complex.attrib:
                complexType = XComplexTypeCommon(name)
            else:
                if name not in self.m_meta_complex_types:
                    complexType = XComplexTypePB(name)
                else:
                    continue
#                    print("[Warning] complexType %s is not one of (w:pbcommon, w:pbinc, w:pbout), discard it" % (name))
#                    raise XTypeException("complexType %s has no one attribute of (w:pbcommon, w:pbinc, w:pbout), amend it please" % (name));
#                continue

            complexType.parse(complex)
            self.type_add(complexType)
            complexType.invalidate()

    def dagsort(self):
        """
        Directed Acyclic Graph, topologic sorting
        """
        indegrees = dict((u, 0) for u in self.m_complex_types)
        vertexnum = len(indegrees)
        for u in self.m_complex_types:
            for v in self.m_complex_type_dict[u.m_name].m_refedby:
                indegrees[v] += 1

        seq = []
        Q = [u for u in sorted(
            self.m_complex_types, key=lambda d:d.m_name.upper()) if indegrees[u] == 0]
        logger.debug("no dependency complexType : %s" %
                     ([d.m_name for d in Q]))
        while Q:
            u = Q.pop(0)
            seq.append(u)

            tmpQ = []
            for v in self.m_complex_type_dict[u.m_name].m_refedby:
                indegrees[v] -= 1
                if indegrees[v] == 0:
                    tmpQ.append(v)
                elif indegrees[v] < 0:
                    raise XTypeException("DAG sort BUG!!")
            tmpQ = sorted(tmpQ, key=lambda d: d.m_name.upper())
            logger.debug("pop %s, push %s" %
                         (u.m_name, [d.m_name for d in tmpQ]))
            Q.extend(tmpQ)
            logger.debug("new Q %s " % ([d.m_name for d in Q]))

        if len(seq) == vertexnum:
            logger.debug("DAG sorting before:%s" %
                         [d.m_name for d in self.m_complex_types])
            self.m_complex_types = seq
            logger.debug("DAG sorting after:%s" %
                         [d.m_name for d in self.m_complex_types])
        else:
            raise XTypeException("there is a circle")

    """
    return block complextype and its dependency as list
    """

    def iterblocks(self):
        for field in self.m_complex_root.m_elements:
            depends = [field.m_type_obj]
            field.m_type_obj.dependency(depends)
            yield depends


def isXSimpleType(inSimpleType):
    if isinstance(inSimpleType, XSimpleType):
        return True
    else:
        return False


def isXSimpleTypeEnum(inSimpleType):
    if isinstance(inSimpleType, XSimpleTypeEnum):
        return True
    else:
        return False


def isXComplexType(inComplexType):
    if isinstance(inComplexType, XComplexType):
        return True
    else:
        return False


def isXComplexTypeCommon(inComplexType):
    if isinstance(inComplexType, XComplexTypeCommon):
        return True
    else:
        return False


def isXComplexTypeInc(inComplexType):
    if isinstance(inComplexType, XComplexTypeInc):
        return True
    else:
        return False


def isXComplexTypeOut(inComplexType):
    if isinstance(inComplexType, XComplexTypeOut):
        return True
    else:
        return False


def isXComplexTypeRoot(inComplexType):
    if isinstance(inComplexType, XComplexTypeRoot):
        return True
    else:
        return False
