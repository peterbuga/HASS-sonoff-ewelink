# The domain of your component. Should be equal to the name of your component.
import logging, time, hmac, hashlib, random, base64, json, socket, requests, re
import voluptuous as vol

from datetime import timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util.async_ import run_coroutine_threadsafe
from homeassistant.helpers import discovery
from homeassistant.helpers import config_validation as cv
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP, CONF_SCAN_INTERVAL,
    CONF_EMAIL, CONF_PASSWORD, CONF_USERNAME,
    HTTP_MOVED_PERMANENTLY, HTTP_BAD_REQUEST, 
    HTTP_UNAUTHORIZED, HTTP_NOT_FOUND)
# from homeassistant.util import Throttle

CONF_API_REGION     = 'api_region'
CONF_GRACE_PERIOD   = 'grace_period'

SCAN_INTERVAL = timedelta(seconds=60)
DOMAIN = "sonoff"

REQUIREMENTS = ['uuid', 'websocket-client']

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Exclusive(CONF_USERNAME, CONF_PASSWORD): cv.string, 
        vol.Exclusive(CONF_EMAIL, CONF_PASSWORD): cv.string,

        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_API_REGION, default='eu'): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_GRACE_PERIOD, default=600): cv.positive_int
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)

def gen_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

async def async_setup(hass, config):
    """Set up the eWelink/Sonoff component."""

    SCAN_INTERVAL   = config.get(DOMAIN, {}).get(CONF_SCAN_INTERVAL,'')

    _LOGGER.debug("Create the main object")

    # hass.data[DOMAIN] = Sonoff(hass, email, password, api_region, grace_period)
    hass.data[DOMAIN] = Sonoff(config)

    for component in ['switch', 'sensor']:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    def update_devices(event_time):
        """Refresh"""     
        _LOGGER.debug("Updating devices status")

        # @REMINDER figure it out how this works exactly and/or replace it with websocket
        run_coroutine_threadsafe( hass.data[DOMAIN].async_update(), hass.loop)

    async_track_time_interval(hass, update_devices, SCAN_INTERVAL)

    return True

