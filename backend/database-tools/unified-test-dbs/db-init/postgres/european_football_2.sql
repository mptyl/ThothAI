-- PostgreSQL schema for european_football_2 database
CREATE DATABASE european_football_2;
\c european_football_2;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE Player_Attributes (
id INTEGER,
player_fifa_api_id INTEGER,
player_api_id INTEGER,
date TEXT,
overall_rating INTEGER,
potential INTEGER,
preferred_foot TEXT,
attacking_work_rate TEXT,
defensive_work_rate TEXT,
crossing INTEGER,
finishing INTEGER,
heading_accuracy INTEGER,
short_passing INTEGER,
volleys INTEGER,
dribbling INTEGER,
curve INTEGER,
free_kick_accuracy INTEGER,
long_passing INTEGER,
ball_control INTEGER,
acceleration INTEGER,
sprint_speed INTEGER,
agility INTEGER,
reactions INTEGER,
balance INTEGER,
shot_power INTEGER,
jumping INTEGER,
stamina INTEGER,
strength INTEGER,
long_shots INTEGER,
aggression INTEGER,
interceptions INTEGER,
positioning INTEGER,
vision INTEGER,
penalties INTEGER,
marking INTEGER,
standing_tackle INTEGER,
sliding_tackle INTEGER,
gk_diving INTEGER,
gk_handling INTEGER,
gk_kicking INTEGER,
gk_positioning INTEGER,
gk_reflexes INTEGER,
    PRIMARY KEY (id)
);

COMMENT ON COLUMN Player_Attributes.id IS 'the unique id for players';
COMMENT ON COLUMN Player_Attributes.player_fifa_api_id IS 'the id of the player fifa api';
COMMENT ON COLUMN Player_Attributes.player_api_id IS 'the id of the player api';
COMMENT ON COLUMN Player_Attributes.date IS 'date';
COMMENT ON COLUMN Player_Attributes.overall_rating IS 'the overall rating of the player';
COMMENT ON COLUMN Player_Attributes.potential IS 'potential of the player';
COMMENT ON COLUMN Player_Attributes.preferred_foot IS 'the player''s preferred foot when attacking';
COMMENT ON COLUMN Player_Attributes.attacking_work_rate IS 'the player''s attacking work rate';
COMMENT ON COLUMN Player_Attributes.defensive_work_rate IS 'the player''s defensive work rate';
COMMENT ON COLUMN Player_Attributes.crossing IS 'the player''s crossing score';
COMMENT ON COLUMN Player_Attributes.finishing IS 'the player''s finishing rate';
COMMENT ON COLUMN Player_Attributes.heading_accuracy IS 'the player''s heading accuracy';
COMMENT ON COLUMN Player_Attributes.short_passing IS 'the player''s short passing score';
COMMENT ON COLUMN Player_Attributes.volleys IS 'the player''s volley score';
COMMENT ON COLUMN Player_Attributes.dribbling IS 'the player''s dribbling score';
COMMENT ON COLUMN Player_Attributes.curve IS 'the player''s curve score';
COMMENT ON COLUMN Player_Attributes.free_kick_accuracy IS 'the player''s free kick accuracy';
COMMENT ON COLUMN Player_Attributes.long_passing IS 'the player''s long passing score';
COMMENT ON COLUMN Player_Attributes.ball_control IS 'the player''s ball control score';
COMMENT ON COLUMN Player_Attributes.acceleration IS 'the player''s acceleration score';
COMMENT ON COLUMN Player_Attributes.sprint_speed IS 'the player''s sprint speed';
COMMENT ON COLUMN Player_Attributes.agility IS 'the player''s agility';
COMMENT ON COLUMN Player_Attributes.reactions IS 'the player''s reactions score';
COMMENT ON COLUMN Player_Attributes.balance IS 'the player''s balance score';
COMMENT ON COLUMN Player_Attributes.shot_power IS 'the player''s shot power';
COMMENT ON COLUMN Player_Attributes.jumping IS 'the player''s jumping score';
COMMENT ON COLUMN Player_Attributes.stamina IS 'the player''s stamina score';
COMMENT ON COLUMN Player_Attributes.strength IS 'the player''s strength score';
COMMENT ON COLUMN Player_Attributes.long_shots IS 'the player''s long shots score';
COMMENT ON COLUMN Player_Attributes.aggression IS 'the player''s aggression score';
COMMENT ON COLUMN Player_Attributes.interceptions IS 'the player''s interceptions score';
COMMENT ON COLUMN Player_Attributes.positioning IS 'the player''s 
positioning score';
COMMENT ON COLUMN Player_Attributes.vision IS 'the player''s vision score';
COMMENT ON COLUMN Player_Attributes.penalties IS 'the player''s penalties score';
COMMENT ON COLUMN Player_Attributes.marking IS 'the player''s markingscore';
COMMENT ON COLUMN Player_Attributes.standing_tackle IS 'the player''s standing tackle score';
COMMENT ON COLUMN Player_Attributes.sliding_tackle IS 'the player''s sliding tackle score';
COMMENT ON COLUMN Player_Attributes.gk_diving IS 'the player''s goalkeep diving score';
COMMENT ON COLUMN Player_Attributes.gk_handling IS 'the player''s goalkeep diving score';
COMMENT ON COLUMN Player_Attributes.gk_kicking IS 'the player''s goalkeep kicking score';
COMMENT ON COLUMN Player_Attributes.gk_positioning IS 'the player''s goalkeep positioning score';
COMMENT ON COLUMN Player_Attributes.gk_reflexes IS 'the player''s goalkeep reflexes score';

