# -*- coding: utf-8 -*-

#%% Libraries

import json
import pandas as pd
import numpy as np

#%% Get game data

def get_json(game_id,file_name):    
    file_path = 'opendata-master//data//matches//'+str(game_id)+"//"
    with open(file_path+file_name,'r') as myfile:
        data = myfile.read()    
    file_json = json.loads(data)    
    return file_json

def get_game_info(game_id):    
    game_json = get_json(game_id,'match_data.json')    
    return game_json

def get_game_data(game_id):    
    game_json = get_json(game_id,'structured_data.json')    
    return game_json

def time_minutes(string_time):
    try:
        minute,seconds = string_time.split(':')
    except:
        return None
    minute = int(minute)
    seconds = float(seconds)
    time = minute+seconds/60
    return time

def get_game_possessions(game_data):
    
    #tracking with actual possession
    game_possession = [{
    'player_id':x['possession']['trackable_object'],
    'team':x['possession']['group'],
    'frame':x['frame'],
    'period':x['period'],
    'time':x['time'],
    'time_m':time_minutes(x['time']),
    'data':x['data']
    } 
    for x in game_data if x['possession']['trackable_object'] is not None]
    
    #unnesting coordenates of player with possession
    for i in range(len(game_possession)):
        try:
            coord = [x for x in game_possession[i]['data'] if game_possession[i]['player_id']==x.get('trackable_object')][0]
            game_possession[i]['x'] = coord['x']
            game_possession[i]['y'] = coord['y']
            game_possession[i]['track_id'] = coord['track_id']
        except:
            game_possession[i]['x'] = -999
            game_possession[i]['y'] = -999
            game_possession[i]['track_id'] = -999
        game_possession[i].pop('data',None)
    #transforming to dataframe
    game_possession = pd.DataFrame(game_possession)
    game_possession = game_possession[game_possession['track_id']!=-999]
    
    return game_possession

    
def process_speed(df):

    aux1 = df.copy()
    aux1['frame'] = aux1['frame']-1
    aux2 =  df.merge(aux1,on=['track_id','frame','player_id','period','team'],how='left')
    aux2['distance'] = np.linalg.norm(aux2[['x_x','y_x',]].values-aux2[['x_y','y_y',]].values,axis=1)
    aux2['time_delta'] = aux2['time_m_y']-aux2['time_m_x'] 
    aux2['speed'] = aux2['distance']/aux2['time_delta']/60
    aux2 = aux2.rename(columns={'x_x':'x','y_x':'y','time_x':'time','time_m_x':'time_m','frame_aux_x':'frame_aux'})
    cols = ['player_id','team','frame','frame_aux','period','time','time_m','x','y','track_id','distance','time_delta','speed']
    
    return aux2[cols]

  
def smooth_speed(df):
    
    cols = list(df)
    aux0,aux1,aux2 = df.copy(), df.copy(), df.copy()    
    aux1['frame_aux'] = aux1['frame_aux']-1
    aux2['frame_aux'] = aux2['frame_aux']+1
    
    cols_merge = ['track_id','frame_aux','player_id','period','team']
    aux =  aux0.merge(aux1,on=cols_merge,how='left')
    aux =  aux.merge(aux2,on=cols_merge,how='left')
    
    #len_issue = len(aux[~(aux['speed_x'].isna())&~(aux['speed_y'].isna())&~(aux['speed'].isna())&((aux['speed_x']<aux['speed'])&(aux['speed_x']<aux['speed_y'])|((aux['speed_x']>aux['speed'])&(aux['speed_x']>aux['speed_y'])))][['speed_x','speed_y','speed']])    
    #if len(len_issue)>0:
    aux['speed_x'] = [(s0+s2)/2 if ((s0 is not None)&(s1 is not None)&(s2 is not None)&((s1<min(s0,s2))|(s1>max(s0,s2)))) else s1 for s0,s1,s2 in zip(aux['speed'],aux['speed_x'],aux['speed_y'])]
    aux = aux.rename(columns={'x':'x_z','y':'y_z','time':'time_z','time_m':'time_m_z','frame':'frame_z','distance':'distance_z','time_delta':'time_delta_z','speed':'speed_z'})
    aux = aux.rename(columns={'x_x':'x','y_x':'y','time_x':'time','time_m_x':'time_m','frame_x':'frame','distance_x':'distance','time_delta_x':'time_delta','speed_x':'speed'})
    aux = aux[cols]
    #aux = smooth_speed(aux) #tried to make this function recursive but my pc is crushing... instead of recursive I could try an row by row approach
        
    return aux


def outlier_speed(df,percentile):
    aux = df.copy()
    cols = list(aux)
    aux['Percentile'] =  aux['speed'].rank(pct=True)    
    threshold = aux[aux.Percentile>percentile]['speed'].min()
    aux['speed'] = [s if s<threshold else threshold for s in aux['speed']]
    return aux[cols]


def outlier_acceleration(df,percentile):
    
    cols = list(df)
    aux0,aux1 = df.copy(),df.copy()    
    aux1['frame_aux'] = aux1['frame_aux']+1
    
    aux =  aux0.merge(aux1,on=['track_id','frame_aux','player_id','game_id','period','team','team_name','last_name'],how='left')
    aux['dif'] = abs(aux['speed_x']-aux['speed_y'])
    aux['Percentile'] =  aux['dif'].rank(pct=True)
    
    threshold = aux[aux.Percentile>percentile]['dif'].min()
    aux['speed_x'] = [s1 if d<threshold else s0+threshold for s1,s0,d in zip(aux['speed_x'],aux['speed_y'],aux['dif'])]
    
    aux = aux.rename(columns={'x_x':'x','y_x':'y','time_x':'time','time_m_x':'time_m','frame_x':'frame','distance_x':'distance','time_delta_x':'time_delta','speed_x':'speed'})
    aux = aux[cols]
    
    return aux
