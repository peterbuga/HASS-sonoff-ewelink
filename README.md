# Home Assistant component for original firmware Sonoff / eWeLink switches
Simple Home Assistant component to add/control Sonoff/eWeLink smart switches using the stock firmware and cloud capabilities.

***
### WARNING: completely deactivate the `sonoff` component from HA while doing a firmware update, due to auto-relogin function you might be kicked out of the app before the process is completed. I would not be held liable for any problems occuring if not following this steps!
***

**CHECK COMPATIBILITY LIST BELOW! IF IT DOESN'T WORK FOR YOUR DEVICE DON'T COMPLAIN AND OPEN A PROPER ISSUE**

## Setup

To setup add to your configuration.yaml:
```yaml
sonoff:
  username: [email or phone number]
  password: [password]
  scan_interval: 60 (optional)
  grace_period: 600 (optional)
  api_region: 'eu' (optional)
```
And copy the *.py files in `custom_components` folder using the same structure like defined here:
```
 custom_components
    ├── sonoff.py
    └── switch
        └── sonoff.py
```

`email` [Deprecated] only for compatibility, may be eliminated in future.

`username` the username that you registered for ewelink account be it an email or a phone number (the phone number should lead with region number, '+8612345678901' for example).

`scan_interval` you can define how fast the state of devices is refreshed (by default every 60sec).  for example if you change the switch from an external source like Alexa or Google Home the change will show up in HA in maximum less than specified period, while changing it using HA interface/actions/etc it's instantly

`grace_period` eWeLink app allows **only one active session at a time**, therefore this will temporarily block HA refreshes for the specified amount (in seconds) to allow (or better said **after**) you to login in the app and do required changes to your devices. following that sonoff component does an internal re-login invalidating the mobile session and the process restarts. (as a workaround for this, you can create a 2nd account and share the devices from main one, therefore one will be used in HA another one in mobile app)

`api_region` this component tries to find, login & connect to the proper region assigned to you. specifying a proper region will help the component to load faster and reconnect after the expired grace period explained above, possible values: `eu` (default), `us` and `cn`

This is just a proof of concept because I searched for it and there was no implementation to use Sonoff/eWeLink devices without flashing them. (althought I know how to do it, I don't have a real extensive usage for now and I prefer to keep them on stock firmware).


## Compatibility list
| Model                              | Supported | Fw 1.6 | Fw 1.8.1 | Fw 2.6 | Remarks                      |
|------------------------------------|:---------:|:------:|:--------:|:------:|------------------------------|
| Sonoff Basic                       |    yes    |   yes  |    yes   |   yes  |                              |
| Sonoff 4CH Pro (R2)                |    yes    |        |          |   yes  |                              |
| Sonoff S20                         |    yes    |        |    yes   |        |                              |
| [3 Gang Generic Wall Switch](https://www.amazon.in/gp/product/B07FLY398G)         |    yes    |        |       |    yes    |  Manfufacturer: pro-sw, Model: PS-15-ES (according to ewelink app)                              |
| [1 Gang Generic Wall Switch](https://www.aliexpress.com/item/1-Gang-US-EU-UK-Plug-Wall-Wifi-Light-Switch-Smart-Touch-LED-Lights-Switch-for/32934184095.html)         |    yes    |        |       |    yes    |  Manfufacturer: KingART, Model: KING-N1 (according to ewelink app), Chip: PSF-B85 (ESP8285)                             |
| WHDTS WiFi Momentary Inching Relay |    yes    |        |          |        | displayed as a switch button |
| [Sonoff S26](https://www.aliexpress.com/item/Sonoff-S26-WiFi-Smart-Socket-Wireless-Plug-Power-Socket-Smart-Home-Switch-Smart-Remote-Control-for/32956551752.html)                         |    yes    |        |          |   yes  |  Version: Euro                            |

`yes` = confirmed version, [empty] = unknown for sure 

## Updates
- 2018.12.5 
  - mandarin phone number login support
  - removed `entity_name` option, the entities will have a fixed structure from now on
- 2018.12.01
  - ability to control devices with multiple switches 
  - added mobile app specified device-name as default to be listed in HA entity, added `entity_name` option and removed the default `sonoff_` prefix
  - fixed bug that will show device as unavailable in the grace period
- 2018.11.29 
  - shared devices from another account can be used also
- 2018.11.28 
  - mobile app-like login to the closest region 
  - added `scan_interval` option
  - added `grace_period` option

## Requests / Bugs
Feel free to properly ask support for new devices [using these guidelines](https://github.com/peterbuga/HASS-sonoff-ewelink/tree/master/sonoff-debug) / report bugs / request features / fork (& pull request) and I'll try to see what I can do.

## Credits 
- most of the logic & code was done (partialy) porting this awesome repo (+those that it extends itself) https://github.com/howanghk/homebridge-ewelink
- [@2016for](https://github.com/2016for) for assisting me with properly integrating the switches with multiple outlets
- [@fireinice](https://github.com/fireinice) for providing the mandarin implementation

