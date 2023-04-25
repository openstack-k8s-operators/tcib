#!/bin/sh

HOMEDIR=/var/lib/tempest
TEMPEST_DIR=$HOMEDIR/openshift

pushd $HOMEDIR

export OS_CLOUD=default

TEMPEST_LIST=$HOMEDIR/
if [ ! -z ${USE_EXTERNAL_FILES} ]; then
    TEMPEST_LIST=$HOMEDIR/external_files/
    mkdir -p $HOME/.config/openstack
    cp ${TEMPEST_LIST}clouds.yaml $HOME/.config/openstack/clouds.yaml
fi

tempest init openshift

pushd $TEMPEST_DIR

discover-tempest-config --os-cloud $OS_CLOUD --debug --create identity.v3_endpoint_type public

if [ -f ${TEMPEST_LIST}include.txt ]; then
    echo "tempest.api.identity.v3" > ${TEMPEST_LIST}include.txt
fi
if [ -f ${TEMPEST_LIST}/exclude.txt ]; then
    touch ${TEMPEST_LIST}exclude.txt
fi

tempest run \
    --include-list ${TEMPEST_LIST}include.txt \
    --exclude-list ${TEMPEST_LIST}exclude.txt

RETURN_VALUE=$?

echo "Generate subunit"
stestr last --subunit > ${TEMPEST_LIST}testrepository.subunit || true

echo "Generate html result"
subunit2html ${TEMPEST_LIST}testrepository.subunit ${TEMPEST_LIST}/stestr_results.html || true

echo Copying logs file
cp -rf ${TEMPEST_DIR}/* ${TEMPEST_LIST}

exit ${RETURN_VALUE}

popd
popd
