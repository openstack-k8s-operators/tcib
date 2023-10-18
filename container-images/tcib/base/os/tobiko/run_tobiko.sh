#!/bin/sh

TOBIKO_DIR=/var/lib/tobiko

if [ ! -z ${USE_EXTERNAL_FILES} ]; then
    mkdir -p $TOBIKO_DIR/.config/openstack
    cp $TOBIKO_DIR/external_files/clouds.yaml $HOME/.config/openstack/
fi

pushd ${TOBIKO_DIR}

export OS_CLOUD=default

if [ ! -z ${TOBIKO_UBUNTU_MINIMAL_IMAGE_URL} ]; then
    mkdir -p .downloaded-images
    curl ${TOBIKO_UBUNTU_MINIMAL_IMAGE_URL} -o .downloaded-images/ubuntu-minimal
fi

git clone https://opendev.org/x/tobiko

pushd tobiko
echo '
[DEFAULT]
debug = true
log_file = tobiko.log

[ubuntu]
interface_name = enp3s0
image_file = /var/lib/tobiko/.downloaded-images/ubuntu-minimal

[keystone]
interface = public' > tobiko.conf

if [ ! -z ${TOBIKO_VERSION} ]; then
    git checkout ${TOBIKO_VERSION}
fi
python3 -m tox -e py3 --notest
python3 -m tox -e scenario
RETURN_VALUE=$?

echo "Copying logs file"
cp -rf /var/lib/tobiko/tobiko/.tox/py3/log $TOBIKO_DIR


exit ${RETURN_VALUE}
