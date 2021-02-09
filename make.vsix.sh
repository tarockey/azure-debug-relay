#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

rm -rf "${DIR}/build/vscode"
mkdir -p "${DIR}/build/vscode"
vsce package --out "${DIR}/build/vscode"
