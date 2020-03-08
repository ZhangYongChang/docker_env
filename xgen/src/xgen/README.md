xGenc is used to generate proto and cpp file from yang model.

# 环境安装

## 配置环境变量

set PYTHONHOME=F:/yczhang/3.7.0/tool/win32
set path=%PYTHONHOME%;%PYTHONHOME%/Scripts;%path%

## 源码开发模式安装

python3 setup.py develop

## 源码生产环境安装(稳定版本生产环境使用)

python3 setup.py install

## 打包为whl文件使用pip安装(测试阶段生产环境建议使用)

python3 setup.py sdist bdist_wheel


# yymapping

  yang模型是一个树形的模型，xsd是一个扁平的模型，当yang转成xsd时必然面临名称冲突的问题，需要一系列使用扩展来解决名称冲突问题。

  NETCONF本身定义所有结点均可以带操作，但实际实现只有少量的结点可以操作，我们定义YANG扩展语句，标识出可以操作的结点，生成代码
过程中使用extension定义的新特性来实现对节点进行特殊处理。

yymapping语句|父语句|描述
expanddefault|module|定义模块的默认展开行为，包括: expand、noexpand
expand|container|展开container结点
noexpand|container不展开container结点
rename|leaf、container、list、type|结点重命名
nodeopr|leaf、container|结点可带操作
