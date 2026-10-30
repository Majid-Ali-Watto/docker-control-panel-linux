#!/bin/bash
# Run the installer on real distro images:   tests/distro_smoke.sh [image ...]
# Needs docker. With no arguments it tests the images in DEFAULT_IMAGES.
DEFAULT_IMAGES="ubuntu:20.04 ubuntu:22.04 ubuntu:24.04 debian:12 fedora:latest rockylinux:8 rockylinux:9 almalinux:9 archlinux:latest opensuse/leap:15.6 opensuse/tumbleweed:latest alpine:latest ghcr.io/void-linux/void-glibc:latest amazonlinux:2023"
cd "$(dirname "$0")/.." || exit 1
images=("$@"); [ ${#images[@]} -eq 0 ] && read -r -a images <<< "$DEFAULT_IMAGES"
status=0
for image in "${images[@]}"; do
    echo "=== $image"
    out=$(docker run --rm -v "$PWD":/src:ro "$image" sh /src/tests/distro_inner.sh 2>&1)
    echo "$out" | tail -22
    echo "$out" | grep -q "^RESULT: PASS" || status=1
done
exit $status
