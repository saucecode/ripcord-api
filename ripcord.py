
import requests, json

class DiscordClient:
	def __init__(self):
		self.login_url = 'https://discordapp.com/api/v6/auth/login'
		self.me_url = 'https://discordapp.com/api/v6/users/@me'
		self.headers = {'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0'}

	def login(self, email : str, password : str):
		data = json.dumps({'email': email, 'password':password}).encode('utf-8')

		print('Attempting login of', email, ':', '*'*len(password))
		req = requests.post(self.login_url, data=data, headers={**self.headers, 'Content-Type':'application/json'})
		self.debug = req

		if req.status_code == 200:
			self.token = req.json()['token']
			return True
		return False

	def get_me(self):
		req = requests.get(self.me_url, headers={**self.headers, 'Authorization':self.token})
		if req.status_code == 200:
			data = req.json()

			self.me = data

			return True
		return False


if __name__ == '__main__':
	client = DiscordClient()

	with open('credentials','r') as f:
		email,password = json.load(f)

	print(client.login( email, password ))
