#!/usr/bin/env bash

set -eu

unset CDPATH
cd "$( dirname "${BASH_SOURCE[0]}" )/../.."

pip install -r "test/integration_tests/requirements-integration-test.txt"

NODE_URL="https://nodejs.org/dist/v6.4.0/node-v6.4.0-linux-x64.tar.gz"
curl $NODE_URL | tar xz -C $VIRTUAL_ENV --strip-components 1

npm install -g test/integration_tests
