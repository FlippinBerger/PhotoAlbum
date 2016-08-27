import gdata.photos.service
import gdata.media
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
import socket
import threading
import webbrowser
import datetime
import urllib2
import os

auth_code = ''

def main():
	secret_file = 'secrets'
	user_file = 'user_info.txt'
	email = ''
	pswd = ''
	app_path = ''

	#get information from the credential file
	with open(user_file, 'r') as f:
		email = f.readline().strip()
		pswd = f.readline().strip()
		app_path = f.readline().strip()

	username = email.split('@')[0]

	gd_client = OAuth2Login(secret_file, email, pswd, app_path)

	#Get all the albums
	albums = gd_client.GetUserFeed(user = email)

	#Get the album where the photos are stored
	album = ''
	album_name = 'Adventures<3'

	for a in albums.entry:
		if album_name in a.title.text:
			album = a

	#Get the photos from your album
	photos = gd_client.GetFeed('/data/feed/api/user/%s/albumid/%s?kind=photo' % (username, album.gphoto_id.text))
	
	#Collect the urls from the photos
	photo_urls = []
	for photo in photos.entry:
		photo_urls.append(photo.content.src)

	DownloadPhotos(app_path + '/pics', photo_urls)

#authenticates the user using OAuth2
def OAuth2Login(client_secrets, email, pswd, app_path):
	global auth_code
	scope = 'https://picasaweb.google.com/data/'
	user_agent = 'PhotoAlbum'
	cred_file = 'credentials.txt'

	#we already have the credentials stored in the file system
	if cred_file in os.listdir(app_path):
		credentials = Storage(app_path + cred_file).get()
	else: #we have to get the credentials from google
		flow = flow_from_clientsecrets(client_secrets, scope=scope, redirect_uri='http://localhost:9999')

		#start a thread to listen for the auth code
		listen_thread = threading.Thread(target = Listen)
		listen_thread.start()

		uri = flow.step1_get_authorize_url()
		webbrowser.open(uri)

		#wait for the thread to finish so we have the auth code
		listen_thread.join()

		code = auth_code.split('code=')[1].split()[0]
		#print 'The code is: {0}'.format(code)
		credentials = flow.step2_exchange(code)
		Storage(app_path + cred_file).put(credentials)
		
	if (credentials.token_expiry - datetime.datetime.utcnow()) < datetime.timedelta(minutes=5):
		http = httplib2.Http()
		http = credentials.authorize(http)
		credentials.refresh(http)

	gd_client = gdata.photos.service.PhotosService(source=user_agent,
		email=email,
		additional_headers={'Authorization' : 'Bearer %s' % credentials.access_token})
	return gd_client


#receives the data and sets auth code
def HandleCode(client):
	global auth_code
	request = client.recv(2048)
	request.strip()
	auth_code = request
	#print 'auth_code is here!! -> {0}'.format(auth_code)
	client.close()


#Listener thread to get the auth code
def Listen():
	global auth_code
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_address = ('localhost', 9999)
	sock.bind(server_address)
	sock.listen(1)
	#print 'Listening now!!!!!!!!!!!!!'
	while True:
		client, addr = sock.accept()
		#print '--------------{0}:{1}'.format(client, addr)
		HandleCode(client)
		if auth_code != '':
			break
	sock.close()

#downloads the photos to the /pics folder at path
def DownloadPhotos(path, urls):
	directory = []
	#first create the pics folder if it doesn't exist
	if not os.path.exists(path):
		os.makedirs(path)
	else: #otherwise we need to make a set of all the pics in the dir
		directory = os.listdir(path)
	for url in urls:
		response = urllib2.urlopen(url)
		file_name = response.geturl().split('/')[-1]

		#check for the file_name in the directory; Don't add it again
		if file_name in directory:
			continue
		else:
			with open('pics/%s' % (file_name), 'wb') as file:
				file.write(response.read())


if __name__ == '__main__':
	main()