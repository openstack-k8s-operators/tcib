#!/bin/sh
# run_rally.sh
# ==============
#
# This script is executed inside the rally containers defined in the tcib
# repository. The main purpose of this script is executing the rally command
# with correct arguments. The execution of the script can be influenced by
# setting values for environment variables which match the RALLY_* regex.
#
#
# RALLY_* environment variables
# -----------------------------

set -x

HOMEDIR=/var/lib/rally
RALLY_PATH=$HOMEDIR/
RALLY_DIR=$HOMEDIR/openshift


export OS_CLOUD=default

if [ -e ${RALLY_PATH}clouds.yaml ]; then
    mkdir -p $HOME/.config/openstack
    cp ${RALLY_PATH}clouds.yaml $HOME/.config/openstack/clouds.yaml
fi

# at this point, we have everything ready in the container for users to make it
# a sleepy container and jump to it so that they can run their rally commands

# rally deployment check
