#!/usr/bin/python
import requests, json, datetime, subprocess, os
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
            print "writing to %s" % outfile.name
    #else print to error logs

def local_query(storenum, query='LEGO'):
    #storenum = '5669'
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)
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
    call("jq --slurp '[.[].results[]]' /opt/walmart/python/data/local/local_query-" + storenum + "*.json > /opt/walmart/python/data/local/full_query-" + storenum + "-" + datestamp + ".json", shell=True )


def get_local_item_data(itemid,storenum):
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    localfile = '/opt/walmart/python/data/local/full_query-%s-%s.json' % (storenum,datestamp)
    if not os.path.isfile(localfile):
        local_query(storenum)

    cmd = Popen("jq '[.[] | select(.productId.WWWItemId==\"" + itemid + "\")]|.[0]' " + localfile, stdout=subprocess.PIPE,shell=True)
    cmd_out, cmd_err = cmd.communicate()
    localjson = json.loads(cmd_out)

    name = localjson['name'] if 'name' in localjson else 'null'
    price = localjson['price']['priceInCents'] if 'priceInCents' in localjson['price'] else 0
    prealtime = localjson['price']['isRealTime'] if 'isRealTime' in localjson['price'] else 'null'
    quantity = localjson['inventory']['quantity'] if 'quantity' in localjson['inventory'] else 'null'
    qrealtime = localjson['inventory']['isRealTime'] if 'isRealTime' in localjson['inventory'] else 'null'
    url = localjson['walmartCanonicalUrl'] if 'walmartCanonicalUrl' in localjson else 'null'

    data = {
        'name': name,
        'priceInCents': price,
        'priceRealTime': prealtime,
        'quantity': quantity,
        'quantityRealTime': qrealtime,
        'url': url
        }
    return data

def get_online_item_data(itemid):
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    onlinefile = '/opt/walmart/python/data/online/webData-%s-%s.json' % (itemid, datestamp)
    if not os.path.isfile(onlinefile):
        onlinelookup(itemid)

    with open(onlinefile, 'r') as jsonfile:
        onlinejson = json.load(jsonfile)

    name = onlinejson['name'] if 'name' in onlinejson else 'null'
    msrp = onlinejson['msrp'] if 'msrp' in onlinejson else 0
    saleprice = onlinejson['salePrice'] if 'salePrice' in onlinejson else 0
    modelnum = onlinejson['modelNumber'] if 'modelNumber' in onlinejson else 'null'

    data = {
        'name': name,
        'msrp': msrp,
        'salePrice': saleprice,
        'modelNumber': modelnum
        }
    return data



def compare_item_data(itemid, storenum):
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)
    print 'comparing itemid:%s for storenum:%s for date:%s' % (itemid, storenum, datestamp)

    localdata = get_local_item_data(itemid, storenum)
    onlinedata = get_online_item_data(itemid)

    localcents = localdata['priceInCents']
    msrpcents = int(onlinedata['msrp'] * 100)
    salepricecents = int(onlinedata['salePrice'] * 100)

    onlinecents = msrpcents if salepricecents > msrpcents and msrpcents > 0 else salepricecents

    if localcents < onlinecents and localcents > 0:
        discount = (1-(float(localcents)/float(onlinecents)))*100
    else:
        discount = 0.0
    #print discount

    itemdata = {
            'itemId': itemid,
            'storeNum': storenum,
            'name': {
            'localName': localdata['name'],
            'onlineName': onlinedata['name']
            },
            'price': {
            'localPriceInCents': localdata['priceInCents'],
            'msrpInCents': msrpcents,
            'salePriceInCents': salepricecents
            },
            'localDiscount': "%.2f" % round(discount,2),
            'localQuantity': localdata['quantity'],
            'modelNumber': onlinedata['modelNumber'],
            'url': localdata['url']
            }

    with open ('/opt/walmart/python/data/compare/compare-%s-%s.json' % (storenum, datestamp), 'a') as outfile:
        json.dump(itemdata, outfile)
        outfile.write('\n')
        print "writing to %s" % outfile.name



def main():
    print ("Running pricechecker")
    #onlinelookup('951814057')
    #local_query('5669')
    #local_query('5669', 'LEGO')
    #compare_item_data('951814057', '5669')
    #get_local_item_data('946006306', '5669')
    #get_online_item_data('951814057')

    compare_item_data('951814057', '5669')
    compare_item_data('946006306', '5669')
    compare_item_data('799194178', '5669')


#how to parse json
#json_str = r.json()
#print json_str['value']


if __name__ == '__main__':
    main()
