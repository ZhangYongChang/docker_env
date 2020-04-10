
import logging
import concurrent.futures
from jinja2 import Environment, DictLoader
from .xtype import *

logger = logging.getLogger(__name__)


class XGenUtil(object):
    def capital(inStr):
        return inStr[:1].upper() + inStr[1:]

    def classname(inXType):
        if not isinstance(inXType, XComplexType):
            raise XGenException("")
        return 'C' + XGenUtil.capital(inXType.m_name)

    def memberclass(inObj, inOrig=False):
        if not isinstance(inObj, XElement):
            raise XGenException("")

        name = ''

        if isinstance(inObj.m_type_obj, XSimpleType):
            if inObj.m_type_obj.m_len == 1:
                name = 'BYTE'
            elif inObj.m_type_obj.m_len == 2:
                name = 'WORD'
            elif inObj.m_type_obj.m_len == 4:
                name = 'DWORD'
            elif inObj.m_type_obj.m_len > 0:
                name = 'BYTE'
            else:
                raise XGenException('unkown simple type len')
        elif isinstance(inObj.m_type_obj, XComplexType):
            if hasattr(inObj, 'm_while') and inObj.m_while and not inOrig:
                name = 'vector<' + XGenUtil.classname(inObj.m_type_obj) + '> '
            else:
                name = XGenUtil.classname(inObj.m_type_obj)
        else:
            raise XGenException('unkown inObj.m_type_obj %s for field %s' % (
                inObj.m_type_obj, inObj.m_name))
        return name

    def memberclasspb(inObj):
        if not isinstance(inObj, XElement):
            raise XGenException("")
        name = ''
        if isinstance(inObj.m_type_obj, XSimpleType):
            if inObj.m_type_obj.m_len in (1, 2, 4):
                name = 'int32'
            elif inObj.m_type_obj.m_len > 0:
                name = 'bytes'
            else:
                raise XGenException('unkown simple type len')
        elif isinstance(inObj.m_type_obj, XComplexType):
            name = inObj.m_type_obj.m_name.lower()
        else:
            raise XGenException('unkown ftype %s', inObj.m_type_obj)
        return name

    def membername(inObj):
        if not isinstance(inObj, XElement):
            raise XGenException("")

        name = ''
        if isinstance(inObj.m_type_obj, XSimpleType):
            if inObj.m_type_obj.m_len == 1:
                name = 'm_by' + XGenUtil.capital(inObj.m_name)
            elif inObj.m_type_obj.m_len == 2:
                name = 'm_w' + XGenUtil.capital(inObj.m_name)
            elif inObj.m_type_obj.m_len == 4:
                name = 'm_dw' + XGenUtil.capital(inObj.m_name)
            elif inObj.m_type_obj.m_len > 0:
                name = 'm_ar' + XGenUtil.capital(inObj.m_name)
#                print (inObj.m_name)
            else:
                raise XGenException('unkown simple type len')
        elif isinstance(inObj.m_type_obj, XComplexType):
            if hasattr(inObj, 'm_while') and inObj.m_while:
                name = 'm_ar' + XGenUtil.capital(inObj.m_name)
            else:
                name = 'm_o' + XGenUtil.capital(inObj.m_name)
        else:
            raise XGenException('unkown ftype %s', inObj.m_type_obj)
        return name

    def membernamepb(inObj):
        if not isinstance(inObj, XElement):
            raise XGenException("")

        name = ''
        if isinstance(inObj.m_type_obj, XSimpleType):
            name = inObj.m_name.lower()
        elif isinstance(inObj.m_type_obj, XComplexType):
            name = inObj.m_name.lower()
        else:
            raise XGenException('unkown ftype %s', inObj.m_type_obj)
        return name

    def memberprefixpb(inObj):
        if not isinstance(inObj, XElement):
            raise XGenException("")
        name = ''
        if hasattr(inObj, 'm_while') and inObj.m_while:
            name = 'repeated'
        else:
            name = 'optional'
        return name

    def membersuffix(inObj):
        name = ''
        if not isinstance(inObj, XElement):
            raise XGenException("")

        if isinstance(inObj.m_type_obj, XSimpleType):
            if inObj.m_type_obj.m_len not in (1, 2, 4) and inObj.m_type_obj.m_len > 0:
                name = '[' + str(inObj.m_type_obj.m_len) + ']'
        return name

    def defaultallzero(inObj):
        if not isinstance(inObj, XElement):
            raise XGenException("")

        if not hasattr(inObj, 'm_default') or not inObj.m_default or len(inObj.m_default) <= 0:
            return True

        for ch in inObj.m_default:
            if ch != '0':
                logger.debug('notallzero default:%s' % (inObj.m_default))
                return False

        return True

    def defaulthex(inStr):
        hexs = ''
        idx = 0
        while idx < len(inStr):
            if idx % 2:
                hexs += inStr[idx]
            else:
                hexs += r'\x' + inStr[idx]
            idx += 1
        logger.debug('default %s hexed %s' % (inStr, hexs))
        return hexs


