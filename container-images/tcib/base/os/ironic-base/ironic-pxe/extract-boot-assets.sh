#!/bin/sh

set -ex

# Create temporary working directory
WORKDIR=$(mktemp -d)
cd ${WORKDIR}

# Create target directory structure with arch-specific subdirectories
TARGET_DIR="/usr/share/ironic-operator/var-lib-ironic"
mkdir -p ${TARGET_DIR}/httpboot/x86_64
mkdir -p ${TARGET_DIR}/httpboot/aarch64
mkdir -p ${TARGET_DIR}/tftpboot/x86_64
mkdir -p ${TARGET_DIR}/tftpboot/aarch64
mkdir -p ${TARGET_DIR}/tftpboot/pxelinux.cfg

# Download boot asset packages for x86_64
mkdir -p ${WORKDIR}/x86_64
cd ${WORKDIR}/x86_64
dnf download ipxe-bootimgs-x86 grub2-efi-x64 shim-x64

# Extract x86_64 RPMs
for rpm in *.rpm; do
    rpm2cpio ${rpm} | cpio -idmv
done

# Check for expected EFI directories
if [ -d "${WORKDIR}/x86_64/boot/efi/EFI/centos" ]; then
    efi_dir_x86=centos
elif [ -d "${WORKDIR}/x86_64/boot/efi/EFI/redhat" ]; then
    efi_dir_x86=redhat
else
    echo "No x86_64 EFI directory detected"
    exit 1
fi

# Download boot asset packages for aarch64
mkdir -p ${WORKDIR}/aarch64
cd ${WORKDIR}/aarch64
dnf download --forcearch=aarch64 ipxe-bootimgs-aarch64 grub2-efi-aa64 shim-aa64

# Extract aarch64 RPMs
for rpm in *.rpm; do
    rpm2cpio ${rpm} | cpio -idmv
done

# Check for expected EFI directories for aarch64
if [ -d "${WORKDIR}/aarch64/boot/efi/EFI/centos" ]; then
    efi_dir_aa64=centos
elif [ -d "${WORKDIR}/aarch64/boot/efi/EFI/redhat" ]; then
    efi_dir_aa64=redhat
else
    echo "No aarch64 EFI directory detected"
    exit 1
fi

# Copy x86_64 iPXE and grub files to arch-specific directories
for dir in httpboot tftpboot; do
    # x86_64 iPXE files
    cp ${WORKDIR}/x86_64/usr/share/ipxe/ipxe-snponly-x86_64.efi ${TARGET_DIR}/${dir}/x86_64/snponly.efi
    cp ${WORKDIR}/x86_64/usr/share/ipxe/undionly.kpxe ${TARGET_DIR}/${dir}/x86_64/undionly.kpxe

    # ipxe.lkrn is not packaged in RHEL 10, copy if it exists
    if [ -f "${WORKDIR}/x86_64/usr/share/ipxe/ipxe.lkrn" ]; then
        cp ${WORKDIR}/x86_64/usr/share/ipxe/ipxe.lkrn ${TARGET_DIR}/${dir}/x86_64/ipxe.lkrn
    fi

    # x86_64 UEFI boot files (shim and grub)
    cp ${WORKDIR}/x86_64/boot/efi/EFI/${efi_dir_x86}/shimx64.efi ${TARGET_DIR}/${dir}/x86_64/bootx64.efi
    cp ${WORKDIR}/x86_64/boot/efi/EFI/${efi_dir_x86}/grubx64.efi ${TARGET_DIR}/${dir}/x86_64/grubx64.efi

    # aarch64 iPXE files
    cp ${WORKDIR}/aarch64/usr/share/ipxe/arm64-efi/snponly.efi ${TARGET_DIR}/${dir}/aarch64/snponly.efi

    # aarch64 UEFI boot files (shim and grub)
    cp ${WORKDIR}/aarch64/boot/efi/EFI/${efi_dir_aa64}/shimaa64.efi ${TARGET_DIR}/${dir}/aarch64/bootaa64.efi
    cp ${WORKDIR}/aarch64/boot/efi/EFI/${efi_dir_aa64}/grubaa64.efi ${TARGET_DIR}/${dir}/aarch64/grubaa64.efi
done

# Ensure all files are readable
chmod -R +r ${TARGET_DIR}

# Build x86_64 ESP image
pushd ${TARGET_DIR}/httpboot/x86_64
dd if=/dev/zero of=esp.img bs=4096 count=2048
mkfs.msdos -F 12 -n 'ESP_IMAGE' esp.img

mmd -i esp.img EFI
mmd -i esp.img EFI/BOOT
mcopy -i esp.img -v bootx64.efi ::EFI/BOOT
mcopy -i esp.img -v grubx64.efi ::EFI/BOOT
mdir -i esp.img ::EFI/BOOT
popd

echo "x86_64 ESP image created successfully at ${TARGET_DIR}/httpboot/x86_64/esp.img"

# Build aarch64 ESP image
pushd ${TARGET_DIR}/httpboot/aarch64
dd if=/dev/zero of=esp.img bs=4096 count=2048
mkfs.msdos -F 12 -n 'ESP_IMAGE' esp.img

mmd -i esp.img EFI
mmd -i esp.img EFI/BOOT
mcopy -i esp.img -v bootaa64.efi ::EFI/BOOT
mcopy -i esp.img -v grubaa64.efi ::EFI/BOOT
mdir -i esp.img ::EFI/BOOT
popd

echo "aarch64 ESP image created successfully at ${TARGET_DIR}/httpboot/aarch64/esp.img"

# Create compatibility symlinks in httpboot and tftpboot for backwards compatibility
for dir in httpboot tftpboot; do
    pushd ${TARGET_DIR}/${dir}
    ln -sf x86_64/snponly.efi snponly.efi
    ln -sf x86_64/undionly.kpxe undionly.kpxe
    if [ -f "x86_64/ipxe.lkrn" ]; then
        ln -sf x86_64/ipxe.lkrn ipxe.lkrn
    fi
    ln -sf x86_64/bootx64.efi bootx64.efi
    ln -sf x86_64/grubx64.efi grubx64.efi
    if [ "${dir}" = "httpboot" ]; then
        ln -sf x86_64/esp.img esp.img
    fi
    popd
done

echo "Compatibility symlinks created in ${TARGET_DIR}/httpboot and ${TARGET_DIR}/tftpboot"

# Clean up
cd /
rm -rf ${WORKDIR}

echo "Boot assets extracted successfully to ${TARGET_DIR}"
