# -*- coding: utf-8 -*-
import argparse, sys, json, time, random, pprint, base64, requests, hmac, hashlib, re, uuid, string

# named params
if not sys.argv[1].startswith('-') and not sys.argv[2].startswith('-'):
	username	= sys.argv[1]
	password 	= sys.argv[2]

else:
	parser=argparse.ArgumentParser()
	parser.add_argument('-u', '--username', 	help='email/phone number used to login in eWeLink app')
	parser.add_argument('-p', '--password', 	help='password for email/account')

	args=parser.parse_args()

	# positional params
	if hasattr(args, 'username') and hasattr(args, 'password'):
		username	= args.username
		password 	= args.password

	else:
		print('Please read the instructions better!')
		sys.exit(1)

headers = {'Content-Type'  : 'application/json'}
user_details = {}
api_region='us'

model         = 'iPhone' + random.choice(['6,1', '6,2', '7,1', '7,2', '8,1', '8,2', '8,4', '9,1', '9,2', '9,3', '9,4', '10,1', '10,2', '10,3', '10,4', '10,5', '10,6', '11,2', '11,4', '11,6', '11,8'])
romVersion    = random.choice([
	'10.0', '10.0.2', '10.0.3', '10.1', '10.1.1', '10.2', '10.2.1', '10.3', '10.3.1', '10.3.2', '10.3.3', '10.3.4',
	'11.0', '11.0.1', '11.0.2', '11.0.3', '11.1', '11.1.1', '11.1.2', '11.2', '11.2.1', '11.2.2', '11.2.3', '11.2.4', '11.2.5', '11.2.6', '11.3', '11.3.1', '11.4', '11.4.1',
	'12.0', '12.0.1', '12.1', '12.1.1', '12.1.2', '12.1.3', '12.1.4', '12.2', '12.3', '12.3.1', '12.3.2', '12.4', '12.4.1', '12.4.2',
	'13.0', '13.1', '13.1.1', '13.1.2', '13.2'
])
appVersion    = random.choice(['3.5.3', '3.5.4', '3.5.6', '3.5.8', '3.5.10', '3.5.12', '3.6.0', '3.6.1', '3.7.0', '3.8.0', '3.9.0', '3.9.1', '3.10.0', '3.11.0'])
imei          = str(uuid.uuid4())

def do_login():
	global api_region

	app_details = {
		'password'  : password,
		'version'   : '6',
		'ts'        : int(time.time()),
		'nonce'     : ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8)),
		'appid'     : 'oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq',
		'imei'      : imei,
		'os'        : 'iOS',
		'model'     : model,
		'romVersion': romVersion,
		'appVersion': appVersion
	}

	if '@' not in username:
		app_details['phoneNumber'] = username
	else:
		app_details['email'] = username

	try:
		#python3.6+
		decryptedAppSecret = b'6Nz4n0xA8s8qdxQf2GqurZj2Fs55FUvM'
		hex_dig = hmac.new(decryptedAppSecret, str.encode(json.dumps(app_details)), digestmod=hashlib.sha256).digest()
	except:
		#python2.7
		decryptedAppSecret = '6Nz4n0xA8s8qdxQf2GqurZj2Fs55FUvM'
		hex_dig = hmac.new(decryptedAppSecret, json.dumps(app_details), digestmod=hashlib.sha256).digest()

	sign = base64.b64encode(hex_dig).decode()

	headers.update({'Authorization' : 'Sign ' + sign})
	r = requests.post('https://%s-api.coolkit.cc:8080/api/user/login' % api_region, headers=headers, json=app_details)
	resp = r.json()

	if 'error' in resp and 'region' in resp and resp['error'] == 301:
		# re-login using the new localized endpoint
		api_region = resp['region']
		do_login()

	else:
		global user_details
		user_details = r.json()

def get_devices():
	headers.update({'Authorization' : 'Bearer ' + user_details['at']})
	r = requests.get('https://%s-api.coolkit.cc:8080/api/user/device?lang=en&apiKey=%s&getTags=1' % \
		(api_region, user_details['user']['apikey']),
		headers=headers)

	r = requests.get('https://%s-api.coolkit.cc:8080/api/user/device?lang=en&apiKey=%s&getTags=1&version=6&ts=%s&nonce=%s&appid=oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq&imei=%s&os=iOS&model=%s&romVersion=%s&appVersion=%s' % (
			api_region,
			user_details['user']['apikey'],
			str(int(time.time())), ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8)),
			imei, model, romVersion, appVersion),
		headers=headers)
	devices = r.json()

	return json.dumps(devices, indent=2, sort_keys=True)

def clean_data(data):
	data = re.sub(r'"phoneNumber": ".*"', '"phoneNumber": "[hidden]",', data)
	data = re.sub(r'"name": ".*"', '"name": "[hidden]",', data)
	data = re.sub(r'"ip": ".*",', '"ip": "[hidden]",', data)
	data = re.sub(r'"deviceid": ".*",', '"deviceid": "[hidden]",', data)
	data = re.sub(r'"_id": ".*",', '"_id": "[hidden]",', data)
	data = re.sub(r'"\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}"', '"xx:xx:xx:xx:xx:xx"', data)
	data = re.sub(r'"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}"', '"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"', data)
	data = re.sub(r'"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z"', '"xxxx-xx-xxxxx:xx:xx.xxx"', data)

	return data

if __name__ == "__main__":
	do_login()
	devices_json = get_devices()
	print(clean_data(devices_json))

