#!/bin/sh

TOBIKO_DIR=/var/lib/tobiko

if [ ! -z ${USE_EXTERNAL_FILES} ]; then
    mkdir -p $TOBIKO_DIR/.config/openstack
    cp $TOBIKO_DIR/external_files/clouds.yaml $HOME/.config/openstack/
fi

pushd ${TOBIKO_DIR}

export OS_CLOUD=default
echo "export OS_CLOUD=default" > .bashrc

mkdir -p .downloaded-images
curl https://cloud-images.ubuntu.com/minimal/releases/jammy/release/ubuntu-22.04-minimal-cloudimg-amd64.img -o .downloaded-images/ubuntu-minimal

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

python3 -m tox -e py3 --notest
sleep 9999999
python3 -m tox -e scenario

RETURN_VALUE=$?

echo Copying logs file
# Take care of test results

exit ${RETURN_VALUE}

popd
