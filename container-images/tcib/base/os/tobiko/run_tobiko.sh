#!/bin/sh

TOBIKO_DIR=/var/lib/tobiko

pushd ${TOBIKO_DIR}

python3 -m tox -e py3 --notest
source .tox/py3/bin/activate
python3 -m stestr run -n tobiko/tobiko/tests/scenario/octavia/test_traffic.py

RETURN_VALUE=$?

echo Copying logs file
# Take care of test results

exit ${RETURN_VALUE}

popd
