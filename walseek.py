#!/usr/bin/python
import requests, json, datetime, subprocess, os, time, glob
from subprocess import call, Popen
from time import strftime
def onlinelookup(itemid):
    #itemid = '951814057'
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    with open('/opt/walmart/python/.walmartkey', 'r') as keyfile:
        apikey = keyfile.read().strip('\n')
    r = requests.get('http://api.walmartlabs.com/v1/items/%s?format=json&apiKey=%s' % (itemid, apikey))

    #if r.status_code == 200:
    with open('/opt/walmart/python/data/online/%s/webData-%s-%s.json' % (datestamp,itemid,datestamp), 'w') as outfile:
        if r.status_code == 200:
            json.dump(r.json(), outfile)
            print "writing to %s" % outfile.name
        else:
            json.dump('{}', outfile)
            print "writing empty file %s" % outfile.name
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
    for f in glob.glob("/opt/walmart/python/data/local/local_query-%s-*.json" % storenum):
        os.remove(f)


def get_local_item_data(itemid, storenum, strdate=strftime("%m%d")):
    localfile = '/opt/walmart/python/data/local/full_query-%s-%s.json' % (storenum,strdate)
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

    onlinefile = '/opt/walmart/python/data/online/%s/webData-%s-%s.json' % (datestamp, itemid, datestamp)
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
            'localDiscount': "%.f" % round(discount,2),
            'localQuantity': localdata['quantity'],
            'modelNumber': onlinedata['modelNumber'],
            'url': localdata['url']
            }

    with open ('/opt/walmart/python/data/compare/compare-%s-%s.json' % (storenum, datestamp), 'a') as outfile:
        json.dump(itemdata, outfile)
        outfile.write('\n')
        print "writing to %s" % outfile.name


def compare_store(storenum):
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    localfile = '/opt/walmart/python/data/local/full_query-%s-%s.json' % (storenum,datestamp)
    if not os.path.isfile(localfile):
        local_query(storenum)

    cmd = Popen("jq -r '.[].productId.WWWItemId' " + localfile, stdout=subprocess.PIPE,shell=True)
    cmd_out, cmd_err = cmd.communicate()

    for line in cmd_out.splitlines():
        compare_item_data(line, storenum)

def check_compare_data(storenum):
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)
    yesterday = str(now.month) + str(now.day -1)

    currentcompare = '/opt/walmart/python/data/compare/compare-%s-%s.json' % (storenum, datestamp)
    previouscompare = '/opt/walmart/python/data/compare/compare-%s-%s.json' % (storenum, yesterday)

    cmd = Popen("jq -c 'select(.localDiscount!=\"0\")|.' " + currentcompare, stdout=subprocess.PIPE,shell=True)
    cmd_out, cmd_err = cmd.communicate()
    print 'Comparing StoreNum:%s data from %s and %s.' % (storenum, datestamp, yesterday)
    for line in cmd_out.splitlines():
        curjson = json.loads(line)
        itemid = curjson['itemId']
        scmd = Popen("jq -c 'select(.itemId==\"" + itemid + "\")' " + previouscompare + " |head -n 1", stdout=subprocess.PIPE,shell=True)
        scmd_out, scmd_err = scmd.communicate()
        if scmd_out == '':
            prevprice = -1
        else:
            prevjson = json.loads(scmd_out)
            prevprice = prevjson['price']['localPriceInCents']
        curprice = curjson['price']['localPriceInCents']
        pricelowered = True if curprice < prevprice else False
        if pricelowered:
            print 'StoreNum:%s ItemId:%s CurrentPrice:%s PreviousPrice:%s' % (storenum, itemid, curprice, prevprice)

def main():
    print ("Running pricechecker")
    #onlinelookup('951814057')
    #local_query('5669')
    #local_query('5669', 'LEGO')
    #compare_item_data('951814057', '5669')
    #get_local_item_data('946006306', '5669')
    #get_online_item_data('951814057')

#Test compares
    #compare_item_data('951814057', '5669')
    #compare_item_data('946006306', '5669')
    #compare_item_data('799194178', '5669')

#Full Local Compare
    compare_store('1294')
    compare_store('1515')
    compare_store('1551')
    compare_store('2452')
    compare_store('2828')
    compare_store('2936')
    compare_store('5438')
    compare_store('5668')
    compare_store('5669')
    compare_store('6394')

#Full Check Compare Data
    check_compare_data('1294')
    check_compare_data('1515')
    check_compare_data('1551')
    check_compare_data('2452')
    check_compare_data('2828')
    check_compare_data('2936')
    check_compare_data('5438')
    check_compare_data('5668')
    check_compare_data('5669')
    check_compare_data('6394')

#how to parse json
#json_str = r.json()
#print json_str['value']


if __name__ == '__main__':
    main()
