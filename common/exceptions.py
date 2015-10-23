"""Exceptions for run.py"""


class ProvisionException(Exception):
    """Provisioning exceptions"""


class VirtualCenterException(Exception):
    """vCenter configuration exceptions"""


class DevstackException(Exception):
    """Devstack installation and configuration exceptions"""
