import logging, json

from homeassistant.components.light import (SUPPORT_BRIGHTNESS, SUPPORT_COLOR_TEMP,
    SUPPORT_EFFECT, SUPPORT_FLASH, SUPPORT_COLOR, SUPPORT_TRANSITION, SUPPORT_WHITE_VALUE,
    LightEntity)
from homeassistant.components.light import DOMAIN
from custom_components.sonoff import (DOMAIN as SONOFF_DOMAIN, SonoffDevice)

from homeassistant.util import color

_LOGGER = logging.getLogger(__name__)

EFFECT_WARMCOOL = 'warmcool'
EFFECT_COLOR    = 'color'

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Add the Sonoff Light entities"""

    entities = []
    for device in hass.data[SONOFF_DOMAIN].get_devices(force_update = False):

        # so far Sonoff B1 is the only I was able to identify as a light
        # unfortunately Sonoff Slampher is identified as a switch

        # @TODO figure out a better way to detect sonoff light capable devices
        if 'state' in device['params'] and 'switch' not in device['params']:
            entity = SonoffLight(hass, device)
            entities.append(entity)

    if len(entities):
        async_add_entities(entities, update_before_add=False)

class SonoffLight(SonoffDevice, LightEntity):
    """Representation of a Sonoff switch device."""

    def __init__(self, hass, device):
        """Initialize the device."""

        # add light unique stuff here if needed
        SonoffDevice.__init__(self, hass, device)

        self._name   = device['name']
        self._state  = self.get_state()

        self._ch01          = [int(device['params']['channel0']), int(device['params']['channel1'])]
        self._ch234         = [int(device['params']['channel2']), int(device['params']['channel3']), int(device['params']['channel4'])]

        # calculate the mode
        if int(device['params']['channel0']) > 0 or int(device['params']['channel1']) > 0:
            self._mode          = EFFECT_WARMCOOL
            self._hs_color      = [0, 0]
        else:
            self._mode          = EFFECT_COLOR
            self._hs_color      = color.color_RGB_to_hs(*self._ch234)

        # @TODO calculate below values
        if int(device['params']['channel0']) > 245 and int(device['params']['channel1']) < 10:
            self._color_temp    = 155
        elif int(device['params']['channel0']) > 245 and int(device['params']['channel1']) > 245:
            self._color_temp    = 325
        elif int(device['params']['channel0']) < 10 and int(device['params']['channel1']) > 245:
            self._color_temp    = 500
        else:
            self._color_temp    = 325 # fallback

        # full brightness all the time till i figure a way to calculate it
        self._brightness    = 255

    @property
    def name(self):
        """Return the name of the Sonoff light."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        self._state = self.get_state()
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def hs_color(self):
        """Return the hue and saturation color value [float, float]."""
        return self._hs_color

    @property
    def color_temp(self):
        """Return the CT color value in mireds."""
        return self._color_temp

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return [EFFECT_WARMCOOL, EFFECT_COLOR]

    @property
    def effect(self):
        """Return the current effect."""
        return self._mode

    def turn_on(self, **kwargs):
        """Turn the device on."""
        _LOGGER.debug('Light ON: %s', json.dumps(kwargs) )

        params = {}

        if 'brightness' in kwargs:
            self._brightness = kwargs['brightness']

            if self._mode == EFFECT_WARMCOOL:

                ch0 = int(self._ch01[0] * self._brightness / 255)
                ch1 = int(self._ch01[1] * self._brightness / 255)

                params = {
                    "channel0": str(ch0), # cool
                    "channel1": str(ch1), # white
                    "channel2": "0", # red
                    "channel3": "0", # green
                    "channel4": "0" # blue
                }
            else: # rgb mode
                rgb = color.color_hs_to_RGB(*self._hs_color)
                rgb = [int(x * self._brightness / 255) for x in rgb]

                params = {
                    "channel0": "0", # cool
                    "channel1": "0", # white
                    "channel2": str(rgb[0]), # red
                    "channel3": str(rgb[1]), # green
                    "channel4": str(rgb[2]) # blue
                }

        if 'effect' in kwargs:
            self._mode = kwargs['effect']

            if self._mode == EFFECT_WARMCOOL:
                ch0 = int(self._ch01[0] * self._brightness / 255)
                ch1 = int(self._ch01[1] * self._brightness / 255)

                params = {
                    "channel0": str(ch0), # cool
                    "channel1": str(ch1), # white
                    "channel2": "0", # red
                    "channel3": "0", # green
                    "channel4": "0" # blue
                }

            else: # RGB mode
                rgb = color.color_hs_to_RGB(*self._hs_color)
                rgb = [int(x * self._brightness / 255) for x in rgb]

                params = {
                    "channel0": "0", # cool
                    "channel1": "0", # white
                    "channel2": str(rgb[0]), # red
                    "channel3": str(rgb[1]), # green
                    "channel4": str(rgb[2]) # blue
                }

        if 'color_temp' in kwargs:
            if self._mode == EFFECT_COLOR:
                self._mode = EFFECT_WARMCOOL

            self._color_temp = kwargs['color_temp']
            # 347 range value

            # middle full cool + warm white
            if kwargs['color_temp'] > 322 and kwargs['color_temp'] < 332:
                ch0 = 255
                ch1 = 255

            else:
                if kwargs['color_temp'] <= 322:
                    color_temp = kwargs['color_temp'] - 153 # default min color temp val

                    ch0 = int(((173 - color_temp) * 255) / 173)
                    ch1 = int((color_temp * 255) / 173) if color_temp else 0
                else:
                    color_temp = kwargs['color_temp'] - 153 - 174

                    ch0 = int(((173 - color_temp) * 255) / 173) if color_temp else 0
                    ch1 = int( (color_temp * 255) / 173)

            # apply brightness to values
            self._ch01 = [ch0, ch1]

            ch0 = int(ch0 * self._brightness / 255)
            ch1 = int(ch1 * self._brightness / 255)

            params = {
                "channel0": str(ch0), # cool
                "channel1": str(ch1), # white
                "channel2": "0", # red
                "channel3": "0", # green
                "channel4": "0" # blue
            }

        if 'hs_color' in kwargs:
            if self._mode == EFFECT_WARMCOOL:
                self._mode = EFFECT_COLOR

            self._hs_color = kwargs['hs_color']
            rgb = color.color_hs_to_RGB(*kwargs['hs_color'])

            # apply brightness
            rgb = [int(x * self._brightness / 255) for x in rgb]

            params = {
                "channel0": "0", # cool
                "channel1": "0", # white
                "channel2": str(rgb[0]), # red
                "channel3": str(rgb[1]), # green
                "channel4": str(rgb[2]) # blue
            }

        params.update({"state" : "on"})

        _LOGGER.debug('Light params: %s', json.dumps(params) )

        self._hass.bus.async_fire('sonoff_state', {
            'deviceid'  : self._deviceid,
            'params'    : params
        })

        self.async_schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        _LOGGER.debug('Light OFF: %s', json.dumps(kwargs) )
        params = {"state" : "off"}

        self._hass.bus.async_fire('sonoff_state', {
            'deviceid'  : self._deviceid,
            'params'    : params
        })

        self.async_schedule_update_ha_state()

    # entity id is required if the name use other characters not in ascii
    @property
    def entity_id(self):
        """Return the unique id of the light."""

        if self._hass.data[SONOFF_DOMAIN].get_entity_prefix():
            entity_id = "{}.{}_{}".format(DOMAIN, SONOFF_DOMAIN, self._deviceid)
        else:
            entity_id = "{}.{}".format(DOMAIN, self._deviceid)

        return entity_id

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""

        # self._attributes.update({})
        return self._attributes

    @property
    def supported_features(self):
        """Flag supported features."""

        if self._mode == EFFECT_WARMCOOL:
            return (SUPPORT_EFFECT | SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP)
        else:
            return (SUPPORT_EFFECT | SUPPORT_BRIGHTNESS | SUPPORT_COLOR)
