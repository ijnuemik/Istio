import csv
import json
import requests
from elasticsearch import Elasticsearch
from kubernetes import client, config
import keplergl
import pandas as pd
from flask import Flask, render_template, request
import time

app = Flask(__name__)

def services_to_kepler():
    ##setting about kubernetes client
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pod = v1.list_pod_for_all_namespaces(watch=False)
    namespace_list = v1.list_namespace()
    svc = v1.list_service_for_all_namespaces(watch=False)

    ##get elasticsearch URL
    for i in svc.items:
       if i.metadata.name == 'elasticsearch':
           elasticIp = i.spec.cluster_ip + ':9200'

    ##get nodes and location
    ##sol 1) from ipstack api (latitude, longitude) -> node_dict
    # node = v1.list_node(watch=False)
    # node_dict = {}
    # for i in node.items:
    #     adds = i.status.addresses
    #     InternalIP = adds[0].address
    #     hostname = adds[1].address
    #     print(hostname)
        # url = "http://api.ipstack.com/"+InternalIP+"?access_key={YOUR_API_KEY}"
        # result = json.loads(requests.get(url).text)
        # node_dict[hostname+'_lat'] = result['latitude']
        # node_dict[hostname+'_lng'] = result['longitude']
        # print(result['latitude'],result['longitude'])

    ##sol 2) write your nodes and location below
    node_dict = {}
    node_dict['netcs-quantagrid-d52g-4u'+'_lat'] = 35.229247
    node_dict['netcs-quantagrid-d52g-4u'+'_lng'] = 126.84459686279297
    node_dict['netcs-virtual-machine'] = 35.229581
    node_dict['netcs-virtual-machine'] = 126.847718


    ### save services' communication information from elasticsearch to info.csv
    csv_columns = ['@timestamp', 'source', 'srcnamespace', 'destination', 'latency', 'desnamespace', 'severity','tag','responseCode','user','responseSize', ]
    csv_file = './info.csv'

    es = Elasticsearch(hosts=elasticIp)
    data = es.indices.get_alias("*")
    for k in data.keys():
        if k != '.kibana':
            data = es.search(index=k, size=10000, body={"query": {"match_all":{}}})
            with open(csv_file,'w') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                for document in [x['_source'] for x in data['hits']['hits']]:
                    writer.writerow(document)

    ### get 'services by namespace' from info.csv
    f = open('info.csv', 'r', encoding='utf-8')
    rdr = csv.reader(f)

    for i in namespace_list.items:
        kepler_file_name = './Kepler/Kepler-csvfiles/kepler_' + i.metadata.name + '.csv'
        with open(kepler_file_name, 'w') as csvfile1:
            wtr1 = csv.writer(csvfile1)
            wtr1.writerow(['node1_lat','node1_lng','node1','p1','node2_lat','node2_lng','node2','p2','duration','timestamp'])

    for line in rdr:
        time_stamp = line[0]
        p1 = line[1]
        p2 = line[3]
        duration = line[4]
        src_namespace = line[2]
        des_namespace = line[5]
        node1 = ""
        node2 = ""
        if time_stamp == 'unknown' or p1 == 'unknown' or p2 == 'unknown' or src_namespace == 'unknown' or des_namespace == 'unknown':
            continue

        for i in pod.items:
            if p1 == i.metadata.name:
                node1 = i.spec.node_name
            if p2 == i.metadata.name:
                node2 = i.spec.node_name

        if src_namespace == des_namespace:
            kepler_file_name = './Kepler/Kepler-csvfiles/kepler_' + src_namespace + '.csv'
        else:
            if src_namespace == 'istio-system' or des_namespace == 'istio-system':
                kepler_file_name = './Kepler/Kepler-csvfiles/kepler_istio-system.csv'
            else:
                continue
        with open(kepler_file_name, 'a', newline = '') as csvfile:
            node1_lat = ""
            node1_lng = ""
            node2_lat = ""
            node2_lng = ""
            wtr = csv.writer(csvfile)
            a = 0
            if node1+'_lat' in node_dict:
                node1_lat = node_dict[node1+'_lat']
            else:
                a = 1
            if node1+'_lat' in node_dict:
                node1_lng = node_dict[node1+'_lng']
            else:
                a = 1
            if node2+'_lat' in node_dict:
                node2_lat = node_dict[node2+'_lat']
            else:
                a = 1
            if node2+'_lat' in node_dict:
                node2_lng = node_dict[node2+'_lng']
            else:
                a = 1
            if a != 1:
                wtr.writerow([node1_lat,node1_lng,node1,p1,node2_lat,node2_lng,node2,p2,duration,time_stamp])

    f.close()


    ### Kepler config (you can change kepler config)
    kepler_config = {'version': 'v1',
     'config': {'visState': {'filters': [{'dataId': 'data_1',
         'id': 'uisb16gma',
         'name': 'time_stamp',
         'type': 'timeRange',
         'value': [1585094781038, 1585094781538],
         'enlarged': True,
         'plotType': 'histogram',
         'yAxis': None}],
       'layers': [{'id': '9rm0hg',
         'type': 'point',
         'config': {'dataId': 'data_1',
          'label': 'node1',
          'color': [14, 112, 119],
          'columns': {'lat': 'node1_lat', 'lng': 'node1_lng', 'altitude': None},
          'isVisible': True,
          'visConfig': {'radius': 10,
           'fixedRadius': False,
           'opacity': 0.8,
           'outline': False,
           'thickness': 2,
           'strokeColor': None,
           'colorRange': {'name': 'Global Warming',
            'type': 'sequential',
            'category': 'Uber',
            'colors': ['#5A1846',
             '#900C3F',
             '#C70039',
             '#E3611C',
             '#F1920E',
             '#FFC300']},
           'strokeColorRange': {'name': 'Global Warming',
            'type': 'sequential',
            'category': 'Uber',
            'colors': ['#5A1846',
             '#900C3F',
             '#C70039',
             '#E3611C',
             '#F1920E',
             '#FFC300']},
           'radiusRange': [0, 50],
           'filled': True},
          'textLabel': [{'field': {'name': 'p1', 'type': 'string'},
            'color': [255, 255, 255],
            'size': 18,
            'offset': [0, 0],
            'anchor': 'start',
            'alignment': 'center'}]},
         'visualChannels': {'colorField': None,
          'colorScale': 'quantile',
          'strokeColorField': None,
          'strokeColorScale': 'quantile',
          'sizeField': None,
          'sizeScale': 'linear'}},
        {'id': '52mxpob',
         'type': 'point',
         'config': {'dataId': 'data_1',
          'label': 'node2',
          'color': [18, 92, 119],
          'columns': {'lat': 'node2_lat', 'lng': 'node2_lng', 'altitude': None},
          'isVisible': True,
          'visConfig': {'radius': 10,
           'fixedRadius': False,
           'opacity': 0.8,
           'outline': False,
           'thickness': 2,
           'strokeColor': None,
           'colorRange': {'name': 'Global Warming',
            'type': 'sequential',
            'category': 'Uber',
            'colors': ['#5A1846',
             '#900C3F',
             '#C70039',
             '#E3611C',
             '#F1920E',
             '#FFC300']},
           'strokeColorRange': {'name': 'Global Warming',
            'type': 'sequential',
            'category': 'Uber',
            'colors': ['#5A1846',
             '#900C3F',
             '#C70039',
             '#E3611C',
             '#F1920E',
             '#FFC300']},
           'radiusRange': [0, 50],
           'filled': True},
          'textLabel': [{'field': {'name': 'duration_str', 'type': 'string'},
            'color': [255, 254, 230],
            'size': 18,
            'offset': [0, 0],
            'anchor': 'start',
            'alignment': 'top'},
           {'field': {'name': 'p2', 'type': 'string'},
            'color': [255, 255, 255],
            'size': 18,
            'offset': [0, 0],
            'anchor': 'start',
            'alignment': 'center'}]},
         'visualChannels': {'colorField': None,
          'colorScale': 'quantile',
          'strokeColorField': None,
          'strokeColorScale': 'quantile',
          'sizeField': None,
          'sizeScale': 'linear'}},
        {'id': 'ld5iezk',
         'type': 'arc',
         'config': {'dataId': 'data_1',
          'label': 'node1 -> node2 arc',
          'color': [255, 254, 230],
          'columns': {'lat0': 'node1_lat',
           'lng0': 'node1_lng',
           'lat1': 'node2_lat',
           'lng1': 'node2_lng'},
          'isVisible': True,
          'visConfig': {'opacity': 0.8,
           'thickness': 7,
           'colorRange': {'name': 'Global Warming',
            'type': 'sequential',
            'category': 'Uber',
            'colors': ['#5A1846',
             '#900C3F',
             '#C70039',
             '#E3611C',
             '#F1920E',
             '#FFC300']},
           'sizeRange': [0, 10],
           'targetColor': [87, 136, 46]},
          'textLabel': [{'field': None,
            'color': [255, 255, 255],
            'size': 18,
            'offset': [0, 0],
            'anchor': 'start',
            'alignment': 'center'}]},
         'visualChannels': {'colorField': None,
          'colorScale': 'quantile',
          'sizeField': None,
          'sizeScale': 'linear'}},
        {'id': 'kcsigvh',
         'type': 'line',
         'config': {'dataId': 'data_1',
          'label': 'node1 -> node2 line',
          'color': [77, 193, 156],
          'columns': {'lat0': 'node1_lat',
           'lng0': 'node1_lng',
           'lat1': 'node2_lat',
           'lng1': 'node2_lng'},
          'isVisible': False,
          'visConfig': {'opacity': 0.8,
           'thickness': 2,
           'colorRange': {'name': 'Global Warming',
            'type': 'sequential',
            'category': 'Uber',
            'colors': ['#5A1846',
             '#900C3F',
             '#C70039',
             '#E3611C',
             '#F1920E',
             '#FFC300']},
           'sizeRange': [0, 10],
           'targetColor': None},
          'textLabel': [{'field': None,
            'color': [255, 255, 255],
            'size': 18,
            'offset': [0, 0],
            'anchor': 'start',
            'alignment': 'center'}]},
         'visualChannels': {'colorField': None,
          'colorScale': 'quantile',
          'sizeField': None,
          'sizeScale': 'linear'}}],
       'interactionConfig': {'tooltip': {'fieldsToShow': {'data_1': ['node1',
           'p1',
           'node2',
           'p2',
           'pro_namespace']},
         'enabled': True},
        'brush': {'size': 0.5, 'enabled': False}},
       'layerBlending': 'normal',
       'splitMaps': [],
       'animationConfig': {'currentTime': None, 'speed': 1}},
      'mapState': {'bearing': 11.94979079497908,
       'dragRotate': True,
       'latitude': 35.22821027516838,
       'longitude': 126.84184175512864,
       'pitch': 58.88625196338873,
       'zoom': 13.94183054311009,
       'isSplit': False},
      'mapStyle': {'styleType': 'dark',
       'topLayerGroups': {},
       'visibleLayerGroups': {'label': True,
        'road': True,
        'border': False,
        'building': True,
        'water': True,
        'land': True,
        '3d building': False},
       'threeDBuildingColor': [9.665468314072013,
        17.18305478057247,
        31.1442867897876],
       'mapStyles': {}}}}

    ### draw map through kepler.gl and save_to_html
    for i in namespace_list.items:
        kepler_file_name = './Kepler/Kepler-csvfiles/kepler_' + i.metadata.name + '.csv'
        kepler_html_filename = './templates/kepler_'+i.metadata.name+'.html'
        df = pd.read_csv(kepler_file_name)
        w2 = keplergl.KeplerGl(height = 600,data={'data_1':df},config = kepler_config)
        w2.save_to_html(file_name=kepler_html_filename)

@app.route('/<namespace>/')
def kepler_by_namespace(namespace):
    filename = 'kepler_' + namespace + '.html'
    return render_template(filename)

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown')
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

if __name__ == '__main__':
    while True:
        print("here")
        services_to_kepler()
        app.run(host="localhost", port="8080")
        time.sleep(5)
