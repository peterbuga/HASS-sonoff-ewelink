# The domain of your component. Should be equal to the name of your component.
import logging, time, hmac, random, base64, json, re, threading, hashlib, string
import voluptuous as vol
import asyncio
import aiohttp

from datetime import timedelta
from datetime import datetime

from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import (async_track_time_interval, track_point_in_time)
from homeassistant.helpers import (config_validation as cv, discovery)
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP, CONF_SCAN_INTERVAL,
    CONF_EMAIL, CONF_PASSWORD, CONF_USERNAME,
    HTTP_MOVED_PERMANENTLY, HTTP_BAD_REQUEST,
    HTTP_UNAUTHORIZED, HTTP_NOT_FOUND)
from homeassistant.const import TEMP_CELSIUS

HTTP_NOT_ACCEPTED   = 406

CONF_API_REGION     = 'api_region'
CONF_GRACE_PERIOD   = 'grace_period'
CONF_DEBUG          = 'debug'
CONF_ENTITY_PREFIX  = 'entity_prefix'

DOMAIN              = "sonoff"

SONOFF_SENSORS_MAP = {
    'power'                 : { 'eid' : 'power',        'uom' : 'W',            'icon' : 'mdi:flash-outline' },
    'current'               : { 'eid' : 'current',      'uom' : 'A',            'icon' : 'mdi:current-ac' },
    'voltage'               : { 'eid' : 'voltage',      'uom' : 'V',            'icon' : 'mdi:power-plug' },
    'dusty'                 : { 'eid' : 'dusty',        'uom' : 'µg/m3',        'icon' : 'mdi:select-inverse' },
    'light'                 : { 'eid' : 'light',        'uom' : 'lx',           'icon' : 'mdi:car-parking-lights' },
    'noise'                 : { 'eid' : 'noise',        'uom' : 'Db',           'icon' : 'mdi:surround-sound' },

    'currentHumidity'       : { 'eid' : 'humidity',     'uom' : '%',            'icon' : 'mdi:water-percent' },
    'humidity'              : { 'eid' : 'humidity',     'uom' : '%',            'icon' : 'mdi:water-percent' },

    'currentTemperature'    : { 'eid' : 'temperature',  'uom' : TEMP_CELSIUS,   'icon' : 'mdi:thermometer' },
    'temperature'           : { 'eid' : 'temperature',  'uom' : TEMP_CELSIUS,   'icon' : 'mdi:thermometer' }
}

REQUIREMENTS        = ['uuid', 'websocket-client==0.54.0']