class XGenException(Exception):
    pass


class XGenField(object):
    """
    XGenField
    """

    def __init__(self, inField):
        self.m_field = inField
        pass

    def parse(self):
        self.x_member_class = XGenUtil.memberclass(self.m_field)
        self.x_member_class_orig = XGenUtil.memberclass(self.m_field, True)
        self.x_member_class_pb = XGenUtil.memberclasspb(self.m_field)
        self.x_member_name = XGenUtil.membername(self.m_field)
        self.x_member_name_pb = XGenUtil.membernamepb(self.m_field)
        self.x_member_suffix = XGenUtil.membersuffix(self.m_field)
        self.x_member_prefix_pb = XGenUtil.memberprefixpb(self.m_field)
        if isinstance(self.m_field.m_type_obj, XSimpleType):
            self.x_member_default_allzero = XGenUtil.defaultallzero(
                self.m_field)
            if hasattr(self.m_field, 'm_default') and self.m_field.m_default and self.m_field.m_type_obj.m_len not in (1, 2, 4):
                self.x_member_default_hexed = XGenUtil.defaulthex(
                    self.m_field.m_default)


class XGenComplex(object):
    """
    wrapper for XComplexType
    """

    def __init__(self, inComplex):
        self.m_complex = inComplex

        self.x_class = XGenUtil.classname(self.m_complex)
        self.x_class_pb = self.m_complex.m_name.lower()
        self.x_fields = []

    def parse(self):
        for field in self.m_complex.m_elements:
            xfield = XGenField(field)
            xfield.parse()
            self.x_fields.append(xfield)


class XGen(object):
    """
    XGen, define method which is call by XGen group
    """

    def __init__(self, inName):
        self.m_name = inName
        self.m_result = ''
        self.m_env = None
        self.m_xgeng = None
        self.m_xtypes = []
        self.m_xcomplexs = []
        self.m_xsimples = []

    def xtype_add(self, inXType):
        self.m_xtypes.append(inXType)

    def parse(self):
        for type in self.m_xtypes:
            if isinstance(type, XSimpleType):
                self.m_xsimples.append(type)
            else:
                complex = XGenComplex(type)
                complex.parse()
                self.m_xcomplexs.append(complex)

    def render(self):
        #        self.m_result = xgenenv.render(inTemplate, kwargs)
        pass

    def generate(self):
        self.parse()
        self.render()


def fn_gen(inXGen):
    return inXGen.generate()


def fn_output_file(inFile, inStr):
    inFile.write(inStr)


