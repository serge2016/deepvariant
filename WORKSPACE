# The workspace name appears at the top of the runfiles tree,
# and in paths to tests, so to keep python happy it is best
# if it is unique.
workspace(name = "com_google_deepvariant")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# Note: absl_py and com_google_absl (the Python and C++ abseil libraries) are
# provided by TensorFlow.

# CCTZ (Time-zone framework).
# redacted
# work in bazel, so we need to include this to enable nucleus's use of
# //absl/{time,synchronization}
http_archive(
    name = "com_googlesource_code_cctz",
    strip_prefix = "cctz-master",
    urls = ["https://github.com/google/cctz/archive/master.zip"],
)

# This is the 1.10.2 release of htslib.
http_archive(
    name = "htslib",
    build_file = "//:third_party/htslib.BUILD",
    sha256 = "f7994e9636f8a4032dea477a8613f5f73b330c23b5538e45666ce7306240ac14",
    strip_prefix = "htslib-1.10.2",
    urls = [
        "https://github.com/samtools/htslib/archive/1.10.2.zip",
    ],
)

http_archive(
    name = "libssw",
    build_file = "//:third_party/libssw.BUILD",
    sha256 = "10b9305e5a580ee5319f736d3581916f6c873ef4475bd0c0e564c2934334732c",
    strip_prefix = "Complete-Striped-Smith-Waterman-Library-1.0",
    urls = [
        "https://github.com/mengyao/Complete-Striped-Smith-Waterman-Library/archive/v1.0.tar.gz",
    ],
)

# Import tensorflow.  Note path.
local_repository(
    name = "org_tensorflow",
    path = "../tensorflow",
)

# Required boilerplate for tf_workspace().
# This is copied from https://github.com/tensorflow/tensorflow/blob/v2.3.0/WORKSPACE.
http_archive(
    name = "io_bazel_rules_closure",
    sha256 = "5b00383d08dd71f28503736db0500b6fb4dda47489ff5fc6bed42557c07c6ba9",
    strip_prefix = "rules_closure-308b05b2419edb5c8ee0471b67a40403df940149",
    urls = [
        "https://storage.googleapis.com/mirror.tensorflow.org/github.com/bazelbuild/rules_closure/archive/308b05b2419edb5c8ee0471b67a40403df940149.tar.gz",
        "https://github.com/bazelbuild/rules_closure/archive/308b05b2419edb5c8ee0471b67a40403df940149.tar.gz",  # 2019-06-13
    ],
)

# This needs to be in sync with the version of protobuf used by TensorFlow,
# which is currently defined in @tensorflow/tensorflow/workspace.bzl.
# We supply our own BUILD file, though, so we can prevent ODR violations by
# putting all of Nucleus's C++ binary dependencies into a single library.
# That BUILD file must be kept in sync with the version of protobuf used.
http_archive(
    name = "com_google_protobuf",
    build_file = "//:third_party/protobuf.BUILD",
    sha256 = "cfcba2df10feec52a84208693937c17a4b5df7775e1635c1e3baffc487b24c9b",
    # This protobuf release is based on protobuf 3.9.2.
    strip_prefix = "protobuf-3.9.2",
    urls = [
        "https://storage.googleapis.com/mirror.tensorflow.org/github.com/protocolbuffers/protobuf/archive/v3.9.2.zip",
        "https://github.com/protocolbuffers/protobuf/archive/v3.9.2.zip",
    ],
)

http_archive(
    name = "com_google_glog",
    sha256 = "1ee310e5d0a19b9d584a855000434bb724aa744745d5b8ab1855c85bff8a8e21",
    strip_prefix = "glog-028d37889a1e80e8a07da1b8945ac706259e5fd8",
    urls = [
        "https://mirror.bazel.build/github.com/google/glog/archive/028d37889a1e80e8a07da1b8945ac706259e5fd8.tar.gz",
        "https://github.com/google/glog/archive/028d37889a1e80e8a07da1b8945ac706259e5fd8.tar.gz",
    ],
)


# bazel_skylib is now a required dependency of protobuf_archive.
http_archive(
    name = "bazel_skylib",
    sha256 = "97e70364e9249702246c0e9444bccdc4b847bed1eb03c5a3ece4f83dfe6abc44",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/bazel-skylib/releases/download/1.0.2/bazel-skylib-1.0.2.tar.gz",
        "https://github.com/bazelbuild/bazel-skylib/releases/download/1.0.2/bazel-skylib-1.0.2.tar.gz",
    ],
)

# Import all of the tensorflow dependencies.
# Copied from tensorflow/WORKSPACE. Updated in v2.5.0:
load("@org_tensorflow//tensorflow:workspace3.bzl", "tf_workspace3")

tf_workspace3()

load("@org_tensorflow//tensorflow:workspace2.bzl", "tf_workspace2")

tf_workspace2()

load("@org_tensorflow//tensorflow:workspace1.bzl", "tf_workspace1")

tf_workspace1()

load("@org_tensorflow//tensorflow:workspace0.bzl", "tf_workspace0")

tf_workspace0()

new_local_repository(
    name = "clif",
    build_file = "third_party/clif.BUILD",
    path = "/usr/local",
)
