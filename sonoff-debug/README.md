Basic script that outputs a json of the current devices you have in your eWeLink account, send this output (post **full** output anywhere and link it to a github issue etc) to me along with the human description of the devices "Sonoff Basic", "Sonoff Dual", "Sonoff 4CH", "Sonoff SC" so I can identify them better etc and I'll do my best to integrate them in this component.

## NOTICE!

Under no circumstances I'm not using this script to capture any emails or passwords and it's better to read/examine its contents before running it! 

### The script tries to remove automatically the sensitive data, but please double check it before posting it - your output might be slightly different!

To run this it just, `cd` to the location of the script and:

`python sonoff-debug.py 'email or phone-number username' 'password'` > devices.json 

OR

`python sonoff-debug.py --username='email or phone-number username' --password='password'` > devices.json 

OR

`python sonoff-debug.py -u 'email or phone-number username' -p 'password'` > devices.json

**This script can be ran from any place/computer that has the required modules installed (google how to install the missing ones, it's out of the scope of this repo) meaning it's not mandatory to have HA installation to run it.** 

This might help those who have a **Hassio installation** https://community.home-assistant.io/t/test-python-script-on-hassio/55268 

## Example of expected output (Sonoff Basic)

```json
[
  {
    "__v": 0, 
    "_id": "[hidden]" 
    "apikey": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", 
    "brandName": "Sonoff", 
    "createdAt": "2018-11-18T11:21:58.513Z", 
    "deviceStatus": "", 
    "deviceUrl": "", 
    "deviceid": "[hidden]" 
    "devicekey": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", 
    "extra": {
      "_id": "[hidden]" 
      "extra": {
        "apmac": "xx:xx:xx:xx:xx:xx", 
        "brandId": "58e5f344baeb368720e25469", 
        "description": "WWJG001219", 
        "mac": "xx:xx:xx:xx:xx:xx", 
        "manufacturer": "\u6df1\u5733\u677e\u8bfa\u6280\u672f\u6709\u9650\u516c\u53f8", 
        "model": "ITA-GZ1-GL", 
        "modelInfo": "5a2e1ac20cf772f92c342eef", 
        "ui": "\u5f00\u5173\u6539\u88c5\u6a21\u5757", 
        "uiid": 14
      }
    }, 
    "group": "", 
    "groups": [], 
    "ip": "[hidden]" 
    "location": "", 
    "name": "[hidden]", 
    "offlineTime": "2018-11-29T09:52:16.353Z", 
    "online": true, 
    "onlineTime": "2018-11-30T11:25:23.934Z", 
    "params": {
      "controlType": 4, 
      "fwVersion": "2.6.0", 
      "partnerApikey": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", 
      "rssi": -59, 
      "staMac": "xx:xx:xx:xx:xx:xx", 
      "startup": "off", 
      "switch": "off", 
      "timers": [
        {
          "at": "40 23 * * 1,2,3,4,5,6,0", 
          "coolkit_timer_type": "repeat", 
          "do": {
            "switch": "off"
          }, 
          "enabled": 1, 
          "mId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", 
          "type": "repeat"
        }
      ]
    }, 
    "productModel": "Basic", 
    "settings": {
      "alarmNotify": 1, 
      "opsHistory": 1, 
      "opsNotify": 0
    }, 
    "sharedTo": [], 
    "showBrand": true, 
    "type": "10", 
    "uiid": 14
  }
]
```

