# 简介

xGenc is used to generate proto and cpp file from yang model.
generated cpp file can used convert pb message to xml and convert xml to pb message.

# 环境安装

## 配置环境变量

set PYTHONHOME=F:/yczhang/3.7.0/tool/win32
set path=%PYTHONHOME%;%PYTHONHOME%/Scripts;%path%

## 源码生产环境安装(稳定版本生产环境使用)

python3 setup.py install

## 打包为whl文件(生产环境建议使用pip安装)

python3 setup.py sdist bdist_wheel


# yymapping

yang模型是一个树形的模型，xsd是一个扁平的模型，当yang转成xsd时必然面临名称冲突的问题，需要一系列使用扩展来解决名称冲突问题。

NETCONF本身定义所有结点均可以带操作，但实际实现只有少量的结点可以操作，定义YANG扩展语句，标识出可以操作的结点，生成代码过程中使用extension定义的新特性来实现对节点进行特殊理。

yymapping语句 |  父语句                   |描述
-----------------------|-------------------------------------------|------------------------------------------
expanddefault |module                                         |定义模块的默认展开行为，包括: expand、noexpand
expand               |container                                      |展开container结点
noexpand          |container                                      |不展开container结点
rename               |leaf、container、list、type   |结点重命名
nodeopr             |leaf、container                           |结点可带操作


# Example

## 配置

根据实际需求配置下述文件：

例如：config.json

```json
[
  {
    "input": "yang",
    "output": "xsd_tmp",
    "logfile": "xgen.log",
    "loglevel": "INFO",
    "command": "ypk_xsd",
    "path": [],
    "with_warning": false,
    "exception_on_duplicate": false
  },
  {
    "input": "xsd_tmp",
    "output": "yxsd",
    "logfile": "xgen.log",
    "loglevel": "INFO",
    "command": "xsdcompare",
    "path": "xsd_his"
  },
  {
    "input": "yxsd",
    "output": "PBProto",
    "logfile": "xgen.log",
    "loglevel": "INFO",
    "command": "ypk_proto",
    "bundle": "Fos"
  },
  {
    "input": "yxsd",
    "output": "unmyangpbkit",
    "logfile": "xgen.log",
    "loglevel": "INFO",
    "command": "ypk_cpp",
    "bundle": "Fos"
  },
  {
    "input": "PBProto",
    "output": "PBSrc",
    "logfile": "xgen.log",
    "loglevel": "INFO",
    "command": "protoc",
    "protoc": "protoc.exe",
    "path": [
      "PBProto",
      "d:/.conan/data/protobuf/2.4.1/ext/stable/package/6afee21f36d6e1e46b8c7d7a75dd643322a02372/include",
      "d:/.conan/data/protobuf/2.4.1/ext/stable/package/6afee21f36d6e1e46b8c7d7a75dd643322a02372/proto"
    ],
    "format": "cpp",
    "excludefile": []
  }
]
```

子命令protoc根据所在的平台不一样，请合理的配置path和protoc。

注意"protoc": "protoc.exe"是相关的protoc程序文件名

需要指定第三方库proto的头文件和相关proto路径

## 产生骨架代码

python3 xgenc.py config.json
