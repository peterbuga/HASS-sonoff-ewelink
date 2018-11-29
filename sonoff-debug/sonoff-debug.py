# -*- coding: utf-8 -*-
import argparse, sys, json, time, random, pprint, base64, requests, hmac, hashlib

def gen_nonce(length=8):
	"""Generate pseudorandom number."""
	return ''.join([str(random.randint(0, 9)) for i in range(length)])

parser=argparse.ArgumentParser()

parser.add_argument('--email', 		help='email used for eWeLink app')
parser.add_argument('--password', 	help='password for email/account')

args=parser.parse_args()

# positional params
if '--' not in sys.argv[1] and '--' not in sys.argv[2]:
	email 		= sys.argv[1]
	password 	= sys.argv[2]

# named params	
elif hasattr(args, 'email') and hasattr(args, 'password'):
	email 		= args.email
	password 	= args.password

else:
	print 'Please read the instructions better!'
	sys.exit(1)

app_details = {
	'email'     : email,
	'password'  : password,
	'version'   : '6',
	'ts'        : int(time.time()),
	'nonce'     : gen_nonce(15),
	'appid'     : 'oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq',
	'imei'      : '01234567-89AB-CDEF-0123-456789ABCDEF',
	'os'        : 'iOS',
	'model'     : 'iPhone10,6',
	'romVersion': '11.1.2',
	'appVersion': '3.5.3'
}

decryptedAppSecret = '6Nz4n0xA8s8qdxQf2GqurZj2Fs55FUvM'

hex_dig = hmac.new(decryptedAppSecret, json.dumps(app_details), digestmod=hashlib.sha256).digest()
sign = base64.b64encode(hex_dig).decode()

headers = {
	'Authorization' : 'Sign ' + sign,
	'Content-Type'  : 'application/json'
}

r = requests.post('https://eu-api.coolkit.cc:8080/api/user/login', headers=headers, json=app_details)

user_details = r.json()

headers.update({'Authorization' : 'Bearer ' + user_details['at']})
r = requests.get('https://eu-api.coolkit.cc:8080/api/user/device', headers=headers)
devices = r.json()

print json.dumps(devices, indent=2, sort_keys=True)
