#!/usr/bin/python
import requests, json, glob
from subprocess import call

def onlinelookup(itemid):
    apikey = open('~/.walmartkey', 'r').read().strip('\n')
    r = requests.get('http://api.walmartlabs.com/v1/items/%s?format=json&apiKey=%s' % (itemid, apikey))

    if r.status_code == 200:
        with open('/opt/walmart/python/data/online/webData-%s.json' % itemid, 'w') as outfile:
            json.dump(r.json(), outfile)
    #else print to error logs

def local_query():
    query = 'LEGO'
    storenum = '5669'

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


def main():
    print ("Running pricechecker")
    #onlinelookup('')
    local_query()

#how to parse json
#json_str = r.json()
#print json_str['value']


if __name__ == '__main__':
    main()
