import logging

from datetime import timedelta
from homeassistant.components.sensor import DOMAIN
from custom_components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)
from custom_components.sonoff import SONOFF_SENSORS_MAP

SCAN_INTERVAL = timedelta(seconds=15)

_LOGGER = logging.getLogger(__name__)

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
        self._state         = None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return SONOFF_SENSORS_MAP[self._sensor]['uom']

    @property
    def state(self):
        """Return the state of the sensor."""
        state = self.get_device()['params'].get(self._sensor, None)

        # they should also get updated via websocket
        if state is not None and state != "unavailable":
            self._state = state

        return self._state

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
