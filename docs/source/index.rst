.. title:: Overview

.. automodule:: aiida_wannier90
    :members:


`Wannier90`_ is a tool for obtaining maximally localized wannier functions from
DFT calculations. The Wannier90 code is freely available under the GNU LGPL
license (the Wannier90 installation guide and the source can be found `here`_).

.. _here: http://www.wannier.org/


Supported codes
---------------
The plugin supports all the Wannier90 versions from v1.0 to v3.x.
In particular, it has been tested on v3.0 (and v3.1) and v2.x.
However, it should also work with v1.x.

We strongly suggest that this plugin is used in combination with version v3.x
of Wannier (better support for parsing band structures, new features, ...).

Input description
-----------------

.. toctree::
    :maxdepth: 3

    inputexample.rst

Parsed output description
-------------------------

.. toctree::
    :maxdepth: 3

    parser.rst

Tutorials
---------

The Wannier90 plugin is provided with two example based on a GaAs crystalline sample. The first example is a simple wannierization step by step, with which we aim to show the format of the inputs expected by the plugin.
The second case of study aims to provide the user with a practical example of a simple workflow to perform the same wannierization procedure. 

.. toctree::
    :maxdepth: 3

    tutorial_calculation.rst
    tutorial_minimal_workflow.rst

Reference
---------

.. toctree::
    :maxdepth: 3

    reference.rst


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
