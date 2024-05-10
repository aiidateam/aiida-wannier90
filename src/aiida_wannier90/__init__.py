################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""AiiDA Wannier90 plugin.

This is a plugin for running `Wannier90 <http://wannier.org>`_ calculations on the `AiiDA <http://aiida.net>`_ platform.

**Please cite:**

-  **Wannier90 as a community code: new features and applications**
   G. Pizzi, V. Vitale, R. Arita, S. Blügel, F. Freimuth, G. Géranton,
   M. Gibertini, D. Gresch, C. Johnson, T.Koretsune, J. Ibañez-Azpiroz,
   H. Lee, J. M. Lihm, D. Marchand, A. Marrazzo, Y. Mokrousov,
   J. I. Mustafa, Y. Nohara, Y. Nomura, L. Paulatto, S. Poncé,
   T. Ponweiser, J. Qiao, F. Thöle, S. S. Tsirkin, M. Wierzbowska,
   N. Marzari, D. Vanderbilt, I. Souza, A. A. Mostofi, and J. R. Yates
   *J. Phys. Cond. Matt.* **32**, 165902 (2020)
   `[Online Journal] <http://doi.org/10.1088/1361-648X/ab51ff>`_
-  **AiiDA: automated interactive infrastructure and database for computational science**
   G. Pizzi, A. Cepellotti, R. Sabatini, N. Marzari, and B. Kozinsky,
   *Comp. Mat. Sci.* **111**, 218-230 (2016)
   `[Journal link] <https://doi.org/10.1016/j.commatsci.2015.09.013>`_
   `[arXiv link] <https://arxiv.org/abs/1504.01163>`_
"""

__authors__ = "The AiiDA team."
__license__ = "MIT License, see LICENSE.txt file."
__version__ = "2.2.0"

from . import calculations, io, orbitals, parsers, utils

__all__ = ("io", "parsers", "orbitals", "calculations", "utils")
