#!/bin/bash

# Be verbose, and stop with error as soon there's one
set -ev

case "$TEST_TYPE" in
    docs)
        # Compile the docs (HTML format); -W to convert warnings in errors,
        # -n to warn about all missing references
        SPHINXOPTS="-nW" make -C docs html
        ;;
    tests)
        # Run the AiiDA tests
        cd ${TRAVIS_BUILD_DIR}/.travis-data; ./build_wannier90.sh
        python ${TRAVIS_BUILD_DIR}/.travis-data/configure.py ${TRAVIS_BUILD_DIR}/.travis-data ${TRAVIS_BUILD_DIR}/tests;
        cd ${TRAVIS_BUILD_DIR}/tests; py.test
        ;;
    pre-commit)
        pre-commit run --all-files || git status --short && git diff
        ;;
esac
