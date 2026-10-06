#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
gson="$here/../java/lib/gson-2.14.0.jar"
if [ ! -r "$gson" ]; then
    printf '%s\n' 'Missing ../java/lib/gson-2.14.0.jar. Keep the supplied resource directories together.' >&2
    exit 2
fi
exec java -cp "$here/reference-client.jar:$gson" ReferenceClient "$@"
