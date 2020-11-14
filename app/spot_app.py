"""
Prerequisites
    pip3 install spotipy Flask Flask-Session
    // from your [app settings](https://developer.spotify.com/dashboard/applications)
    export SPOTIPY_CLIENT_ID=client_id_here
    export SPOTIPY_CLIENT_SECRET=client_secret_here
    export SPOTIPY_REDIRECT_URI='http://127.0.0.1:8080' // must contain a port
    // SPOTIPY_REDIRECT_URI must be added to your [app settings](https://developer.spotify.com/dashboard/applications)
    OPTIONAL
    // in development environment for debug output
    export FLASK_ENV=development
    // so that you can invoke the app outside of the file's directory include
    export FLASK_APP=/path/to/spotipy/examples/app.py

    // on Windows, use `SET` instead of `export`
Run app.py
    python3 -m flask run --port=8080
    NOTE: If receiving "port already in use" error, try other ports: 5000, 8090, 8888, etc...
        (will need to be updated in your Spotify app and SPOTIPY_REDIRECT_URI variable)
"""

import os
from flask import Flask, session, request, redirect, render_template
from flask_session import Session
import spotipy
import uuid
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)

caches_folder = './.spotify_caches/'
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)

def session_cache_path():
    return caches_folder + session.get('uuid')

@app.route('/')
def index():
    if not session.get('uuid'):
        # Step 1. Visitor is unknown, give random ID
        session['uuid'] = str(uuid.uuid4())

    auth_manager = spotipy.oauth2.SpotifyOAuth(scope='user-top-read user-library-read user-read-currently-playing playlist-modify-public',
                                                cache_path=session_cache_path(),
                                                show_dialog=True)

    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.get_cached_token():
        # Step 2. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return f'<center> '\
                    f'<h1>See what music you have in common with Justin</h1>' \
                    f'<h2><a href="{auth_url}">Sign in</a></h2>' \
               f'</center>'

    # Step 4. Signed in, display data
    # return common_tracks()
    return top_artists()

@app.route('/sign_out')
def sign_out():
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(session_cache_path())
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))
    session.clear()
    return redirect('/')

@app.route('/common-tracks/')
def common_tracks():

    # Fetch Justin's library each time
    sp_jsech = jsech_creds()
    jsechs_tracks = get_library(sp_jsech)

    # Get this users info
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_path=session_cache_path())
    if not auth_manager.get_cached_token():
        return redirect('/')

    sp = spotipy.Spotify(auth_manager=auth_manager)
    tracks = get_library(sp)
    user_id = sp.current_user()['id']

    common_tracks = tracks.intersection(jsechs_tracks)

    playlist = sp_jsech.user_playlist_create(user='j.sech' ,name=f'Common Tracks -  {user_id} & j.sech')
    for i in range(0, len(common_tracks), 100):
        sp_jsech.user_playlist_add_tracks(user='j.sech',playlist_id=playlist['uri'], tracks=list(common_tracks)[i:i+100])

    return f'<center> '\
               f'<h2> You have {len(common_tracks)} songs in common with Justin: </h2>'\
               f'<p>(click the Spotify logo to open in Spotify and save to you library) </p>' \
               f'<iframe src="https://open.spotify.com/embed/playlist/{playlist["id"]}" width="500" height="580" frameborder="0" ' \
               f'allowtransparency="true" allow="encrypted-media"></iframe> '\
               f'<h2><a href="/sign_out">[sign out]<a/></h2>' \
           f'</center>' \


def top_tracks():
    # Fetch Justin's library each time
    sp_jsech = jsech_creds()


    # Get this users info
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_path=session_cache_path())
    if not auth_manager.get_cached_token():
        return redirect('/')

    sp = spotipy.Spotify(auth_manager=auth_manager)
    tracks = get_library(sp)
    user_id = sp.current_user()['id']

    jsech_top = set()
    user_top = set()

    for item in sp_jsech.current_user_top_tracks(50)['items']:
        jsech_top.add(item['id'])

    for item in sp.current_user_top_tracks(50)['items']:
        user_top.add(item['id'])

    common_top = user_top.intersection(jsech_top)

    playlist = sp_jsech.user_playlist_create(user='j.sech' ,name=f'Currently Listenning -  {user_id} & j.sech')

    if common_top:
        sp_jsech.user_playlist_add_tracks(user='j.sech',playlist_id=playlist['uri'], tracks=list(common_top))

        return f'<center> '\
                   f'<h2> You and Justin share {len(common_top)} of your current favorite songs: </h2>'\
                   f'<p>(click the Spotify logo to open in Spotify and save to you library) </p>' \
                   f'<iframe src="https://open.spotify.com/embed/playlist/{playlist["id"]}" width="500" height="580" frameborder="0" ' \
                   f'allowtransparency="true" allow="encrypted-media"></iframe> '\
                   f'<h2><a href="/sign_out">[sign out]<a/></h2>' \
               f'</center>'

    return f'<center> '\
               f'<h2> You and Justin haven\'t been listenning to any of the same songs recently :( </h2>' \
               f'<h2><a href="/sign_out">[sign out]<a/></h2>' \
           f'</center>'

@app.route("/top_artists/")
def top_artists():
    # Fetch Justin's library each time
    sp_jsech = jsech_creds()

    # Get this users info
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_path=session_cache_path())
    if not auth_manager.get_cached_token():
        return redirect('/')

    sp = spotipy.Spotify(auth_manager=auth_manager)
    tracks = get_library(sp)
    user_id = sp.current_user()['id']

    jsech_top = set()
    user_top = set()

    for item in sp_jsech.current_user_top_artists(50)['items']:
        jsech_top.add(item['name'])

    for item in sp.current_user_top_artists(50)['items']:
        user_top.add(item['name'])

    common_top = user_top.intersection(jsech_top)

    return render_template("list_template.html", data=[common_top, len(common_top)])



def jsech_creds():
    jsech_auth = spotipy.oauth2.SpotifyOAuth(scope='user-top-read user-library-read user-read-currently-playing playlist-modify-public',
                                                cache_path=caches_folder + "jsech_token",
                                                show_dialog=True)
    return spotipy.Spotify(auth_manager=jsech_auth)

# get a users liked songs
def get_library(sp):
    # collect liked songs
    results = sp.current_user_saved_tracks(limit=50) # 50 is the max you can get at once
    library = results['items']
    total_tracks = results['total']
    # collect 50 tracks at a time
    for i in range(50, total_tracks, 50):
        results = sp.current_user_saved_tracks(limit=50,offset=i)
        library += results['items']

    # save full library
    with open(f'data/{sp.me()["display_name"]}_liked_songs.json', 'w') as f:
        json.dump(library, f)

    tracks = set()
    for item in library:
        tracks.add(item['track']['id'])

    return tracks


'''
Following lines allow application to be run more conveniently with
`python app.py` (Make sure you're using python3)
(Also includes directive to leverage pythons threading capacity.)
'''
if __name__ == '__main__':
	app.run(threaded=True, port=int(os.environ.get("PORT", 5000)))
