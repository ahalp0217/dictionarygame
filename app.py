from flask import Flask, render_template, flash, redirect, url_for, request
from flask_socketio import SocketIO, join_room, leave_room
import os
import jsonpickle
import random
import re
import datetime

#Set up https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/putty.html?icmpid=docs_ec2_console

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

from game import *

GAME_ROOMS = {}

def strip_tags(text):
    return re.sub('<[^<]+?>', '', text)

def convert_to_json(game):
    #Converts from Python Object to JSON
    return json.loads(jsonpickle.encode(game))

def convert_to_object(game):
    #Converts from JSON to Python Object
    return jsonpickle.decode(game)

def get_game_id(request):
    return request.headers['Referer'].split("/game/")[1]

def get_word_of_the_day():
    lines = open(STANDARD_WORDS_PATH).read().splitlines()
    start_date = datetime.date(2018, 3, 4)
    date_now = datetime.date.today()
    delta = date_now - start_date
    diff_days = delta.days
    line = lines[diff_days]
    data = {
        'word' : line.split("|")[0],
        'definition' : line.split("|")[1]
    }
    return data

@app.route("/", methods=['POST', 'GET'])
def home():
    avatars = os.listdir(os.path.join(app.static_folder, 'avatars'))
    #If gameid passed into a player is trying to join

    rooms = convert_to_json(GAME_ROOMS)

    word_of_the_day = get_word_of_the_day()
    try:
        gameid = request.args['game']
        game = GAME_ROOMS[gameid]
        game_name = game.game_name
        return render_template("index.html", avatars=avatars, rooms=rooms, gameid=gameid, roomname=game_name, word=word_of_the_day['word'], definition = word_of_the_day['definition'])
    except KeyError:
        pass
    return render_template("index.html", avatars=avatars, rooms=rooms, word=word_of_the_day['word'], definition = word_of_the_day['definition'])

@app.route('/game/<gameid>', methods=['POST', 'GET'])
def game(gameid):
    try:
        game_id = strip_tags(request.form['game_id'])
        game_name = strip_tags(request.form['game_name'])
        game_type = strip_tags(request.form['game_type'])
        rounds = strip_tags(request.form['rounds'])

        player_name = strip_tags(request.form['player_name'])
        player_avatar = strip_tags(request.form['player_avatar'])

        #TODO: Add check to see if player is already in the game room, weird bug if just refreshing page returns form again

        game = Game(game_id, game_name, game_type, int(rounds), player_name)

        if not player_avatar:
            player_avatar = "doge2.png"

        game.players.append(Player(player_name, player_avatar))
        GAME_ROOMS[game_id] = game

        return render_template('game.html', game_name=game_name, game_type=game_type, rounds=rounds, player_name=player_name)
    except KeyError:
        game = GAME_ROOMS.get(gameid)
        if game:
            print(game.game_state)
            if game.game_state != GAME_STATES['PREGAME']:
                flash('Game already started. Sawwy.')
                return redirect(url_for('home'))
            try:
                #TODO: Remove Duplicate code
                player_name = strip_tags(request.form['player_name'])
                player_avatar = strip_tags(request.form['player_avatar'])

                if not player_avatar:
                    player_avatar = "doge2.png"

                if game.get_player_instance(player_name):
                    player_name = player_name + "-1"

                game.players.append(Player(player_name, player_avatar))

                #TODO: Add check to see if player is already in the game room

                return render_template('game.html', game_name=game.game_name, game_type=game.game_type, rounds=game.total_rounds, player_name=player_name)
            except KeyError:
                #Game Exists but player went to link directly, redirect back home and open form
                return redirect(url_for('home', game=gameid))
        else:
            flash('Game does not exist. Womp.')
            return redirect(url_for('home'))

@socketio.on('connect')
def connected():
    print("Player Connected")

@socketio.on("sendplayerinfo")
def get_player_info(data):
    player_id = data['playerID']
    player_name = data['playerName']
    game_id = get_game_id(request)
    join_room(game_id)

    #Set PlayerID to socketID
    game = GAME_ROOMS[game_id]
    player = game.get_player_instance(player_name)
    player.set_player_id(player_id)

    game = convert_to_json(GAME_ROOMS[game_id])
    socketio.emit('renderScoreBoard', game["players"], room=game_id)

@socketio.on('disconnect')
def on_disconnect():
    game_id = get_game_id(request)
    leave_room(game_id)
    game = GAME_ROOMS[game_id]
    game.remove_player(request.sid)

    if not game.players:
        GAME_ROOMS.pop(game_id, None)
        return

    if game.is_voting_time():
        reveal_definitions(game, game_id)
    elif game.is_reveal_time():
        reveal_answers(game, game_id)

    game = convert_to_json(game)
    socketio.emit("showplayersubmissionprogress", game['players'], room=game_id)
    socketio.emit('renderScoreBoard', game["players"], room=game_id)

