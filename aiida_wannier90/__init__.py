# -*- coding: utf-8 -*-
"""
AiiDA Wannier90 plugin
======================

This is a plugin for running `Wannier90 <http://wannier.org>`_ calculations on the `AiiDA <http://aiida.net>`_ platform.

Please cite:
    * *An updated version of wannier90: A tool for obtaining maximally-localised Wannier functions* A. A. Mostofi, J. R. Yates, G. Pizzi, Y. S. Lee, I. Souza, D. Vanderbilt, and N. Marzari *Comput. Phys. Commun.* **185**, 2309 (2014) `[Online Journal] <http://dx.doi.org/10.1016/j.cpc.2014.05.003>`_
    * *AiiDA: automated interactive infrastructure and database for computational science* G. Pizzi, A. Cepellotti, R. Sabatini, N. Marzari, and B. Kozinsky *Comp. Mat. Sci.* **111**, 218-230 (2016) `[Journal link] <http://dx.doi.org/10.1016/j.commatsci.2015.09.013>`_ `[arXiv link] <https://arxiv.org/abs/1504.01163>`_
"""

__authors__ = "Dominik Gresch, Antimo Marrazzo, Daniel Marchand, Giovanni Pizzi & The AiiDA Team."
__license__ = "MIT License, see LICENSE.txt file."
## If upgraded, remember to change it also in setup.json (for pip)
__version__ = "1.0.0"

from . import io
from . import parsers
from . import orbitals
## If this is imported then AiiDA ORM is loaded and this fails if the load_dbenv has not
## been yet called
#from . import calculations
