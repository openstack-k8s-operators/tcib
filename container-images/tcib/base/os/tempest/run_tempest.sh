#!/bin/sh

HOMEDIR=/var/lib/tempest
TEMPEST_DIR=$HOMEDIR/openshift

pushd $HOMEDIR

export OS_CLOUD=default

TEMPEST_PATH=$HOMEDIR/
if [ ! -z ${USE_EXTERNAL_FILES} ]; then
    TEMPEST_PATH=$HOMEDIR/external_files/
    mkdir -p $HOME/.config/openstack
    cp ${TEMPEST_PATH}clouds.yaml $HOME/.config/openstack/clouds.yaml
fi

tempest init openshift

pushd $TEMPEST_DIR

discover-tempest-config --os-cloud $OS_CLOUD --debug --create identity.v3_endpoint_type public

if [ ! -f ${TEMPEST_PATH}include.txt ]; then
    echo "tempest.api.identity.v3" > ${TEMPEST_PATH}include.txt
fi
if [ ! -f ${TEMPEST_PATH}exclude.txt ]; then
    touch ${TEMPEST_PATH}exclude.txt
fi

tempest run \
    --include-list ${TEMPEST_PATH}include.txt \
    --exclude-list ${TEMPEST_PATH}exclude.txt

RETURN_VALUE=$?

echo "Generate subunit"
stestr last --subunit > ${TEMPEST_PATH}testrepository.subunit || true

echo "Generate html result"
subunit2html ${TEMPEST_PATH}testrepository.subunit ${TEMPEST_PATH}stestr_results.html || true

echo Copying logs file
cp -rf ${TEMPEST_DIR}/* ${TEMPEST_PATH}

exit ${RETURN_VALUE}

popd
popd
