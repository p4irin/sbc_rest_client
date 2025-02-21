# sbc_rest_client - v0.1.0

This Python package provides a REST client class allowing you to remotely
script the management of an Oracle Communications Session Border Controller
via its REST API. Not all API calls are implemented! Only the ones I needed
at the time and some I included randomly on the go. Feel free to have a go
at it and add the calls you're missing.

## Stack

- Oracle Communications Session Border Controller
  - Acme Packet OS VM SCZ8.3.0 MR-1 Patch 9 (Build 400)
    Oracle Linux branches-7/el7-u8 {2020-04-08T07:00:00+0000}
    Build Date=07/17/20
- Ubuntu: 20.04.2 LTS
- Python: 3.8.10
- letsencrypt certificate
- Visual Studio Code

## Implemented API calls

For reference consult [REST API for Session Border Controller Release 8.3](https://docs.oracle.com/en/industries/communications/session-border-controller/8.3.0/rest/index.html)

Operation | Method or property | Returns | Description
---------|----------|---------|---------
 Request an access token | _get_token() | `None`. _Gets_ and _sets_ an access token on an `Sbc` object | This is done under the hood when instantiating an `Sbc` object. You do not call this method directly.
 Get system status information | @property role | A string value of either `standalone`, `active` or `standby`. Or, `False` if the API request failed | Get the role of a Session Border Controller
 Reboot the system | reboot() | A `bool` indicating the succes of the operation |
 Execute HA switchover | switchover() | A `bool` indicating the succes of the operation |
 Get supported REST API versions | @property supported_rest_api_versions() | A list of supported API versions |
 Get various statistics | @property global_cps | Global calls per second |
 | | @property global_con_sessions | The global number of connected sessions |
 Get the metadata for a configuration element type | config_element_key_attributes(self, element_type: str) | A list of a configuration element's _key_ attributes | _Key_ attributes uniquely identify configuration elements. You need them to update configuration elements. [ see update_config_element() ]. _element_type_ specifies the type of the element for which you want to get the _key_ attributes.
 Get one or more configuration element instances | get_config_elements(self, element_type: str, key_attribs: str = None) | `None`. Prints the configuration element instances to console | Specify the _element_type_ and _key_attribs_ of the configuration elements. _key_attribs_ is a string of query parameters that represent the _key_ attributes. E.g., &name1=value1&name2=value2. The string MUST start with an &.
Lock the configuration | lock() | A `bool` indicating the succes of the operation |
Unlock the configuration | unlock() | A `bool` indicating the succes of the operation |
Update a single configuration element instance | update_config_element(self, xml_str: str) | A `bool` indicating the succes of the operation | To identify a configuration element you need to set the key attributes in _xml_str_. [Also see self.config_element_key_attributes()] and a usage example below.
Back up or activate a configuration, Save, verify or restore a configuration | activate_config() | A `bool` indicating the succes of the operation | This will _verify_ and _save_ the configuration behind the scenes before it's _activated_
Add configuration element instance | add_config_element(self, xml_str: str) | A bool Indicating succes of the operation | To identify a configuration element you need to set the key attributes in xml_str. [Also see self.config_element_key_attributes()] [Important note on singletons](https://docs.oracle.com/en/industries/communications/session-border-controller/8.3.0/rest/op-rest-version-configuration-configelements-post.html#:~:text=If%20the%20configuration,already%2Dconfigured%20instance.)
Delete configuration element instance | delete_config_element(self, element_type: str, key_attribs: Union[str, None] = None | A bool indicating succes or failure |

## Installation

Create your new project directory and cd into it.
```bash
$ mkdir new_project
$ cd new_project
$
```
Create a virtual environment and activate it.
```bash
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $
```
pip install from GitHub.
```bash
(venv) $ pip install git+https://github.com/p4irin/sbc_rest_client.git
```
Verify in a REPL. Replace "admin", "password" and "sbc.example.com" with your credentials and SBC hostname.
```bash
(venv) $ python
Python 3.8.10 (default, Jun  2 2021, 10:49:15) 
[GCC 9.4.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from sbc_rest_client.sbc import Sbc
>>> sbc = Sbc("admin", "password", "sbc.example.com")
Get a token from sbc.example.com: Ok!
>>> sbc.role
'standalone'
>>> sbc.global_con_sessions
'13'
>>>
```

### Notes

- I used a letsencrypt certificate on the Session Border Controller.
The letsencrypt root ca is installed allongside and used by the sbc_rest_client package.
- The Session Border Controller needs a reboot for the webserver to notice a TLS certificate update!

## Usage examples

In general, you will follow these steps for configuration management related operations:

1. Instantiate an Sbc object
1. Lock the configuration
1. Execute configuration changes
1. Activate the configuration
1. Unlock the configuration

The moment you instantiate an `Sbc` object an access token is acquired. The token is used behind the scenes to authenticate all your API calls. From this point you should lock the configuration, make your changes, activate it and finally unlock it.

For admin related operations locking and unlocking is not required.

### Import

First things first. This applies to and should precede all standalone examples below.

```python
from sbc_rest_client.sbc import Sbc


# Use your credentials and the hostname or ip address of your Oracle Communications Session Border Controller
sbc = Sbc("<your admin user>", "<your password>", "<sbc.your-domain.com>")

# Verification of the letsencrypt TLS certificate I used on the
# Session Border Controller is enabled by default
# If you're using a self signed or other certificate you
# can disable this by passing "verify=False".

# sbc = Sbc("<your admin user>", "<your password>", "<sbc.your-domain.com>", verify=False)

# Disabling certificate verification causes a bunch of SSL warnings
# on the console. To suppress those, pass "ssl_warnings=False"

# sbc = Sbc("<your admin user>", "<your password>", "<sbc.your-domain.com>", ssl_warnings=False, verify=False)
```

Let's start with some simple admin examples. As said, these don't need configuration locking.

### Reboot an SBC

```python
if sbc.reboot():
  print("Rebooting the SBC")
else:
  print("Something went wrong")
```

### Execute a switchover in a High Availability setup

```python
if sbc.switchover():
  print("Switching the active SBC")
else:
  print("Something went wrong)
```

### Change a configuration element

```python
# Decide what needs to be updated
# Here, a session-group is modified
# The attribute "group-name" is a key attribute and identifies the element
# to be changed. Use the helper methods config_element_key_attributes and
# get_config_elements to figure out which key attributes you need
# and the structure and nodes of the configElement.
# Notice, in the xml, that you only need to include the attributes
# you want to have changed
xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
  <configElement>
    <elementType>session-group</elementType>
    <attribute>
      <name>group-name</name>
      <value>sg_proxies</value>
    </attribute>
    <attribute>
      <name>dest</name>
      <value>proxy1.example.com</value>
      <value>proxy2.example.com</value>
    </attribute>
  </configElement>
"""

# Acquire a configuration lock and exit on failure
if not sbc.lock():
    print("Error: Failed to lock the config.! Exiting!")
    exit(1)

# Update an element
if not sbc.update_config_element(xml):
    print("Error: Failed to update configuration element!")

# Activate the change
if not sbc.activate_config(): print("Error: Failed to activate config.!")

# Free the lock
if not sbc.unlock(): print(
    "Error: Failed to unlock config."
)
```

## Notes

- I've set the default api version used to _v1.1_. The API reference mentions a _v1.0_ but does not elaborate on it at all other than that it's in the output of the _supportedversions_ operation. Like, what are the differences or when and why to use or prefer one over the other. The reference examples use _v1.1_ so let's stick to that.
- An access token is valid for 10 minutes. This is not accounted for. The scripts I use don't last that long so I didn't bother to handle token expiry. 

## Reference

- [REST API for Session Border Controller Release 8.3](https://docs.oracle.com/en/industries/communications/session-border-controller/8.3.0/rest/index.html)
- [Requests: HTTP for Humans](https://requests.readthedocs.io/en/latest/)
- [XML and HTML with Python](https://lxml.de/)
