#!/bin/bash -u

print_usage()
{
    echo "Usage:"
    echo " $0 [options]"
    echo ""
    echo "Options:"
    echo " -c, --clang          build clang warning lists"
    echo " -g, --gcc            build gcc warning lists"
    echo " -x, --xcode          build xcode warning lists"
    echo " -h, --help           display this help"
}

OPTS=$(getopt -o cgxh -l clang,gcc,xcode,help -- "$@")
if [ $? != 0 ]; then
    print_usage
    exit 1
fi

eval set -- "$OPTS"

BUILD_CLANG=0
BUILD_GCC=0
BUILD_XCODE=0
while true; do
    case "$1" in
        -c | --clang )
            BUILD_CLANG=1
            shift
            ;;
        -g | --gcc )
            BUILD_GCC=1
            shift
            ;;
        -x | --xcode )
            BUILD_XCODE=1
            shift
            ;;
        -h | --help )
            print_usage
            exit 0
            ;;
        -- )
            shift
            break
            ;;
        -* )
            echo "Unexpected output from getopt"
            exit 1
            ;;
    esac
done

if [ ${BUILD_CLANG} -eq 0 -a ${BUILD_GCC} -eq 0 -a ${BUILD_XCODE} -eq 0 ]; then
    BUILD_CLANG=1
    BUILD_GCC=1
    BUILD_XCODE=1
fi

set -e

DOCKER_IMAGE_TAG="pkolbus/compiler-warnings"

#
# Test Docker availability
#
if ! which docker > /dev/null; then
    echo "Docker is required but doesn't seem to be installed. See https://www.docker.com/ to get started"
    exit 1
fi

if groups | grep docker > /dev/null; then
    DOCKER="docker"
else
    echo "Using sudo to invoke docker since you're not a member of the docker group..."
    DOCKER="sudo docker"
fi

run_in_docker()
{
    ${DOCKER} container run -it --rm \
        --user "$(id -u)":"$(id -g)" \
        --network host \
        --volume ${PWD}:${PWD} \
        --workdir ${PWD} \
        ${DOCKER_IMAGE_TAG} \
        "$@"
}

#
# Build the Docker image
#
echo "Getting docker image up to date (this may take a few minutes)..."

cp parsers/requirements.txt docker/requirements.txt
${DOCKER} image build \
    -q \
    -t ${DOCKER_IMAGE_TAG} \
    --network host \
    --cache-from=${DOCKER_IMAGE_TAG}:latest \
    ./docker/

# Linting requires the gcc parser to be built
echo "Building the gcc parser..."
run_in_docker ninja -C parsers
run_in_docker ninja -C parsers test

# Run formatting/linting
run_in_docker black .
run_in_docker flake8 .
for f in $(git ls-files "*.sh"); do
    run_in_docker shellcheck "${f}"
done

#
# Prepare to build the warning options
#
mkdir -p build

if [ ${BUILD_CLANG} -eq 1 -o ${BUILD_XCODE} -eq 1 ]; then
    echo "Testing the clang parser..."
    run_in_docker python3 -mdoctest ./parsers/parse-clang-diagnostic-groups.py
fi

if [ ${BUILD_CLANG} -eq 1 ]; then
    echo "Running the clang parser..."
    CLANG_REMOTE="https://github.com/llvm/llvm-project.git"

    if [ -e build/clang/.git ]; then
        run_in_docker git -C build/clang remote set-url origin ${CLANG_REMOTE}
        run_in_docker git -C build/clang remote update
    else
        run_in_docker git clone ${CLANG_REMOTE} build/clang
    fi

    run_in_docker ./parsers/process-clang-git.sh build/clang
fi

if [ ${BUILD_GCC} -eq 1 ]; then
    echo "Running the gcc parser..."

    if [ -e build/gcc/.git ]; then
        run_in_docker git -C build/gcc remote update
    else
        run_in_docker git clone git://gcc.gnu.org/git/gcc.git build/gcc
    fi
    run_in_docker ./parsers/process-gcc-git.sh build/gcc
fi

if [ ${BUILD_XCODE} -eq 1 ]; then
    echo "Running the xcode parser..."
    CLANG_REMOTE="https://github.com/apple/llvm-project.git"

    if [ -e build/xcode/.git ]; then
        run_in_docker git -C build/xcode remote set-url origin ${CLANG_REMOTE}
        run_in_docker git -C build/xcode remote update
    else
        run_in_docker git clone ${CLANG_REMOTE} build/xcode
    fi

    run_in_docker ./parsers/process-xcode-git.sh build/xcode
fi
