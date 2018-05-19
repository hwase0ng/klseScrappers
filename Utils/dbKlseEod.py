'''
Created on May 14, 2018

@author: hwase0ng
'''

from pymongo import MongoClient
from Utils.fileutils import cd
from common import getDataDir, loadCfg
from pandas.errors import EmptyDataError
import pandas as pd
import settings as S
import os
import glob
import json
import pprint
import socket
import subprocess

header = ["0-Code", "1-Date", "2-Open", "3-High", "4-Low", "5-Close", "6-Volume"]


def isOpen(ip, port):
    s = socket.socket(socket. AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((ip, port))
        s.shutdown(2)
        return True
    except Exception:
        return False


def initKlseEod():
    if not isOpen('127.0.0.1', 27017):
        print 'Startind MongoDB ...'
        with cd(S.DATA_DIR):
            mongod = subprocess.Popen(['mongod', '--dbpath', os.path.expanduser(S.DATA_DIR)])

    mongo_client = MongoClient()
    db = mongo_client.klsedb
    return db


def dbUpsertCounters(db, filenm):
    try:
        data = pd.read_csv(S.DATA_DIR + filenm, header=None)
        data_json = json.loads(data.to_json(orient='records'))
        if data_json is not None and len(data_json) > 0:
            if S.DBG_ALL:
                print data_json[:3]
            for jitem in data_json:
                print "Upserting", jitem['0']
                key = {'0': jitem['0'], '1': jitem['1']}
                db.klseeod.update(key, jitem, upsert=True)
                if S.DBG_ALL:
                    pprint.pprint(db.klseeod.find_one(key))
    except EmptyDataError:
        pass


def dbReplaceCounter(db, filenm):
    if db is None:
        return None
    stk = filenm.split('.')
    print stk[0], stk[1]
    try:
        data = pd.read_csv(filenm, header=None)
        data_json = json.loads(data.to_json(orient='records'))
        if data_json is not None and len(data_json) > 0:
            if S.DBG_ALL:
                print data_json[:3]
            db.klseeod.remove({0: stk[0]})
            db.klseeod.insert(data_json)
    except EmptyDataError:
        pass


def dbNewImport(db, filenm):
    if db is None:
        return None

    print filenm
    try:
        data = pd.read_csv(filenm, header=None)
        '''
        data.columns = header
        '''
        data_json = json.loads(data.to_json(orient='records'))
        if data_json is not None and len(data_json) > 0:
            if S.DBG_ALL:
                print data_json[:3]
            db.klseeod.insert(data_json)
    except EmptyDataError:
        pass


def processCsv(db, csvfile):
    with cd(getDataDir(S.DATA_DIR, 1)):
        print os.getcwd()
        if len(csvfile) > 0:
            dbReplaceCounter(db, csvfile)
            if S.DBG_ALL:
                pprint.pprint(db.klseeod.find_one({0: '3A', 1: '2018-05-08'}))
        else:
            db.klseeod.drop()
            csvfiles = glob.glob("*.csv")
            for csvf in csvfiles:
                dbNewImport(db, csvf)
            if S.DBG_ALL:
                pprint.pprint(db.klseeod.find_one({'0': '3A', '1': '2018-01-08'}))


if __name__ == '__main__':
    '''
    with cd('../data'):
        exportQuotes('2018-05-10')
    '''
    loadCfg(getDataDir(S.DATA_DIR, 1))
    db = initKlseEod()
    if db is None:
        print "No DB connection"
    else:
        '''
        dbUpsertCounters(db, 'latest.eod')
        '''
        csvfile = ''
        processCsv(db, csvfile)
    pass