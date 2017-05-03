from websocket import create_connection

import requests, json, threading, select, multiprocessing, time, datetime


class DiscordClient:
	def __init__(self):
		self.login_url = 'https://discordapp.com/api/v6/auth/login'
		self.me_url = 'https://discordapp.com/api/v6/users/@me'
		self.gateway_url = 'https://discordapp.com/api/v6/gateway'

		self.ws_gateway_query_params = '/?encoding=json&v=6'

		self.headers = {'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0'}

		self.ws = None
		self.ws_send_queue = multiprocessing.Queue()

		self.message_counter = 0

	def login(self, email : str, password : str):
		""" Attempts to login with the given credentials.
		Returns true on sucess, and stores the authtoken in self.token """

		data = json.dumps({'email': email, 'password':password}).encode('utf-8')

		print('Attempting login of', email, ':', '*'*len(password))
		req = requests.post(self.login_url, data=data, headers={**self.headers, 'Content-Type':'application/json'})
		self.debug = req

		if req.status_code == 200:
			self.token = req.json()['token']
			return True
		return False

	def get_me(self):
		""" Downloads information about the client.
		Returns true if successful, and stores this information in a dict in self.me
		"""

		req = requests.get(self.me_url, headers={**self.headers, 'Authorization':self.token})
		if req.status_code == 200:
			data = req.json()

			self.me = data

			return True
		return False

	def retrieve_websocket_gateway(self):
		""" Attempts to get the websocket URL. Returns that URL. """
		req = requests.get(self.gateway_url, headers={**self.headers, 'Authorization':self.token})
		if req.status_code == 200:
			data = req.json()
			return data['url']
		return False

	def download_messages(self, channelid : str, limit=50):
		""" Downloads messages for a specific channel id. Must have an authtoken. """
		request_url = 'https://discordapp.com/api/v6/channels/{}/messages?limit={}'.format(channelid, limit)
		req = requests.get(request_url, headers={**self.headers, 'Authorization':self.token})
		if req.status_code == 200:
			data = req.json()
			return data
		return req

	def connect_websocket(self, gateway_url : str):
		# do connect to websocket url gateway_url
		self.ws = create_connection(gateway_url + self.ws_gateway_query_params)

		self.ws_thread = threading.Thread(target=self.websocket_loop)
		self.ws_ping_thread = threading.Thread(target=self.websocket_ping)
		self.ws_thread.start()
		print('Started websocket thread\n')

	def websocket_loop(self):
		while 1:
			readable, writable, executable = select.select( [self.ws, self.ws_send_queue._reader], [], [] )

			for item in readable:
				if item == self.ws:
					self.ws_recv_callback(self.ws.recv())

				elif item == self.ws_send_queue._reader:
					self.ws.send( self.ws_send_queue.get() )

	def websocket_ping(self):
		while 1:
			time.sleep(self.heartbeat_interval)
			ping_packet = json.dumps( {'op':1, 'd':self.message_counter} )
			self.websocket_send( ping_packet )
			print('Sent ping: %s' % ping_packet)


	def websocket_send(self, data : bytes):
		self.ws_send_queue.put(data)

	def websocket_received_callback(self, callback):
		# call the callback function when receiving a packet
		self.ws_recv_callback = callback


if __name__ == '__main__':
	client = DiscordClient()

	with open('credentials','r') as f:
		email,password = json.load(f)

	# do login
	print(client.login( email, password ))
	print(client.token)

	# download @me data
	print(client.get_me())
	print(client.me)

	# get the gateway
	websocket_url = client.retrieve_websocket_gateway()
	print(websocket_url)

	# create websocket callback
	def ws_callback(message):
		print('RECV %s' % message)
		client.message_counter += 1

		if type(message) == str:
			data = json.loads(message)
			if data['op'] == 10:
				client.heartbeat_interval = data['d']['heartbeat_interval'] / 1000
				client.ws_ping_thread.start()
				print('Started ping thread')

			elif data['op'] == 11: # do not count pings!
				client.message_counter -= 1

		else:
			pass

	client.websocket_received_callback(ws_callback)

	# start the websocket
	client.connect_websocket(websocket_url)
	client.websocket_send(json.dumps({
		"op": 2,
		"d": {
			"token": client.token,
			"properties": {
				"os": "Linux",
				"browser": "Firefox",
				"device": "",
				"referrer": "",
				"referring_domain": ""
			},
			"large_threshold": 100,
			"synced_guilds": [],
			"presence": {
				"status": "online",
				"since": 0,
				"afk": False,
				"game": None
			},
			"compress": True
		}
	}))

	client.websocket_send(json.dumps(
		{"op":4,"d":{"guild_id":None,"channel_id":None,"self_mute":True,"self_deaf":False,"self_video":False}}
	))
