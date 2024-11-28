import requests
from urllib3.exceptions import InsecureRequestWarning
import polling2
import base64
from lxml import etree
from typing import Union
import os


__author__ = '139928764+p4irin@users.noreply.github.com'


class Sbc(object):
    """Interact with the REST API of a Session Border Controller."""

    _accept_header = { "Accept": "application/xml"}

    def __init__(
            self, user: str, passwd: str, host: str,
            api_version: str = "v1.1",
            request_timeout: int = 10,
            ssl_warnings: bool = True,
            verify: bool = True
        ) -> None:

        """Initialize an Sbc object.

        Getting and setting an access token for the object is done implicitly.
        
        Args:
            user: A user name with admin privileges.
            passwd: The admin user password.
            host: The hostname or ip-address of the Session Border Controller
            api_version: Supported REST API version. The documentation uses
                v1.1 in its examples. We'll stick to that.
            request_timeout: The timeout for API calls. API calls that time out
                raise a requests.exceptions.RequestException.
            ssl_warnings: Enable or disable verbose SSL related warnings.
            verify: Enable or disable verification of the SBC certificate.
                Disabling certificate verification results in verbose SSL
                warnings on the concole. You can suppress those by passing
                ssl_warnings=False.
        """
        self.user = user
        self.passwd = passwd
        self.host = host
        self.api_version = api_version
        self._session = requests.Session()
        if verify:
            module_path = os.path.abspath(__file__)
            cert_path = os.path.dirname(module_path)
            self._session.verify = cert_path + "/letsencrypt.pem"
        else:
            self._session.verify = False
        if not ssl_warnings:
            requests.packages.urllib3.disable_warnings(
                category=InsecureRequestWarning
            )
        self._request_timeout = request_timeout

        self._get_token()

    def _print_response_code(self, r: requests.Response, text: bool = True):
        """Print the response code and reason to the console.

        Args:
            r: A requests.Response object
            text: Enable or disable printing the response text
        """

        print("Response Code: {code}".format(code=r.status_code))
        print("Reason: {reason}".format(reason=r.reason))
        if text: print(r.text)

    @property
    def _base_url(self):
        return "https://{sbc}/rest/{api_version}".format(
            sbc=self.host, api_version=self.api_version
        )

    @property
    def _token_url(self):
        return "{base}/auth/token".format(base=self._base_url)

    @property
    def _status_url(self):
        return "{base}/system/status".format(base=self._base_url)

    @property
    def _reboot_url(self):
        return "{base}/admin/reboot".format(base=self._base_url)

    @property
    def _switchover_url(self):
        return "{base}/admin/switchover".format(base=self._base_url)

    @property
    def _supportedversion_url(self):
        return "https://{sbc}/rest/api/supportedversions".format(
            sbc=self.host
        )

    # Configuration endpoints

    @property
    def _lock_url(self):
        return "{base}/configuration/lock".format(base=self._base_url)
    
    @property
    def _unlock_url(self):
        return "{base}/configuration/unlock".format(base=self._base_url)

    @property
    def _element_types_meta_data_url(self):
        url = "{base}/configuration/elementTypes".format(base=self._base_url)
        url += "/metadata?elementType="
        return url

    @property
    def _config_elements_url(self):
        return "{base}/configuration/configElements".format(
            base=self._base_url
        )

    @property
    def _verify_config_url(self):
        return "{base}/configuration/management?action=verify".format(
            base=self._base_url
        )

    @property
    def _save_config_url(self):
        return "{base}/configuration/management?action=save".format(
            base=self._base_url
        )

    @property
    def _activate_config_url(self):
        return "{base}/configuration/management?action=activate".format(
            base=self._base_url
        )

    # Statistics endpoints

    @property
    def _global_sessions_url(self):
        return "{base}/statistics/kpis?type=globalSessions".format(
            base=self._base_url
        )


    def _get_token(self) -> None:
        """Get and set an access token.

        Get an access token and save it for subsequent API calls.
        The access token is incorporated in the Authorization header for
        subsequent API calls.
        
        N.B:
            Access tokens are valid for 10 minutes.

        Raises:
            requests.exceptions.RequestException: The API request failed for
                some reason.
            Exception("Failed to get a token!"): The API request returned a
                status code other than a 200 Ok.
        """

        msg = "Get a token from {}: ".format(self.host)

        headers = self._accept_header

        creds = "{user}:{passwd}".format(user=self.user, passwd=self.passwd)
        creds = creds.encode('utf-8')
        creds_b64_bytestr = base64.encodebytes(creds).strip()
        creds_b64 = creds_b64_bytestr.decode('utf-8')
        self._auth_header = { "Authorization": "Basic " + creds_b64 }

        headers.update(self._auth_header)
        try:
            r = self._session.post(
                self._token_url, headers=headers,
                timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg += "Nok!"
            print(msg)
            raise e
        if r.status_code ==200:
            msg += "Ok!"
            print(msg)
        else:
            msg += "Nok! Status code = {}, Reason = {}".format(
                r.status_code, r.reason
            )
            print(msg)
            raise Exception("Failed to get a token!")
        tree = etree.fromstring(r.text.encode())
        self._token = tree.xpath("//accessToken")[0].text
        self._token_header = {
            "Authorization": "Bearer " + self._token
        }
        self._request_headers = self._accept_header
        self._request_headers.update(self._token_header)

    @property
    def role(self) -> Union[str, bool]:
        """Get the role of a Session Border Controller.
        
        Returns:
            str: This can be either 'standalone', 'active' or 'standby'.
                You can use this in an HA setup where configuration is only
                allowed on the active SBC.
            False: A requests.exceptions.RequestException occured, indicating
                that the API request failed for some reason.
        """

        msg = "Get role: "

        try:
            r = self._session.get(
                self._status_url, headers=self._request_headers,
                timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg += "Nok!"
            print(msg)
            return False
        tree = etree.fromstring(r.text.encode())
        role = tree.xpath("///role")[0].text
        msg += " {}".format(role)
        return role

    def reboot(self) -> bool:
        """Reboot a Session Border Controller.

        N.B.: A reboot takes about 2 min.

        Returns:
            True: The reboot is executed
            False: A requests.exceptions.RequestException occured, indicating
                that the API request failed for some reason.
        """

        msg = "Reboot: "

        try:
            r = self._session.post(
                self._reboot_url, headers=self._request_headers,
                timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg += "Nok!"
            print(msg)
            return False

        tree = etree.fromstring(r.text.encode())
        link = tree.xpath("////link")[0].text
        print(link)
        return True

    def switchover(self) -> bool:
        """Switch the active Session Border Controller in an HA setup.

        Takes about 5 secs.

        Returns:
            True: The switch over is executed.
            False: A requests.exceptions.RequestException occured, indicating
                that the API request failed for some reason.
        """

        msg = "Switchover: "

        try:
            r = self._session.post(
                self._switchover_url, headers=self._request_headers,
                timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg += "Nok!"
            print(msg)
            return False
        if r.status_code == 204:
            msg += "Ok!"
            print(msg)
            return True
        else:
            msg += "Nok! Status code = {}, Reason = {}".format(
                r.status_code, r.reason
            )
            print(msg)
            return False

    @property
    def supported_rest_api_versions(self) -> "list[str]":
        """Returns a list of supported API versions."""

        versions = list()
        r = self._session.get(
            self._supportedversion_url, headers=self._token_header
        )
        tree = etree.fromstring(r.text.encode())
        latest_version = tree.xpath("///latestVersion")[0].text
        other_versions = tree.xpath("////version")
        for version in other_versions:
            versions.append(version.text)
        versions.append(latest_version)
        return versions

    # Statistics

    @property
    def global_cps(self) -> str:
        """Returns the global calls per second."""

        r = self._session.get(
            self._global_sessions_url, headers=self._request_headers
        )
        tree = etree.fromstring(r.text.encode())
        cps = tree.xpath("///sysGlobalCPS")[0].text
        return cps

    @property
    def global_con_sessions(self) -> str:
        """Returns the global number of connected sessions."""

        r = self._session.get(
            self._global_sessions_url, headers=self._request_headers
        )
        tree = etree.fromstring(r.text.encode())
        con_sessions = tree.xpath("///sysGlobalConSessions")[0].text
        return con_sessions

    # Configuration

    def config_element_key_attributes(self, element_type: str) -> "list[str]":
        """Get the key attributes of a configuration element.
        
        A helper method. To update a configuration element you need the
        key attribute(s) that uniquely identifies it.

        Args:
            element_type: A configuration element type. E.g., session-group,
                local-policy...

        Returns:
            A list of a configuration element's key attributes.
        """

        url = self._element_types_meta_data_url + element_type
        r = self._session.get(
            url, headers=self._request_headers
        )
        tree = etree.fromstring(r.text.encode())
        metadatas = tree.xpath("/response/data/attributeMetadata")
        key_attributes = list()
        for metadata in metadatas:
            name = metadata.xpath("name")[0].text
            key = metadata.xpath("key")[0].text
            if key == 'true':
                key_attributes.append(name)
        return key_attributes

    def get_config_elements(self, element_type: str, key_attribs: str = None
                            ) -> None:
        """Get one or more configuration element instances.

        A helper method. Prints the configuration element instances to console.
        Example for key_attributes you pass: '&name1=value1&name2=value2'

        Args:
            element_type: The element type. E.g., session-group, local-policy
            key_attribs: String of query parameters that represent the key
                attributes. E.g, &name1=value1&name2=value2. The string MUST
                start with an &
        """

        url = self._config_elements_url + "?"
        url += "elementType=" + element_type + "&running=true"
        if key_attribs:
            url += key_attribs

        r = self._session.get(
            url, headers=self._request_headers
        )
        print(r.text)

    def lock(self) -> bool:
        """Lock the configuration.

        Returns:
            True: The lock operation executed.
            False: A requests.exceptions.RequestException occured, indicating
                that the API request failed for some reason.
        """

        msg = "Lock config.: "

        try:
            r = self._session.post(
                self._lock_url, headers=self._request_headers,
                timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg += "Nok!"
            print(msg)
            return False
        if r.status_code == 204:
            msg += "Ok!"
            print(msg)
            return True
        else:
            msg += "Nok! Status code = {}. Reason = {}".format(
                r.status_code, r.reason
            )
            print(msg)
            return False

    def unlock(self) -> bool:
        """Unlock the configuration.

        Returns:
            True: The unlock operation executed.
            False: A requests.exceptions.RequestException occured, indicating
                that the API request failed for some reason.        
        """

        msg = "Unlock config.: "

        try:
            r = self._session.post(
                self._unlock_url, headers=self._request_headers,
                timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg += "Nok!"
            print(msg)
            return False
        if r.status_code == 204:
            msg += "Ok!"
            print(msg)
            return True
        else:
            msg += "Nok! Status code = {}. Reason = {}".format(
                r.status_code, r.reason
            )
            print(msg)
            return False            

    def update_config_element(self, xml_str: str) -> bool:
        """Update a configuration element.

        To identify a configuration element you need to set the key attributes
        in xml_str. [Also see self.config_element_key_attributes()]

        Args:
            xml_str:

        Returns:
            True: The configuration element was updated
            False: A status code other than 200 Ok was returned or a
                requests.exceptions.RequestException occured.
        """

        msg = "Update config. element: "

        try:
            r = self._session.put(
                self._config_elements_url, headers=self._token_header,
                data=xml_str, timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg += "Nok!"
            print(msg)
            return False
        if r.status_code == 200:
            msg += "Ok!"
            print(msg)
            return True
        else:
            msg += "Nok! Status code = {}. Reason = {}".format(
                r.status_code, r.reason
            )
            print(msg)
            return False  

    def add_config_element(self, xml_str: str) -> bool:
        """Add a configuration element.

        To identify a configuration element you need to set the key attributes
        in xml_str. [Also see self.config_element_key_attributes()]

        Args:
            xml_str:

        Returns:
            True: The configuration element was added
            False: A status code other than 200 Ok was returned or a
                requests.exceptions.RequestException occured.
        """

        msg = "Add config. element: "

        try:
            r = self._session.post(
                self._config_elements_url, headers=self._token_header,
                data=xml_str, timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg += "Nok!"
            print(msg)
            return False
        if r.status_code == 200:
            msg += "Ok!"
            print(msg)
            return True
        else:
            msg += "Nok! Status code = {}. Reason = {}".format(
                r.status_code, r.reason
            )
            print(msg)
            return False  

    def delete_config_elements(self, element_type: str, key_attribs: str = None
                            ) -> None:
        """Delete one configuration element instances.

        Delete the configuration element.
        Example for key_attributes you pass: '&name1=value1&name2=value2'

        Args:
            element_type: The element type. E.g., session-group, local-policy
            key_attribs: String of query parameters that represent the key
                attributes. E.g, &name1=value1&name2=value2. The string MUST
                start with an &
        """

        msg = "Delete config. element: "

        try:
            url = self._config_elements_url + "?"
            url += "elementType=" + element_type
            if key_attribs:
                url += key_attribs

            r = self._session.delete(
                url, headers=self._request_headers
            )
            print(r.text)
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg += "Nok!"
            print(msg)
            return False
        if r.status_code == 204:
            msg += "Ok!"
            print(msg)
            return True
        else:
            msg += "Nok! Status code = {}. Reason = {}".format(
                r.status_code, r.reason
            )
            print(msg)
            return False  

    def _verify_config_status(self, r:requests.Response) -> bool:
        """Return the status of the verify configuration operation."""

        if r.status_code != 200:
            self._print_response_code(r)
            return False
        tree = etree.fromstring(r.text.encode())
        operation = tree.xpath(
            "/response/data/operationState/operation"
        )[0].text
        status = tree.xpath("/response/data/operationState/status")[0].text
        msg = "Operation: {}, Status: {}".format(operation, status)
        print(msg)                
        if operation == "verify" and status == "success":
            return True
        else:
            return False                       

    def _verify_config(self) -> bool:
        """Verify the configuration.

        Returns:
            True: Verification of the configuration was succesful.
            False: Verification of the confguration was NOT successful or a
                requests.exceptions.RequestException occured indicating the
                API request failed for some reason.
        """

        try:
            r = self._session.put(
                self._verify_config_url, headers=self._request_headers,
                timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg +="Nok!"
            print(msg)
            return False

        tree = etree.fromstring(r.text.encode())
        link = tree.xpath("/response/links/link")[0].text

        try:                  
            polling2.poll(
                self._session.get, step=3, args=(link,),
                kwargs={
                    'headers': self._request_headers,
                    'timeout': self._request_timeout
                },
                timeout=15,
                check_success=self._verify_config_status
            )
            return True
        except Exception as e:
            print(e.args)
            msg +="Nok!"
            print(msg)            
            return False

    def _save_config_status(self, r:requests.Response) -> bool:
        """Return the status of the save configuration operation."""

        if r.status_code != 200:
            self._print_response_code(r)
            return False
        tree = etree.fromstring(r.text.encode())
        operation = tree.xpath(
            "/response/data/operationState/operation"
        )[0].text
        status = tree.xpath("/response/data/operationState/status")[0].text
        msg = "Operation: {}, Status: {}".format(operation, status)
        print(msg)                
        if operation == "save" and status == "success":
            return True
        else:
            return False            

    def _save_config(self) -> bool:
        """Save the configuration."""

        msg = "Save config.: "

        try:
            r = self._session.put(
                self._save_config_url, headers=self._request_headers,
                timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg +="Nok!"
            print(msg)            
            return False

        tree = etree.fromstring(r.text.encode())
        link = tree.xpath("/response/links/link")[0].text

        try:
            polling2.poll(
                self._session.get, step=2, args=(link,),
                kwargs={
                    'headers': self._request_headers,
                    'timeout': self._request_timeout
                },
                timeout=15,
                check_success=self._save_config_status
            )
            return True            
        except Exception as e:
            print(e.args)
            msg +="Nok!"
            print(msg)            
            return False

    def _activate_config_status(self, r:requests.Response):
        """Return the status of the activate configuration operation."""

        if r.status_code != 200:
            self._print_response_code(r)
            return False
        tree = etree.fromstring(r.text.encode())
        operation = tree.xpath(
            "/response/data/operationState/operation"
        )[0].text
        status = tree.xpath("/response/data/operationState/status")[0].text
        msg = "Operation: {}, Status: {}".format(operation, status)
        print(msg)                
        if operation == "activate" and status == "success":
            return True
        else:
            return False            

    def activate_config(self) -> bool:
        """Activate the configuration.

        This will verify and save the configuration first
        """

        msg = "Activate config.: "        

        if (not self._verify_config()) or (not self._save_config()):
            msg +="Nok!"
            print(msg)            
            return False

        try:
            r = self._session.post(
                self._activate_config_url, headers=self._request_headers,
                timeout=self._request_timeout
            )
        except requests.exceptions.RequestException as e:
            print(e.args)
            msg +="Nok!"
            print(msg)            
            return False

        tree = etree.fromstring(r.text.encode())
        link = tree.xpath("/response/links/link")[0].text

        try:
            r = self._session.get(
                link, headers=self._request_headers,
                timeout=self._request_timeout
            )
            polling2.poll(
                self._session.get, step=2, args=(link,),
                kwargs={
                    'headers': self._request_headers,
                    'timeout': self._request_timeout
                },
                timeout=15,
                check_success=self._activate_config_status
            )
            return True            
        except Exception as e:
            print(e.args)
            msg +="Nok!"
            print(msg)            
            return False
