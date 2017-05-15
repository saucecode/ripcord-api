from websocket import create_connection

import requests, json, threading, select, multiprocessing, time, datetime


class DiscordClient:
	def __init__(self):
		self.login_url = 'https://discordapp.com/api/v6/auth/login'
		self.me_url = 'https://discordapp.com/api/v6/users/@me'
		self.settings_url = 'https://discordapp.com/api/v6/users/@me/settings'
		self.guilds_url = 'https://discordapp.com/api/v6/users/@me/guilds'
		self.gateway_url = 'https://discordapp.com/api/v6/gateway'
		self.logout_url = 'https://discordapp.com/api/v6/auth/logout'
		self.track_url = 'https://discordapp.com/api/v6/track'
		self.members_url = 'https://discordapp.com/api/v6/guilds/{}/members'

		self.ws_gateway_query_params = '/?encoding=json&v=6'

		self.headers = {'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0'}

		self.ws = None
		self.ws_send_queue = multiprocessing.Queue()

		self.message_counter = 0

		self.requester = requests.Session()

		self.print_traffic = False

	def do_request(self, method : str, url : str, data=None, headers={}, params=None):
		resp = self.requester.request(method, url, data=data, headers={**self.headers, **headers}, params=params)
		if self.print_traffic: print('%s %s with data %s -- %i\n' % (method, url, data, resp.status_code))
		return resp

	def login(self, email : str, password : str):
		""" Attempts to login with the given credentials.
		Returns true on sucess, and stores the authtoken in self.token

		Returns:
			bool: True if successful
		"""

		data = json.dumps({'email': email, 'password':password}).encode('utf-8')

		print('Attempting login of', email, ':', '*'*len(password))
		req = self.do_request('POST', self.login_url, data=data, headers={'Content-Type':'application/json'})
		self.debug = req

		if req.status_code == 200:
			self.token = req.json()['token']
			return True
		return False

	def logout(self):
		""" Attempts to logout.
		Will close the websocket client if opened.

		Returns:
			bool: True if successful
		"""

		data = json.dumps(
			{ 'provider':None, 'token':None }
		)

		if self.ws and self.ws.connected:
			self.ws.close()
			self.ws_send_queue.put('nosend')

		req = self.do_request('POST', self.logout_url, headers={'Authorization':self.token, 'Content-Type':'application/json'}, data=data)

		self.debug = req.text

		if req.status_code == 204:
			return True
		else:
			return False


	def get_me(self):
		""" Downloads information about the client.
		Stores this information in a dict in self.me.

		Returns:
			bool: True if successful
		"""

		# req = requests.get(self.me_url, headers={**self.headers, 'Authorization':self.token})
		req = self.do_request('GET', self.me_url, headers={'Authorization':self.token})
		if req.status_code == 200:
			data = req.json()

			self.me = data

			return True
		return False

	def retrieve_websocket_gateway(self):
		""" Attempts to get the websocket URL.

		Returns:
			str: The gateway URL.
		"""
		# req = requests.get(self.gateway_url, headers={**self.headers, 'Authorization':self.token})
		req = self.do_request('GET', self.gateway_url, headers={'Authorization':self.token})

		if req.status_code == 200:
			data = req.json()
			return data['url']
		return False

	def download_messages(self, channelid : str, limit=50):
		""" Downloads messages for a specific channel id. Must have an authtoken.

		Returns:
			list: A list of the most recent messages.
		"""
		request_url = 'https://discordapp.com/api/v6/channels/{}/messages?limit={}'.format(channelid, limit)
		# req = requests.get(request_url, headers={**self.headers, 'Authorization':self.token})
		req = self.do_request('GET', request_url, headers={'Authorization':self.token})
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
		while self.ws.connected:
			readable, writable, executable = select.select( [self.ws, self.ws_send_queue._reader], [], [], 1.0 )

			if not self.ws.connected:
				break

			for item in readable:
				if item == self.ws:
					read = self.ws.recv()

					if self.print_traffic:
						try:
							print('RECEIVED %s\n' % json.dumps(json.loads(read), indent=4, separators=(',', ': ')))
						except:
							print('RECEIVED %s\n' % read)

					self.message_counter += 1
					if type(read) == str and len(read) >= 2: # server information packet
						data = json.loads(read)
						if data['op'] == 10:
							self.heartbeat_interval = data['d']['heartbeat_interval'] / 1000
							self.ws_ping_thread.start()
							print('Started ping thread')

						elif data['op'] == 11: # Ping packet -- do not count pings!
							client.message_counter -= 1

						else:
							self.ws_recv_callback(data)

				elif item == self.ws_send_queue._reader:
					while not self.ws_send_queue.empty():
						read = self.ws_send_queue.get()

						if self.print_traffic:
							try:
								print('SENDING  %s\n' % json.dumps(json.loads(read), indent=4, separators=(',', ': ')))
							except:
								print('SENDING  %s\n' % read)

						self.ws.send( read )

		print('Websocket loop thread exited.')

	def websocket_ping(self):
		ticker = 0
		delta = self.heartbeat_interval / 60.0
		while self.ws.connected:
			time.sleep(delta)

			if not self.ws.connected:
				break

			if delta > self.heartbeat_interval:
				ticker = 0

				ping_packet = json.dumps( {'op':1, 'd':self.message_counter} )
				self.websocket_send( ping_packet )
				print('Sent ping.')

		print('Ping thread exited.')


	def websocket_send(self, data : bytes):
		self.ws_send_queue.put(data)

	def websocket_received_callback(self, callback):
		# call the callback function when receiving a packet
		self.ws_recv_callback = callback

	def send_message(self, channelid : str, message : str, tts=False, nonce="123"):
		""" Sends a message to a specific channel.

		Returns:
			bool: True if successful
		"""

		data = json.dumps(
			{"content": message, "tts":tts, "nonce": nonce}
		)

		request_url = 'https://discordapp.com/api/v6/channels/{}/messages'.format(channelid)
		# req = requests.post(request_url, headers={**self.headers, 'Authorization':self.token, 'Content-Type':'application/json'}, data=data)
		req = self.do_request('POST', request_url, headers={'Authorization':self.token, 'Content-Type':'application/json'}, data=data)
		if req.status_code == 200:
			self.debug = req.json()

			return True

		self.debug = req.text
		return False

	def send_start_typing(self, channelid : str):
		""" Sends a signal to start typing to a specific channel.

		Returns:
			bool: True if successful
		"""

		request_url = 'https://discordapp.com/api/v6/channels/{}/typing'.format(channelid)
		# req = requests.post(request_url, headers={**self.headers, 'Authorization':self.token})
		req = self.do_request('POST', request_url, headers={'Authorization':self.token})
		if req.status_code == 204:
			return True
		self.debug = req
		return False

	def send_presence_change(self, presence : str):
		""" Sends a presence update.
		presence should be one of 'idle', 'online', 'dnd', 'invisible'

		Returns:
			bool: True if successful
		"""

		data = json.dumps({
			'op': 3,
			'd': {
				'status': presence,
				'since': 0,
				'game': None,
				'afk': False
			}
		})

		self.websocket_send(data)

		data = json.dumps(
			{'status': presence}
		)

		#req = requests.patch(request_url, headers={**self.headers, 'Authorization':self.token, 'Content-Type':'application/json'}, data=data)
		req = self.do_request('PATCH', self.settings_url, headers={'Authorization':self.token, 'Content-Type':'application/json'}, data=data)

		self.debug = req

		if req.status_code == 200:
			return True
		else:
			return False

	def send_game_change(self, gamename : str):
		""" Send a game change update.

		Returns:
			bool: True if successful
		"""

		# TODO FIX ME -- I DON'T WORK

		data = json.dumps(
			{ 'event':'Launch Game', 'properties':{'Game': gamename}, 'token':self.token }
		)

		# req = requests.post(self.track_url, headers={**self.headers, 'Authorization':self.token, 'Content-Type':'application/json'}, data=data)
		req = self.do_request('POST', self.track_url, headers={**self.headers, 'Authorization':self.token, 'Content-Type':'application/json'}, data=data)

		self.debug = req

		if req.status_code == 204:
			return True
		else:
			return False

	def retrieve_servers(self):
		""" Retrieve a list of servers user is connected to.

		Returns:
			list: List of servers.
		"""
		req = self.do_request('GET', self.guilds_url, headers={**self.headers, 'Authorization':self.token})
		self.debug = req

		if req.status_code == 200:
			return req.json()

		return None

	def retrieve_server_channels(self, serverid : str):
		""" Retrieve a list of channels in the server.

		This list includes channels that the user is not a part of.
		Attempting to run download_messages on these channels yields a 403 Forbidden error.

		Returns:
			list: List of channels or None if request fails.
		"""
		req = self.do_request('GET', 'https://discordapp.com/api/v6/guilds/{}/channels'.format(serverid), headers={**self.headers, 'Authorization':self.token})
		self.debug = req

		if req.status_code == 200:
			return req.json()

		return None

	def retrieve_server_members(self, serverid : str, limit=1000):
		""" Retrieves a list of members in the server given by serverid.

		Returns:
			list: List of members, up to limit.
		"""
		query_params = {'limit': limit}
		req = self.do_request('GET', self.members_url.format(serverid), headers={**self.headers, 'Authorization':self.token}, params=query_params)
		self.debug = req

		if req.status_code == 200:
			return req.json()

		return None