import websocket

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Exclusive(CONF_USERNAME, CONF_PASSWORD): cv.string,
        vol.Exclusive(CONF_EMAIL, CONF_PASSWORD): cv.string,

        vol.Required(CONF_PASSWORD): cv.string,

        vol.Optional(CONF_API_REGION, default='eu'): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=timedelta(seconds=600)): cv.time_period,
        vol.Optional(CONF_GRACE_PERIOD, default=600): cv.positive_int,
        vol.Optional(CONF_ENTITY_PREFIX, default=True): cv.boolean,

        vol.Optional(CONF_DEBUG, default=False): cv.boolean
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Setup the eWelink/Sonoff component."""

    _LOGGER.debug("Create the main object")

    hass.data[DOMAIN] = Sonoff(hass, config)

    await hass.data[DOMAIN].do_login()

    if hass.data[DOMAIN].get_wshost(): # make sure login was successful

        for component in ['switch', 'sensor', 'binary_sensor', 'light', 'fan']:
            await discovery.async_load_platform(hass, component, DOMAIN, {}, config)

        hass.bus.async_listen('sonoff_state', hass.data[DOMAIN].state_listener)

        # close the websocket when HA stops
        # hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, hass.data[DOMAIN].get_ws().close())

        async def update_devices(event_time):
            asyncio.run_coroutine_threadsafe( hass.data[DOMAIN].async_update(), hass.loop)

        async_track_time_interval(hass, update_devices, await hass.data[DOMAIN].get_scan_interval())

    return True

class Sonoff():
    def __init__(self, hass, config):

        self._hass          = hass

        # get config details from from configuration.yaml
        self._email         = config.get(DOMAIN, {}).get(CONF_EMAIL,'')
        self._username      = config.get(DOMAIN, {}).get(CONF_USERNAME,'')
        self._password      = config.get(DOMAIN, {}).get(CONF_PASSWORD,'')
        self._api_region    = config.get(DOMAIN, {}).get(CONF_API_REGION,'')
        self._entity_prefix = config.get(DOMAIN, {}).get(CONF_ENTITY_PREFIX,'')
        self._scan_interval = config.get(DOMAIN, {}).get(CONF_SCAN_INTERVAL)

        self._sonoff_debug  = config.get(DOMAIN, {}).get(CONF_DEBUG, False)
        self._sonoff_debug_log = []

        if self._email and not self._username: # backwards compatibility
            self._username = self._email.strip()

        self._skipped_login = 0
        self._grace_period  = timedelta(seconds=config.get(DOMAIN, {}).get(CONF_GRACE_PERIOD,''))

        self._devices       = []
        self._user_apikey   = None
        self._ws            = None
        self._wshost        = None

        self._login_cnt     = 0

        self.write_debug('{}', new=True)

        self.rf2trig       = {} # dict to hold the mapping of rf triggers IDs to their websocket value response
        # lazy to store this in another place for now...
        self.uiid_to_name = {
            1       : "SOCKET",
            2       : "SOCKET_2",
            3       : "SOCKET_3",
            4       : "SOCKET_4",
            5       : "SOCKET_POWER",
            6       : "SWITCH",
            7       : "SWITCH_2",
            8       : "SWITCH_3",
            9       : "SWITCH_4",
            77      : "SWITCH_4",
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

    async def get_scan_interval(self):
        if DOMAIN in self._hass.data and self._hass.data[DOMAIN].get_debug_state():
            self._scan_interval = timedelta(seconds=10)

        elif self._scan_interval < timedelta(seconds=600):
            self._scan_interval = timedelta(seconds=600)

        return self._scan_interval

    def get_debug_state(self):
        return self._sonoff_debug

    def get_entity_prefix(self):
        # if the entities should have `sonoff_` prefixed or not
        # a quick fix between (i-blame-myself) `master` vs. `websocket` implementations
        return self._entity_prefix

    async def do_login(self):

        import uuid

        # reset the grace period
        self._skipped_login = 0

        self._model         = 'iPhone' + random.choice(['6,1', '6,2', '7,1', '7,2', '8,1', '8,2', '8,4', '9,1', '9,2', '9,3', '9,4', '10,1', '10,2', '10,3', '10,4', '10,5', '10,6', '11,2', '11,4', '11,6', '11,8'])
        self._romVersion    = random.choice([
            '10.0', '10.0.2', '10.0.3', '10.1', '10.1.1', '10.2', '10.2.1', '10.3', '10.3.1', '10.3.2', '10.3.3', '10.3.4',
            '11.0', '11.0.1', '11.0.2', '11.0.3', '11.1', '11.1.1', '11.1.2', '11.2', '11.2.1', '11.2.2', '11.2.3', '11.2.4', '11.2.5', '11.2.6', '11.3', '11.3.1', '11.4', '11.4.1',
            '12.0', '12.0.1', '12.1', '12.1.1', '12.1.2', '12.1.3', '12.1.4', '12.2', '12.3', '12.3.1', '12.3.2', '12.4', '12.4.1', '12.4.2',
            '13.0', '13.1', '13.1.1', '13.1.2', '13.2'
        ])
        self._appVersion    = random.choice(['3.5.3', '3.5.4', '3.5.6', '3.5.8', '3.5.10', '3.5.12', '3.6.0', '3.6.1', '3.7.0', '3.8.0', '3.9.0', '3.9.1', '3.10.0', '3.11.0'])
        self._imei          = str(uuid.uuid4())

        _LOGGER.debug(json.dumps({
            'model'         : self._model,
            'romVersion'    : self._romVersion,
            'appVersion'    : self._appVersion,
            'imei'          : self._imei
        }))

        app_details = {
            'password'  : self._password,
            'version'   : '6',
            'ts'        : int(time.time()),
            'nonce'     : ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8)),
            'appid'     : 'oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq',
            'imei'      : self._imei,
            'os'        : 'iOS',
            'model'     : self._model,
            'romVersion': self._romVersion,
            'appVersion': self._appVersion
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

        if self._login_cnt > 4:
            _LOGGER.error("SONOFF COMPONENT FAILED TO LOGIN AFTER 5 ATTEMPTS!")
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://{}-api.coolkit.cc:8080/api/user/login'.format(self._api_region),
                    headers=self._headers, json=app_details, timeout=30) as r:
                    resp = await r.json()

        except:
            _LOGGER.warning("Login failed! retrying... %s", self._api_region)
            self._login_cnt += 1
            await asyncio.sleep(5)
            await self.do_login()
            return

        else:
            # get a new region to login
            if 'error' in resp and 'region' in resp and resp['error'] == HTTP_MOVED_PERMANENTLY:
                self._api_region    = resp['region']
                self._wshost        = None

                _LOGGER.warning("found new region: >>> %s <<< (you should change api_region option to this value in configuration.yaml)", self._api_region)

                # re-login using the new localized endpoint
                await self.do_login()

            elif 'error' in resp and resp['error'] in [HTTP_NOT_FOUND, HTTP_BAD_REQUEST]:
                # (most likely) login with +86... phone number and region != cn
                if '@' not in self._username and self._api_region in ['eu', 'us']:
                    # self._api_region = 'cn'
                    # self.do_login()
                    _LOGGER.error('Login failed! try to change the api_region to \'cn\' OR \'as\'')

                else:
                    _LOGGER.error("Couldn't authenticate using the provided credentials!")

            else:

                if 'at' not in resp:
                    _LOGGER.error('Login failed! Please check credentials!')
                    return

                self._bearer_token  = resp['at']
                self._user_apikey   = resp['user']['apikey']
                self._headers.update({'Authorization' : 'Bearer ' + self._bearer_token})

                await self.update_devices() # to write the devices list

                # get/find the websocket host
                if not self._wshost:
                    await self.set_wshost()

                if self.get_wshost() is not None:
                    self.thread = threading.Thread(target=self.init_websocket)
                    self.thread.daemon = True
                    self.thread.start()

    async def set_wshost(self):
        async with aiohttp.ClientSession() as session:
            async with session.post('https://%s-disp.coolkit.cc:8080/dispatch/app' % self._api_region, headers=self._headers) as r:
                resp = await r.json()

                if 'error' in resp and resp['error'] == 0 and 'domain' in resp:
                    self._wshost = resp['domain']
                    _LOGGER.info("Found websocket address: %s", self._wshost)
                else:
                    _LOGGER.error("Couldn't find a valid websocket host, abording Sonoff init")

    async def state_listener(self, event):
        if not self.get_ws().connected:
            _LOGGER.error('websocket is not connected')
            return

        _LOGGER.debug('Received state event change for: %s' % event.data['deviceid'])

        params = event.data.get('params', None)

        if params is None:
            _LOGGER.error('improper event state sent')
            return

        # # convert from True/False to on/off
        # if isinstance(new_state, (bool)):
        #     new_state = 'on' if new_state else 'off'

        device = self.get_device(event.data['deviceid'])
        # outlet = event.data.get('outlet', None)

        if 'outlet' in params: # it's a multi switch capable device

            _LOGGER.debug("Switching `%s - %s` on outlet %d to state: %s", \
                device['deviceid'], device['name'] , (int(params['outlet']) + 1), params['switch'])

            p = { 'switches' : device['params']['switches'] }
            p['switches'][params['outlet']]['switch'] = params['switch']
            params = p

        else:
            _LOGGER.debug("Device `%s` change to: %s", device['deviceid'], json.dumps(params))

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
                if 'outlet' in params:
                    self._devices[idxd]['params']['switches'][params['outlet']]['switch'] = params['switch']
                else:
                    self._devices[idxd]['params'].update(params)

        # data = json.dumps({'device_id' : str(device['deviceid']), 'params' : params})
        # self.write_debug(data, type='S')

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
        if 'action' in data and data['action'] in ['update', 'sysmsg'] and 'params' in data:
            for idx, device in enumerate(self._devices):
                if device['deviceid'] == data['deviceid']:

                    self._devices[idx]['params'].update(data['params'])
                    self.set_entity_state(data['deviceid'], data['params'])

                    break # do not remove


        # self.write_debug(json.dumps(data), type='W')

    def on_error(self, *args):
        error = args[-1] # to accomodate the case when the function receives 2 or 3 args
        _LOGGER.error('websocket error: %s' % str(error))

    def is_grace_period(self):
        grace_time_elapsed = self._skipped_login * int(self.get_scan_interval().total_seconds())
        grace_status = grace_time_elapsed < int(self._grace_period.total_seconds())

        if grace_status:
            self._skipped_login += 1

        return grace_status

    # TBH this starts to look like ewelink app spaghetti code :(
    def get_device_entity_types(self, deviceid, params): # switch, light, etc
        entity_types = []
        device = self.get_device(deviceid)

        if 'FAN' in self.device_type_by_uiid(device):
            entity_types.append({'domain': 'fan',   'type': None})
            entity_types.append({'domain': 'light', 'type': None})

        elif 'state' in device['params'] and 'switch' not in device['params']:
            entity_types.append({'domain': 'light', 'type': None}) # sonoff b1

        elif self.uiid_to_name[device['uiid']] == 'RF_BRIDGE':
            entity_types.append({'domain': 'binary_sensor', 'type': None})

        elif 'switch' in device['params'] or 'switches' in device['params']:
            entity_types.append({'domain': 'switch', 'type': None})

            # add sensors list
            for sensor_type in SONOFF_SENSORS_MAP.keys():
                if sensor_type in params.keys():
                    entity_types.append({
                        'domain': 'sensor',
                        'type'  : SONOFF_SENSORS_MAP[sensor_type]['eid'],
                        'key'   : sensor_type
                    })

        # elif 'switches' in device['params']:
        #     entity_types.append({'domain': 'switch', 'type': None})

        return entity_types

    def set_entity_state(self, deviceid, params):
        entities = []

        device_entity_types = self.get_device_entity_types(deviceid, params)
        for entity_type in device_entity_types:
            if 'switches' in params:

                # stupid itead serialization
                if 'FAN' in self.device_type_by_uiid(self.get_device(deviceid)):
                    entity_id = "{}.{}_{}".format(
                        entity_type['domain'],
                        DOMAIN if self._entity_prefix else '',
                        deviceid
                    )

                    entities.append({"entity_id" : entity_id, "type": None })

                else: # 4-3-2 gang switch
                    for idx, switch in enumerate(params['switches']):
                        entity_id = "{}.{}_{}_{}".format(
                            entity_type['domain'],
                            DOMAIN if self._entity_prefix else '',
                            deviceid,
                            str(idx+1)
                        )

                        entities.append({"entity_id" : entity_id, "type": None, "gang": idx})
            else:
                entity_id = "{}.{}_{}{}".format(
                    entity_type['domain'],
                    DOMAIN if self._entity_prefix else '',
                    deviceid if 'cmd' not in params.keys() else self.rf2trig[list(params.keys())[-1]], # for rf bridge use trigger ID
                    '_' + entity_type['type'] if entity_type['type'] is not None else ''
                )

                entities.append({
                    "entity_id" : entity_id,
                    "type"      : entity_type['type'],
                    "key"       : entity_type['key'] if 'key' in entity_type else None
                })

        # @TODO update the availability
        # if 'online' in params:
        #    pass

        for ent in entities:
            entity = self._hass.states.get(ent['entity_id'])

            # ugly fix to overcome the 2-3 gang switches
            # should be on-par with the generation part in switch.py
            if not entity:
                continue

            # @INFO it happens that sometimes these values are missing
            if not hasattr(entity, 'attributes') or not hasattr(entity, 'state'):
                continue

            if 'switches' in params:
                if 'FAN' in self.device_type_by_uiid(self.get_device(deviceid)):
                    # @TODO calculate fan state + light on/off
                    pass

                else:
                    attr = {}

                    if hasattr(self._hass.states.get(ent['entity_id']), 'attributes'):
                        attr = self._hass.states.get(ent['entity_id']).attributes

                    _LOGGER.debug('updating device: {} => {} '.format(
                        ent['entity_id'],
                        params['switches'][ent['gang']]['switch']
                    ))

                    self._hass.states.set(ent['entity_id'], params['switches'][ent['gang']]['switch'], attr)
            else:
                state = entity.state
                attr  = entity.attributes

                if ent['type'] is not None: # it's a sensor entity
                    state = params[ent['key']]

                else:
                    # update the attributes of the "parent" entities

                    # @TODO learn how to update attributes class
                    # until then they'll be updated via poll refresh of entity

                    # for at in ['rssi', 'voltage', 'current', 'power',
                    #     'temperature', 'currentTemperature',
                    #     'humidity', 'currentHumidity']:
                    #     if at in params.keys():
                    #         setattr(attr, at, params[at])

                    if 'switch' in params:
                        state = params['switch']

                    elif 'state' in params: # light sonoff b1
                        # @TODO calculate color/color_temp and maybe brightness
                        state = params['state']

                    elif 'cmd' in params: # it's an RF trigger
                        # reset the binary sensor
                        track_point_in_time(
                              self._hass,
                              self.reset_binary_sensors,
                              dt_util.utcnow() + timedelta(seconds=2)
                        )

                        state = 'on'

                _LOGGER.debug('updating device: {} => {}'.format(ent['entity_id'], state))

                self._hass.states.set(ent['entity_id'], state, attr)

        # data = json.dumps({'device_id' : deviceid, 'params': params})
        # self.write_debug(data, type='s')

    # @TODO @FIX too ugly!!!!!
    def reset_binary_sensors(self, now=None):
        for device in self.get_devices():
            if self.uiid_to_name[device['uiid']] == 'RF_BRIDGE':
                for rf in device['params']['rfList']:
                    entity = self._hass.states.get('binary_sensor.sonoff_'+rf['rfVal'].lower())
                    attr  = entity.attributes
                    self._hass.states.set('binary_sensor.sonoff_'+rf['rfVal'].lower(), 'off', attr)

    async def update_devices(self):
        if self.get_user_apikey() is None:
            _LOGGER.error("Initial login failed, devices cannot be updated!")
            return self._devices

        # we are in the grace period, no updates to the devices
        if self._skipped_login and self.is_grace_period():
            _LOGGER.info("Grace period active")
            return self._devices

        async with aiohttp.ClientSession() as session:
            async with session.get('https://{}-api.coolkit.cc:8080/api/user/device?lang=en&apiKey={}&getTags=1&version=6&ts=%s&nonce=%s&appid=oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq&imei=%s&os=iOS&model=%s&romVersion=%s&appVersion=%s'.format(
            self._api_region, self.get_user_apikey(), str(int(time.time())), ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8)), self._imei, self._model, self._romVersion, self._appVersion
            ), headers=self._headers) as r:
                resp = await r.json()

        if 'error' in resp and resp['error'] in [HTTP_BAD_REQUEST, HTTP_UNAUTHORIZED, HTTP_NOT_ACCEPTED]:
            # @IMPROVE add maybe a service call / switch to deactivate sonoff component
            if self.is_grace_period():
                _LOGGER.warning("Grace period activated!")

                # return the current (and possible old) state of devices
                # in this period any change made with the mobile app (on/off) won't be shown in HA
                return self._devices

            _LOGGER.info("Re-login component")
            await self.do_login()

        self._devices = resp['devicelist'] if 'devicelist' in resp else resp

        # self.write_debug(r.text, type='D')
        return self._devices

    def get_devices(self, force_update = False):
        # if force_update:
        #     return await self.update_devices()

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

    def get_model(self):
        return self._model

    def get_romVersion(self):
        return self._romVersion

    async def async_update(self):
        devices = await self.update_devices()

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

        if device['uiid'] in self.uiid_to_name.keys() and \
            self.uiid_to_name[device['uiid']] in name_to_outlets.keys():
            return name_to_outlets[self.uiid_to_name[device['uiid']]]

        return None

    def device_type_by_uiid(self, device):
        return self.uiid_to_name.get(device['uiid'], None)
    ### sonog_debug.log section ###
    def write_debug(self, data, type = '', new = False):

        if self._sonoff_debug and self._hass.states.get('switch.sonoff_debug') and self._hass.states.is_state('switch.sonoff_debug','on'):

            if not len(self._sonoff_debug_log):
                _LOGGER.debug("init sonoff debug data capture")
                self._sonoff_debug_log.append(".\n--------------COPY-FROM-HERE--------------\n\n")

            data = json.loads(data)

            # remove extra info
            if isinstance(data, list):
                for idx, d in enumerate(data):
                    for k in ['extra', 'sharedTo','settings','group','groups','deviceUrl','deviceStatus',
                                'location','showBrand','brandLogoUrl','__v','_id','ip',
                                'deviceid','createdAt','devicekey','apikey','partnerApikey','tags']:
                        if k in d.keys(): del d[k]

                    for k in ['staMac','bindInfos','rssi','timers','partnerApikey']:
                        if k in d['params'].keys(): del d['params'][k]

                    # hide deviceid
                    if 'deviceid' in d.keys():
                        m = hashlib.md5()
                        m.update(d['deviceid'].encode('utf-8'))
                        d['deviceid'] = m.hexdigest()

                    data[idx] = d

            data = json.dumps(data, indent=2, sort_keys=True)
            data = self.clean_data(data)
            data = json.dumps(json.loads(data))

            data = "%s [%s] %s\n\n" % (datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], type, data)
            self._sonoff_debug_log.append(data)

        elif self._sonoff_debug and len(self._sonoff_debug_log) and \
            self._hass.states.get('switch.sonoff_debug') and \
            self._hass.states.is_state('switch.sonoff_debug','off'):

            _LOGGER.debug("end of sonoff debug log")
            self._sonoff_debug_log.append("---------------END-OF-COPY----------------\n")
            self._sonoff_debug_log = [x.encode('utf-8') for x in self._sonoff_debug_log]
            self._hass.components.persistent_notification.async_create(str(b"".join(self._sonoff_debug_log), 'utf-8'), 'Sonoff debug')
            self._sonoff_debug_log = []

    def clean_data(self, data):
        data = re.sub(r'"phoneNumber": ".*"', '"phoneNumber": "[hidden]",', data)
        # data = re.sub(r'"name": ".*"', '"name": "[hidden]",', data)
        data = re.sub(r'"ip": ".*",', '"ip": "[hidden]",', data)
        # data = re.sub(r'"deviceid": ".*",', '"deviceid": "[hidden]",', data)
        # data = re.sub(r'"_id": ".*",', '"_id": "[hidden]",', data)
        data = re.sub(r'"\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}"', '"xx:xx:xx:xx:xx:xx"', data)
        data = re.sub(r'"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}"', '"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"', data)
        # data = re.sub(r'"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z"', '"xxxx-xx-xxxxx:xx:xx.xxx"', data)
        return data

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
            'appid'     : 'oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq',
            'action'    : 'userOnline',
            'userAgent' : 'app',
            'version'   : 6,
            'nonce'     : ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8)),
            'apkVersion': '1.8',
            'os'        : 'iOS',
            'at'        : self._sonoff.get_bearer_token(),
            'apikey'    : self._sonoff.get_user_apikey(),
            'ts'        : str(int(time.time())),
            'model'     : self._sonoff.get_model(),
            'romVersion': self._sonoff.get_romVersion(),
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

        if 'dusty' in device['params']:
            self._attributes['dusty'] = device['params']['dusty']
        if 'light' in device['params']:
            self._attributes['light'] = device['params']['light']
        if 'noise' in device['params']:
            self._attributes['noise'] = device['params']['noise']

        # TH10/TH16
        if 'currentHumidity' in device['params'] and device['params']['currentHumidity'] != "unavailable":
            self._attributes['humidity'] = device['params']['currentHumidity']
        if 'currentTemperature' in device['params'] and device['params']['currentTemperature'] != "unavailable":
            self._attributes['temperature'] = device['params']['currentTemperature']

        if 'humidity' in device['params'] and device['params']['humidity'] != "unavailable":
            self._attributes['humidity'] = device['params']['humidity']
        if 'temperature' in device['params'] and device['params']['temperature'] != "unavailable":
            self._attributes['temperature'] = device['params']['temperature']

        if 'rssi' in device['params']:
            self._attributes['rssi'] = device['params']['rssi']

        # the device has more switches
        if self._outlet is not None:
            return device['params']['switches'][self._outlet]['switch'] == 'on' if device else False

        else:
            # `state` for B1
            # `switch` for everything else

            state_key = 'state' if 'state' in device['params'] and not 'switch' in device['params'] else 'switch'
            return device['params'][state_key] == 'on' if device else False

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
    def device_info(self):
        """Return the device info."""

        device = self.get_device()

        return {
            'model' : device['productModel'],
            'mac'   : device['params']['staMac']
        }


    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return self._attributes
