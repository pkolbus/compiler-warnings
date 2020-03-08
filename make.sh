#!/bin/bash -u

print_usage()
{
    echo "Usage:"
    echo " $0 [options]"
    echo ""
    echo "Options:"
    echo " -c, --clang          build clang warning lists"
    echo " -g, --gcc            build gcc warning lists"
    echo " -h, --help           display this help"
}

OPTS=`getopt -o cgh -l clang,gcc,help -- $@`
if [ $? != 0 ]; then
    print_usage
    exit 1
fi

eval set -- "$OPTS"

BUILD_CLANG="false"
BUILD_GCC="false"
while true; do
    case "$1" in
        -c | --clang )
            BUILD_CLANG="true"
            shift
            ;;
        -g | --gcc )
            BUILD_GCC="true"
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

if [ "${BUILD_CLANG}" == "false" ] && [ "${BUILD_GCC}" == "false" ]; then
    BUILD_CLANG="true"
    BUILD_GCC="true"
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
        --user $(id -u):$(id -g) \
        --network host \
        --volume ${PWD}:${PWD} \
        --workdir ${PWD} \
        ${DOCKER_IMAGE_TAG} \
        $@
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

#
# Prepare to build the warning options
#
mkdir -p build

if [ "${BUILD_CLANG}" == "true" ]; then
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

if [ "${BUILD_GCC}" == "true" ]; then
    echo "Building the gcc parser..."

    run_in_docker ninja -C parsers
    run_in_docker ninja -C parsers test

    echo "Running the gcc parser..."

    if [ -e build/gcc/.git ]; then
        run_in_docker git -C build/gcc remote update
    else
        run_in_docker git clone git://gcc.gnu.org/git/gcc.git build/gcc
    fi
    run_in_docker ./parsers/process-gcc-git.sh build/gcc
fi
