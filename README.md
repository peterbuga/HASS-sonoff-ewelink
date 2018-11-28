# Home Assistant component for original firmware Sonoff / eWeLink Basic switches
Simple Home Assistant component to add/control Sonoff/eWeLink Basic smart switches using the stock firmware and cloud capabilities.

**CURRENTLY WORKS ONLY WITH `Sonoff / eWeLink Basic` MODELS**

To setup add to your configuration.yaml:
```yaml
sonoff:
  email: [registered email]
  password: [password]
  scan_interval: 60 (optional)
  grace_period: 600 (optional)
  apihost: 'eu-api.coolkit.cc' (optional*)
```
And copy the *.py files in `custom_components` folder using the same structure like defined here:
```
 custom_components
    ├── sonoff.py
    └── switch
        └── sonoff.py
```

`scan_interval` you can define how fast the state of devices is refreshed (by default every 60sec).  for example if you change the switch from an external source like Alexa or Google Home  the change will show up in HA in maximum less than specified period, while changing it using HA interface/actions/etc it's instantly.
`grace_period` eWeLink app allows **only one active session at a time**, therefore this will temporarily block HA refreshes for the specified amount (in seconds) to allow (or better said **after**) you to login in the app and do required changes to your devices. following that sonoff component does an internal re-login invalidating the mobile session and the process restarts.
`apihost` this component tries to find & connect to the proper region assigned to you, *only fill this section if you know how to fetch the mobile app requests using Charles Proxy or other utilities alike. possible values that were tested and work are _us-api.coolkit.cc_ or _eu-api.coolkit.cc_, setting this right will save some extra requests when the HA boots up (i.e. making it a bit faster)

For now the devices will be registered in HA under this format `switch.sonoff_[sonoff device id]` to avoid human name conflicting with other possible already present switches *(this might change in the future or an option will be added to select a desired naming scheme)*.

This is just a proof of concept because I searched for it and there was no implementation to use Sonoff/eWeLink devices without flashing them. (althought I know how to do it, I don't have a real extensive usage for now and I prefer to keep them on stock firmware).

## Requests / Bugs
As I said earlier this is just a proof-of-concept to get familiar with HomeAssistant's framework. Feel free to report bugs / request features / fork (& pull request) I'll try to see what I can do.

## Credits 
Most of the logic & code was done (partialy) porting this awesome repo (+those that it extends itself) https://github.com/howanghk/homebridge-ewelink