if __name__ == '__main__':
	import sys

	client = DiscordClient()

	with open('credentials','r') as f:
		email,password = json.load(f)

	# do login
	if client.login( email, password ):
		print('Login successful - Authtoken: %s' % client.token)
	else:
		print('Failed to login.')
		sys.exit(0)

	# download @me data
	client.get_me()
	print(client.me)

	# get the gateway
	websocket_url = client.retrieve_websocket_gateway()
	print(websocket_url)

	# create websocket callback
	def ws_callback(message):
		if message['op'] == 0 and message['t'] == 'MESSAGE_CREATE':
			print('<%s> %s' % (message['d']['author']['username'], message['d']['content']) )

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

	# download servers

	servers = client.retrieve_servers()

	# print channels
	for server in servers:
		serverid = server['id']
		server_members = client.retrieve_server_members(serverid)

		print('Server:', server['name'], 'ID:', serverid)

		channels = client.retrieve_server_channels(serverid)

		print('Found %i channels:' % len(channels))

		for chan in channels:
			if chan['type'] == 0: # regular channel
				print( '\t(%s) %s: %s' % (chan['id'], chan['name'], chan['topic']) )

			elif chan['type'] == 2:
				print( '\t(%s) %s %ik [Voice Channel]' % (chan['id'], chan['name'], int(chan['bitrate']/1000)) )

		print('\nThis server has %i members:' % len(server_members))
		for member in server_members:
			print('\t%s: (%s) %s' % (member['user']['id'], member['user']['username'], member['nick'] if 'nick' in member else member['user']['username']) )

		print('')

	# client.send_start_typing('304959901376053248')
	# time.sleep(1)
	# client.send_message('304959901376053248', time.ctime())

	time.sleep(2)
	print(client.send_presence_change('idle'))
	time.sleep(2)
	print(client.send_presence_change('dnd'))
	time.sleep(2)
	print(client.send_presence_change('invisible'))
	time.sleep(2)
	print(client.send_presence_change('online'))

	time.sleep(2)

	print('Signing out...')
	client.logout()
