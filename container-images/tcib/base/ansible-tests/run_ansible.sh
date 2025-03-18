#!/bin/bash

set -euo pipefail

ANSIBLE_DIR="/var/lib/ansible/ansible"
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
git clone "$POD_ANSIBLE_GIT_REPO" "$ANSIBLE_DIR"

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

# Navigate to ansible directory and run playbook
cd "$ANSIBLE_DIR"
ansible-playbook "$POD_ANSIBLE_PLAYBOOK" $ANSIBLE_DEBUG -i $ANSIBLE_DIR/inventory $POD_ANSIBLE_EXTRA_VARS $ANSIBLE_FILE_EXTRA_VARS_PARAM
