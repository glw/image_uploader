FROM alpine:edge

MAINTAINER glw <https://github.com/glw/image_uploader>

ENV GDAL_VERSION="2.3.1"

WORKDIR $ROOTDIR/

RUN apk add build-base gdal=${GDAL_VERSION}-r0 gdal-dev python2 python2-dev py2-pip --update-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
        && rm -rf /tmp/* \
        && rm -rf /var/cache/apk/* \
        && pip install \
           numpy \
	       GDAL==${GDAL_VERSION}

# Externally accessible data is by default put in /data
WORKDIR /data