@socketio.on('startgame')
def on_startround():
    game_id = get_game_id(request)
    game = GAME_ROOMS[game_id]
    game.game_state = GAME_STATES["INGAME"]
    game.round_state = ROUND_STATES["SUBMISSION_TIME"]
    game.reset_all_player_states()

    game = convert_to_json(game)
    socketio.emit("emitstartgame", game, room=game_id)
    socketio.emit('renderScoreBoard', game["players"], room=game_id)

@socketio.on('submitdefinition')
def on_submitdefinition(data):
    definition = data['definition']
    player_name = data['playerName']

    game_id = get_game_id(request)
    game = GAME_ROOMS[game_id]

    player = game.get_player_instance(player_name)
    player.insert_definition(definition, game.get_round_num())
    player.update_player_state(PLAYER_STATES['SUBMITTED'])

    if game.is_voting_time():
        game.round_state = ROUND_STATES["VOTING_TIME"]
        reveal_definitions(game, game_id)

    game = convert_to_json(game)
    socketio.emit('renderScoreBoard', game["players"], room=game_id)

@socketio.on('vote')
def on_vote(data):
    vote_for = data['voteFor']
    vote_from = data['voteFrom']

    game_id = get_game_id(request)
    game = GAME_ROOMS[game_id]

    voter = game.get_player_instance(vote_from)
    voter.update_votes_for(vote_for, game.get_round_num())

    try:
        votee = game.get_player_instance(vote_for)
        votee.update_votes_from(vote_from, game.get_round_num())
    except AttributeError: #Player voted for computer of person not in the game
        pass

    if vote_for == COMPUTER_NAME:
        voter.increment_player_score(CORRECT_DEFINITION_SCORE)
        notification = "{} voted correctly! +1".format(vote_from)
    elif vote_for == vote_from:
        voter.increment_player_score(SELF_VOTED_SCORE)
        notification = "{} voted for themself! +0".format(vote_from)
    else:
        votee = game.get_player_instance(vote_for)
        votee.increment_player_score(TRICKED_PLAYER_SCORE)
        notification = "{} voted for {}! +3".format(vote_from, vote_for)

    voter.update_player_state(PLAYER_STATES['VOTED'])

    if game.is_reveal_time():
        reveal_answers(game, game_id)
    if game.game_over():
        reveal_match_summary(game, game_id)

    game = convert_to_json(game)

    socketio.emit('renderScoreBoard', game["players"], room=game_id)
    socketio.emit("notification", notification, room=game_id)

@socketio.on('startnextround')
def on_nextround():
    game_id = get_game_id(request)
    game = GAME_ROOMS[game_id]

    game.reset_all_player_states()

    game.set_next_round_num()
    game = convert_to_json(game)
    socketio.emit("nextroundstarting", game, room=game_id)
    socketio.emit('renderScoreBoard', game["players"], room=game_id)

@socketio.on("sendmessage")
def on_send_message(data):
    game_id = get_game_id(request)
    message = { "player_name" : data['player_name'],
                "message" : strip_tags(data['message'])
              }
    socketio.emit("sendbackmessage", message, room=game_id)

@socketio.on('showsummary')
def on_summary():
    game_id = get_game_id(request)
    game = GAME_ROOMS[game_id]

    reveal_match_summary(game, game_id)

@socketio.on('message')
def on_message():
    pass

#Send data to generate all definitions submitted
def reveal_definitions(game, game_id):
    correct_definition = game.get_round_definition()
    game = convert_to_json(game)
    data = []
    for player in game['players']:
        data.append({
                    "player_name" : player['player_name'],
                   "definition" : player['definitions'][str(game['current_round_num'])]
                   })
    data.append({
                "player_name" : COMPUTER_NAME,
                "definition" : correct_definition
                })
    random.shuffle(data)
    socketio.emit("showdefinitions", data, room=game_id)

#Send data to reveal all answers and show who voted for each player
def reveal_answers(game, game_id):
    game_json = convert_to_json(game)
    data = []
    for player in game_json['players']:
        data.append({
                    "player_name" : player['player_name'],
                    "avatar" : player['avatar'],
                    "votes_for" : player['votes_for'][str(game_json['current_round_num'])]
                    })

    socketio.emit("revealanswers", convert_to_json(data), room=game_id)

def reveal_match_summary(game, game_id):

    game.calculate_winning_players()
    game.calculate_losing_players()
    game.calculate_player_most_correct_votes()
    game_json = convert_to_json(game)

    socketio.emit("showmatchsummary", game_json, room=game_id)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=8000)

#How to set up and run on server
#https://damyanon.net/post/flask-series-deployment/

#This was important to run with NGINX
#https://github.com/socketio/socket.io/issues/1942 otherwise had handshake errors
