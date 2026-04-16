#!/bin/sh

set -ex

# Create temporary working directory
WORKDIR=$(mktemp -d)
cd ${WORKDIR}

# Create target directory structure
TARGET_DIR="/usr/share/ironic-operator/var-lib-ironic"
mkdir -p ${TARGET_DIR}/httpboot
mkdir -p ${TARGET_DIR}/tftpboot/pxelinux.cfg

# Download boot asset packages (without installing)
# For x86_64 architecture only
dnf download ipxe-bootimgs grub2-efi-x64 shim-x64

# Extract files from RPMs
for rpm in *.rpm; do
    rpm2cpio ${rpm} | cpio -idmv
done

# Check for expected EFI directories
if [ -d "${WORKDIR}/boot/efi/EFI/centos" ]; then
    efi_dir=centos
elif [ -d "${WORKDIR}/boot/efi/EFI/redhat" ]; then
    efi_dir=redhat
else
    echo "No EFI directory detected"
    exit 1
fi

# Copy iPXE and grub files to both httpboot and tftpboot
for dir in httpboot tftpboot; do
    # iPXE files
    cp ${WORKDIR}/usr/share/ipxe/ipxe-snponly-x86_64.efi ${TARGET_DIR}/${dir}/snponly.efi
    cp ${WORKDIR}/usr/share/ipxe/undionly.kpxe ${TARGET_DIR}/${dir}/undionly.kpxe

    # ipxe.lkrn is not packaged in RHEL 10, copy if it exists
    if [ -f "${WORKDIR}/usr/share/ipxe/ipxe.lkrn" ]; then
        cp ${WORKDIR}/usr/share/ipxe/ipxe.lkrn ${TARGET_DIR}/${dir}/ipxe.lkrn
    fi

    # UEFI boot files (shim and grub)
    cp ${WORKDIR}/boot/efi/EFI/${efi_dir}/shimx64.efi ${TARGET_DIR}/${dir}/bootx64.efi
    cp ${WORKDIR}/boot/efi/EFI/${efi_dir}/grubx64.efi ${TARGET_DIR}/${dir}/grubx64.efi
done

# Ensure all files are readable
chmod -R +r ${TARGET_DIR}

# Build an ESP image
# Uses existing script recipe from ironic-operator pxe-init.sh
pushd ${TARGET_DIR}/httpboot
dd if=/dev/zero of=esp.img bs=4096 count=2048
mkfs.msdos -F 12 -n 'ESP_IMAGE' esp.img

mmd -i esp.img EFI
mmd -i esp.img EFI/BOOT
mcopy -i esp.img -v bootx64.efi ::EFI/BOOT
mcopy -i esp.img -v grubx64.efi ::EFI/BOOT
mdir -i esp.img ::EFI/BOOT
popd

echo "ESP image created successfully at ${TARGET_DIR}/httpboot/esp.img"

# Clean up
cd /
rm -rf ${WORKDIR}

echo "Boot assets extracted successfully to ${TARGET_DIR}"
