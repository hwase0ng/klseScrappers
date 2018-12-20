'''
Created on Apr 13, 2018

@author: hwase0ng
'''

import settings as S
import requests
from BeautifulSoup import BeautifulSoup
from utils.dateutils import getToday
from common import getDataDir
from analytics.mvp import updateMPV, load_mvp_args
from analytics.mvpchart import mvpChart, mvpSynopsis
from utils.fileutils import tail

I3STOCKSURL = 'https://klse.i3investor.com/jsp/stocks.jsp?g=S&m=int&s='


def connectStocksListing(initial):
    if len(initial) != 1:
        print "ERR:Invalid initial = ", initial
        return

    global soup
    stocksListingUrl = I3STOCKSURL + initial
    try:
        page = requests.get(stocksListingUrl, headers=S.HEADERS)
        assert(page.status_code == 200)
        html = page.content
        soup = BeautifulSoup(html)
    except Exception as e:
        print(e)
        soup = ''
    return soup


def scrapeStocksListing(soup):
    if soup is None or len(soup) <= 0:
        print 'ERR: no result'
        return

    stocks = {}
    table = soup.find('table', {'class': 'nc'})
    # for each row, there are many rows including no table
    for tr in table.findAll('tr'):
        leftTag = tr.findAll('td', {'class': 'left'})
        if leftTag is not None and len(leftTag) > 0:
            stockShortName = leftTag[0].text.replace(';', '')
            stockName = leftTag[1].text.replace(';', '')
            stockLink = tr.find('a').get('href')
            # Sample stockLink: /servlets/stk/1234.jsp
            stockCode = stockLink[14:-4]
            td = tr.findAll('td')
            tds = [x.text.strip() for x in td]
            mktCap = int(tds[2].replace(',', ''))
            if S.DBG_ALL:
                print stockShortName, stockName, stockCode, mktCap
            stocks[stockShortName] = [stockCode, stockName, mktCap]
    return stocks


def unpackListing(scode, sname, mktcap):
    return scode, sname, mktcap


def writeStocksListing(outfile='klse.txt'):
    initials = '0ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    stocksListing = {}
    for initial in list(initials):
        listing = scrapeStocksListing(connectStocksListing(initial))
        stocksListing.update(listing)

    fh = open(outfile, "w")
    for key in sorted(stocksListing.iterkeys()):
        stock = key + ',' + \
            ','.join(map(str, unpackListing(*(stocksListing[key]))))
        if S.DBG_ALL:
            print stock
        fh.write(stock + '\n')
    fh.close()


def unpackTD(shortname, longname, cap, price_open, price_range, price_close, change, cpc, volume):
    '''
    Sample table:
    <tr role="row" class="odd"> <td class="left sorting_1"><a href="/servlets/stk/7054.jsp">AASIA</a>
        </td> <td class="left" nowrap=""><a href="/servlets/stk/7054.jsp">ASTRAL ASIA BHD</a></td>
        <td class="right">125</td>
        <td class="right">0.19</td>
        <td class="right">0.19</td>
        <td class="right" nowrap="nowrap"><span class="up">0.00</span></td>
        <td class="right">10,000</td>
    </tr>
    '''
    prange = [x.strip() for x in price_range.split('-')]
    return shortname.replace(';', '').replace('.iew/', ''), \
        price_open, prange[1], prange[0], price_close, volume


