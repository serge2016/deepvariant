#!/bin/bash
set -euo pipefail

# Copyright 2017 Google LLC.
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

echo ========== This script is only maintained for Ubuntu 20.04.
echo ========== Load config settings.

source settings.sh

################################################################################
# Misc. setup
################################################################################

note_build_stage "Install the runtime packages"

# This installs all the libraries (python, dso, etc) that are needed
# by DeepVariant at runtime (except for tensorflow, which is special).
# Some extra stuff may also be included.

note_build_stage "Misc setup"

APT_ARGS=(
"-y"
)

if [[ "$EUID" = "0" ]]; then
  # Ensure sudo exists, even if we don't need it.
  apt-get update "${APT_ARGS[@]}" > /dev/null
  apt-get install "${APT_ARGS[@]}" sudo > /dev/null
else
  PIP_ARGS=(
    "--user")
fi

note_build_stage "Update package list"

sudo -H apt-get update "${APT_ARGS[@]}"

note_build_stage "run-prereq.sh: Install development packages + for htslib + for the debruijn graph"

# Need to wait for dpkg lock (see internal)
wait_for_dpkg_lock

sudo -H DEBIAN_FRONTEND=noninteractive apt-get install "${APT_ARGS[@]}" pkg-config zip zlib1g-dev unzip curl git wget libssl-dev libcurl4-openssl-dev liblz-dev libbz2-dev liblzma-dev libboost-graph-dev g++

note_build_stage "Install python3 packaging infrastructure, including pip3"

sudo -H DEBIAN_FRONTEND=noninteractive apt-get install "${APT_ARGS[@]}" python3-distutils "python${PYTHON_VERSION}-dev" "python$PYTHON_VERSION-distutils" 
curl -Ss -o get-pip.py https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py --force-reinstall
rm -f get-pip.py

python3 --version
pip3 --version

note_build_stage "Install python3 packages"


pip3 install "${PIP_ARGS[@]}" -r requirements.txt
pip3 install "${PIP_ARGS[@]}" "numpy==${DV_TF_NUMPY_VERSION}"
pip3 install "${PIP_ARGS[@]}" 'oauth2client>=4.0.0'
pip3 install "${PIP_ARGS[@]}" --upgrade google-api-python-client



################################################################################
# TensorFlow
################################################################################
note_build_stage "Install TensorFlow pip package"
if [[ "${DV_USE_PREINSTALLED_TF}" = "1" ]]; then
  echo "Skipping TensorFlow installation at user request; will use pre-installed TensorFlow."
else
  # Also pip install the latest TensorFlow with cpu support. We don't build the
  # full TF from source, but instead using prebuilt version. However, we still
  # need the full source version to build DeepVariant.

  # Gets the nightly TF build: https://pypi.python.org/pypi/tf-nightly which is
  # necessary right now if we aren't pinning the TF source. We have observed
  # runtime failures if there's too much skew between the released TF package and
  # the source.
  if [[ "${DV_TF_NIGHTLY_BUILD}" = "1" ]]; then
    if [[ "${DV_GPU_BUILD}" = "1" ]]; then
      echo "Installing GPU-enabled TensorFlow nightly wheel"
      pip3 install "${PIP_ARGS[@]}" --upgrade tf_nightly_gpu
    else
      echo "Installing CPU-only TensorFlow nightly wheel"
      pip3 install "${PIP_ARGS[@]}" --upgrade tf_nightly
    fi
  else
    # Use the official TF release pip package.
    if [[ "${DV_GPU_BUILD}" = "1" ]]; then
      echo "Installing GPU-enabled TensorFlow ${DV_TENSORFLOW_STANDARD_GPU_WHL_VERSION} wheel"
      pip3 install "${PIP_ARGS[@]}" --upgrade "tensorflow-gpu==${DV_TENSORFLOW_STANDARD_GPU_WHL_VERSION}"
    elif [[ "${DV_USE_GCP_OPTIMIZED_TF_WHL}" = "1" ]]; then
      echo "Installing Intel's CPU-only MKL TensorFlow ${DV_GCP_OPTIMIZED_TF_WHL_VERSION} wheel"
      pip3 install "${PIP_ARGS[@]}" --upgrade "intel-tensorflow==${DV_GCP_OPTIMIZED_TF_WHL_VERSION}"
    else
      echo "Installing standard CPU-only TensorFlow ${DV_TENSORFLOW_STANDARD_CPU_WHL_VERSION} wheel"
      pip3 install "${PIP_ARGS[@]}" --upgrade "tensorflow==${DV_TENSORFLOW_STANDARD_CPU_WHL_VERSION}"
    fi
  fi
