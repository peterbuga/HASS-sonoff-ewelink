# Home Assistant component for original firmware Sonoff / eWeLink smart devices
Simple Home Assistant component to add/control Sonoff/eWeLink smart devices using the stock firmware and retaining the cloud capabilities.

***
### WARNING: completely deactivate the `sonoff` component from HA while doing a firmware update, due to auto-relogin function you might be kicked out of the app before the process is completed. I would not be held liable for any problems occuring if not following this steps!
***

**CHECK COMPATIBILITY LIST IN README.MD (not everyday updated)! 
TRY THE COMPONENT FIRST AND IF IT DOESN'T WORK FOR YOUR DEVICE DON'T COMPLAIN AND OPEN A PROPER ISSUE**

## Setup

To setup add to your configuration.yaml:
```yaml
sonoff:
  username: [email or phone number]
  password: [password]
  scan_interval: 60 (optional, lower values than 60 won't work anymore!)
  grace_period: 600 (optional)
  api_region: 'eu' (optional)
  entity_prefix: True (optional)
  debug: False (optional)
```
And copy the *.py files in `custom_components` folder using the same structure like defined here:
```
 custom_components
    └── sonoff
        └── __init__.py
        └── switch.py
        └── sensor.py
```

`email` [Deprecated] used only for compatibility, may be eliminated in future.

`username` the username that you registered for ewelink account be it an email or a phone number (the phone number should lead with region number, '+8612345678901' for example).

`scan_interval` you can define how fast the state of devices is refreshed (by default every 60sec).  for example if you change the switch from an external source like Alexa or Google Home the change will show up in HA in maximum less than specified period, while changing it using HA interface/actions/etc it's instantly

`grace_period` eWeLink app allows **only one active session at a time**, therefore this will temporarily block HA refreshes for the specified amount (in seconds) to allow (or better said **after**) you to login in the app and do required changes to your devices. following that sonoff component does an internal re-login invalidating the mobile session and the process restarts. (as a workaround for this, you can create a 2nd account and share the devices from main one, therefore one will be used in HA another one in mobile app)

`api_region` this component tries to find, login & connect to the proper region assigned to you. specifying a proper region will help the component to load faster and reconnect after the expired grace period explained above, possible values: `eu` (default), `us`, `as` or `cn`

`entity_prefix` this option removes the `sonoff_` prefix from entities name (it's more or a less a compatibility mode between previous `master` vs `websocket` branch implementations)

### debug log generation / new device / new features requests
`debug` if enabled this will give you the ability to generate a log of messages from ewelink that can be easily posted here to debug/implement new devices. 

steps and how it works:
- this option creates a pseudo switch entity `switch.sonoff_debug` (**notice** it won't show up automatically in frontend in lovelace you have to **manually add it** or toggle it from `Developer tools > Services` section). 
- to generate a sonoff debug log toggle the pseudo-switch ON and the capture of messages will silently start in the background. now **pick up the phone -> open eWeLink app** and start changing settings of your Sonoff device but not faster than 10+ seconds between each change. 
- when you finish toggle the pseudo-switch OFF and a new (very long) persistent notification will show up. 
- go to `Developer tools > States` section and look for a `persistent_notification.notification` entity (impossible to miss due to its extremely long attribute text) and copy the message from there (to remove this notifications and others just push the button Dismiss them from main HA notifications area and you can restart the process and generate a new log if needed). 

**INFORMATION**: it'll be better if you share the device-to-debugged to a 2nd eWeLink account and use this in HA and main account in mobile app, this way you won't be logged out of the app anymore and the generated log will be restricted to only 1 device

**NOTICE**: you should **NOT** leave debug-mode enabled for everyday use, please please just don't!
 
This is just a proof of concept because I searched for it and there was no implementation to use Sonoff/eWeLink devices without flashing them. (althought I know how to do it, I don't have a real extensive usage for now and I prefer to keep them on stock firmware).