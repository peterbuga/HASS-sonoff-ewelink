# Home Assistant component for original firmware Sonoff / eWeLink smart devices
Simple Home Assistant component to add/control Sonoff/eWeLink smart devices using the stock firmware and retaining the cloud capabilities.

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
    └── sensor
        └── sonoff.py
```

`email` [Deprecated] used only for compatibility, may be eliminated in future.

`username` the username that you registered for ewelink account be it an email or a phone number (the phone number should lead with region number, '+8612345678901' for example).

`scan_interval` you can define how fast the state of devices is refreshed (by default every 60sec).  for example if you change the switch from an external source like Alexa or Google Home the change will show up in HA in maximum less than specified period, while changing it using HA interface/actions/etc it's instantly

`grace_period` eWeLink app allows **only one active session at a time**, therefore this will temporarily block HA refreshes for the specified amount (in seconds) to allow (or better said **after**) you to login in the app and do required changes to your devices. following that sonoff component does an internal re-login invalidating the mobile session and the process restarts. (as a workaround for this, you can create a 2nd account and share the devices from main one, therefore one will be used in HA another one in mobile app)

`api_region` this component tries to find, login & connect to the proper region assigned to you. specifying a proper region will help the component to load faster and reconnect after the expired grace period explained above, possible values: `eu` (default), `us` or `cn`

This is just a proof of concept because I searched for it and there was no implementation to use Sonoff/eWeLink devices without flashing them. (althought I know how to do it, I don't have a real extensive usage for now and I prefer to keep them on stock firmware).


## Compatibility list
| Model | Supported | 1.6 | 1.8.1 | 2.6 | 2.6.1 | 2.7.1 | Remarks |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------:|:---:|:-----:|:---:|-------|:-----:|--------------------------------------------------------------------------------------------|
| Sonoff Basic | yes | yes | yes | yes | yes |  |  |
| Sonoff Dual | yes |  |  |  |  |  |  |
| Sonoff RF | yes |  |  |  | yes |  |  |
| Sonoff G1 | ? |  |  |  |  |  |  |
| Sonoff 4CH Pro | yes |  |  | yes |  | yes |  |
| Sonoff 4CH Pro R2 | yes |  |  | yes |  |  |  |
| Sonoff S20 | yes |  | yes |  |  |  |  |
| Sonoff S31 | yes |  |  |  |  |  | only switch operation |
| [Sonoff S26](https://www.aliexpress.com/item/Sonoff-S26-WiFi-Smart-Socket-Wireless-Plug-Power-Socket-Smart-Home-Switch-Smart-Remote-Control-for/32956551752.html) | yes |  |  | yes |  |  | version: Euro |
| Sonoff T1 1C | yes |  |  | yes |  |  |  |
| Sonoff T1 EU 2C | yes |  |  |  |  | yes |  |
| Sonoff T1 UK 3C | yes |  |  | yes |  | yes |  |
| Sonoff T1 US 3C | yes |  |  |  |  |  |  |
| Sonoff Pow | yes |  |  |  |  |  | + power sensor |
| Sonoff Pow R2 | yes |  |  |  |  |  | + power/current/voltage sensors |
| Sonoff TH10/TH16 | yes |  |  |  |  |  | + temp/humidity sensors |
| Sonoff iFan02 | yes |  |  |  |  |  | it creates 4 switches, 1 for the light and 3 for the various fan speeds |
| Sonoff HT-TH31 | ? |  |  |  |  |  |  |
| [Sonoff Slampher RF](https://www.gearbest.com/smart-light-bulb/pp_1824903.html) | yes |  |  |  |  | yes |  |
| [3 Gang Generic Wall Switch](https://www.amazon.in/gp/product/B07FLY398G) | yes |  |  | yes |  |  | Manfufacturer: pro-sw, Model: PS-15-ES (according to ewelink app) |
| [1 Gang Generic Wall Switch](https://www.aliexpress.com/item/1-Gang-US-EU-UK-Plug-Wall-Wifi-Light-Switch-Smart-Touch-LED-Lights-Switch-for/32934184095.html) | yes |  |  | yes |  |  | manfufacturer: KingART, model: KING-N1 (according to ewelink app), Chip: PSF-B85 (ESP8285) |
| WHDTS WiFi Momentary Inching Relay | yes |  |  |  |  |  | displayed as a switch button |
| [MHCOZY WiFi Wireless 5V/12V](https://www.amazon.com/gp/product/B07CJ6DSQC/ref=oh_aui_search_detailpage?ie=UTF8&psc=1) | yes |  |  |  |  |  |  |
| [Geekcreit 2 Channel AC 85V-250V](https://www.ebay.es/itm/Geekcreit-2-Channel-AC-85V-250V-APP-Remote-Control-WIFI-Wireless-Switch-Socket-F-/162844446103) | yes |  |  |  |  | yes |  |
| [Smart Wi-Fi Outlet](https://www.amazon.com/gp/product/B073VK9X49/ref=oh_aui_detailpage_o01_s01?ie=UTF8&psc=1) | yes |  |  |  |  |  |  |

`yes` = confirmed version, [empty] = unknown for sure 

## Updates
- 2019.01.06
  - create sensors for devices that have support for power/current/voltage/temperature/humidity
- 2018.12.05 
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
- [@SergeyAnokhin](https://github.com/SergeyAnokhin) for adding power metter info to entity attributes