class Sonoff():
    # def __init__(self, hass, email, password, api_region, grace_period):
    def __init__(self, config):

        # get username & password from configuration.yaml
        email           = config.get(DOMAIN, {}).get(CONF_EMAIL,'')
        username        = config.get(DOMAIN, {}).get(CONF_USERNAME,'')
        password        = config.get(DOMAIN, {}).get(CONF_PASSWORD,'')
        api_region      = config.get(DOMAIN, {}).get(CONF_API_REGION,'')
        grace_period    = config.get(DOMAIN, {}).get(CONF_GRACE_PERIOD,'')

        if email and not username: # backwards compatibility
            self._username = email.strip()

        else: # already validated by voluptous
            self._username      = username.strip()

        self._password      = password
        self._api_region    = api_region
        self._wshost        = None

        self._skipped_login = 0
        self._grace_period  = timedelta(seconds=grace_period)

        self._user_apikey   = None
        self._devices       = []
        self._ws            = None

        self.do_login()

    def do_login(self):
        import uuid

        # reset the grace period
        self._skipped_login = 0
        
        app_details = {
            'password'  : self._password,
            'version'   : '6',
            'ts'        : int(time.time()),
            'nonce'     : gen_nonce(15),
            'appid'     : 'oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq',
            'imei'      : str(uuid.uuid4()),
            'os'        : 'iOS',
            'model'     : 'iPhone10,6',
            'romVersion': '11.1.2',
            'appVersion': '3.5.3'
        }

        if re.match(r'[^@]+@[^@]+\.[^@]+', self._username):
            app_details['email'] = self._username
        else:
            app_details['phoneNumber'] = self._username

        decryptedAppSecret = b'6Nz4n0xA8s8qdxQf2GqurZj2Fs55FUvM'

        hex_dig = hmac.new(
            decryptedAppSecret, 
            str.encode(json.dumps(app_details)), 
            digestmod=hashlib.sha256).digest()
        
        sign = base64.b64encode(hex_dig).decode()

        self._headers = {
            'Authorization' : 'Sign ' + sign,
            'Content-Type'  : 'application/json;charset=UTF-8'
        }

        r = requests.post('https://{}-api.coolkit.cc:8080/api/user/login'.format(self._api_region), 
            headers=self._headers, json=app_details)

        resp = r.json()

        # get a new region to login
        if 'error' in resp and 'region' in resp and resp['error'] == HTTP_MOVED_PERMANENTLY:
            self._api_region    = resp['region']

            _LOGGER.warning("found new region: >>> %s <<< (you should change api_region option to this value in configuration.yaml)", self._api_region)

            # re-login using the new localized endpoint
            self.do_login()
            return

        elif 'error' in resp and resp['error'] in [HTTP_NOT_FOUND, HTTP_BAD_REQUEST]:
            # (most likely) login with +86... phone number and region != cn
            if '@' not in self._username and self._api_region != 'cn':
                self._api_region    = 'cn'
                self.do_login()

            else:
                _LOGGER.error("Couldn't authenticate using the provided credentials!")

            return

        self._bearer_token  = resp['at']
        self._user_apikey   = resp['user']['apikey']
        self._headers.update({'Authorization' : 'Bearer ' + self._bearer_token})

        # get the websocket host
        if not self._wshost:
            self.set_wshost()

        self.update_devices() # to get the devices list 

    def set_wshost(self):
        r = requests.post('https://%s-disp.coolkit.cc:8080/dispatch/app' % self._api_region, headers=self._headers)
        resp = r.json()

        if 'error' in resp and resp['error'] == 0 and 'domain' in resp:
            self._wshost = resp['domain']
            _LOGGER.info("Found websocket address: %s", self._wshost)
        else:
            raise Exception('No websocket domain')

    def is_grace_period(self):
        grace_time_elapsed = self._skipped_login * int(SCAN_INTERVAL.total_seconds()) 
        grace_status = grace_time_elapsed < int(self._grace_period.total_seconds())

        if grace_status:
            self._skipped_login += 1

        return grace_status

    def update_devices(self):

        # the login failed, nothing to update
        if not self._wshost:
            return []

        # we are in the grace period, no updates to the devices
        if self._skipped_login and self.is_grace_period():          
            _LOGGER.info("Grace period active")            
            return self._devices

        r = requests.get('https://{}-api.coolkit.cc:8080/api/user/device'.format(self._api_region), 
            headers=self._headers)

        resp = r.json()
        if 'error' in resp and resp['error'] in [HTTP_BAD_REQUEST, HTTP_UNAUTHORIZED]:
            # @IMPROVE add maybe a service call / switch to deactivate sonoff component
            if self.is_grace_period():
                _LOGGER.warning("Grace period activated!")

                # return the current (and possible old) state of devices
                # in this period any change made with the mobile app (on/off) won't be shown in HA
                return self._devices

            _LOGGER.info("Re-login component")
            self.do_login()

        self._devices = r.json()
        return self._devices

    def get_devices(self, force_update = False):
        if force_update: 
            return self.update_devices()

        return self._devices

    def get_device(self, deviceid):
        for device in self.get_devices():
            if 'deviceid' in device and device['deviceid'] == deviceid:
                return device

    def get_bearer_token(self):
        return self._bearer_token

    def get_user_apikey(self):
        return self._user_apikey

    # async def async_get_devices(self):
    #     return self.get_devices()

    async def async_update(self):
        # devs = await self.async_get_devices()
        devices = self.update_devices()

    def _get_ws(self):
        """Check if the websocket is setup and connected."""
        try:
            create_connection
        except:
            from websocket import create_connection

        if self._ws is None:
            try:
                self._ws = create_connection(('wss://{}:8080/api/ws'.format(self._wshost)), timeout=10)

                payload = {
                    'action'    : "userOnline",
                    'userAgent' : 'app',
                    'version'   : 6,
                    'nonce'     : gen_nonce(15),
                    'apkVesrion': "1.8",
                    'os'        : 'ios',
                    'at'        : self.get_bearer_token(),
                    'apikey'    : self.get_user_apikey(),
                    'ts'        : str(int(time.time())),
                    'model'     : 'iPhone10,6',
                    'romVersion': '11.1.2',
                    'sequence'  : str(time.time()).replace('.','')
                }

                self._ws.send(json.dumps(payload))
                wsresp = self._ws.recv()
                # _LOGGER.error("open socket: %s", wsresp)

            except (socket.timeout, ConnectionRefusedError, ConnectionResetError):
                _LOGGER.error('failed to create the websocket')
                self._ws = None

        return self._ws
        
    def switch(self, new_state, deviceid, outlet):
        """Switch on or off."""

        # we're in the grace period, no state change
        if self._skipped_login:
            _LOGGER.info("Grace period, no state change")
            return (not new_state)

        self._ws = self._get_ws()
        
        if not self._ws:
            _LOGGER.warning('invalid websocket, state cannot be changed')
            return (not new_state)

        # convert from True/False to on/off
        if isinstance(new_state, (bool)):
            new_state = 'on' if new_state else 'off'

        device = self.get_device(deviceid)

        if outlet is not None:
            _LOGGER.debug("Switching `%s - %s` on outlet %d to state: %s", \
                device['deviceid'], device['name'] , (outlet+1) , new_state)
        else:
            _LOGGER.debug("Switching `%s` to state: %s", deviceid, new_state)

        if not device:
            _LOGGER.error('unknown device to be updated')
            return False

        # the payload rule is like this:
        #   normal device (non-shared) 
        #       apikey      = login apikey (= device apikey too)
        #
        #   shared device
        #       apikey      = device apikey
        #       selfApiKey  = login apikey (yes, it's typed corectly selfApikey and not selfApiKey :|)

        if outlet is not None:
            params = { 'switches' : device['params']['switches'] }
            params['switches'][outlet]['switch'] = new_state

        else:
            params = { 'switch' : new_state }

        payload = {
            'action'        : 'update',
            'userAgent'     : 'app',
            'params'        : params,
            'apikey'        : device['apikey'],
            'deviceid'      : str(deviceid),
            'sequence'      : str(time.time()).replace('.',''),
            'controlType'   : device['params']['controlType'] if 'controlType' in device['params'] else 4,
            'ts'            : 0
        }

        # this key is needed for a shared device
        if device['apikey'] != self.get_user_apikey():
            payload['selfApikey'] = self.get_user_apikey()

        self._ws.send(json.dumps(payload))
        wsresp = self._ws.recv()
        # _LOGGER.debug("switch socket: %s", wsresp)
        
        self._ws.close() # no need to keep websocket open (for now)
        self._ws = None

        # set also te pseudo-internal state of the device until the real refresh kicks in
        for idx, device in enumerate(self._devices):
            if device['deviceid'] == deviceid:
                if outlet is not None:
                    self._devices[idx]['params']['switches'][outlet]['switch'] = new_state
                else:
                    self._devices[idx]['params']['switch'] = new_state


        # @TODO add some sort of validation here, maybe call the devices status 
        # only IF MAIN STATUS is done over websocket exclusively

        return new_state