fi



################################################################################
# CUDA
################################################################################
# See https://www.tensorflow.org/install/source#gpu for versions required.
if [[ "${DV_GPU_BUILD}" = "1" ]]; then
  if [[ "${DV_INSTALL_GPU_DRIVERS}" = "1" ]]; then
    # This script is only maintained for Ubuntu 20.04.
    UBUNTU_VERSION_SHORT="${UBUNTU_VERSION/./}"
    # https://developer.nvidia.com/cuda-downloads?target_os=Linux&target_arch=x86_64&Distribution=Ubuntu&target_version=20.04&target_type=deb_local
    echo "Checking for CUDA..."
    if ! dpkg-query -W cuda-11-3; then
      echo "Installing CUDA..."
      CUDA_DEB="cuda-repo-ubuntu${UBUNTU_VERSION_SHORT}-11-3-local_11.3.0-465.19.01-1_amd64.deb"
      curl -Ss -O "https://developer.download.nvidia.com/compute/cuda/repos/ubuntu${UBUNTU_VERSION_SHORT}/x86_64/cuda-ubuntu${UBUNTU_VERSION_SHORT}.pin"
      sudo mv "cuda-ubuntu${UBUNTU_VERSION_SHORT}.pin" /etc/apt/preferences.d/cuda-repository-pin-600
      curl -Ss -O "https://developer.download.nvidia.com/compute/cuda/11.3.0/local_installers/${CUDA_DEB}"
      sudo -H apt-key adv --fetch-keys "http://developer.download.nvidia.com/compute/cuda/repos/ubuntu${UBUNTU_VERSION_SHORT}/x86_64/7fa2af80.pub"
      sudo -H dpkg -i "./${CUDA_DEB}"
      sudo apt-key add "/var/cuda-repo-ubuntu${UBUNTU_VERSION_SHORT}-11-3-local/7fa2af80.pub"
      sudo -H apt-get update "${APT_ARGS[@]}" > /dev/null
      sudo -H apt-get install "${APT_ARGS[@]}" cuda
    fi
    echo "Checking for CUDNN..."
    if [[ ! -e /usr/local/cuda-11/include/cudnn.h ]]; then
      echo "Installing CUDNN..."
      CUDNN_TAR_FILE="cudnn-11.3-linux-x64-v8.2.0.53.tgz"
      wget -q https://developer.download.nvidia.com/compute/redist/cudnn/v8.2.0/${CUDNN_TAR_FILE}
      tar -xzvf ${CUDNN_TAR_FILE}
      sudo cp -P cuda/include/cudnn.h /usr/local/cuda-11/include
      sudo cp -P cuda/lib64/libcudnn* /usr/local/cuda-11/lib64/
      sudo cp -P cuda/lib64/libcudnn* /usr/local/cuda-11/lib64/
      sudo chmod a+r /usr/local/cuda-11/lib64/libcudnn*
      sudo ldconfig
    fi
    # Tensorflow says to do this.
    sudo -H apt-get install "${APT_ARGS[@]}" libcupti-dev
  fi
  # If we are doing a gpu-build, nvidia-smi should be install. Run it so we
  # can see what gpu is installed.
  nvidia-smi || :
fi



################################################################################
# OpenVINO
################################################################################
if [[ "${DV_OPENVINO_BUILD}" = "1" ]]; then
  pip3 install "${PIP_ARGS[@]}" git+https://github.com/openvinotoolkit/openvino.git@releases/2021/4#subdirectory=model-optimizer
  pip3 install "${PIP_ARGS[@]}" openvino==2021.4
fi



