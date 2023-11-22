#!/bin/sh
set -x

HOMEDIR=/var/lib/tempest
TEMPEST_DIR=$HOMEDIR/openshift
PROFILE_ARG=""
CONCURRENCY="${CONCURRENCY:-}"

TEMPESTCONF_ARGS=""

[[ ${TEMPESTCONF_CREATE:=true} == true ]] && TEMPESTCONF_ARGS+="--create "
[[ ${TEMPESTCONF_INSECURE} == true ]] && TEMPESTCONF_ARGS+="--insecure "
[[ ${TEMPESTCONF_COLLECT_TIMING} == true ]] && TEMPESTCONF_ARGS+="--collect-timing "
[[ ${TEMPESTCONF_NO_DEFAULT_DEPLOYER} == true ]] && TEMPESTCONF_ARGS+="--no-default-deployer "
[[ ${TEMPESTCONF_DEBUG:=true} == true ]] && TEMPESTCONF_ARGS+="--debug "
[[ ${TEMPESTCONF_VERBOSE} == true ]] && TEMPESTCONF_ARGS+="--verbose "
[[ ${TEMPESTCONF_NO_RNG} == true ]] && TEMPESTCONF_ARGS+="--no-rng "
[[ ${TEMPESTCONF_NON_ADMIN} == true ]] && TEMPESTCONF_ARGS+="--non-admin "
[[ ${TEMPESTCONF_RETRY_IMAGE} == true ]] && TEMPESTCONF_ARGS+="--retry-image "
[[ ${TEMPESTCONF_CONVERT_TO_RAW} == true ]] && TEMPESTCONF_ARGS+="--convert-to-raw "

[[ ! -z ${TEMPESTCONF_TIMEOUT} ]] && TEMPESTCONF_ARGS+="--timeout ${TEMPESTCONF_TIMEOUT} "
[[ ! -z ${TEMPESTCONF_OUT} ]] && TEMPESTCONF_ARGS+="--out ${TEMPESTCONF_OUT} "
[[ ! -z ${TEMPESTCONF_DEPLOYER_INPUT} ]] && TEMPESTCONF_ARGS+="--deployer-input ${TEMPESTCONF_DEPLOYER_INPUT} "
[[ ! -z ${TEMPESTCONF_TEST_ACCOUNTS} ]] && TEMPESTCONF_ARGS+="--test-accounts ${TEMPESTCONF_TEST_ACCOUNTS} "
[[ ! -z ${TEMPESTCONF_CREATE_ACCOUNTS_FILE} ]] && TEMPESTCONF_ARGS+="--create-accounts-file ${TEMPESTCONF_CREATE_ACCOUNTS_FILE} "
[[ ! -z ${TEMPESTCONF_PROFILE} ]] && TEMPESTCONF_ARGS+="--profile ${TEMPESTCONF_PROFILE} "
[[ ! -z ${TEMPESTCONF_GENERATE_PROFILE} ]] && TEMPESTCONF_ARGS+="--generate-profile ${TEMPESTCONF_GENERATE_PROFILE} "
[[ ! -z ${TEMPESTCONF_IMAGE_DISK_FORMAT} ]] && TEMPESTCONF_ARGS+="--image-disk-format ${TEMPESTCONF_IMAGE_DISK_FORMAT} "
[[ ! -z ${TEMPESTCONF_IMAGE} ]] && TEMPESTCONF_ARGS+="--image ${TEMPESTCONF_IMAGE} "
[[ ! -z ${TEMPESTCONF_FLAVOR_MIN_MEM} ]] && TEMPESTCONF_ARGS+="--flavor-min-mem ${TEMPESTCONF_FLAVOR_MIN_MEM} "
[[ ! -z ${TEMPESTCONF_FLAVOR_MIN_DISK} ]] && TEMPESTCONF_ARGS+="--flavor-min-disk ${TEMPESTCONF_FLAVOR_MIN_DISK} "
[[ ! -z ${TEMPESTCONF_NETWORK_ID} ]] && TEMPESTCONF_ARGS+="--network-id ${TEMPESTCONF_NETWORK_ID} "

if [[ ! -z ${TEMPESTCONF_APPEND} ]]; then
    while IFS= read -r line; do
        TEMPESTCONF_ARGS+="--append $line "
    done <<< "$TEMPESTCONF_APPEND"
fi

if [[ ! -z ${TEMPESTCONF_REMOVE} ]]; then
    while IFS= read -r line; do
        TEMPESTCONF_ARGS+="--remove $line "
    done <<< "$TEMPESTCONF_REMOVE"
fi

TEMPESTCONF_OVERRIDES="$(echo ${TEMPESTCONF_OVERRIDES} | tr '\n' ' ') identity.v3_endpoint_type public"

pushd $HOMEDIR

export OS_CLOUD=default

TEMPEST_PATH=$HOMEDIR/
if [ ! -z ${USE_EXTERNAL_FILES} ]; then
    TEMPEST_PATH=$HOMEDIR/external_files/
    mkdir -p $HOME/.config/openstack
    cp ${TEMPEST_PATH}clouds.yaml $HOME/.config/openstack/clouds.yaml
fi

if [ -f ${TEMPEST_PATH}profile.yaml ] && [ -z ${TEMPESTCONF_PROFILE} ]; then
    TEMPESTCONF_ARGS+="--profile ${TEMPEST_PATH}profile.yaml "
fi

tempest init openshift

pushd $TEMPEST_DIR
discover-tempest-config ${TEMPESTCONF_ARGS} ${TEMPESTCONF_OVERRIDES}

if [ ! -f ${TEMPEST_PATH}include.txt ]; then
    echo "tempest.api.identity.v3" > ${TEMPEST_PATH}include.txt
fi
if [ ! -f ${TEMPEST_PATH}exclude.txt ]; then
    touch ${TEMPEST_PATH}exclude.txt
fi

if [ -n "$CONCURRENCY" ]; then
    CONCURRENCY_ARGS="--concurrency ${CONCURRENCY}"
fi

tempest run ${CONCURRENCY_ARGS:-} \
    --include-list ${TEMPEST_PATH}include.txt \
    --exclude-list ${TEMPEST_PATH}exclude.txt

RETURN_VALUE=$?

echo "Generate subunit"
stestr last --subunit > ${TEMPEST_PATH}testrepository.subunit || true

echo "Generate subunit xml file"
subunit2junitxml ${TEMPEST_PATH}testrepository.subunit > ${TEMPEST_PATH}tempest_results.xml || true

echo "Generate html result"
subunit2html ${TEMPEST_PATH}testrepository.subunit ${TEMPEST_PATH}stestr_results.html || true

echo Copying logs file
cp -rf ${TEMPEST_DIR}/* ${TEMPEST_PATH}

exit ${RETURN_VALUE}

popd
popd
