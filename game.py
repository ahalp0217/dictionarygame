import datetime
import random
import json

#Game States
GAME_STATES = {
    "PREGAME" : "PREGAME",
    "INGAME" : "INGAME",
    "POSTGAME" : "POSTGAME"
}

#Round States
ROUND_STATES = {
    "SUBMISSION_TIME" : "SUBMISSION TIME",
    "VOTING_TIME" : "VOTING TIME",
    "ANSWER_TIME" : "ANSWER TIME"
}

#Player States
PLAYER_STATES = {
    "CONNECTED" : "CONNECTED",
    "READY" : "READY",
    "SUBMITTED" : "SUBMITTED",
    "VOTED" : "VOTED",
    "DISCONNECTED" : "DISCONNECTED"
}

#Scores
SELF_VOTED_SCORE = 0
CORRECT_DEFINITION_SCORE = 1
TRICKED_PLAYER_SCORE = 3

#Dictionary Definition "Player"
COMPUTER_NAME = "Dictionary Definition"

#Words data
STANDARD_WORDS_PATH = './words/words.csv'
NSFW_WORDS_PATH = './words/nsfwwords.csv'

class Game(object):
    """ Create a new game object."""

    def __init__(self, game_id, game_name, game_type, total_rounds, player):
        self.game_id = game_id
        self.game_type = game_type
        self.total_rounds = total_rounds
        self.game_name = game_name
        self.admin = player
        self.date_created = datetime.datetime.now().strftime("%Y-%m-%d %I:%M")
        self.word_set = self.generate_word_set(self.game_type, self.total_rounds)
        self.current_round_num = 1
        self.game_state = GAME_STATES["PREGAME"]
        self.round_state = ""
        self.players = []

    def __str__(self):
        return str(self.__class__) + ": " + self.to_json()

    def to_json(self):
        """Serialize object to JSON"""
        return json.dumps({ self.game_id : self.__dict__ })

    def generate_word_set(self, gametype, numrounds):
        randomWords = []
        if gametype == "NSFW":
            lines = open(NSFW_WORDS_PATH).read().splitlines()
        else:
            lines = open(STANDARD_WORDS_PATH).read().splitlines()
        for i in range(1, self.total_rounds + 1):
            line = random.choice(lines)
            word = line.split("|")[0]
            definition = line.split("|")[1]
            definition = definition[0].lower() + definition[1:]
            definition = definition.rstrip(".")
            randomWords.append({"word": word, "definition": })
        return randomWords

    def get_player_instance(self, player_name):
        for player in self.players:
            if player.player_name == player_name:
                return player
        return False

    def set_next_round_num(self):
        self.current_round_num += 1

    def get_round_num(self):
        return self.current_round_num

    def get_round_word(self):
        return self.word_set[self.current_round_num - 1]['word']

    def get_round_definition(self):
        return self.word_set[self.current_round_num - 1]['definition']

    def update_round_state(self, new_round_state):
        self.round_state = new_round_state
        return self.round_state

    def count_connected_players(self):
        total_connected = 0
        for player in self.players:
            if player.player_state != PLAYER_STATES['DISCONNECTED']:
                total_connected += 1
        return total_connected

    def count_number_submissions(self):
        total_submitted = 0
        for player in self.players:
            if self.current_round_num in player.definitions:
                total_submitted += 1
        return total_submitted

    def count_number_votes(self):
        total_votes = 0
        for player in self.players:
            if self.current_round_num in player.votes_for:
                total_votes += 1
        return total_votes

    def is_voting_time(self):
        total_connected = self.count_connected_players()
        total_submitted = self.count_number_submissions()
        if total_connected != total_submitted:
            return False
        return True

    def is_reveal_time(self):
        total_connected = self.count_connected_players()
        total_voted = self.count_number_votes()
        if total_connected != total_voted:
            return False
        return True

    def game_over(self):
        if self.current_round_num == len(self.word_set):
            return True
        return False

    def calculate_winning_players(self):
        winning_score = 0
        self.winning_players = []
        for player in self.players:
            if player.score > winning_score:
                winning_score = player.score
        for player in self.players:
            if player.score == winning_score:
                self.winning_players.append(player.player_name)
        return self.winning_players

    def calculate_player_most_correct_votes(self):
        most_correct_votes = 0
        self.most_correct_players = []
        for player in self.players:
            if player.correct_votes > most_correct_votes:
                most_correct_votes = player.correct_votes
        for player in self.players:
            if player.correct_votes == most_correct_votes:
                self.most_correct_players.append(player.player_name)
        return self.most_correct_players

    def calculate_losing_players(self):
        losing_score = 100000
        self.losing_players = []
        for player in self.players:
            if player.score < losing_score:
                losing_score = player.score
        for player in self.players:
            if player.score == losing_score:
                self.losing_players.append(player.player_name)
        return self.losing_players

    def remove_player(self, socket_id):
        for player in self.players:
            if player.player_id == socket_id:
                self.players.remove(player)
        return False

    def reset_all_player_states(self):
        for player in self.players:
            player.update_player_state(PLAYER_STATES["READY"])

class Player(object):
    """ Create a new player object. """

    def __init__(self, player_name, avatar):
        self.player_name = player_name
        self.score = 0
        self.player_state = PLAYER_STATES['CONNECTED']
        self.definitions = {}
        self.votes_for = {}
        self.votes_from = {}
        self.avatar = avatar
        self.player_id = None
        self.correct_votes = 0

    def __str__(self):
        return str(self.__class__) + ": " + self.to_json()

    def to_json(self):
        """Serialize object to JSON"""
        return json.dumps({ self.player_name : self.__dict__ })

    def increment_player_score(self, increase_score):
        self.score += increase_score

    def update_player_state(self, status):
        self.player_state = status

    def set_player_id(self, player_id):
        self.player_id = player_id

    def update_votes_for(self, player_name, round):
        self.votes_for[round] = player_name

    def update_votes_from(self, player_name, round):
        self.votes_from[round] = player_name

    def insert_definition(self, definition, round):
        self.definitions[round] = definition