################################################################################
# bazel
################################################################################
note_build_stage "Install bazel ${DV_BAZEL_VERSION}"
function ensure_wanted_bazel_version {
  local wanted_bazel_version="$1"
  if [[ "$(which bazel > /dev/null; echo "$?")" -eq "0" && "$(bazel --version | sed -e 's/bazel //')" == "$wanted_bazel_version" ]]; then
    echo "Bazel ${wanted_bazel_version} already installed on the machine, not reinstalling"
  else
    mkdir -p "$SOFT"
    pushd "$SOFT"
    curl -L -Ss -o "$SOFT/bazel-${wanted_bazel_version}-installer-linux-x86_64.sh" "https://github.com/bazelbuild/bazel/releases/download/${wanted_bazel_version}/bazel-${wanted_bazel_version}-installer-linux-x86_64.sh"
    chmod +x "$SOFT/bazel-${wanted_bazel_version}-installer-linux-x86_64.sh"
    "$SOFT/bazel-${wanted_bazel_version}-installer-linux-x86_64.sh" --prefix="$SOFT/bazel-${wanted_bazel_version}"
    rm "$SOFT/bazel-${wanted_bazel_version}-installer-linux-x86_64.sh"
    export PATH="$SOFT/bazel-${wanted_bazel_version}/bin:$PATH"
    echo "ATTENTION!!!"
    echo "The next line should be added to ~/.bashrc:"
    echo "export PATH=\"$SOFT/bazel-${wanted_bazel_version}/bin:$PATH\""
    popd
  fi
}
ensure_wanted_bazel_version "${DV_BAZEL_VERSION}"



################################################################################
# CLIF
################################################################################
note_build_stage "Install CLIF binary"
if [[ -e "/usr/local/bin/pyclif" ]]; then
  echo "CLIF already installed."
else
  # Build clif binary from scratch. Might not be ideal because it installs a
  # bunch of dependencies, but this works fine when we used this in a Dockerfile
  # because we don't do build-prereq.sh in the final image.
  note_build_stage "Build CLIF."
  sudo CLIF_UBUNTU_VERSION="${UBUNTU_VERSION}" CLIF_PYTHON_VERSION="${PYTHON_VERSION}" bash tools/build_clif.sh
  # redacted
  # Figure out why these symbolic links are needed and see if we can do this better.
  sudo mkdir -p /usr/clang/bin/
  sudo ln -sf /usr/local/bin/clif-matcher /usr/clang/bin/clif-matcher
  sudo mkdir -p /usr/local/clif/bin
  sudo ln -sf /usr/local/bin/pyclif* /usr/local/clif/bin/
  DIST_PACKAGES_PYCLIF_CLIF_DIR="$(python3 -c "import clif; print(clif.__path__[0])")"
  sudo ln -sf "${DIST_PACKAGES_PYCLIF_CLIF_DIR}/python" /usr/local/clif/
fi



################################################################################
# TensorFlow
################################################################################
note_build_stage "Download and configure TensorFlow sources"
if [[ ! -d "../tensorflow" ]]; then
  pushd ".."
  if [[ "$DV_CPP_TENSORFLOW_TAG" != "master" ]]; then # exact version
    wget -q -O "tensorflow-${DV_CPP_TENSORFLOW_TAG:1}.tar.gz" "https://github.com/tensorflow/tensorflow/archive/refs/tags/${DV_CPP_TENSORFLOW_TAG}.tar.gz"
    tar -xzf "tensorflow-${DV_CPP_TENSORFLOW_TAG:1}.tar.gz"
    mv "tensorflow-${DV_CPP_TENSORFLOW_TAG:1}" "tensorflow"
  else # master
    git clone https://github.com/tensorflow/tensorflow
  fi
  pushd "tensorflow"
  # PYTHON_BIN_PATH and PYTHON_LIB_PATH are set in settings.sh.
  # I had to remove this line in tensorflow v2.5.0 because I got an ERROR:
  # rule() got unexpected keyword argument 'incompatible_use_toolchain_transition'.
  sed -i '/    incompatible_use_toolchain_transition = True,/d' "tensorflow/core/kernels/mlir_generated/build_defs.bzl"
  echo | ./configure
  popd
  popd
fi

note_build_stage "build-prereq.sh complete"
