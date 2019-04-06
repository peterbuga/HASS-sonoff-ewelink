import logging, time, json

from homeassistant.components.switch import SwitchDevice
from homeassistant.components.switch import DOMAIN
# from homeassistant.components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)
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

            elif 'switch' in device['params'] or 'state' in device['params']:
                entity = SonoffSwitch(hass, device)
                entities.append(entity)

        elif outlets_number > 1: # the device has multiple switches, split them by available outlets
            for outlet in range(0, outlets_number):
                entity = SonoffSwitch(hass, device, outlet)
                entities.append(entity)
	
        # normal device = Sonoff Basic (and alike)
        elif 'switch' in device['params'] or 'state' in device['params']: #ignore devices like Sonoff RF bridge: 
            entity = SonoffSwitch(hass, device)
            entities.append(entity)

    if len(entities):
        async_add_entities(entities, update_before_add=False)

class SonoffSwitch(SonoffDevice, SwitchDevice):
    """Representation of a Sonoff switch device."""

    def __init__(self, hass, device, outlet = None):
        """Initialize the device."""

        # add switch unique stuff here if needed
        SonoffDevice.__init__(self, hass, device)
        self._outlet = outlet
        self._name   = '{}{}'.format(device['name'], '' if outlet is None else ' '+str(outlet+1))

        if outlet is None:
            self._name      = device['name']

        else:
            self._attributes['outlet'] = outlet

            if 'tags' in device and 'ck_channel_name' in device['tags']:
                if str(outlet) in device['tags']['ck_channel_name'].keys() and \
                    device['tags']['ck_channel_name'][str(outlet)]:
                    self._name = '{} - {}'.format(device['name'], device['tags']['ck_channel_name'][str(outlet)])

                    self._attributes['outlet_name'] = device['tags']['ck_channel_name'][str(outlet)]
                else:
                    self._name = '{} {}'.format(device['name'], ('CH %s' % str(outlet+1)) )
            else:
                self._name = '{} {}'.format(device['name'], ('CH %s' % str(outlet+1)) )

    @property
    def is_on(self):
        """Return true if device is on."""
        self._state = self.get_state()
        return self._state

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._hass.bus.async_fire('sonoff_state', {
            'state'     : True,
            'deviceid'  : self._deviceid,
            'outlet'    : self._outlet
        })
        self.async_schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._hass.bus.async_fire('sonoff_state', {
            'state'     : False,
            'deviceid'  : self._deviceid,
            'outlet'    : self._outlet
        })
        self.async_schedule_update_ha_state()

    # entity id is required if the name use other characters not in ascii
    @property
    def entity_id(self):
        """Return the unique id of the switch."""
        entity_id = "{}.{}".format(DOMAIN, self._deviceid)

        if self._outlet is not None:
            entity_id = "{}_{}".format(entity_id, str(self._outlet+1))
        
        return entity_id
