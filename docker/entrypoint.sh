#!/bin/sh
set -eu
mkdir -p /in /work /tmp
tar -C /in -xf -
exec python /grader/grader.py
