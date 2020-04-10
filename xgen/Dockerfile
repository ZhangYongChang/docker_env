FROM python:3.7

WORKDIR /build

ADD protobuf-2.4.1.tar.gz /build

RUN cd protobuf-2.4.1 && ./configure --prefix=/usr && make && make install && cd .. && rm -rf protobuf-2.4.1

ADD dist/xgen-0.1.1-py3-none-any.whl /build

RUN pip3 install xgen-0.1.1-py3-none-any.whl && rm xgen-0.1.1-py3-none-any.whl

WORKDIR /workspace
RUN rm -rf /build

ADD xgenc.py /workspace
ADD linux-config.json /workspace
ADD yang/turing-machine.yang /workspace/yang/