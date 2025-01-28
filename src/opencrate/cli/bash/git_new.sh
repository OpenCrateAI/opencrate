#!/bin/bash

version=$1

git branch -m main main-$version > /dev/null
git checkout -b dev-$version > /dev/null