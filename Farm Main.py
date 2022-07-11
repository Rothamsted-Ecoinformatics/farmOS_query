import configparser
from farmOS import farmOS
import csv
import json
import time
from progress.bar import Bar   #ONLY FOR VISUAL

W  = '\033[0m'   
R  = '\033[1;31m'
DR = '\033[0;31m'
G  = '\033[1;32m'
DG = '\033[0;32m'
C  = '\033[1;36m'
V  = '\033[0;35m'
P  = '\033[1;35m' 
B  = '\033[0;36m'

import_API = True
print()

if import_API == True:
    config = configparser.ConfigParser()
    read = config.read("config.ini",encoding="utf-8")
    sections = config.sections()
    
    hostname = config["AUTHENTICATE"].get("hostname")
    username = config["AUTHENTICATE"]["username"]
    password = config["AUTHENTICATE"]["password"]
    
    
    # Create the client.
    farm_client = farmOS(
        hostname=hostname,
        client_id = "farm", # Optional. The default oauth client_id "farm" is enabled on all farmOS servers.
        scope="farm_manager" # Optional. The default scope is "user_access". Only needed if authorizing with a differnt scope.
    )
    
    # Authorize the client, save the token.
    token = farm_client.authorize(username, password, scope="farm_manager")

#log_mods = ['activity', 'input', 'drilling', 'harvest', 'observation', 'seeding']
log_mods = ['harvest']

start_time = time.time()

imported = {'user': {'user': {}},
            'taxonomy_term': {'log_category': {}},
            'asset': {'land': {},
                      'equipment': {},
                      'plant': {}},
            'quantity':{'standard':{},
                        'material': {}}
            }

