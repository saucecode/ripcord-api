
import requests, json

class DiscordClient:
	def __init__(self):
		self.login_url = 'https://discordapp.com/api/v6/auth/login'
		self.me_url = 'https://discordapp.com/api/v6/users/@me'
		self.gateway_url = 'https://discordapp.com/api/v6/gateway'
		self.headers = {'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0'}

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


if __name__ == '__main__':
	client = DiscordClient()

	with open('credentials','r') as f:
		email,password = json.load(f)

	print(client.login( email, password ))
	print(client.get_me())
	print(client.me)
	print(client.retrieve_websocket_gateway())
	with open('dump.json','w') as f:
		json.dump(client.download_messages('181226314810916865'), f)