def scrapeLatestPrice(soup, checkLastTrading=""):
    if soup is None or len(soup) <= 0:
        print 'ERR: no result'
        return None
    i3eod = {}
    table = soup.find('table', {'class': 'nc'})
    if table is None:
        print 'ERR: table is empty'
        return None
    # for each row, there are many rows including no table
    for tr in table.findAll('tr'):
        td = tr.findAll('td')
        eod = [x.text.strip() for x in td]
        if len(eod) == 9:
            shortname, price_open, price_high, price_low, price_close, volume = unpackTD(
                *eod)
            if int(volume.replace(',', '')) > 0:
                # <a href="/servlets/stk/7054.jsp">AASIA</a>
                stockLink = tr.find('a').get('href')
                stkcd = stockLink[14:-4]
                if 'iew/' in stkcd:
                    print 'INF:Replacing stkcd:', stkcd
                    stkcd = stkcd.replace('iew/', '')
                    print 'INF:New stkcd:', stkcd
                if len(checkLastTrading) > 0:
                    if stkcd == str(checkLastTrading):
                        return price_open, price_close, volume
                    continue
                i3eod[shortname + '.' + stkcd] = [
                    price_open, price_high, price_low, price_close, volume]
            else:
                continue
            # print type(dt), type(price_open), type(price_high), type(price_low), type(price_close), type(volume)
            if S.DBG_ALL:
                print shortname, stkcd, price_open, price_high, price_low, price_close, volume
        elif len(eod) > 0:
            print "ERR:Unknown len:", eod
    return i3eod


def unpackEOD(popen, phigh, plow, pclose, pvol):
    return "{:.4f}".format(float(popen)), "{:.4f}".format(float(phigh)), \
        "{:.4f}".format(float(plow)), "{:.4f}".format(float(pclose)), \
        int(pvol.replace(',', ''))


def i3ScrapeStocks(initials=""):
    print 'Scraping latest price from i3 ...'
    if len(initials) == 0:
        initials = '0ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    stocksListing = {}
    for initial in list(initials):
        eod = scrapeLatestPrice(connectStocksListing(initial))
        stocksListing.update(eod)
    return stocksListing


def unpackStockData(key, lastTradingDate, skey):
    # key = L&G;.iew/3174
    # IOError: [Errno 2] No such file or directory: u'.../data/L&G.iew/3174.csv'
    if '.iew/' in key:
        print 'INF:Replacing key:', key
        key = key.replace('.iew/', '.')
        print 'INF:New key:', key
    key = key.replace(';', '')
    stk = key.split('.')
    shortname = stk[0].replace(';', '')
    stockCode = stk[1]
    eod = shortname + ',' + lastTradingDate + ',' + ','.join(
        map(str, unpackEOD(*(skey))))
    return eod, shortname, stockCode


def writeLatestPrice(lastTradingDate=getToday('%Y-%m-%d'), writeEOD=False, resume=False):

    def checkMPV():
        if resume:
            mpvfile = getDataDir(S.DATA_DIR) + S.MVP_DIR + shortname + '.csv'
            lines = tail(mpvfile)
            ldata = lines.split(',')
            if ldata[1] == lastTradingDate:
                print "Resume mode: Skipped MPV downloaded ->", shortname
                return

        if updateMPV(shortname, stockCode, eod):
            load_mvp_args(True)
            if mvpSynopsis(shortname, stockCode):
                load_mvp_args(False)
                mvpChart(shortname, stockCode)

    stocksListing = i3ScrapeStocks()
    eodlist = []

    print ' Writing latest price from i3 ...'
    for key in sorted(stocksListing.iterkeys()):
        eod, shortname, stockCode = unpackStockData(key, lastTradingDate, stocksListing[key])
        outfile = getDataDir(S.DATA_DIR) + shortname + '.' + stockCode + '.csv'
        if resume:
            lines = tail(outfile)
            ldata = lines.split(',')
            if ldata[1] == lastTradingDate:
                print "Resume mode: Skipped downloaded ->", shortname
                checkMPV()
                continue
        eodlist.append(eod)
        if writeEOD:
            try:
                with open(outfile, "ab") as fh:
                    fh.write(eod + '\n')
            except Exception:
                print " ERR:WriteLatestPrice:", key, ':', shortname, ':', stockCode
                raise
        else:
            print eod

        checkMPV()

    return eodlist


if __name__ == '__main__':
    S.DBG_ALL = False
    writeStocksListing()
    writeLatestPrice(getDataDir(S.DATA_DIR) + 'i3/', False)
    pass
