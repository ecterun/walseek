#!/usr/bin/python
import requests, json, datetime, subprocess
from subprocess import call, Popen

def onlinelookup(itemid):
    #itemid = '951814057'
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    with open('/opt/walmart/python/.walmartkey', 'r') as keyfile:
        apikey = keyfile.read().strip('\n')
    r = requests.get('http://api.walmartlabs.com/v1/items/%s?format=json&apiKey=%s' % (itemid, apikey))

    if r.status_code == 200:
        with open('/opt/walmart/python/data/online/webData-%s-%s.json' % (itemid,datestamp), 'w') as outfile:
            json.dump(r.json(), outfile)
    #else print to error logs

def local_query(query, storenum):
    #query = 'LEGO'
    #storenum = '5669'
    offset = 0
    size = 50
    totalcount = 1
    while ( offset < totalcount ):
        r = requests.get('http://search.mobile.walmart.com/search?query=%s&store=%s&size=%d&offset=%d' % (query, storenum, size, offset))
        print 'http://search.mobile.walmart.com/search?query=%s&store=%s&size=%d&offset=%d' % (query, storenum, size, offset)
        totalcount =  r.json()['totalCount']
        offset = r.json()['offset'] + r.json()['count']
        with open('/opt/walmart/python/data/local/local_query-%s-%d.json' % (storenum, offset), 'w') as outfile:
            json.dump(r.json(), outfile)
    print 'creating full_query file'
    call("jq --slurp '[.[].results[]]' /opt/walmart/python/data/local/local_query-" + storenum + "*.json > /opt/walmart/python/data/local/full_query-" + storenum + ".json", shell=True )



def get_local_item_data(itemid,storenum):
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    localfile = '/opt/walmart/python/data/local/full_query-%s.json' % storenum

    cmd = Popen("jq '[.[] | select(.productId.WWWItemId==\"" + itemid + "\")]|.[0]' " + localfile, stdout=subprocess.PIPE,shell=True)
    cmd_out, cmd_err = cmd.communicate()

    localjson = json.loads(cmd_out)

    name = localjson['name']
    price = localjson['price']['priceInCents']
    prealtime = localjson['price']['isRealTime']
    quantity = localjson['inventory']['quantity']
    qrealtime = localjson['inventory']['isRealTime']
    url = localjson['walmartCanonicalUrl']


def get_online_item_data(itemid):
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    onlinefile = '/opt/walmart/python/data/online/webData-%s-%s.json' % (itemid, datestamp)

    with open(onlinefile, 'r') as jsonfile:
        onlinejson = json.load(jsonfile)

    name = onlinejson['name']
    msrp = onlinejson['msrp']
    saleprice = onlinejson['salePrice']
    modelnum = onlinejson['modelNumber']




def compare_item_data(itemid, storenum):
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)
    print 'comparing itemid:%s for storenum:%s for date:%s' % (itemid, storenum, datestamp)

    #localJSON
    localfile = '/opt/walmart/python/data/local/full_query-%s.json' % storenum

    #onlineJSON
    onlinefile = '/opt/walmart/python/data/online/webPrice-%s-%s.json' % (itemid, datestamp)



def main():
    print ("Running pricechecker")
    #onlinelookup('951814057')
    #local_query('LEGO', '5669')
    #compare_item_data('951814057', '5669')
    get_local_item_data('946006306', '5669')
    #get_online_item_data('951814057')

#how to parse json
#json_str = r.json()
#print json_str['value']


if __name__ == '__main__':
    main()