class XGenG(object):
    """
    XGen group, mutithread, output gen result same order as it is added
    """

    def __init__(self, maxworkers=None, outputer=None, outputargs=()):
        self.m_name = 'XGenG'
        self.m_xgens = {}
        self.m_xgen_to_future = {}
        self.m_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=maxworkers)
        if outputer and not callable(outputer):
            raise XGenException("outputer must be callable")
        self.m_outputer = outputer
        self.m_outputargs = outputargs
        self.m_parent = None

    def xgen_add(self, inXGen):
        if inXGen.m_name in self.m_xgens:
            raise XGenException("XGen name must be unique")
        inXGen.m_xgeng = self
        self.m_xgens[inXGen.m_name] = inXGen

    def xtype_add(self, inXGenName, inXTypes):
        if inXGenName not in self.m_xgens:
            raise XGenException("XGen %s not exist" % (inXGenName))

        for xtype in inXTypes:
            self.m_xgens[inXGenName].xtype_add(xtype)

    def generate(self):
        for (name, xgen) in self.m_xgens.items():
            future = self.m_executor.submit(fn_gen, xgen)
            self.m_xgen_to_future[xgen] = future

        for (xgen, future) in self.m_xgen_to_future.items():
            concurrent.futures.wait([future])
            try:
                data = future.result()
            except Exception as exc:
                raise XGenException('%s %s occur an exception: %s' %
                                    (type(self), xgen.m_name, exc))
            else:
                #                logger.debug('%s %s generated: %s' % (type(self), xgen.m_name, xgen.m_result))
                logger.debug('%s:%s generated: %s' %
                             (self.m_name, xgen.m_name, ''))
                self.m_outputer(self.m_outputargs, xgen.m_result)


class XGenFile(object):
    def __init__(self, inXTree, inDir, inFile):
        self.m_xtree = inXTree
        self.m_dir = inDir
        self.m_filename = inFile
        self.m_file = open(self.m_dir + '/' + self.m_filename, 'w')
        self.m_xgeng = XGenG(
            maxworkers=None, outputer=fn_output_file, outputargs=self.m_file)
#        self.m_xgeng = XGenG(maxworkers=1, outputer=fn_output_file, outputargs = self.m_file)
        self.m_xgeng.m_parent = self

    def mappre(self):
        """
        build pre XGen and add it to XGenG
        """
        pass

    def xgenp(self, inGenName):
        """
        build parallel XGen, called by mapparallel()
        """
        raise XGenException('you should implement %s' % ('xgenp'))

    def paralit(self, inXType):
        """
        map XType to parallel XGen of XGenG or not
        """
        if inXType.m_refcnt < 1:
            return False
        return True

    def paralmap(self):
        """
        return XType list which put int parallel XGens of XGenG
        """
        complexs = []
        for complex in sorted(self.m_xtree.m_complex_types, key=lambda d: d.m_name.upper()):
            if complex.m_refcnt < 1:
                continue

            if self.paralit(complex):
                complexs.append(complex)

        return complexs

    def mapparallel(self):
        """
        build parallel XGen and add it to XGenG
        """
        xtypes = self.paralmap()
        logger.debug("%s will parallel process %s" %
                     (type(self).__name__, [d.m_name for d in xtypes]))
        total = len(xtypes)
        if total < 1:
            return

        xtypes = xtypes
        paranum = 4
        if total < 50:
            paranum = 1
        elif total < 200:
            paranum = 2
        elif total < 500:
            paranum = 3

        step = int(total / paranum)
        if step < 1:
            raise XGenException(
                "too much parallel, total[%d], paranum[%d]" % (total, paranum))
        i = 0
        while i < total:
            genname = 'xgenparallel' + str(int(i/step))
            xgen = self.xgenp(genname)
            self.m_xgeng.xgen_add(xgen)
            end = i + step
            self.m_xgeng.xtype_add(genname, xtypes[i:end])
            logger.debug("%s %s process %s" % (type(self).__name__,
                                               genname, [d.m_name for d in xtypes[i:end]]))
            i += step

    def mappost(self):
        """
        build post XGen and add it to XGenG
        """
        pass

    def map(self):
        """
        build XGens, and map part of inXTree to XGenG
        """
        self.mappre()
        self.mapparallel()
        self.mappost()

    def reduce(self):
        """
        process part of XTree mapped
        """
        self.m_xgeng.generate()
#        logger.warning("reduce not implement by subclass")

    def generate(self):
        self.map()
        self.reduce()
        self.output()
#        logger.info("file generated %s", self.m_filename)

    def output(self):
        pass

    def __del__(self):
        self.m_file.close()
