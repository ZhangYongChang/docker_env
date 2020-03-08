FROM yczhang88/pyang:1.0.0

WORKDIR /build

ADD protobuf-2.4.1.tar.gz /build

RUN cd protobuf-2.4.1 && ./configure --prefix=/usr && make && make install