for mod in log_mods:
    
    if import_API == True:
        current_time = time.time()
        print(C + 'Importing ' + mod + ' mod Data...')
        
        response = farm_client.log.get(mod)
        id_list = []
        count = 0
        for client in response['data']:
            count += 1
            info = None
            if (client['attributes']['notes'] != None):
                description = client['attributes']['notes']['value']
            else: 
                description = None
            id_list.append({'Action': client['attributes']['name'],
                                  'Link': client['links']['self']['href'],
                                  'TimeStamp': client['attributes']['timestamp'],
                                  'Description': description,
                                  'Relationships': []})
            for relationship in client['relationships']:
                data = client['relationships'][relationship]['data']
                if type(data) == list:
                    if(data != []):
                        for row in data:
                            id_list[-1]['Relationships'].append({'Relationship': relationship, 
                                                                       'Type': row['type'], 
                                                                       'Id': row['id']})
                else:
                    id_list[-1]['Relationships'].append({'Relationship': relationship, 
                                                               'Type': data['type'], 
                                                               'Id': data['id']})
                processing = ((str(count) + '/' + str(len(response['data']))))
            bar = Bar(C+processing+B, max=len(id_list[-1]['Relationships']))
            for relationship in id_list[-1]['Relationships']:
                relationship['Info'] = {}
                if relationship['Type'] == 'user--user':
                    if(relationship['Id'] not in imported['user']['user']):
                        imported['user']['user'][relationship['Id']] = farm_client.resource.get_id("user","user",relationship['Id'])
                    user = imported['user']['user'][relationship['Id']]
                    display_name = user['data']['attributes']['display_name']
                    if display_name != 'Anonymous':
                        relationship['Info']['Name'] = user['data']['attributes']['name']
                        relationship['Info']['Mail'] = user['data']['attributes']['mail']
                        relationship['Info']['TimeZone'] = user['data']['attributes']['timezone']
                        relationship['Info']['LastUpdate'] = user['data']['attributes']['changed']
                    else:
                        relationship['Info']['Name'] = 'Anonymous'
                elif relationship['Type'] == 'taxonomy_term--log_category':
                    if(relationship['Id'] not in imported['taxonomy_term']['log_category']):
                        imported['taxonomy_term']['log_category'][relationship['Id']] = farm_client.resource.get_id("taxonomy_term","log_category",relationship['Id']) 
                    category = imported['taxonomy_term']['log_category'][relationship['Id']]
                    relationship['Info']['Name'] = category['data']['attributes']['name']
                    relationship['Info']['LastUpdate'] = category['data']['attributes']['changed']
                    if category['data']['attributes']['description'] != None:
                        relationship['Info']['Description'] = category['data']['attributes']['description']['value']
                    elif 'notes' in category['data']['attributes']:
                        if category['data']['attributes']['notes'] != None:
                            relationship['Info']['Description'] = category['data']['attributes']['notes']['value']
                elif relationship['Type'] == 'asset--land':
                    if(relationship['Id'] not in imported['asset']['land']):
                        imported['asset']['land'][relationship['Id']] = farm_client.resource.get_id("asset","land",relationship['Id']) 
                    land = imported['asset']['land'][relationship['Id']]
                    relationship['Info']['Name'] = land['data']['attributes']['name']
                    relationship['Info']['LastUpdate'] = land['data']['attributes']['changed']
                    relationship['Info']['Type'] = land['data']['attributes']['land_type']
                    if land['data']['attributes']['geometry'] != None:
                        relationship['Info']['Latitude'] = land['data']['attributes']['geometry']['lat']
                        relationship['Info']['Longitude'] = land['data']['attributes']['geometry']['lon']
                elif relationship['Type'] == 'quantity--standard':
                    if(relationship['Id'] not in imported['quantity']['standard']):
                        imported['quantity']['standard'][relationship['Id']] = [farm_client.resource.get_id("quantity","standard",relationship['Id'])]
                        imported['quantity']['standard'][relationship['Id']].append(farm_client.term.get_id("unit", imported['quantity']['standard'][relationship['Id']][0]['data']['relationships']['units']['data']['id']))
                    standard = imported['quantity']['standard'][relationship['Id']][0]
                    unit_query = imported['quantity']['standard'][relationship['Id']][1]
                    unit_name = unit_query['data']['attributes']['name']
                    relationship['Info']['Measure'] = standard['data']['attributes']['measure']
                    relationship['Info']['LastUpdate'] = standard['data']['attributes']['changed']
                    if standard['data']['attributes']['value'] != None:
                        relationship['Info']['Value'] = standard['data']['attributes']['value']['decimal']
                    relationship['Info']['Unit'] = unit_name
                elif relationship['Type'] == 'quantity--material':
                    if(relationship['Id'] not in imported['quantity']['material']):
                        imported['quantity']['material'][relationship['Id']] = [farm_client.resource.get_id("quantity","material",relationship['Id'])]
                        if(imported['quantity']['material'][relationship['Id']][0]['data']['relationships']['material_type']['data'] != None):
                            imported['quantity']['material'][relationship['Id']].append(farm_client.term.get_id("material_type", imported['quantity']['material'][relationship['Id']][0]['data']['relationships']['material_type']['data']['id']))
                    material = imported['quantity']['material'][relationship['Id']][0]
                    if(material['data']['relationships']['material_type']['data'] != None):
                        mat_query = imported['quantity']['material'][relationship['Id']][1]
                        mat_name = mat_query['data']['attributes']['name']
                        relationship['Info']['Name'] = mat_name
                        if mat_query['data']['attributes']['description'] != None:
                            mat_description = mat_query['data']['attributes']['description']['value']
                            relationship['Info']['Description'] = mat_description
                        relationship['Info']['LastUpdate'] = material['data']['attributes']['changed']
                elif relationship['Type'] == 'asset--equipment':
                    if(relationship['Id'] not in imported['asset']['equipment']):
                        imported['asset']['equipment'][relationship['Id']] = farm_client.resource.get_id("asset","equipment",relationship['Id']) 
                    equipment = imported['asset']['equipment'][relationship['Id']]
                    relationship['Info']['Name'] = equipment['data']['attributes']['name']
                    relationship['Info']['LastUpdate'] = equipment['data']['attributes']['changed']
                    if equipment['data']['attributes']['notes'] != None:
                        relationship['Info']['Description'] = equipment['data']['attributes']['notes']['value']
                elif relationship['Type'] == 'asset--plant':
                    if(relationship['Id'] not in imported['asset']['plant']):
                        imported['asset']['plant'][relationship['Id']] = [farm_client.resource.get_id("asset","plant",relationship['Id'])]
                        imported['asset']['plant'][relationship['Id']].append(farm_client.resource.get_id("taxonomy_term","plant_type", imported['asset']['plant'][relationship['Id']][0]['data']['relationships']['plant_type']['data'][0]['id']))
                    plant = imported['asset']['plant'][relationship['Id']][0]
                    plant_type = imported['asset']['plant'][relationship['Id']][1]
                    relationship['Info']['Name'] = plant['data']['attributes']['name']
                    relationship['Info']['LastUpdate'] = plant['data']['attributes']['changed']
                    relationship['Info']['Type'] = plant_type['data']['attributes']['name']
                bar.next()
            bar.finish()
        with open(('json/' + mod + '.json'), 'w') as outfile:
            json.dump({'Data': id_list}, outfile) 
        end_time = time.time()
        total_time = round((end_time - current_time), 1)
        time_string = ''
        if total_time > 60:
            minute = 0
            while total_time > 60:
                minute += 1
                total_time -= 60
            time_string += str(minute) + " mn "
        time_string += str(round(total_time)) + " sec"
        print()
        print(V+ mod + " Data regrouped in " + time_string+W)
        print()

