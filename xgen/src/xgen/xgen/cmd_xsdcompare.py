#! /usr/bin/python
#

"""
Auto compare xsd file to auto merge xsd
"""
import pdb
import concurrent.futures
import logging
import re
import glob
import os
import shutil
from xml.dom.minidom import parse
import xml.dom.minidom
import xml.etree.ElementTree as ElementTree

logger = logging.getLogger(__name__)

XSDNS = {'xsd': 'http://www.w3.org/2001/XMLSchema',
         'w': 'http://www.fiberhome.com.cn/board/control',
         'y': 'http://www.fiberhome.com.cn/ns/yang',
         'xdo': 'urn:pxp',
         'ms': 'urn:schemas-microsoft-com:xslt',
         'stack': 'urn:anything',
         'xdb': 'http://xmlns.oracle.com/xdb'}

ElementTree.register_namespace('xsd', 'http://www.w3.org/2001/XMLSchema')
ElementTree.register_namespace(
    'w', 'http://www.fiberhome.com.cn/board/control')
ElementTree.register_namespace('y', 'http://www.fiberhome.com.cn/ns/yang')
ElementTree.register_namespace('xdo', 'urn:pxp')
ElementTree.register_namespace('ms', 'urn:schemas-microsoft-com:xslt')
ElementTree.register_namespace('stack', 'urn:anything')
ElementTree.register_namespace('xdb', 'http://xmlns.oracle.com/xdb')


