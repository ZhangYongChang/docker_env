FROM ubuntu:18.04

ADD sources.list /etc/apt/

RUN apt-get update && apt-get install -y vim xsltproc jing python3 python3-pip

RUN pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple pyang==1.7.3
