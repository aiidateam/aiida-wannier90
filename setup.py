# -*- coding: utf-8 -*-

import re

from setuptools import setup, find_packages

with open('./aiida_wannier90/__init__.py', 'r') as f:
    init_file = f.read()
version_match_expr = "__version__[^'\"]+['\"]([^'\"]+)"
version = re.search(version_match_expr, init_file).group(1).strip()
author_match_expr = "__authors__[^'\"]+['\"]([^'\"]+)"
authors = re.search(author_match_expr, init_file).group(1).strip()

if __name__ == '__main__':
    setup(
        name='aiida-wannier90',
        version=version,
        description='AiiDA Plugin for Wannier90',
        author=authors,
        author_email='developers@aiida.net',
        license='MIT',
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Environment :: Plugins',
            'Framework :: AiiDA',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: MIT License',
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
                'wannier90.wannier90 = aiida_wannier90.calculations:Wannier90Calculation',
            ],
            'aiida.data': [
            ],
            'aiida.parsers': [
                'wannier90.wannier90 = aiida_wannier90.parsers:Wannier90Parser'
            ],
        },
    )
