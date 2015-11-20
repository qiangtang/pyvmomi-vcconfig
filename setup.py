from distutils.core import setup

setup(
    name='vcconfig',
    version='1.0.0',
    scripts=['bin/vc-config',
             'bin/clean_up',
             'bin/vcopt'],
    packages=['common'],
    data_files=[('/usr/local/data', ['data/config.ini'])]
)
