from distutils.core import setup

setup(
    name='vcconfig',
    version='1.0.0',
    scripts=['bin/vc-cfg',
             'bin/vc-clean',
             'bin/vc-opt'],
    packages=['common',
              'common.parser'],
    data_files=[('/usr/local/data', ['data/config.ini'])]
)
