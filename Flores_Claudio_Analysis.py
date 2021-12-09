#%% Libraries
from utils import get_game_data, get_game_info, get_game_possessions, process_speed, smooth_speed, outlier_acceleration, outlier_speed
import pandas as pd
from matplotlib import pyplot as plt
from os import listdir

#%% Getting player posessions from game data dictionaries and transforming to dataframe
game_ids = [x for x in listdir('opendata-master//data//matches//')]

cols = ['game_id','player_id','team','frame','frame_aux','period','time','time_m','x','y','track_id','distance','time_delta','speed','team_name','last_name']
game_possessions = pd.DataFrame(columns=cols)

#for game_id in [game_ids[0]]:
for game_id in game_ids:
    
    game_info = get_game_info(game_id)
    home_team = game_info['home_team']['name']
    away_team = game_info['away_team']['name']
    players = pd.DataFrame(game_info['players'])    
    players = players.rename(columns= {'trackable_object':'player_id'})
    
    game_data = get_game_data(game_id)
    game_possessions_aux = get_game_possessions(game_data) 
    game_possessions_aux['frame_aux'] = game_possessions_aux.index
    game_possessions_aux = process_speed(game_possessions_aux)
    game_possessions_aux = smooth_speed(game_possessions_aux)
    game_possessions_aux['game_id'] = game_id
    
    game_possessions_aux['team_name'] = [home_team if x=='home team' else away_team if x=='away team' else None for x in game_possessions_aux['team']]
    game_possessions_aux = game_possessions_aux.merge(players[['player_id','last_name']],on=['player_id'],how='left')
    
    game_possessions = game_possessions.append(game_possessions_aux)
    
#%% Remove possessions where there are more than 1 player
player_count = game_possessions[['track_id','player_id']].drop_duplicates()
player_count = player_count.groupby('track_id').agg({'player_id':'count'})
game_possessions = game_possessions[game_possessions['track_id'].isin(player_count[player_count['player_id']==1].index)]

#%%  Smooth outliers
game_possessions = outlier_acceleration(game_possessions,0.999)
#game_possessions = outlier_speed(game_possessions,0.9995)

#%% Histogram of speeds
plt.hist(game_possessions.speed,bins=[x for x in range(10+1)])
print(game_possessions.speed.max())

#%% Histogram of distances
plt.hist(game_possessions.distance)
print(game_possessions.distance.max())

#%% Summary for possesions with a minimum distance covered
summary_speeds = game_possessions.groupby(['game_id','period','team_name','player_id','last_name','track_id']).agg({'distance':'sum','time_m':['count','min','max'],'speed':'max'})
summary_speeds = summary_speeds[summary_speeds[('time_m', 'count')]>1]
summary_speeds.columns = ['distance','n_records','time_start','time_end','speed_max']
summary_speeds['speed_average'] = summary_speeds['distance']/(summary_speeds['time_end']-summary_speeds['time_start'])/60
summary_speeds['Percentile_Max_Speed'] =  summary_speeds['speed_max'].rank(pct=True)
summary_speeds['Percentile_Avg_Speed'] =  summary_speeds['speed_average'].rank(pct=True)
summary_speeds = summary_speeds.reset_index()

#%% Top Average Speed
aux = summary_speeds.sort_values('speed_average',ascending=False).head(10)
print(aux[['team_name','last_name','game_id','track_id','speed_average']])

#%% Top Max Speed
aux = summary_speeds.sort_values('speed_max',ascending=False).head(10)
print(aux[['team_name','last_name','game_id','track_id','speed_max']])

#%% Count when Average Speed is in top percentile
percentile = 0.9
aux = summary_speeds[summary_speeds['Percentile_Avg_Speed']>percentile]
aux = aux.groupby(['team_name','last_name']).size().reset_index()
aux.columns = ['team_name','last_name','count']
aux = aux.sort_values('count',ascending=False).head(10)
print(aux)
      
#%% Count when Max Speed is in top percentile
percentile = 0.9
aux = summary_speeds[summary_speeds['Percentile_Max_Speed']>percentile]
aux = aux.groupby(['team_name','last_name']).size().reset_index()
aux.columns = ['team_name','last_name','count']
aux = aux.sort_values('count',ascending=False).head(10)
print(aux)
