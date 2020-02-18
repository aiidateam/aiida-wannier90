# -*- coding: utf-8 -*-
"""
AiiDA Wannier90 plugin
======================

This is a plugin for running `Wannier90 <http://wannier.org>`_ calculations on the `AiiDA <http://aiida.net>`_ platform.

Please cite:
    * *An updated version of wannier90: A tool for obtaining maximally-localised Wannier functions* A. A. Mostofi, J. R. Yates,
       G. Pizzi, Y. S. Lee, I. Souza, D. Vanderbilt, and N. Marzari *Comput. Phys. Commun.* **185**, 2309 (2014) `
       [Online Journal] <https://doi.org/10.1016/j.cpc.2014.05.003>`_
    * *AiiDA: automated interactive infrastructure and database for computational science* G. Pizzi, A. Cepellotti, R. Sabatini,
       N. Marzari, and B. Kozinsky, *Comp. Mat. Sci.* **111**, 218-230 (2016) ` [Journal link] <https://doi.org/10.1016/j.commatsci.2015.09.013>`_
       `[arXiv link] <https://arxiv.org/abs/1504.01163>`_
"""

from __future__ import absolute_import

__authors__ = "Dominik Gresch, Antimo Marrazzo, Daniel Marchand, Giovanni Pizzi & The AiiDA Team."
__license__ = "MIT License, see LICENSE.txt file."
## If upgraded, remember to change it also in setup.json (for pip)
__version__ = "2.0.0a1"

from . import io
from . import parsers
from . import orbitals
from . import calculations

__all__ = ('io', 'parsers', 'orbitals', 'calculations')
