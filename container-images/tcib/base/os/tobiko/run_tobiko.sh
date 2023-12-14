#!/bin/sh

TOBIKO_DIR=/var/lib/tobiko

# obtain clouds.yaml from external_files directory
if [ ! -z ${USE_EXTERNAL_FILES} ]; then
    mkdir -p $TOBIKO_DIR/.config/openstack
    cp $TOBIKO_DIR/external_files/clouds.yaml $HOME/.config/openstack/
fi

# download Ubuntu minimal image used by the Tobiko scenario tests, if needed
if [ ! -z ${TOBIKO_UBUNTU_MINIMAL_IMAGE_URL} ]; then
    mkdir -p ${TOBIKO_DIR}/.downloaded-images
    curl ${TOBIKO_UBUNTU_MINIMAL_IMAGE_URL} -o ${TOBIKO_DIR}/.downloaded-images/ubuntu-minimal
fi


# set default values for the required variables
TOBIKO_VERSION=${TOBIKO_VERSION:-master}
TOBIKO_UBUNTU_INTERFACE_NAME=${TOBIKO_UBUNTU_INTERFACE_NAME:-enp3s0}
TOBIKO_KEYSTONE_INTERFACE=${TOBIKO_KEYSTONE_INTERFACE:-public}
TOBIKO_LOGFILE=${TOBIKO_LOGFILE:-tobiko.log}
TOBIKO_TESTCASE_TIMEOUT="${TOBIKO_TESTCASE_TIMEOUT:-1800.0}"
TOBIKO_TESTRUNNER_TIMEOUT="${TOBIKO_TESTRUNNER_TIMEOUT:-14400.0}"

# export OS_CLOUD variable
[ ! -z ${TOBIKO_OS_CLOUD} ] && export OS_CLOUD=${TOBIKO_OS_CLOUD} || export OS_CLOUD=default

# export optional variables, relevant for tox and pytest execution (see tobiko tox.ini file)
[ ! -z ${TOBIKO_PYTEST_ADDOPTS} ] && export PYTEST_ADDOPTS=${TOBIKO_PYTEST_ADDOPTS}
[ ! -z ${TOBIKO_REPORT_DIR} ] && export TOX_REPORT_DIR=${TOBIKO_REPORT_DIR}
[ ! -z ${TOBIKO_RUN_TESTS_TIMEOUT} ] && export TOX_RUN_TESTS_TIMEOUT=${TOBIKO_RUN_TESTS_TIMEOUT}

# assert mandatory variables have been set
[ -z ${TOBIKO_TESTENV} ] && echo "TOBIKO_TESTENV not set" && exit 1

pushd ${TOBIKO_DIR}
git clone https://opendev.org/x/tobiko
pushd tobiko
git checkout ${TOBIKO_VERSION}

# generate tobiko.conf
# DEFAULT
crudini --set tobiko.conf DEFAULT log_file ${TOBIKO_LOGFILE}
[ ! -z ${TOBIKO_REPORT_DIR} ] && crudini --set tobiko.conf DEFAULT log_dir ${TOBIKO_REPORT_DIR}
[ ! -z ${TOBIKO_DEBUG} ] && crudini --set tobiko.conf DEFAULT debug true
# testcase
crudini --set tobiko.conf testcase timeout ${TOBIKO_TESTCASE_TIMEOUT}
crudini --set tobiko.conf testcase timeout ${TOBIKO_TESTRUNNER_TIMEOUT}
# ubuntu
crudini --set tobiko.conf ubuntu interface_name ${TOBIKO_UBUNTU_INTERFACE_NAME}
[ ! -z ${TOBIKO_UBUNTU_MINIMAL_IMAGE_URL} ] && crudini --set tobiko.conf ubuntu image_file ${TOBIKO_DIR}/.downloaded-images/ubuntu-minimal
# keystone
crudini --set tobiko.conf keystone interface ${TOBIKO_KEYSTONE_INTERFACE}
[ ! -z ${TOBIKO_MANILA_SHARE_PROTOCOL} ] && crudini --set tobiko.conf manila share_protocol ${TOBIKO_MANILA_SHARE_PROTOCOL}

# run tobiko tests
python3 -m tox -e ${TOBIKO_TESTENV}
RETURN_VALUE=$?

# copy logs to external_files
if [ ! -z ${USE_EXTERNAL_FILES} ]; then
    echo "Copying logs file"
    LOG_DIR=${TOX_REPORT_DIR:-/var/lib/tobiko/tobiko/.tox/py3/log}
    cp -rf ${LOG_DIR} ${TOBIKO_DIR}/external_files/
    cp tobiko.conf ${TOBIKO_DIR}/external_files/
fi

exit ${RETURN_VALUE}
