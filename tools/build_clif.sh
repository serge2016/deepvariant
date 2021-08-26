#!/bin/bash
# Copyright 2020 Google LLC.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#

set -eux -o pipefail

echo ========== This script has been tested on Ubuntu18.04 and Ubuntu20.04.
echo ========== See https://github.com/google/clif for how to build on different Unix distributions.
echo ========== Run this script in root mode.

CLIF_UBUNTU_VERSION="${CLIF_UBUNTU_VERSION-18.04}"
CLIF_PYTHON_VERSION="${CLIF_PYTHON_VERSION-3.6}"
CLIF_VERSION="0.4"
ABSL_VERSION=20200923
PROTOBUF_VERSION=3.13.0

SOFT="${SOFT-$HOME/soft}"
mkdir -p "$SOFT"

APT_ARGS=(
"-y"
)

apt-get update  "${APT_ARGS[@]}"

apt-get install "${APT_ARGS[@]}" --no-install-recommends \
    autoconf \
    automake \
    cmake \
    curl \
    gpg-agent \
    g++ \
    libtool \
    make \
    pkg-config \
    software-properties-common \
    wget \
    unzip

# Configure LLVM 11 apt repository
wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key |  apt-key add - && \
  add-apt-repository "deb http://apt.llvm.org/$(lsb_release -sc)/ llvm-toolchain-$(lsb_release -sc)-11 main"

# Install CLIF dependencies
apt-get install  "${APT_ARGS[@]}" \
    clang-11 \
    libclang-11-dev \
    libgoogle-glog-dev \
    libgtest-dev \
    libllvm11 \
    llvm-11-dev \
    python3-dev \
    zlib1g-dev

# Uninstall an older version of libclang so that cmake uses the correct one.
apt-get remove "${APT_ARGS[@]}" libclang-common-9-dev

# Configure deadsnakes PPA with the more recent versions of python packaged for
# Ubuntu. See https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa
apt-get install "${APT_ARGS[@]}" \
    "python$CLIF_PYTHON_VERSION-dev" \
    "python$CLIF_PYTHON_VERSION-distutils"

# Install latest version of pip since the version on ubuntu could be outdated
cd "$SOFT" && curl "https://bootstrap.pypa.io/get-pip.py" -o get-pip.py && \
    "python$CLIF_PYTHON_VERSION" get-pip.py && \
    rm get-pip.py

# Compile and install absl-cpp from source
cd "$SOFT" && wget "https://github.com/abseil/abseil-cpp/archive/$ABSL_VERSION.tar.gz" && \
    tar -xzf "$ABSL_VERSION.tar.gz" && \
    mkdir "abseil-cpp-$ABSL_VERSION/build" && \
    cd "abseil-cpp-$ABSL_VERSION/build" && \
    cmake .. -DCMAKE_POSITION_INDEPENDENT_CODE=true && \
    make install && \
    rm -rf "abseil-cpp-$ABSL_VERSION" "$ABSL_VERSION.tar.gz"

# Compile and install protobuf from source
cd "$SOFT" && wget "https://github.com/protocolbuffers/protobuf/releases/download/v$PROTOBUF_VERSION/protobuf-cpp-$PROTOBUF_VERSION.tar.gz" && \
    tar -xzf "protobuf-cpp-$PROTOBUF_VERSION.tar.gz" && \
    cd "protobuf-$PROTOBUF_VERSION" && \
    # Configure and install C++ libraries
    ./autogen.sh && \
    ./configure && \
    make -j"$(nproc)" && \
    make install && \
    ldconfig && \
    rm -rf "protobuf-$PROTOBUF_VERSION" "protobuf-cpp-$PROTOBUF_VERSION.tar.gz"

# Install googletest
cd /usr/src/googletest && \
    cmake . && \
    make install

# Install python runtime and test dependencies
pip3 install \
    absl-py \
    parameterized \
    protobuf=="$PROTOBUF_VERSION" \
    httplib2=="0.18.1" \
    pyparsing=="2.2.0"

cd "$SOFT" && wget -q -O "clif-${CLIF_VERSION}.tar.gz" "https://github.com/google/clif/archive/refs/tags/v${CLIF_VERSION}.tar.gz" && \
  tar -xzf "clif-${CLIF_VERSION}.tar.gz" && \
  cd "clif-${CLIF_VERSION}" && \
  sed -i 's/^find_package(LLVM 11 REQUIRED)$/find_package(LLVM 11.1.0 REQUIRED)/' "clif/cmake/modules/CLIFUtils.cmake" && \
  sed -i '/^find_package(PythonLibs REQUIRED)$/d' "clif/cmake/modules/CLIFUtils.cmake" && \
  sed -i '/^find_package(PythonInterp REQUIRED)$/a find_package(PythonLibs REQUIRED)' "clif/cmake/modules/CLIFUtils.cmake" && \
  sed -i 's/"$PYTHON" -m pip $PIP_VERBOSE install .$/"$PYTHON" setup.py install/' "INSTALL.sh" && \
  ./INSTALL.sh
