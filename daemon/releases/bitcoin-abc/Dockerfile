FROM ubuntu:24.04
ARG RELEASE_ARCHIVE
COPY ${RELEASE_ARCHIVE} /tmp/release.tar.gz
RUN apt-get update && apt-get install -y --no-install-recommends libevent-2.1-7t64 libevent-pthreads-2.1-7t64 libdb5.3++t64 libsqlite3-0 libstdc++6 libnng1 libboost-filesystem1.83.0 libboost-thread1.83.0 && rm -rf /var/lib/apt/lists/* && tar xzf /tmp/release.tar.gz -C /usr/local --strip-components=1 && rm /tmp/release.tar.gz
RUN useradd -rm node && mkdir /data && chown node:node /data
USER node
VOLUME /data
ENTRYPOINT ["bitcoind", "-datadir=/data"]