class SonoffDevice(Entity):
    """Representation of a Sonoff entity"""

    def __init__(self, hass, device):
        """Initialize the device."""

        self._outlet        = None
        self._sensor        = None
        self._state         = None

        self._hass          = hass
        self._deviceid      = device['deviceid']
        self._available     = device['online']

        self._attributes    = {
            'device_id'     : self._deviceid
        }

    def get_device(self):
        for device in self._hass.data[DOMAIN].get_devices():
            if 'deviceid' in device and device['deviceid'] == self._deviceid:
                return device

        return None

    def get_state(self):
        device = self.get_device()

        # Pow & Pow R2:
        if 'power' in device['params']: 
            self._attributes['power'] = device['params']['power']
        
        # Pow R2 only:
        if 'current' in device['params']: 
            self._attributes['current'] = device['params']['current']
        if 'voltage' in device['params']: 
            self._attributes['voltage'] = device['params']['voltage']

        # TH10/TH16
        if 'currentHumidity' in device['params'] and device['params']['currentHumidity'] != "unavailable":
            self._attributes['humidity'] = device['params']['currentHumidity']
        if 'currentTemperature' in device['params'] and device['params']['currentTemperature'] != "unavailable":
            self._attributes['temperature'] = device['params']['currentTemperature']

        if 'rssi' in device['params']:
            self._attributes['rssi'] = device['params']['rssi']            

        # the device has more switches
        if self._outlet is not None:
            return device['params']['switches'][self._outlet]['switch'] == 'on' if device else False

        else:
            return device['params']['switch'] == 'on' if device else False

    def get_available(self):
        device = self.get_device()

        if self._outlet is not None and device:
            # this is a particular case where the state of the switch is reported as `keep` 
            # and i want to track this visualy using the unavailability status in history panel
            if device['online'] and device['params']['switches'][self._outlet]['switch'] == 'keep':
                return False

        return device['online'] if device else False

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def available(self):
        """Return true if device is online."""
        return self.get_available()

    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update device state."""

        # we don't update here because there's 1 single thread that can be active at anytime
        # i.e. eWeLink API allows only 1 active session
        pass

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return self._attributes
