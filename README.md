# Home Assistant component for original firmware Sonoff / eWeLink switches
Simple Home Assistant component to add/control Sonoff/eWeLink smart switches using the stock firmware and cloud capabilities.

**CHECK COMPATIBILITY LIST BELOW! IF IT DOESN'T WORK FOR YOUR DEVICE DON'T COMPLAIN AND OPEN A PROPER ISSUE**

##Setup

To setup add to your configuration.yaml:
```yaml
sonoff:
  email: [registered email]
  password: [password]
  scan_interval: 60 (optional)
  grace_period: 600 (optional)
  api_region: 'eu' (optional)
  entity_name: True (optional)
```
And copy the *.py files in `custom_components` folder using the same structure like defined here:
```
 custom_components
    ├── sonoff.py
    └── switch
        └── sonoff.py
```

`scan_interval` you can define how fast the state of devices is refreshed (by default every 60sec).  for example if you change the switch from an external source like Alexa or Google Home the change will show up in HA in maximum less than specified period, while changing it using HA interface/actions/etc it's instantly

`grace_period` eWeLink app allows **only one active session at a time**, therefore this will temporarily block HA refreshes for the specified amount (in seconds) to allow (or better said **after**) you to login in the app and do required changes to your devices. following that sonoff component does an internal re-login invalidating the mobile session and the process restarts. (as a workaround for this, you can create a 2nd account and share the devices from main one, therefore one will be used in HA another one in mobile app)

`api_region` this component tries to find, login & connect to the proper region assigned to you. specifying a proper region will help the component to load faster and reconnect after the expired grace period explained above, possible values: `eu` (default), `us` and `cn`

`entity_name` this option toggles the device's registered name in HA: set it `True` (default) to have the entity name the same as the one specified in eWeLink app or `False` to have it with the device id (this way your automations won't break upon renaming a device in the mobile app). to replicate the initial behaviour with `sonoff_` prefix for the entities you can use [*entity platform namespace option](https://www.home-assistant.io/docs/configuration/platform_options/#entity-namespace) (*this option generates duplicate entries on my setup, I tend to assume it's a HA bug but in the same time they can easily be hidden in customization.yaml)

This is just a proof of concept because I searched for it and there was no implementation to use Sonoff/eWeLink devices without flashing them. (althought I know how to do it, I don't have a real extensive usage for now and I prefer to keep them on stock firmware).

## Updates

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

## Compatibility list

| Model                              | Supported | Fw 1.6 | Fw 1.8.1 | Fw 2.6 | Remarks                      |
|------------------------------------|:---------:|:------:|:--------:|:------:|------------------------------|
| Sonoff Basic                       |    yes    |   yes  |    yes   |   yes  |                              |
| Sonoff 4CH Pro (R2)                |           |        |          |        |                              |
| WHDTS WiFi Momentary Inching Relay |    yes    |        |          |        | displayed as a switch button |


## Requests / Bugs

Feel free to properly report bugs (using the `sonoff-debug.py` script from this repo) / request features / fork (& pull request) I'll try to see what I can do.

## Credits 
Most of the logic & code was done (partialy) porting this awesome repo (+those that it extends itself) https://github.com/howanghk/homebridge-ewelink
