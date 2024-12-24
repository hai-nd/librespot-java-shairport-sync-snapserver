#!/bin/bash

cd "$(dirname "$0")"
java -jar /usr/local/bin/librespot-api-1.6.3.jar --player.output="MIXER" --player.enableNormalisation=false --player.preferredAudioQuality="VERY_HIGH"