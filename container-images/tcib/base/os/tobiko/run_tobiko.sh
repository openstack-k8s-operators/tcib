#!/bin/sh

TOBIKO_DIR=/var/lib/tobiko

pushd ${TOBIKO_DIR}

export OS_CLOUD=default
echo "export OS_CLOUD=default" > .bashrc

pushd tobiko
python3 -m tox -e py3 --notest
sleep 9999999
python3 -m tox -e scenario

RETURN_VALUE=$?

echo Copying logs file
# Take care of test results

exit ${RETURN_VALUE}

popd
