# The domain of your component. Should be equal to the name of your component.
import logging, time, json

from homeassistant.components.switch import SwitchDevice
from homeassistant.components.switch import DOMAIN
#from homeassistant.util import Throttle

# from homeassistant.components.sonoff import (DOMAIN, SonoffDevice)
from custom_components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Add the Sonoff Switch entities"""
 
    entities = []

    for device in hass.data[SONOFF_DOMAIN].get_devices(force_update = True):
        outlets_number = hass.data[SONOFF_DOMAIN].get_outlets(device)

        if outlets_number is None: # fallback to whatever the device might have
            if 'switches' in device['params']: # the device has multiple switches, split them by outlets
                for outlet in device['params']['switches']:
                    entity = SonoffSwitch(hass, device, outlet['outlet'])
                    entities.append(entity)
            else:
                entity = SonoffSwitch(hass, device)
                entities.append(entity)

        elif outlets_number > 1: # the device has multiple switches, split them by available outlets
            for outlet in range(0, outlets_number):
                entity = SonoffSwitch(hass, device, outlet)
                entities.append(entity)

        else: # normal device = Sonoff Basic (and alike)
            entity = SonoffSwitch(hass, device)
            entities.append(entity)

    async_add_entities(entities, update_before_add=False)

class SonoffSwitch(SonoffDevice, SwitchDevice):
    """Representation of a Sonoff switch device."""

    def __init__(self, hass, device, outlet = None):
        """Initialize the device."""

        # add switch unique stuff here if needed
        SonoffDevice.__init__(self, hass, device, outlet)
	
    # entity id is required if the name use other characters not in ascii
    @property
    def entity_id(self):
        """Return the unique id of the switch."""
        entity_id = "{}.{}".format(DOMAIN, self._deviceid)

        if self._outlet is not None:
            entity_id = "{}_{}".format(entity_id, str(self._outlet+1) )
        
        return entity_id
