from distutils.core import setup

setup(
    name='vcconfig',
    version='1.0.0',
    scripts=['bin/vc-config',
             'bin/clean_up',
             'bin/vmotion'],
    packages=['common'],
    data_files=[('/usr/data', ['data/config.ini'])]
)
