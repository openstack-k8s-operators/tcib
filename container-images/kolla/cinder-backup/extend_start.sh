#!/bin/bash

if [[ $(stat -c %U:%G /var/lib/cinder) != "cinder:cinder" ]]; then
    sudo chown -R cinder:cinder /var/lib/cinder
fi
