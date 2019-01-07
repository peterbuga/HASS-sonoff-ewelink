import logging, time, hmac, hashlib, random, base64, json, socket

from homeassistant.components.switch import SwitchDevice
from datetime import timedelta
from homeassistant.util import Throttle
from homeassistant.components.switch import DOMAIN
# from homeassistant.components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)
from custom_components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)

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
                entity = SonoffSwitch(hass, device, outlet['outlet'])
                entities.append(entity)
        
        # normal device = Sonoff Basic (and alike)
        else:
            entity = SonoffSwitch(hass, device)
            entities.append(entity)    

    async_add_entities(entities, update_before_add=False)

class SonoffSwitch(SonoffDevice, SwitchDevice):
    """Representation of a Sonoff switch."""

    def __init__(self, hass, device, outlet = None):
        """Initialize the device."""

        # add switch unique stuff here if needed
        SonoffDevice.__init__(self, hass, device)
        self._outlet = outlet
        self._name   = '{}{}'.format(device['name'], '' if outlet is None else ' '+str(outlet+1))

    @property
    def is_on(self):
        """Return true if device is on."""
        self._state = self.get_state()
        return self._state

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._state = self._hass.data[SONOFF_DOMAIN].switch(True, self._deviceid, self._outlet)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._state = self._hass.data[SONOFF_DOMAIN].switch(False, self._deviceid, self._outlet)
        self.schedule_update_ha_state()

    # entity id is required if the name use other characters not in ascii
    @property
    def entity_id(self):
        """Return the unique id of the switch."""
        entity_id = "{}.{}_{}".format(DOMAIN, SONOFF_DOMAIN, self._deviceid)

        if self._outlet is not None:
            entity_id = "{}_{}".format(entity_id, str(self._outlet+1) )
        
        return entity_id