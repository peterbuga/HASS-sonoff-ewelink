Basic script that outputs a json of the current devices you have in your eWeLink account, send this output (post it anywhere and link it to a github issue etc) to me along with the human description of the devices "Sonoff Basic", "Sonoff Dual", "Sonoff 4CH", "Sonoff SC" so I can identify them better etc and I'll do my best to integrate them in this component

To run this script just, `cd` to the location of the script and:

`python sonoff-debug.py 'email@used.com' 'password'` > devices.json 

OR

`python sonoff-debug.py --email='email@used.com' --password='password'` > devices.json 

OR

`python sonoff-debug.py -e 'email@used.com' -p 'password'` > devices.json 


##NOTICE 

Under no circumstances I'm not using this script to capture any emails or passwords and it's better to read/examine its contents before running it! 



