# The domain of your component. Should be equal to the name of your component.
import logging, time, hmac, hashlib, random, base64, json, socket, requests, re, threading
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

import websocket

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

async def async_setup(hass, config):
    """Setup the eWelink/Sonoff component."""

    SCAN_INTERVAL   = config.get(DOMAIN, {}).get(CONF_SCAN_INTERVAL,'')

    _LOGGER.debug("Create the main object")

    hass.data[DOMAIN] = Sonoff(hass, config)
    if hass.data[DOMAIN].get_wshost(): # make sure login was successful

        for component in ['switch','sensor']:
            discovery.load_platform(hass, component, DOMAIN, {}, config)
        hass.bus.async_listen('sonoff_state', hass.data[DOMAIN].state_listener)
	
        # close the websocket when HA stops
        # hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, hass.data[DOMAIN].get_ws().close())

        def update_devices(event_time):
            run_coroutine_threadsafe( hass.data[DOMAIN].async_update(), hass.loop)

        async_track_time_interval(hass, update_devices, SCAN_INTERVAL)

    return True

class Sonoff():
    def __init__(self, hass, config):
        self._hass          = hass

        # get config details from from configuration.yaml
        self._email         = config.get(DOMAIN, {}).get(CONF_EMAIL,'')
        self._username      = config.get(DOMAIN, {}).get(CONF_USERNAME,'')
        self._password      = config.get(DOMAIN, {}).get(CONF_PASSWORD,'')
        self._api_region    = config.get(DOMAIN, {}).get(CONF_API_REGION,'')
        self._grace_period  = timedelta(seconds=config.get(DOMAIN, {}).get(CONF_GRACE_PERIOD,''))

        if self._email and not self._username: # backwards compatibility
            self._username = self._email.strip()

        self._skipped_login = 0
        self._grace_period  = timedelta(seconds=config.get(DOMAIN, {}).get(CONF_GRACE_PERIOD,''))

        self._devices       = []
        self._user_apikey   = None
        self._ws            = None
        self._wshost        = None

        self.do_login()
            
    def do_login(self):
        import uuid

        # reset the grace period
        self._skipped_login = 0
        
        app_details = {
            'password'  : self._password,
            'version'   : '6',
            'ts'        : int(time.time()),
            'nonce'     : ''.join([str(random.randint(0, 9)) for i in range(15)]),
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
            self._wshost        = None

            _LOGGER.warning("found new region: >>> %s <<< (you should change api_region option to this value in configuration.yaml)", self._api_region)

            # re-login using the new localized endpoint
            self.do_login()
            return

        elif 'error' in resp and resp['error'] in [HTTP_NOT_FOUND, HTTP_BAD_REQUEST]:
            # (most likely) login with +86... phone number and region != cn
            if '@' not in self._username and self._api_region != 'cn':
                self._api_region = 'cn'
                self.do_login()
                return
            
            else:
                _LOGGER.error("Couldn't authenticate using the provided credentials!")

        else:
            if 'at' not in resp:
                _LOGGER.error('Login failed! Please check credentials!')
                return

            self._bearer_token  = resp['at']
            self._user_apikey   = resp['user']['apikey']
            self._headers.update({'Authorization' : 'Bearer ' + self._bearer_token})

            self.update_devices() # to write the devices list 

            # get/find the websocket host
            if not self._wshost:
                self.set_wshost()

            if self.get_wshost() is not None:
                self.thread = threading.Thread(target=self.init_websocket)
                self.thread.daemon = True
                self.thread.start()

    def set_wshost(self):
        r = requests.post('https://%s-disp.coolkit.cc:8080/dispatch/app' % self._api_region, headers=self._headers)
        resp = r.json()

        if 'error' in resp and resp['error'] == 0 and 'domain' in resp:
            self._wshost = resp['domain']
            _LOGGER.info("Found websocket address: %s", self._wshost)
        else:
            _LOGGER.error("Couldn't find a valid websocket host, abording Sonoff init")

    async def state_listener(self, event):
        if not self.get_ws().connected:
            _LOGGER.error('websocket is not connected') 
            return           

        _LOGGER.debug('received state event change from: %s' % event.data['deviceid'])

        new_state = event.data['state']

        # convert from True/False to on/off
        if isinstance(new_state, (bool)):
            new_state = 'on' if new_state else 'off'

        device = self.get_device(event.data['deviceid'])
        outlet = event.data['outlet']

        if outlet is not None:
            _LOGGER.debug("Switching `%s - %s` on outlet %d to state: %s", \
                device['deviceid'], device['name'] , (outlet+1) , new_state)
        else:
            _LOGGER.debug("Switching `%s` to state: %s", device['deviceid'], new_state)

        if not device:
            _LOGGER.error('unknown device to be updated')
            return False
        
        """
        the payload rule is like this:
          normal device (non-shared) 
              apikey      = login apikey (= device apikey too)
        
          shared device
              apikey      = device apikey
              selfApiKey  = login apikey (yes, it's typed corectly selfApikey and not selfApiKey :|)
        """
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
            'deviceid'      : str(device['deviceid']),
            'sequence'      : str(time.time()).replace('.',''),
            'controlType'   : device['params']['controlType'] if 'controlType' in device['params'] else 4,
            'ts'            : 0
        }

        # this key is needed for a shared device
        if device['apikey'] != self.get_user_apikey():
            payload['selfApikey'] = self.get_user_apikey()

        self.get_ws().send(json.dumps(payload))

        # set also te pseudo-internal state of the device until the real refresh kicks in
        for idxd, dev in enumerate(self._devices):
            if dev['deviceid'] == device['deviceid']:
                if outlet is not None:
                    self._devices[idxd]['params']['switches'][outlet]['switch'] = new_state
                else:
                    self._devices[idxd]['params']['switch'] = new_state

    def init_websocket(self):
        # keep websocket open indefinitely
        while True:
            _LOGGER.debug('(re)init websocket')
            self._ws = WebsocketListener(sonoff=self, on_message=self.on_message, on_error=self.on_error)

            try:
                # 145 interval is defined by the first websocket response after login
                self._ws.run_forever(ping_interval=145)
            finally:
                self._ws.close()

    def on_message(self, *args):
        data = args[-1] # to accomodate the weird behaviour where the function receives 2 or 3 args

        _LOGGER.debug('websocket msg: %s', data)

        data = json.loads(data)
        if 'action' in data and data['action'] == 'update' and 'params' in data:
            if 'switch' in data['params'] or 'switches' in data['params']:
                for idx, device in enumerate(self._devices):
                    if device['deviceid'] == data['deviceid']:
                        self._devices[idx]['params'] = data['params']

                        if 'switches' in data['params']:
                            for switch in data['params']['switches']:
                                self.set_entity_state(data['deviceid'], data['params']['switch'], switch['outlet'])    
                        else:
                            self.set_entity_state(data['deviceid'], data['params']['switch'])

                        break # do not remove

    def on_error(self, *args):
        error = args[-1] # to accomodate the case when the function receives 2 or 3 args
        _LOGGER.error('websocket error: %s' % str(error))

    def is_grace_period(self):
        grace_time_elapsed = self._skipped_login * int(SCAN_INTERVAL.total_seconds()) 
        grace_status = grace_time_elapsed < int(self._grace_period.total_seconds())

        if grace_status:
            self._skipped_login += 1

        return grace_status

    def set_entity_state(self, deviceid, state, outlet=None):
        entity_id = 'switch.%s%s' % (deviceid, '_'+str(outlet+1) if outlet is not None else '')
        attr = self._hass.states.get(entity_id).attributes
        self._hass.states.set(entity_id, state, attr)

    def update_devices(self):
        # we are in the grace period, no updates to the devices
        if self._skipped_login and self.is_grace_period():          
            _LOGGER.info("Grace period active")            
            return self._devices

        r = requests.get('https://{}-api.coolkit.cc:8080/api/user/device?lang=en&apiKey={}&getTags=1'.format(self._api_region, self.get_user_apikey()), 
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

    def get_ws(self):
        return self._ws

    def get_wshost(self):
        return self._wshost

    async def async_update(self):
        devices = self.update_devices()  

    def get_outlets(self, device):
        # information found in ewelink app source code
        name_to_outlets = {
            'SOCKET'                : 1,
            'SWITCH_CHANGE'         : 1,
            'GSM_UNLIMIT_SOCKET'    : 1,
            'SWITCH'                : 1,
            'THERMOSTAT'            : 1,
            'SOCKET_POWER'          : 1,
            'GSM_SOCKET'            : 1,
            'POWER_DETECTION_SOCKET': 1,
            'SOCKET_2'              : 2,
            'GSM_SOCKET_2'          : 2,
            'SWITCH_2'              : 2,
            'SOCKET_3'              : 3,
            'GSM_SOCKET_3'          : 3,
            'SWITCH_3'              : 3,
            'SOCKET_4'              : 4,
            'GSM_SOCKET_4'          : 4,
            'SWITCH_4'              : 4,
            'CUN_YOU_DOOR'          : 4
        }

        uiid_to_name = {
            1       : "SOCKET",
            2       : "SOCKET_2",
            3       : "SOCKET_3",
            4       : "SOCKET_4",
            5       : "SOCKET_POWER",
            6       : "SWITCH",
            7       : "SWITCH_2",
            8       : "SWITCH_3",
            9       : "SWITCH_4",
            10      : "OSPF",
            11      : "CURTAIN",
            12      : "EW-RE",
            13      : "FIREPLACE",
            14      : "SWITCH_CHANGE",
            15      : "THERMOSTAT",
            16      : "COLD_WARM_LED",
            17      : "THREE_GEAR_FAN",
            18      : "SENSORS_CENTER",
            19      : "HUMIDIFIER",
            22      : "RGB_BALL_LIGHT",
            23      : "NEST_THERMOSTAT",
            24      : "GSM_SOCKET",
            25      : 'AROMATHERAPY',
            26      : "RuiMiTeWenKongQi",
            27      : "GSM_UNLIMIT_SOCKET",
            28      : "RF_BRIDGE",
            29      : "GSM_SOCKET_2",
            30      : "GSM_SOCKET_3",
            31      : "GSM_SOCKET_4",
            32      : "POWER_DETECTION_SOCKET",
            33      : "LIGHT_BELT",
            34      : "FAN_LIGHT",
            35      : "EZVIZ_CAMERA",
            36      : "SINGLE_CHANNEL_DIMMER_SWITCH",
            38      : "HOME_KIT_BRIDGE",
            40      : "FUJIN_OPS",
            41      : "CUN_YOU_DOOR",
            42      : "SMART_BEDSIDE_AND_NEW_RGB_BALL_LIGHT",
            43      : "",
            44      : "",
            45      : "DOWN_CEILING_LIGHT",
            46      : "AIR_CLEANER",
            49      : "MACHINE_BED",
            51      : "COLD_WARM_DESK_LIGHT",
            52      : "DOUBLE_COLOR_DEMO_LIGHT",
            53      : "ELECTRIC_FAN_WITH_LAMP",
            55      : "SWEEPING_ROBOT",
            56      : "RGB_BALL_LIGHT_4",
            57      : "MONOCHROMATIC_BALL_LIGHT",
            59      : "MUSIC_LIGHT_BELT",
            60      : "NEW_HUMIDIFIER",
            61      : "KAI_WEI_ROUTER",
            62      : "MEARICAMERA",
            66      : "ZIGBEE_MAIN_DEVICE",
            67      : "RollingDoor",
            68      : "KOOCHUWAH",
            1001    : "BLADELESS_FAN",
            1003    : "WARM_AIR_BLOWER",
            1000    : "ZIGBEE_SINGLE_SWITCH",
            1770    : "ZIGBEE_TEMPERATURE_SENSOR",
            1256    : "ZIGBEE_LIGHT"
        }

        if device['uiid'] in uiid_to_name.keys() and \
            uiid_to_name[device['uiid']] in name_to_outlets.keys():
            return name_to_outlets[uiid_to_name[device['uiid']]]

        return None
  
class WebsocketListener(threading.Thread, websocket.WebSocketApp):
    def __init__(self, sonoff, on_message=None, on_error=None):
        self._sonoff        = sonoff

        threading.Thread.__init__(self)
        websocket.WebSocketApp.__init__(self, 'wss://{}:8080/api/ws'.format(self._sonoff.get_wshost()),
                                        on_open=self.on_open,
                                        on_error=on_error,
                                        on_message=on_message,
                                        on_close=self.on_close)

        self.connected = False
        self.last_update = time.time()

    def on_open(self, *args):
        self.connected = True
        self.last_update = time.time()

        payload = {
            'action'    : "userOnline",
            'userAgent' : 'app',
            'version'   : 6,
            'nonce'     : ''.join([str(random.randint(0, 9)) for i in range(15)]),
            'apkVesrion': "1.8",
            'os'        : 'ios',
            'at'        : self._sonoff.get_bearer_token(),
            'apikey'    : self._sonoff.get_user_apikey(),
            'ts'        : str(int(time.time())),
            'model'     : 'iPhone10,6',
            'romVersion': '11.1.2',
            'sequence'  : str(time.time()).replace('.','')
        }

        self.send(json.dumps(payload))

    def on_close(self, *args):
        _LOGGER.debug('websocket closed')
        self.connected = False

    def run_forever(self, sockopt=None, sslopt=None, ping_interval=0, ping_timeout=None):
        websocket.WebSocketApp.run_forever( self, 
                                            sockopt=sockopt, 
                                            sslopt=sslopt, 
                                            ping_interval=ping_interval,
                                            ping_timeout=ping_timeout)

class SonoffDevice(Entity):
    """Representation of a Sonoff device"""

    def __init__(self, hass, device):
        """Initialize the device."""

        self._outlet        = None
        self._sensor        = None
        self._state         = None

        self._hass          = hass
        self._deviceid      = device['deviceid']
        self._available     = device['online']

        self._attributes    = {
            'device_id'     : self._deviceid,
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
        # and the websocket will send the state update messages
        pass


    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return self._attributes