CREATE TABLE Player (
id INTEGER,
player_api_id INTEGER,
player_name TEXT,
player_fifa_api_id INTEGER,
birthday TEXT,
height INTEGER,
weight INTEGER,
    PRIMARY KEY (id)
);

COMMENT ON COLUMN Player.id IS 'the unique id for players';
COMMENT ON COLUMN Player.player_api_id IS 'the id of the player api';
COMMENT ON COLUMN Player.player_name IS 'player name';
COMMENT ON COLUMN Player.player_fifa_api_id IS 'the id of the player fifa api';
COMMENT ON COLUMN Player.birthday IS 'the player''s birthday';
COMMENT ON COLUMN Player.height IS 'the player''s height';
COMMENT ON COLUMN Player.weight IS 'the player''s weight';

CREATE TABLE League (
id INTEGER,
country_id INTEGER,
name TEXT,
    PRIMARY KEY (id)
);

COMMENT ON COLUMN League.id IS 'the unique id for leagues';
COMMENT ON COLUMN League.country_id IS 'the unique id for countries';
COMMENT ON COLUMN League.name IS 'league name';

CREATE TABLE Country (
id INTEGER,
name TEXT,
    PRIMARY KEY (id)
);

COMMENT ON COLUMN Country.id IS 'the unique id for countries';
COMMENT ON COLUMN Country.name IS 'country name';

CREATE TABLE Team (
id INTEGER,
team_api_id INTEGER,
team_fifa_api_id INTEGER,
team_long_name TEXT,
team_short_name TEXT,
    PRIMARY KEY (id)
);

COMMENT ON COLUMN Team.id IS 'the unique id for teams';
COMMENT ON COLUMN Team.team_api_id IS 'the id of the team api';
COMMENT ON COLUMN Team.team_fifa_api_id IS 'the id of the team fifa api';
COMMENT ON COLUMN Team.team_long_name IS 'the team''s long name';
COMMENT ON COLUMN Team.team_short_name IS 'the team''s short name';

CREATE TABLE Team_Attributes (
id INTEGER,
team_fifa_api_id INTEGER,
team_api_id INTEGER,
date TEXT,
buildUpPlaySpeed INTEGER,
buildUpPlaySpeedClass TEXT,
buildUpPlayDribbling INTEGER,
buildUpPlayDribblingClass TEXT,
buildUpPlayPassing INTEGER,
buildUpPlayPassingClass TEXT,
buildUpPlayPositioningClass TEXT,
chanceCreationPassing INTEGER,
chanceCreationPassingClass TEXT,
chanceCreationCrossing INTEGER,
chanceCreationCrossingClass TEXT,
chanceCreationShooting INTEGER,
chanceCreationShootingClass TEXT,
chanceCreationPositioningClass TEXT,
defencePressure INTEGER,
defencePressureClass TEXT,
defenceAggression INTEGER,
defenceAggressionClass TEXT,
defenceTeamWidth INTEGER,
defenceTeamWidthClass TEXT,
defenceDefenderLineClass TEXT,
    PRIMARY KEY (id)
);

