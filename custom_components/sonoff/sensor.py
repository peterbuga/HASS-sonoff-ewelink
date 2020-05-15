import logging, time, hmac, hashlib, random, base64, json, socket

from datetime import timedelta
from homeassistant.util import Throttle
from homeassistant.components.sensor import DOMAIN
# from homeassistant.components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)
from custom_components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)
from homeassistant.const import TEMP_CELSIUS

SCAN_INTERVAL = timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)

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

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Add the Sonoff Sensor entities"""

    entities = []
    for device in hass.data[SONOFF_DOMAIN].get_devices(force_update = False):
        # as far as i know only 1-switch devices seem to have sensor-like capabilities

        if 'params' not in device.keys(): continue # this should never happen... but just in case

        for sensor in SONOFF_SENSORS_MAP.keys():
            if device['params'].get(sensor) and device['params'].get(sensor) != "unavailable":
                entity = SonoffSensor(hass, device, sensor)
                entities.append(entity)

    if len(entities):
        async_add_entities(entities, update_before_add=False)

class SonoffSensor(SonoffDevice):
    """Representation of a Sonoff sensor."""

    def __init__(self, hass, device, sensor = None):
        """Initialize the device."""
        SonoffDevice.__init__(self, hass, device)
        self._sensor        = sensor
        self._name          = '{} {}'.format(device['name'], SONOFF_SENSORS_MAP[self._sensor]['eid'])
        self._attributes    = {}

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return SONOFF_SENSORS_MAP[self._sensor]['uom']

    @property
    def state(self):
       """Return the state of the sensor."""
       return self.get_device()['params'].get(self._sensor)

    # entity id is required if the name use other characters not in ascii
    @property
    def entity_id(self):
        """Return the unique id of the switch."""
        entity_id = "{}.{}_{}_{}".format(DOMAIN, SONOFF_DOMAIN, self._deviceid, SONOFF_SENSORS_MAP[self._sensor]['eid'])
        return entity_id

    @property
    def icon(self):
        """Return the icon."""
        return SONOFF_SENSORS_MAP[self._sensor]['icon']