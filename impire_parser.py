# -*- coding: utf-8 -*-
"""
impire_parser : Module which provides parsing function for Soccer
            position data based on the impire format.
        Individual parsers are provided for
            general match information data, match event data,
            and match position data.

@author: rein
@license: MIT
@version 0.1
"""
import xml.sax, xml.sax.handler
import datetime as dt
import dateutil.parser as dup
import numpy as np

class MatchInformationParser(xml.sax.handler.ContentHandler):
    """A XML parser for DFL match information files.
    
    Pulls out the pitch dimensions, and player information.
    Args:
    """

    def __init__(self):
        """Initialization of attributes."""
        self.inTeam = False
        self.inHomeTeam = False
        self.inPlayer = False
        self.currentPlayer = None
        self.teams = {'home': [], 'guest': [] }
        self.match = {'match-id': 0, 'home':'', 'guest':''}

    def startElement(self,name,attrs):
        """Gets called for every starting tag."""

        if name == 'event-metadata':
            self.match['match-id'] = attrs['event-key']

        elif name == "team":
            self.inTeam = True

        elif name=='team-metadata' and self.inTeam:
            role = attrs['alignment']
            teamID = attrs['team-key']
            if role == "home":
                self.inHomeTeam = True
                self.match['home'] = teamID
            elif role == "away":
                self.inHomeTeam = False
                self.match['guest'] = teamID
            else:
                raise NameError("Couldn't determine role")
        elif name == 'player':
            self.inPlayer = True

        elif name == "player-metadata" and self.inTeam:
            pid = attrs['player-key']
            trikot = int(attrs['uniform-number'])
            if 'position-event' in attrs.getNames():
                position = attrs['position-event']
            else:
                position = attrs['position-regular']
            self.currentPlayer = {
                        "id": pid,
                        "trikot": trikot,
                        "position": position
                    }

        elif name == 'name' and self.inPlayer:
            name = attrs['nickname']
            self.currentPlayer['name'] = name
            if self.inHomeTeam:
                self.teams['home'].append(self.currentPlayer.copy())
            else:
                self.teams['guest'].append(self.currentPlayer.copy())
            self.currentPlayer = None

    def endElement(self,name):
        """Gets called for every closing tag."""
        if name == "team":
            self.inTeam = False
        elif name == 'player':
            self.inPlayer = False
    
    def getTeamInformation(self):
        """Extractor function."""
        return self.teams, self.match
    
    def run(self,fname):
        """Runs the parse on fname."""
        parser = xml.sax.make_parser()
        parser.setContentHandler(self)
        # prevent external DTD load
        parser.setFeature(xml.sax.handler.feature_external_ges,False)
        parser.parse(fname)
        print 'finished parsing match information'


def convertTime(tstring):
    """ Converts time stamps into datetimes.
    
    convertTime converts the time string into a datetime.datetime
    object with added timezone information.
    
    Args:
        tstring: timestamp string
    Returns:
        A datetime object representing the timestamp.
    """    
    return dup.parse(tstring) 

def read_in_position_data(fname):
    """Reads in a pos file and extract the ball/player data
    Args:
    Returns:
    """

    # MAGIC NUMBER
    _MISSING_ = -10000.0
    NO_PLAYER = 11
    NO_DIM = 3      # FRAME, X, Z
    NO_DIM_BALL = 6     # FRAME, X, Y, Z, POSSESSION, STATUS

    no_frames = sum([1 for f in open(fname)])

    home_team = np.ones((no_frames,NO_PLAYER,NO_DIM)) * _MISSING_
    guest_team = home_team.copy()
    ball = np.ones((no_frames,6)) * _MISSING_
    half_time_id = np.ones(no_frames) * _MISSING_

    def process_player(player):
        """Extracts information from player-pos string"""
        data = player.split(',')
        pid = int(data[0])      # player identifier
        x = float(data[1])      # x-position
        y = float(data[2])      # y-position
        return [pid,x,y]

    for i,frame in enumerate(open(fname)):
        #0: Frame, 1: Home, 2: Guest, 3: Referee, 4: Ball
        hash_split = frame.split('#')
        frame_specs = hash_split[0][:-1].split(',')
        # get frame index
        frame = int(frame_specs[0])
        # half time index
        half_time_id[i] = int(frame_specs[2])
        # process home team
        for j,player in enumerate(hash_split[1][:-1].split(';')):
            home_team[i,j,:] = process_player(player)
        # process guest team
        for j,player in enumerate(hash_split[2][:-1].split(';')):
            guest_team[i,j,:] = process_player(player)
        # ball: frame, x, y, z, possession, status
        ball_data = hash_split[4][:-1].split(',')
        x = float(ball_data[0])
        y = float(ball_data[1])
        z = float(ball_data[2])
        poss = float(ball_data[5])
        status = float(ball_data[4])
        ball[i,:] = [frame,x,y,z,poss,status]

    return home_team, guest_team, ball, half_time_id

def sort_position_data(pos):
    """Sorts the position data according to player and period.
    """
    unique_player = np.unique(pos[:,:,0])
    res = []
    for pid in unique_player:
        res.append(pos[pos[:,:,0]==pid])
    return res

def read_stadium_dimensions_from_pos(fname):
    """Gets the stadium specifications from the pos file."""
    fid = open(fname,'r')
    line = fid.readline()
    fid.close()
    specs_string = line.split('#')[5].rstrip()[:-1].split(',')
    length = float(specs_string[1])
    width = float(specs_string[2])
    return dict(length=length ,width=width)


#######################################
if __name__ == "__main__":
    
    data_path = 'test/impire/'
    fname_specs = 'vistrack-matchfacts-123456.xml'
    fname_pos =  '123456.pos'
    
    print "Parsing match information"
    mip = MatchInformationParser()
    fname_match = data_path + fname_specs
    mip.run(fname_match)
    teams, match = mip.getTeamInformation()
    match['stadium'] = read_stadium_dimensions_from_pos(data_path + fname_pos)
    
    home,guest,ball,half_time_id = read_in_position_data(data_path + fname_pos)
    home_s = sort_position_data(home)

    """
    print "Parsing event data"
    mep = MatchEventParser()
    fname_info = data_path + "EventData/" + fname
    mep.run(fname_info)
    play_time, subs = mep.getEventInformation()
    
    print "Parsing position data"
    mpp = MatchPositionParser(match,teams)
    fname_pos = data_path + "/ObservedPositionalData/" + fname
    mpp.run(fname_pos)
    pos_data,ball_data,timestamps = mpp.getPositionInformation()
    """ 
