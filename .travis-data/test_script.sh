#!/bin/bash

# Be verbose, and stop with error as soon there's one
set -ev

case "$TEST_TYPE" in
    tests)
        # I make sure that I can import the module without the need of having the AiiDA environment/profile loaded
        python -c "import aiida_wannier90"

        # Run the AiiDA tests
        cd ${TRAVIS_BUILD_DIR}/tests; pytest
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
esac