###########################################################################################
    
    outfile = open('json/' + mod + '.json')
    data = json.load(outfile)
    outfile.close()
    lines = []
    
    for action in data['Data']:
        lines += ['Action:', '\t' + action['Action'], '', 
                  'Link:', '\t' + action['Link'], '']
        if action['Description'] != None:
            lines += ['Description: ', '\t"' + action['Description'].replace('\r','').replace('<p>','').replace('<\p>','') + '"', '']
        lines += ['Informations:']
        for rel in action['Relationships']:
            Type = rel['Type']
            if rel['Type'] != 'log_type--log_type':
                lines += ['\t> ' + rel['Relationship'] + f'({Type})']
                for info in rel['Info']:
                    element = rel['Info'][info]
                    if info == 'Description':
                        des = element.replace('\r','').replace('<p>','').replace('<\p>','')
                        lines += [f'\t\t- {info}: "{des}"']
                    else:
                        lines += [f'\t\t- {info}: {element}']
        lines += ['', '==============================================================================================', '']
        
    with open(('text/' + mod + '.txt'), 'w') as file:
        for line in lines:
            file.write(line)
            file.write('\n') 
        file.close()
        
#############################################################################################

    if (mod != 'drilling' and mod != 'seeding'):

        measure_type = ['rate', 'volume', 'area', 'time', 'length', 'count', 'weight', None]
        measure_titles = ['rate', 'volume', 'area', 'time', 'length', 'count', 'weight', 'None type']
        
        with open(('csv/' + mod + '.csv'), mode='w', newline='') as f:
            w = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            titles = ['log ID', 'log date', 'log title', 'field name', 'experiment ID', 'owner', 
                      'category', 'revision date', 'equipment'] + measure_titles + ['material']
            w.writerow(titles)
            for action in data['Data']:
                log_id = action['Link'].split('/')[-1]
                log_date = action['TimeStamp']
                log_title = action['Action']
                field_name = ''
                exp_id = ''
                owner = ''
                category = ''
                revision = ''
                equip = ''
                seed = ''
                standard = [''] * len(measure_type)
                materials = ''
                for rel in action['Relationships']:
                    if rel['Relationship'] == 'location':
                        if rel['Info']['Type'] != 'bed':
                            if field_name == '':
                                field_name = rel['Info']['Name']
                            else:
                                field_name += ', ' + rel['Info']['Name']
                        else:
                            if exp_id == '':
                                exp_id = rel['Info']['Name']
                            else:
                                exp_id += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'owner':
                        if owner == '':
                            owner = rel['Info']['Name']
                        else:
                            owner += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'category':
                        if category == '':
                            category = rel['Info']['Name']
                        else:
                            category += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'uid':
                        if revision == '':
                            revision = rel['Info']['LastUpdate']
                        else:
                            revision += ', ' + rel['Info']['LastUpdate']
                    elif rel['Relationship'] == 'equipment':
                        if equip == '':
                            equip = rel['Info']['Name']
                        else:
                            equip += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'quantity':
                        if rel['Type'] == 'quantity--standard':
                            for index in range(len(measure_type)):
                                if measure_type[index] == rel['Info']['Measure']:
                                    if 'Value' in rel['Info']:
                                        if standard[index] == '':
                                            standard[index] = (rel['Info']['Value'] + ' ' + 
                                                               rel['Info']['Unit'])
                                        else:
                                            standard[index] += ', ' + (rel['Info']['Value'] + ' ' + 
                                                               rel['Info']['Unit'])
                        elif rel['Type'] == 'quantity--material':
                            if('Name' in rel['Info']):
                                if materials == '':
                                    materials = rel['Info']['Name']
                                else:
                                    materials += ', ' + rel['Info']['Name']
        
                w.writerow([log_id, log_date, log_title, field_name, exp_id, owner, 
                            category, revision, equip] + standard + [materials])

