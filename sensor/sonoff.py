# The domain of your component. Should be equal to the name of your component.
import logging, time, hmac, hashlib, random, base64, json, socket

from homeassistant.components.switch import SwitchDevice
from datetime import timedelta
from homeassistant.util import Throttle
from homeassistant.components.sensor import DOMAIN
# from homeassistant.components.sonoff import (DOMAIN, SonoffDevice)
from custom_components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)
from homeassistant.const import TEMP_CELSIUS

# @TODO add PLATFORM_SCHEMA here (maybe)

SCAN_INTERVAL = timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Add the Sonoff Switch entities"""
 
    entities = []

    for device in hass.data[SONOFF_DOMAIN].get_devices(force_update = True):
        # the device has multiple switches, split them by outlet
        if 'switches' in device['params']:
            for outlet in device['params']['switches']:
                if device['params'].get('currentTemperature'):
                    entity = SonoffSensor(hass, device, outlet['outlet'])
                    entities.append(entity)
        
        # normal device = Sonoff Basic (and alike)
        else:
            if 'params' in device.keys() and device['params'].get('currentTemperature'):
                entity = SonoffSensor(hass, device)
                entities.append(entity) 

    async_add_entities(entities, update_before_add=False)

class SonoffSensor(SonoffDevice, SwitchDevice):
    """Representation of a Sonoff device (switch)."""

    def __init__(self, hass, device, outlet = None):
        """Initialize the device."""
        self._state         = None
        self._hass          = hass
        self._name          = '{}{}'.format(device['name'], '' if outlet is None else ' '+str(outlet+1))
        self._deviceid      = device['deviceid']
        self._available     = device['online']
        self._outlet        = outlet 
        self._params        = device['params']
        self._attributes    = {
            'device_id'     : self._deviceid
        }
  
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        if self._params:
            self._state = self._params.get('currentTemperature')

    @property
    def state(self):
       """Return the state of the sensor."""
       return self._state

    # entity id is required if the name use other characters not in ascii
    @property
    def entity_id(self):
        """Return the unique id of the switch."""
        entity_id = "{}.{}_{}".format(DOMAIN, SONOFF_DOMAIN, self._deviceid)

        if self._outlet is not None:
            entity_id = "{}_{}".format(entity_id, str(self._outlet+1) )
        
        return entity_id