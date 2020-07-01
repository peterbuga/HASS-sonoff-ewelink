import logging

from homeassistant.components.fan import (SUPPORT_SET_SPEED,
    SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH,
    ATTR_SPEED, ATTR_SPEED_LIST, FanEntity)
from homeassistant.components.fan import DOMAIN
from custom_components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Add the Sonoff Switch entities"""

    entities = []
    for device in hass.data[SONOFF_DOMAIN].get_devices(force_update = False):

        # @TODO figure out a better way to detect sonoff iFan02 (or probably iFan03)
        if hass.data[SONOFF_DOMAIN].device_type_by_uiid(device) and \
            'FAN' in hass.data[SONOFF_DOMAIN].device_type_by_uiid(device):
            entity = SonoffFan(hass, device)
            entities.append(entity)

    if len(entities):
        async_add_entities(entities, update_before_add=False)

class SonoffFan(SonoffDevice, FanEntity):
    """Representation of a Sonoff switch device."""

    def __init__(self, hass, device):
        """Initialize the device."""

        # add fan unique stuff here if needed
        SonoffDevice.__init__(self, hass, device)
        self._name   = device['name']
        self._speed  = SPEED_OFF

    @property
    def is_on(self):
        """Return true if device is on."""
        self._state = (self.get_device()['params']['switches'][1]['switch'] == 'on')
        return self._state

    def turn_on(self, speed, **kwargs):
        """Turn the device on."""
        self.set_speed(speed)

        data = {
            'deviceid'  : self._deviceid,
            'params'    : {'switches' : { 1: 'on'}}
        }

        switches = {'switches' : {}}
        if speed == SPEED_LOW: # ON intention
            switches = {'switches' : { 2 : 'off', 3 : 'off' }}
        elif speed == SPEED_MEDIUM: # ON intention
            switches = {'switches' : { 2 : 'on', 3 : 'off' }}
        elif speed == SPEED_HIGH: # ON intention
            switches = {'switches' : { 2 : 'off', 3 : 'on' }}

        data['params'].update(switches)

        self._hass.bus.async_fire('sonoff_state', data)
        self.async_schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._hass.bus.async_fire('sonoff_state', {
            'deviceid'  : self._deviceid,
            'params'    : {'switches' : { 1: 'off'}}
        })

        self.async_schedule_update_ha_state()

    # entity id is required if the name use other characters not in ascii
    @property
    def entity_id(self):
        """Return the unique id of the switch."""

        if self._hass.data[SONOFF_DOMAIN].get_entity_prefix():
            entity_id = "{}.{}_{}".format(DOMAIN, SONOFF_DOMAIN, self._deviceid)
        else:
            entity_id = "{}.{}".format(DOMAIN, self._deviceid)

        return entity_id

    @property
    def speed(self):
        """Return the current speed."""
        speeds = self.get_device()['params']['switches']
        if speeds[1]['switch'] == 'off':
            self._speed = SPEED_OFF

        else:
            if speeds[2]['switch'] == 'off' and speeds[3]['switch'] == 'off':
                self._speed = SPEED_LOW
            elif speeds[2]['switch'] == 'on' and speeds[3]['switch'] == 'off':
                self._speed = SPEED_MEDIUM
            elif speeds[2]['switch'] == 'off' and speeds[3]['switch'] == 'on':
                self._speed = SPEED_HIGH

        return self._speed

    def set_speed(self, speed):
        """Set the speed of the fan."""
        self._speed = speed
        self.async_schedule_update_ha_state()

    @property
    def speed_list(self):
        """Get the list of available speeds."""
        return [SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_SET_SPEED
