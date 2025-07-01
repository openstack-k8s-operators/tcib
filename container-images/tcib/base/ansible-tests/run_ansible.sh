#!/bin/bash

set -euo pipefail

ANSIBLE_DIR="/var/lib/ansible/ansible/"
ANSIBLE_FILE_EXTRA_VARS_PARAM="${ANSIBLE_FILE_EXTRA_VARS_PARAM:-}"
POD_ANSIBLE_PLAYBOOK="${POD_ANSIBLE_PLAYBOOK:-}"
POD_ANSIBLE_EXTRA_VARS="${POD_ANSIBLE_EXTRA_VARS:-}"
POD_ANSIBLE_GIT_REPO="${POD_ANSIBLE_GIT_REPO:-}"

# Check and set ansible debug verbosity
ANSIBLE_DEBUG=""
if [[ ${POD_DEBUG:-true} == true ]]; then
    ANSIBLE_DEBUG="-vvvv"
fi

# Clone the Ansible repository
#git clone "$POD_ANSIBLE_GIT_REPO" "$ANSIBLE_DIR"
# This should be passed in via the appropriate vars
git clone -b "efoley/run_fvt_in_test_operator" "http://github.com/infrawatch/feature-verification-tests" "$ANSIBLE_DIR"/feature-verification-tests
ls "$ANSIBLE_DIR"

# Handle extra vars file if provided
if [[ -n "${POD_ANSIBLE_FILE_EXTRA_VARS:-}" ]]; then
    echo "$POD_ANSIBLE_FILE_EXTRA_VARS" > "$ANSIBLE_DIR/extra_vars.yaml"
    ANSIBLE_FILE_EXTRA_VARS_PARAM="-e @$ANSIBLE_DIR/extra_vars.yaml"
fi

# Handle inventory file if provided
if [[ -n "${POD_ANSIBLE_INVENTORY:-}" ]]; then
    echo "$POD_ANSIBLE_INVENTORY" > "$ANSIBLE_DIR/inventory"
fi

# Install collections if specified
if [[ -n "${POD_INSTALL_COLLECTIONS:-}" ]]; then
    ansible-galaxy collection install "$POD_INSTALL_COLLECTIONS"
fi

# Install collections from requirements.yaml if the file exists
if [[ -f "$ANSIBLE_DIR/requirements.yaml" ]]; then
    ansible-galaxy install -r "$ANSIBLE_DIR/requirements.yaml"
else
    echo "requirements.yaml doesn't exist, skipping requirements installation"
fi

# Can I add a special config file here? Or arbitrary config vars?
# Q: Can I pass a config file by path?
# Navigate to ansible directory and run playbook
# ANSIBLE_CONFIG can be passed
# This is only needed if I cannot specify which directory to execute from
# IF the ansible runner is always using custom_junit plugin, then having a test-class var passed in will do no harm.
# The ansible.config would just need to change the classname.
# OR we might need to look into passing a config file content into the runner.
cd "$ANSIBLE_DIR"
export ANSIBLE_CONFIG="$ANSIBLE_DIR/feature-verification-tests/ci/ansible.cfg"
# this should be passed in with the appropriate vars.
ls $ANSIBLE_DIR
export POD_ANSIBLE_PLAYBOOK=$ANSIBLE_DIR/feature-verification-tests/ci/run_verify_metrics_osp18.yml
ansible-playbook "$POD_ANSIBLE_PLAYBOOK" $ANSIBLE_DEBUG -i $ANSIBLE_DIR/inventory $POD_ANSIBLE_EXTRA_VARS $ANSIBLE_FILE_EXTRA_VARS_PARAM
# anything that is run by FVT is always going to pass, since it relies on report_results to run afterwards, so I will need to add a new playbook to do the tests and the reporting.
# Currently, the report-results has to be separate since the custom junit plugin will only create the XML files once the playbook is completed.
# After FVT tests are run, there still needs to be a separate hook to check the results (including fetching the results from the pod)
#  or else there needs to be some mechanism here to check the results.
# the testoperator expects results files to be in /var/lib/AnsibleTests/external_files/ and this will get copied to cifmw-data/logs
# So the sequence here should be: configure the FVTs to use /var/lib/AnsibleTests/external_files/ as the output dir
# Run the playbook
# run report_results to make the pod fail
cp ~/.ansible.log/ /var/lib/AnsibleTests/external_files/
