#!/bin/bash

# Be verbose, and stop with error as soon there's one
set -ev

case "$TEST_TYPE" in
    tests)
        # Run the AiiDA tests
        cd ${TRAVIS_BUILD_DIR}/.travis-data; ./build_wannier90.sh
        python ${TRAVIS_BUILD_DIR}/.travis-data/configure.py ${TRAVIS_BUILD_DIR}/.travis-data ${TRAVIS_BUILD_DIR}/tests;
        export AIIDA_PATH="${TRAVIS_BUILD_DIR}/tests"
        cd ${TRAVIS_BUILD_DIR}/tests; py.test --quiet-wipe
        ;;
    pre-commit)
        # Need to finish with exit 1 otherwise travis thinks that it all went well
        pre-commit run --all-files || (git status --short ; git diff ; exit 1)

        # Compile the docs (HTML format), ensuring there are no warnings either
        # -C change to 'docs' directory before doing anything
        # -n to warn about all missing references
        # -W to convert warnings in errors
        SPHINXOPTS="-nW" make -C docs
        ;;        
        ;;
esac
