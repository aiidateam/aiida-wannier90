# -*- coding: utf-8 -*-

"""
AiiDA Wannier90 plugin
======================

This is a plugin for running `Wannier90 <http://wannier.org>`_ calculations on the `AiiDA <http://aiida.net>`_ platform.

Please cite:
    * *An updated version of wannier90: A tool for obtaining maximally-localised Wannier functions* A. A. Mostofi, J. R. Yates, G. Pizzi, Y. S. Lee, I. Souza, D. Vanderbilt, and N. Marzari *Comput. Phys. Commun.* **185**, 2309 (2014) `[Online Journal] <http://dx.doi.org/10.1016/j.cpc.2014.05.003>`_
    * *AiiDA: automated interactive infrastructure and database for computational science* G. Pizzi, A. Cepellotti, R. Sabatini, N. Marzari, and B. Kozinsky *Comp. Mat. Sci.* **111**, 218-230 (2016) `[Journal link] <http://dx.doi.org/10.1016/j.commatsci.2015.09.013>`_ `[arXiv link] <https://arxiv.org/abs/1504.01163>`_
"""

__authors__ = "Daniel Marchand, Antimo Marrazzo, Dominik Gresch & The AiiDA Team."
__copyright__ = u"Copyright (c), This file is part of the AiiDA platform. For further information please visit http://www.aiida.net/. All rights reserved"
__license__ = "Non-Commercial, End-User Software License Agreement, see LICENSE.txt file."
__version__ = "0.0.0a0"

from . import io
from . import parsers
from . import orbitals
from . import calculations