###################################################################################################
                
    elif mod == 'seeding':
        measure_type = ['rate', 'volume', 'area', 'time', 'length', 'count', 'weight', None]
        measure_titles = ['seeds/m2', 'kg/ha', 'rate', 'volume', 'area', 'time', 'length', 'count', 'weight', 'None type']
        
        with open(('csv/' + mod + '.csv'), mode='w', newline='') as f:
            w = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            titles = ['log ID', 'log date', 'log title', 'field name', 'experiment ID', 'owner', 
                      'category', 'revision date', 'equipment', 'seed'] + measure_titles + ['material']
            w.writerow(titles)
            for action in data['Data']:
                log_id = action['Link'].split('/')[-1]
                log_date = action['TimeStamp']
                log_title = action['Action']
                field_name = ''
                exp_id = ''
                owner = ''
                category = ''
                revision = ''
                equip = ''
                seed = ''
                standard = [''] * (len(measure_type)+2)
                materials = ''
                for rel in action['Relationships']:
                    if rel['Relationship'] == 'location':
                        if rel['Info']['Type'] != 'bed':
                            if field_name == '':
                                field_name = rel['Info']['Name']
                            else:
                                field_name += ', ' + rel['Info']['Name']
                        else:
                            if exp_id == '':
                                exp_id = rel['Info']['Name']
                            else:
                                exp_id += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'owner':
                        if owner == '':
                            owner = rel['Info']['Name']
                        else:
                            owner += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'category':
                        if category == '':
                            category = rel['Info']['Name']
                        else:
                            category += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'uid':
                        if revision == '':
                            revision = rel['Info']['LastUpdate']
                        else:
                            revision += ', ' + rel['Info']['LastUpdate']
                    elif rel['Relationship'] == 'equipment':
                        if equip == '':
                            equip = rel['Info']['Name']
                        else:
                            equip += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'asset':
                        if seed == '':
                            seed = rel['Info']['Name'] + ' (' + rel['Info']['Type'] + ')'
                        else:
                            seed += ', ' + rel['Info']['Name'] + ' (' + rel['Info']['Type'] + ')'
                    elif rel['Relationship'] == 'quantity':
                        if rel['Type'] == 'quantity--standard':
                            for index in range(len(measure_type)):
                                if measure_type[index] == rel['Info']['Measure']:
                                    if 'Value' in rel['Info']:
                                        if standard[index+2] == '':
                                            standard[index+2] = (rel['Info']['Value'] + ' ' + 
                                                               rel['Info']['Unit'])
                                        else:
                                            standard[index+2] += ', ' + (rel['Info']['Value'] + ' ' + 
                                                               rel['Info']['Unit'])
                        elif rel['Type'] == 'quantity--material':
                            if('Name' in rel['Info']):
                                if materials == '':
                                    materials = rel['Info']['Name']
                                else:
                                    materials += ', ' + rel['Info']['Name']
                if mod == 'drilling':
                    hours_list = standard[7].replace('hours','').split(',')
                    standard[7] = str(round(float(hours_list[1]) - float(hours_list[0]),1)) + ' hours'
                
                std_list = standard[2].split(',')
                standard[2] = ''
                for std in std_list:
                    if ' seeds/m2' in std:
                        to_add = int(std.replace(' seeds/m2',''))
                        if standard[0] == '':
                            standard[0] = to_add
                        else:
                            standard[0] += ',' + to_add
                    elif ' seeds per metre squared (seeds/m^2)' in std:
                        to_add = int(std.replace(' seeds per metre squared (seeds/m^2)',''))
                        if standard[0] == '':
                            standard[0] = to_add
                        else:
                            standard[0] += ',' + to_add
                    elif ' kg/ha' in std:
                        to_add = float(std.replace(' kg/ha',''))
                        if standard[1] == '':
                            standard[1] = to_add
                        else:
                            standard[1] += ',' + to_add
                    else:
                        if standard[2] == '':
                            standard[2] = std
                        else:
                            standard[2] += ',' + std
        
                w.writerow([log_id, log_date, log_title, field_name, exp_id, owner, 
                            category, revision, equip, seed] + standard + [materials])
    
    else:
        measure_type = ['rate', 'volume', 'area', 'time', 'length', 'weight', None, 'count']
        measure_titles = ['seeds/m2', 'kg/ha', 'rate', 'volume', 'area', 'time', 'length', 'weight', 'None type', 'count', 'start', 'end']
        
        with open(('csv/' + mod + '.csv'), mode='w', newline='') as f:
            w = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            titles = ['log ID', 'log date', 'log title', 'field name', 'experiment ID', 'owner', 
                      'category', 'revision date', 'equipment', 'seed'] + measure_titles + ['material']
            w.writerow(titles)
            for action in data['Data']:
                log_id = action['Link'].split('/')[-1]
                log_date = action['TimeStamp']
                log_title = action['Action']
                field_name = ''
                exp_id = ''
                owner = ''
                category = ''
                revision = ''
                equip = ''
                seed = ''
                standard = [''] * len(measure_titles)
                materials = ''
                for rel in action['Relationships']:
                    if rel['Relationship'] == 'location':
                        if rel['Info']['Type'] != 'bed':
                            if field_name == '':
                                field_name = rel['Info']['Name']
                            else:
                                field_name += ', ' + rel['Info']['Name']
                        else:
                            if exp_id == '':
                                exp_id = rel['Info']['Name']
                            else:
                                exp_id += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'owner':
                        if owner == '':
                            owner = rel['Info']['Name']
                        else:
                            owner += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'category':
                        if category == '':
                            category = rel['Info']['Name']
                        else:
                            category += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'uid':
                        if revision == '':
                            revision = rel['Info']['LastUpdate']
                        else:
                            revision += ', ' + rel['Info']['LastUpdate']
                    elif rel['Relationship'] == 'equipment':
                        if equip == '':
                            equip = rel['Info']['Name']
                        else:
                            equip += ', ' + rel['Info']['Name']
                    elif rel['Relationship'] == 'asset':
                        if seed == '':
                            seed = rel['Info']['Name'] + ' (' + rel['Info']['Type'] + ')'
                        else:
                            seed += ', ' + rel['Info']['Name'] + ' (' + rel['Info']['Type'] + ')'
                    elif rel['Relationship'] == 'quantity':
                        if rel['Type'] == 'quantity--standard':
                            for index in range(len(measure_type)):
                                if measure_type[index] == rel['Info']['Measure']:
                                    if 'Value' in rel['Info']:
                                        if standard[index+2] == '':
                                            standard[index+2] = (rel['Info']['Value'] + ' ' + 
                                                               rel['Info']['Unit'])
                                        else:
                                            standard[index+2] += ', ' + (rel['Info']['Value'] + ' ' + 
                                                               rel['Info']['Unit'])
                        elif rel['Type'] == 'quantity--material':
                            if('Name' in rel['Info']):
                                if materials == '':
                                    materials = rel['Info']['Name']
                                else:
                                    materials += ', ' + rel['Info']['Name']
                if mod == 'drilling':
                    hours_list = standard[9].replace('hours','').split(',')
                    standard[9] = str(round(float(hours_list[1]) - float(hours_list[0]),1)) + ' hours'
                    standard[10] = hours_list[0] + ' hours'
                    standard[11] = hours_list[1] + ' hours'
                
                std_list = standard[2].split(',')
                standard[2] = ''
                for std in std_list:
                    if ' seeds/m2' in std:
                        to_add = int(std.replace(' seeds/m2',''))
                        if standard[0] == '':
                            standard[0] = to_add
                        else:
                            standard[0] += ',' + to_add
                    elif ' seeds per metre squared (seeds/m^2)' in std:
                        to_add = int(std.replace(' seeds per metre squared (seeds/m^2)',''))
                        if standard[0] == '':
                            standard[0] = to_add
                        else:
                            standard[0] += ',' + to_add
                    elif ' kg/ha' in std:
                        to_add = float(std.replace(' kg/ha',''))
                        if standard[1] == '':
                            standard[1] = to_add
                        else:
                            standard[1] += ',' + to_add
                    else:
                        if standard[2] == '':
                            standard[2] = std
                        else:
                            standard[2] += ',' + std
        
                w.writerow([log_id, log_date, log_title, field_name, exp_id, owner, 
                            category, revision, equip, seed] + standard + [materials])
        
        
end_time = time.time()
total_time = round((end_time - start_time), 1)
time_string = ''
if total_time > 60:
    minute = 0
    while total_time > 60:
        minute += 1
        total_time -= 60
    time_string += str(minute) + " mn "
time_string += str(round(total_time)) + " sec"
print()
print(P+ "Process ended in " + time_string+W)































