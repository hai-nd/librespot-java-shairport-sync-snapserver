# librespot-java-shairport-sync-snapserver

Alpine based Docker image for running the [snapserver part of snapcast](https://github.com/badaix/snapcast) with
[librespot-java](https://github.com/librespot-org/librespot-java) and [shairport-sync](https://github.com/mikebrady/shairport-sync) as input.

Idea adapted from [librespot-shairport-snapserver](https://github.com/yubiuser/librespot-shairport-snapserver) and based on [shairport-sync docker image](https://github.com/mikebrady/shairport-sync/tree/master/docker)

 **Background:** When this project started, the last releases of *librespot-api* is 1.6.4 not work.
  I have to build my own librespot-api version 1.6.3 and put it in the project folder.

 **Note** The coresponding Docker image for runinng `snapclient` can be found here: [https://github.com/yubiuser/snapclient-docker](https://github.com/yubiuser/snapclient-docker)

## Getting started

Images for `amd64` can be found at [ghcr.io/yubiuser/librespot-shairport-snapserver](ghcr.io/yubiuser/librespot-shairport-snapserver).

Use with

```plain
docker pull haingo65/librespot-java-shairport-sync-snapserver
docker run -d \
--name snapserver \
--net host \
--device /dev/snd \
-v ./snapserver/config:/config \
-v ./snapserver/plug-ins:/etc/plug-ins \
--mount type=bind,source="$(pwd)"/tmp,target=/tmp \
haingo65/librespot-java-shairport-sync-snapserver:latest
```

or with `docker-compose.yml`

```yml
services:
  snapcast:
    image: haingo65/librespot-java-shairport-sync-snapserver
    container_name: snapserver
    restart: unless-stopped
    network_mode: host
    volumes:
     - ./snapserver/config:/config
     - ./snapserver/plug-ins:/etc/plug-ins 
     - "$(pwd)"/tmp:/tmp
```

### Build locally

To build the image run it in termial:

`docker build -t librespot-java-shairport-sync-snapserver:local -f alpine.dockerfile .`

## Notes

- Based on Alpine 3:20; final image size is ~478.1 MB
- All `(c)make` calles use the option `-j $(( $(nproc) -1 ))` to leave one CPU for normal operation
- `s6-overlay` is used as `init` system (same as the [shairport-sync docker image](https://github.com/mikebrady/shairport-sync/tree/master/docker)). This is necessary, because *shairport-sync* needs a companion application called [NQPTP](https://github.com/mikebrady/nqptp) which needs to be started from `root` to run as deamon.
  - `s6-rc` with configured dependencies is used to start all services. `snapserver` should start as last
  - `s6-notifyoncheck` is used to check readiness of the started services `dbus` and `avahi`. The actual check is performed by sending `dbus`messages and analyzing the reply.
- Adjust `snapserver.conf` as required (Airplay 2 needs port 7000)
- [Snapweb](https://github.com/badaix/snapweb) is inclued in the image and can be accessed on `http://<snapserver host>:1780`
- Only work in Linux, it does not support Windows or Mac OSX because mDNS can not work from docker desktop to LAN local network.
