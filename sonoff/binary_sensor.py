import logging

from custom_components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)
from homeassistant.components.binary_sensor import (DOMAIN, BinarySensorEntity, DEVICE_CLASS_MOVING)
from homeassistant.const import STATE_ON, STATE_OFF


_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Add the Sonoff Sensor entities"""

    entities = []
    for device in hass.data[SONOFF_DOMAIN].get_devices(force_update = False):

        if 'params' not in device.keys(): continue # this should never happen... but just in case

        if hass.data[SONOFF_DOMAIN].device_type_by_uiid(device) and \
            hass.data[SONOFF_DOMAIN].device_type_by_uiid(device) == 'RF_BRIDGE':

            for rf in device['params']['rfList']:
                for rf_device in device['tags']['zyx_info']: # remote buttons, alarm
                    for btn in rf_device['buttonName']:
                        if list(btn.keys())[0] == str(rf['rfChl']):
                            rf['name']  = list(btn.values())[0] if rf_device['remote_type'] == "4" else rf_device['name']
                            rf['type']  = rf_device['remote_type']
                            break # don't remove

                hass.data[SONOFF_DOMAIN].rf2trig.update({ rf['rfVal'] : 'rfTrig'+str(rf['rfChl']) })
                hass.data[SONOFF_DOMAIN].rf2trig.update({ 'rfTrig'+str(rf['rfChl']): rf['rfVal'] })
                entity = SonoffSensorRF(hass, device, rf)
                entities.append(entity)

    if len(entities):
        async_add_entities(entities, update_before_add=False)

class SonoffSensorRF(SonoffDevice, BinarySensorEntity):
    """Representation of a Sonoff RF binary sensor."""

    def __init__(self, hass, device, rf = None):
        """Initialize the device."""
        SonoffDevice.__init__(self, hass, device)
        self._rf            = rf
        self._name          = self._rf['name']
        self._state         = None
        self._attributes    = {
            'rfid'  : self._rf['rfVal'],
            'type'  : 'remote_button' if self._rf['type'] == "4" else "alarm"
        }

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        # it's almost always False, it'll reset back the trigger
        return False

    @property
    def state(self):
        """Return the state of the binary sensor."""
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_MOVING

    # entity id is required if the name use other characters not in ascii
    @property
    def entity_id(self):
        """Return the unique id of the switch."""
        entity_id = "{}.{}_{}".format(DOMAIN, SONOFF_DOMAIN, self._rf['rfVal'].lower())
        return entity_id