class CmdXsdAutoCompare(object):
    def __init__(self, in_orig_dir, in_new_dir, out_new_dir):
        self.in_orig_dir = in_orig_dir
        self.in_new_dir = in_new_dir
        self.out_new_dir = out_new_dir
        if os.path.exists(self.out_new_dir) is False:
            os.mkdir(self.out_new_dir)

        self.in_orig_files = [filename for filename in glob.glob(
            self.in_orig_dir + '/*.xsd')]
        self.in_new_files = [filename for filename in glob.glob(
            self.in_new_dir + '/*.xsd')]

    @staticmethod
    def merge(create_element, new_element):
        new_fields = list(new_element.iterfind(
            ".//xsd:sequence/xsd:element", XSDNS))
        create_fields = list(create_element.iterfind(
            ".//xsd:sequence/xsd:element", XSDNS))
        if create_fields is None or new_fields is None:
            return

        create_seq = list(create_element.iterfind(".//xsd:sequence", XSDNS))
        if len(create_seq) == 1:
            create_seq = create_seq[0]

        create_max_num = 1
        has_attr_field_index = False
        for create_field in create_fields:
            if create_field.get('field_index') is None:
                create_field.set('field_index', str(create_max_num))
                create_max_num = create_max_num + 1
            else:
                create_max_num = max(create_max_num, int(
                    create_field.get('field_index')))
                has_attr_field_index = True

        if has_attr_field_index is True:
            create_max_num = create_max_num + 1

        for new_field in new_fields:
            is_new_field = True
            for create_field in create_fields:
                if create_field.attrib['name'] == new_field.attrib['name']:
                    is_new_field = False
                    break

            if is_new_field is True:
                new_field.set('field_index', str(create_max_num))
                create_seq.append(new_field)
                create_max_num = create_max_num + 1

    @staticmethod
    def merge_enumeration(create_element, new_element):
        new_fields = list(new_element.iterfind(
            ".//xsd:restriction/xsd:enumeration", XSDNS))
        create_fields = list(create_element.iterfind(
            ".//xsd:restriction/xsd:enumeration", XSDNS))
        if not new_fields or not create_fields:
            return

        create_seq = list(create_element.iterfind(".//xsd:restriction", XSDNS))
        if len(create_seq) == 1:
            create_seq = create_seq[0]
        enum_en_attr = "{%s}en" % (XSDNS['w'])
        enum_cn_attr = "{%s}cn" % (XSDNS['w'])

        create_max_num = 1
        has_attr_field_index = False
        for create_field in create_fields:
            if create_field.get('field_index') is None:
                create_field.set('field_index', str(create_max_num))
                create_max_num = create_max_num + 1
            else:
                create_max_num = max(create_max_num, int(
                    create_field.get('field_index')))
                has_attr_field_index = True

        if has_attr_field_index is True:
            create_max_num = create_max_num + 1

        for new_field in new_fields:
            is_new_field = True
            for create_field in create_fields:
                if create_field.attrib[enum_en_attr] == new_field.attrib[enum_en_attr] \
                        and create_field.attrib[enum_cn_attr] == new_field.attrib[enum_cn_attr]:
                    if create_field.attrib['value'] != new_field.attrib['value']:
                        create_field.set('value', new_field.attrib['value'])
                    is_new_field = False
                    break

            if is_new_field is True:
                new_field.set('field_index', str(create_max_num))
                create_seq.append(new_field)
                create_max_num = create_max_num + 1

    @staticmethod
    def setfieldindex(dst_file):
        create_tree = ElementTree.parse(dst_file)
        create_root = create_tree.getroot()
        create_elements = list(
            create_root.iterfind(".//xsd:complexType", XSDNS))

        for create_element in create_elements:
            field_index = 1
            create_fields = list(create_element.iterfind(
                ".//xsd:sequence/xsd:element", XSDNS))
            for create_field in create_fields:
                create_field.set('field_index', str(field_index))
                field_index = field_index + 1

        create_elements = list(
            create_root.iterfind(".//xsd:simpleType", XSDNS))
        for create_element in create_elements:
            field_index = 1
            create_fields = list(create_element.iterfind(
                ".//xsd:restriction/xsd:enumeration", XSDNS))
            for create_field in create_fields:
                create_field.set('field_index', str(
                    int(create_field.get('value'), base=16)))

        create_tree.write(dst_file, encoding='utf-8', xml_declaration=True)

    @staticmethod
    def setenumerationfieldindex(new_element):
        new_fields = list(new_element.iterfind(
            ".//xsd:restriction/xsd:enumeration", XSDNS))
        for new_field in new_fields:
            new_field.set('field_index', str(
                int(new_field.get('value'), base=16)))

    @staticmethod
    def setcomplexfieldindex(new_element):
        field_index = 1
        new_fields = list(new_element.iterfind(
            ".//xsd:sequence/xsd:element", XSDNS))
        for new_field in new_fields:
            new_field.set('field_index', str(field_index))
            field_index = field_index + 1

    def compare(self, new_file, orig_file):
        logger.info("compare (%s)<-(%s)", orig_file, new_file)
        if orig_file is None:
            logger.info("orig file not found, copy new file:(%s)", new_file)
            dst_file = shutil.copy(new_file, self.out_new_dir)
            CmdXsdAutoCompare.setfieldindex(dst_file)
            return

        dst_file = shutil.copy(orig_file, self.out_new_dir)
        create_tree = ElementTree.parse(dst_file)
        create_root = create_tree.getroot()
        new_dom_tree = ElementTree.parse(new_file)
        new_root = new_dom_tree.getroot()

        create_elements = list(
            create_root.iterfind(".//xsd:complexType", XSDNS))
        new_elements = list(new_root.iterfind(".//xsd:complexType", XSDNS))
        for new_element in new_elements:
            new_type = True
            for create_element in create_elements:
                if new_element.attrib['name'] == create_element.attrib['name']:
                    CmdXsdAutoCompare.merge(create_element, new_element)
                    new_type = False
                    break

            if new_type is True:
                CmdXsdAutoCompare.setcomplexfieldindex(new_element)
                create_root.append(new_element)

        create_elements = list(
            create_root.iterfind(".//xsd:simpleType", XSDNS))
        new_elements = list(new_root.iterfind(".//xsd:simpleType", XSDNS))
        for new_element in new_elements:
            new_type = True
            for create_element in create_elements:
                if new_element.attrib['name'] == create_element.attrib['name']:
                    CmdXsdAutoCompare.merge_enumeration(
                        create_element, new_element)
                    new_type = False
                    break

            if new_type is True:
                CmdXsdAutoCompare.setenumerationfieldindex(new_element)
                create_root.append(new_element)

        create_tree.write(dst_file, encoding='utf-8', xml_declaration=True)

    def run(self):
        new_to_orig_file = {}
        for filename in self.in_new_files:
            base_filename = os.path.basename(filename)
            new_to_orig_file[filename] = None
            for orig_filename in self.in_orig_files:
                if base_filename == os.path.basename(orig_filename):
                    new_to_orig_file[filename] = orig_filename
                    break

        logger.info(new_to_orig_file)
        for key, value in new_to_orig_file.items():
            self.compare(key, value)


cmddescription = 'Auto compare xsd file to auto merge xsd'


def makeoptions(optpartser):
    optpartser.add_argument(
        "--path",
        type=str,
        default='./xsd_his',
        help="specify a old xsd file/directory")


def run(options):
    logger.info("xsd_compare param:(input:%s),(output:%s),(his_xsd:%s)",
                options.input, options.output, options.path)
    cmd = CmdXsdAutoCompare(options.path, options.input, options.output)
    cmd.run()
