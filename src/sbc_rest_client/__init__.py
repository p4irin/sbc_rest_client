"""Provide a REST API client class to interact with the REST API of an SBC.

The SBC is an Oracle Communications Session Border Controller.
(Acme Packet OS VM SCZ8.3.0 MR-1 Patch 9 (Build 400)
Oracle Linux branches-7/el7-u8 {2020-04-08T07:00:00+0000} Build Date=07/17/20)
For reference see https://docs.oracle.com/en/industries/communications/ \
    session-border-controller/8.3.0/rest/index.html

Import example:

    from sbc_rest_client.sbc import Sbc

    sbc = Sbc("admin", "password", "sbc.your-domain.com")

For usage examples see the README.md.
"""

__author__ = '139928764+p4irin@users.noreply.github.com'
__version__ = '0.1.1'