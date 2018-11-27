# Home Assistant component for original firmware Sonoff / eWeLink Basic switches
Simple Home Assistant component to add/control Sonoff/eWeLink Basic smart switches using the stock firmware and cloud capabilities.

**CURRENTLY WORKS ONLY WITH `Sonoff / eWeLink Basic` MODELS**

To setup add to your configuration.yaml:
```yaml
sonoff:
  email: [registered email]
  password: [password]
  #apihost: 'eu-api.coolkit.cc'
  #wshost: 'eu-long.coolkit.cc'
```
And copy the *.py files in `custom_components` folder using the same structure like defined here:
```
 custom_components
    ├── sonoff.py
    └── switch
        └── sonoff.py
```

For now the devices will be registered in HA under this format `switch.sonoff_1000xxxxxx` to avoid human name conflicting with other possible already present switches *(might change in the future)*.

**Notice:** the refresh state of devices is setup to every 60sec if for example you change the switch from an external source like Alexa or Google Home , changing it from HA interface it's instantly.

The `apihost` and `wshost` are optional and they work if you live in Europe, try to replace **eu** with **us** and might work if you live in USA, I'm not sure about the other values for other regions (I didn't had the time *or need for that matter* to test & find available endpoints).

Due to the way eWeLink app works, it allows you to have only 1 active session using the same credentials specified above, meaning you'll be all the time kicked out of the app while this component is active/running. (i might add an option later to pause the HA refresh of Sonoff devices while you might need to use the app like setting timers/a new device/etc)

This is just a proof of concept because I searched for it and there was no implementation to use Sonoff/eWeLink devices without flashing them. (althought I know how to do it, I don't have a real extensive usage for now and I prefer to keep them on stock firmware).

## Requests / Bugs
As I said earlier this is just a proof-of-concept to get familiar with HomeAssistant's framework. Feel free to report bugs / request features / fork (& pull request) I'll try to see what I can do.

## Credits 
Most of the logic & code was done (partialy) porting this awesome repo (+those that it extends itself) https://github.com/howanghk/homebridge-ewelink
