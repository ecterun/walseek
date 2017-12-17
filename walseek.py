#!/usr/bin/python
import requests, json, datetime, subprocess, os, time, glob
import seekconfig as config
from subprocess import call, Popen
from time import strftime


def walseek_init():
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    for loc in config.dir_:
        try:
            os.makedirs(config.dir_[loc])
        except OSError:
            if not os.path.isdir(config.dir_[loc]):
                raise

    path =  config.dir_['online'] + '/' + datestamp
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def onlinelookup(itemid):
    #itemid = '951814057'
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    apikey = config.api_['key']
    r = requests.get('http://api.walmartlabs.com/v1/items/%s?format=json&apiKey=%s' % (itemid, apikey))

    #if r.status_code == 200:
    filepath = '%s/%s/%s-%s-%s.json' % (config.dir_['online'],datestamp,config.file_['onlineItem'],itemid,datestamp)
    with open(filepath, 'w') as outfile:
        if r.status_code == 200:
            json.dump(r.json(), outfile)
            print "writing to %s" % outfile.name
        else:
            json.dump('{}', outfile)
            print "writing empty file %s" % outfile.name
    #else print to error logs


def local_query(storenum, query='LEGO'):
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
        filepath = '%s/%s-%s-%d.json' % (config.dir_['local'],config.file_['localQuery'],storenum,offset)
        with open(filepath, 'w') as outfile:
            json.dump(r.json(), outfile)
    print 'creating full_query file'
    localwildcard = '%s/%s-%s*.json' % (config.dir_['local'],config.file_['localQuery'],storenum)
    fullquery = '%s/%s-%s-%s.json' % (config.dir_['local'],config.file_['fullQuery'],storenum,datestamp)
    call("jq --slurp '[.[].results[]]' " + localwildcard + " > " + fullquery, shell=True )
    for f in glob.glob(localwildcard):
        os.remove(f)


def get_local_item_data(itemid, storenum, strdate=strftime("%m%d")):
    localfile = '%s/%s-%s-%s.json' % (config.dir_['local'],config.file_['fullQuery'],storenum,strdate)
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

    onlinefile = '%s/%s/%s-%s-%s.json' % (config.dir_['online'],datestamp,config.file_['onlineItem'],itemid,datestamp)
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

    comparefilepath = '%s/%s-%s-%s.json' % (config.dir_['compare'],config.file_['compare'],storenum,datestamp)
    with open (comparefilepath, 'a') as outfile:
        json.dump(itemdata, outfile)
        outfile.write('\n')
        print "writing to %s" % outfile.name


def compare_store(storenum):
    now = datetime.datetime.now()
    datestamp = str(now.month) + str(now.day)

    localfile = '%s/%s-%s-%s.json' % (config.dir_['local'],config.file_['fullQuery'],storenum,datestamp)
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

    currentcompare = '%s/%s-%s-%s.json' % (config.dir_['compare'],config.file_['compare'],storenum, datestamp)
    previouscompare = '%s/%s-%s-%s.json' % (config.dir_['compare'],config.file_['compare'],storenum, yesterday)

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
            discount = curjson['localDiscount'] + '%'
            discountdata = {
                        'itemId': itemid,
                        'storeNumber': storenum,
                        'itemName': curjson['name']['localName'],
                        'price':{
                            'localDiscount': curjson['localDiscount'] + '%',
                            'newPrice': curjson['price']['localPriceInCents'],
                            'previousPrice': prevprice
                            },
                        'link': 'https://walmart.com' + curjson['url']
                        }
            discountfilepath = '%s/%s-%s.json' % (config.dir_['discount'],config.file_['discount'],datestamp)
            with open (discountfilepath, 'a') as outfile:
                json.dump(discountdata, outfile)
                outfile.write('\n')
            print discountdata


def main():
    walseek_init()

    for store in config.store_list:
        compare_store(store)

    for store in config.store_list:
        check_compare_data(store)


#Full Local Compare
    #compare_store('1294')
    #compare_store('1515')
    #compare_store('1551')
    #compare_store('2452')
    #compare_store('2828')
    #compare_store('2936')
    #compare_store('5438')
    #compare_store('5668')
    #compare_store('5669')
    #compare_store('6394')

#Full Check Compare Data
    #check_compare_data('1294')
    #check_compare_data('1515')
    #check_compare_data('1551')
    #check_compare_data('2452')
    #check_compare_data('2828')
    #check_compare_data('2936')
    #check_compare_data('5438')
    #check_compare_data('5668')
    #check_compare_data('5669')
    #check_compare_data('6394')

if __name__ == '__main__':
    main()
