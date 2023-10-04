#!/bin/bash

# Copy custom CA certificates to system trusted CA certificates folder
# and run CA update utility

if [[ -d /var/lib/config-data/ca-certificates ]] && \
        [[ ! -z "$(ls -A /var/lib/config-data/ca-certificates/)" ]]; then
    # CentOS
    for cert in /var/lib/config-data/ca-certificates/*; do
        file=$(basename "$cert")
        cp $cert "/etc/pki/ca-trust/source/anchors/ospk8s-customca-$file"
    done
    update-ca-trust
fi
