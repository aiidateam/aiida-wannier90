# -*- coding: utf-8 -*-

import re

from setuptools import setup, find_packages

with open('./aiida_wannier90/_version.py', 'r') as f:
    match_expr = "__version__[^'" + '"]+([' + "'" + r'"])([^\1]+)\1'
    version = re.search(match_expr, f.read()).group(2).strip()

if __name__ == '__main__':
    setup(
        name='aiida-wannier90',
        version=version,
        description='AiiDA Plugin for Wannier90',
        author='The AiiDA Team',
        author_email='developers@aiida.net',
        license='GPL',
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Environment :: Plugins',
            'Framework :: AiiDA',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
            'Programming Language :: Python :: 2.7',
            'Topic :: Scientific/Engineering :: Physics'
        ],
        keywords='wannier90 aiida workflows',
        packages=find_packages(exclude=['aiida']),
        include_package_data=True,
        setup_requires=[
            'reentry'
        ],
        reentry_register=True,
        install_requires=[
            'aiida-core',
        ],
        extras_require={
            'test': ['pytest', 'aiida-pytest']
        },
        entry_points={
            'aiida.calculations': [
                'wannier90.wannier = aiida_tbmodels.calculations.wannier:WannierCalculation',
            ],
            'aiida.data': [
            ],
            'aiida.parsers': [
            ],
        },
    )