COMMENT ON COLUMN Team_Attributes.id IS 'the unique id for teams';
COMMENT ON COLUMN Team_Attributes.team_fifa_api_id IS 'the id of the team fifa api';
COMMENT ON COLUMN Team_Attributes.team_api_id IS 'the id of the team api';
COMMENT ON COLUMN Team_Attributes.date IS 'Date';
COMMENT ON COLUMN Team_Attributes.buildUpPlaySpeed IS 'the speed in which attacks are put together';
COMMENT ON COLUMN Team_Attributes.buildUpPlaySpeedClass IS 'the speed class';
COMMENT ON COLUMN Team_Attributes.buildUpPlayDribbling IS 'the tendency/ frequency of dribbling';
COMMENT ON COLUMN Team_Attributes.buildUpPlayDribblingClass IS 'the dribbling class';
COMMENT ON COLUMN Team_Attributes.buildUpPlayPassing IS 'affects passing distance and support from teammates';
COMMENT ON COLUMN Team_Attributes.buildUpPlayPassingClass IS 'the passing class';
COMMENT ON COLUMN Team_Attributes.buildUpPlayPositioningClass IS 'A team''s freedom of movement in the 1st two thirds of the pitch';
COMMENT ON COLUMN Team_Attributes.chanceCreationPassing IS 'Amount of risk in pass decision and run support';
COMMENT ON COLUMN Team_Attributes.chanceCreationPassingClass IS 'the chance creation passing class';
COMMENT ON COLUMN Team_Attributes.chanceCreationCrossing IS 'The tendency / frequency of crosses into the box';
COMMENT ON COLUMN Team_Attributes.chanceCreationCrossingClass IS 'the chance creation crossing class';
COMMENT ON COLUMN Team_Attributes.chanceCreationShooting IS 'The tendency / frequency of shots taken';
COMMENT ON COLUMN Team_Attributes.chanceCreationShootingClass IS 'the chance creation shooting class';
COMMENT ON COLUMN Team_Attributes.chanceCreationPositioningClass IS 'A teams freedom of movement in the final third of the pitch';
COMMENT ON COLUMN Team_Attributes.defencePressure IS 'Affects how high up the pitch the team will start pressuring';
COMMENT ON COLUMN Team_Attributes.defencePressureClass IS 'the defence pressure class';
COMMENT ON COLUMN Team_Attributes.defenceAggression IS 'Affect the teams approach to tackling the ball possessor';
COMMENT ON COLUMN Team_Attributes.defenceAggressionClass IS 'the defence aggression class';
COMMENT ON COLUMN Team_Attributes.defenceTeamWidth IS 'Affects how much the team will shift to the ball side';
COMMENT ON COLUMN Team_Attributes.defenceTeamWidthClass IS 'the defence team width class';
COMMENT ON COLUMN Team_Attributes.defenceDefenderLineClass IS 'Affects the shape and strategy of the defence';

