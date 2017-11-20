#!/bin/bash
git clone -b master https://github.com/wannier-developers/wannier90.git wannier90
cp make.inc wannier90/
make -C wannier90