CREATE TABLE Match (
id INTEGER,
country_id INTEGER,
league_id INTEGER,
season TEXT,
stage INTEGER,
date TEXT,
match_api_id INTEGER,
home_team_api_id INTEGER,
away_team_api_id INTEGER,
home_team_goal INTEGER,
away_team_goal INTEGER,
home_player_X1 INTEGER,
home_player_X2 INTEGER,
home_player_X3 INTEGER,
home_player_X4 INTEGER,
home_player_X5 INTEGER,
home_player_X6 INTEGER,
home_player_X7 INTEGER,
home_player_X8 INTEGER,
home_player_X9 INTEGER,
home_player_X10 INTEGER,
home_player_X11 INTEGER,
away_player_X1 INTEGER,
away_player_X2 INTEGER,
away_player_X3 INTEGER,
away_player_X4 INTEGER,
away_player_X5 INTEGER,
away_player_X6 INTEGER,
away_player_X7 INTEGER,
away_player_X8 INTEGER,
away_player_X9 INTEGER,
away_player_X10 INTEGER,
away_player_X11 INTEGER,
home_player_Y1 INTEGER,
home_player_Y2 INTEGER,
home_player_Y3 INTEGER,
home_player_Y4 INTEGER,
home_player_Y5 INTEGER,
home_player_Y6 INTEGER,
home_player_Y7 INTEGER,
home_player_Y8 INTEGER,
home_player_Y9 INTEGER,
home_player_Y10 INTEGER,
home_player_Y11 INTEGER,
away_player_Y1 INTEGER,
away_player_Y2 INTEGER,
away_player_Y3 INTEGER,
away_player_Y4 INTEGER,
away_player_Y5 INTEGER,
away_player_Y6 INTEGER,
away_player_Y7 INTEGER,
away_player_Y8 INTEGER,
away_player_Y9 INTEGER,
away_player_Y10 INTEGER,
away_player_Y11 INTEGER,
home_player_1 INTEGER,
home_player_2 INTEGER,
home_player_3 INTEGER,
home_player_4 INTEGER,
home_player_5 INTEGER,
home_player_6 INTEGER,
home_player_7 INTEGER,
home_player_8 INTEGER,
home_player_9 INTEGER,
home_player_10 INTEGER,
home_player_11 INTEGER,
away_player_1 INTEGER,
away_player_2 INTEGER,
away_player_3 INTEGER,
away_player_4 INTEGER,
away_player_5 INTEGER,
away_player_6 INTEGER,
away_player_7 INTEGER,
away_player_8 INTEGER,
away_player_9 INTEGER,
away_player_10 INTEGER,
away_player_11 INTEGER,
goal TEXT,
shoton TEXT,
shotoff TEXT,
foulcommit TEXT,
card TEXT,
cross TEXT,
corner TEXT,
possession TEXT,
B365H DECIMAL(10,2),
B365D DECIMAL(10,2),
B365A DECIMAL(10,2),
BWH DECIMAL(10,2),
BWD DECIMAL(10,2),
BWA DECIMAL(10,2),
IWH DECIMAL(10,2),
IWD DECIMAL(10,2),
IWA DECIMAL(10,2),
LBH DECIMAL(10,2),
LBD DECIMAL(10,2),
LBA DECIMAL(10,2),
PSH DECIMAL(10,2),
PSD DECIMAL(10,2),
PSA DECIMAL(10,2),
WHH DECIMAL(10,2),
WHD DECIMAL(10,2),
WHA DECIMAL(10,2),
SJH DECIMAL(10,2),
SJD DECIMAL(10,2),
SJA DECIMAL(10,2),
VCH DECIMAL(10,2),
VCD DECIMAL(10,2),
VCA DECIMAL(10,2),
GBH DECIMAL(10,2),
GBD DECIMAL(10,2),
GBA DECIMAL(10,2),
BSH DECIMAL(10,2),
BSD DECIMAL(10,2),
BSA DECIMAL(10,2),
    PRIMARY KEY (id)
);

COMMENT ON COLUMN Match.id IS 'the unique id for matches';
COMMENT ON COLUMN Match.country_id IS 'country id';
COMMENT ON COLUMN Match.league_id IS 'league id';
COMMENT ON COLUMN Match.season IS 'the season of the match';
COMMENT ON COLUMN Match.stage IS 'the stage of the match';
COMMENT ON COLUMN Match.date IS 'the date of the match';
COMMENT ON COLUMN Match.match_api_id IS 'the id of the match api';
COMMENT ON COLUMN Match.home_team_api_id IS 'the id of the home team api';
COMMENT ON COLUMN Match.away_team_api_id IS 'the id of the away team api';
COMMENT ON COLUMN Match.home_team_goal IS 'the goal of the home team';
COMMENT ON COLUMN Match.away_team_goal IS 'the goal of the away team';
COMMENT ON COLUMN Match.goal IS 'the goal of the match';
COMMENT ON COLUMN Match.shoton IS 'the shot on goal of the match';
COMMENT ON COLUMN Match.shotoff IS 'the shot off goal of the match, which is the opposite of shot on';
COMMENT ON COLUMN Match.foulcommit IS 'the fouls occurred in the match';
COMMENT ON COLUMN Match.card IS 'the cards given in the match';
COMMENT ON COLUMN Match.cross IS 'Balls sent into the opposition team''s area from a wide position in the match';
COMMENT ON COLUMN Match.corner IS 'Ball goes out of play for a corner kick in the match';
COMMENT ON COLUMN Match.possession IS 'The duration from a player taking over the ball in the match';

