import pymongo
import math
import traceback #找出錯誤行數
import sys       #找出錯誤行數
import numpy as np
from dateutil.relativedelta import relativedelta
import datetime
from bson.objectid import ObjectId
import myfunction
from itertools import zip_longest
from apscheduler.schedulers.background import BackgroundScheduler
import time
from report import genReport
import os

connection = pymongo.MongoClient('mongodb://root:admin@127.0.0.1:27017/')
db = connection['gus']
# ================================================================================================
# 回傳程式發生錯誤時的相關資訊
def traceback_func():
    error_class, error_detail, tb = sys.exc_info() #取得Call Stack
    error_class = error_class.__name__ #取得錯誤類型
    error_detail = error_detail.args[0] #取得詳細內容
    lastCallStack = traceback.extract_tb(tb)[-1] #取得Call Stack的最後一筆資料
    fileName = lastCallStack[0] #取得發生的檔案名稱
    lineNum = lastCallStack[1] #取得發生的行號
    funcName = lastCallStack[2] #取得發生的函數名稱
    errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(fileName, lineNum, funcName, error_class, error_detail)
    return errMsg
# ================================================================================================
def get_model(model_name):
    try:
        model = myfunction.get_model(db=db,ID=model_name)
    except:
        error_message = traceback_func()
        print('Time:{}, info:{}'.format(datetime.datetime.now(), error_message))
        # print(error_message)
        model = {}
    return model
# ================================================================================================
def get_alarm_event(db,collection,ID,fault_type):
    collection = db[collection]
    match = {
        'ID' :ID
    }
    fault_project = {}
    for type in fault_type:  
        fault_project[type] = 1  
    project = {**{"_id":0},**fault_project}
    data = list(collection.aggregate(
        [
            {'$sort' : {"time" :-1} },
            {'$match': match},
            {"$project":project},  
            {'$limit' : 1 },
        ]
    ))
    return data
# ================================================================================================
def give_alarm_return_time(ID,fault_type):
    fault_unreturn = list(db.alarm.aggregate(
        [
            {'$sort' : {"time" :-1} },
            {'$match': {'$and':[{'ID':ID},{'returntime':''},{'fault_type':fault_type}]}},  
        ]
    ))
    if( fault_unreturn != []):
        for event in fault_unreturn:
            db.alarm.update_one({"_id":event['_id']},{"$set": { "returntime": datetime.datetime.now() }})
# ================================================================================================
def insert_new_alarm_protect(ID,fault_dict,fault_type,model):
    fault_str = bin(fault_dict[0][fault_type])[2:].zfill(model[fault_type]['bitIndex'][-1])
    fault_str = reversed(fault_str)
    fault_array = np.fromiter(fault_str, dtype=int)
    fault_state = np.where(fault_array==1)[0]
    for index in fault_state: 
        try:
            # 看該flag是不是需要發alarm，若沒有則會抓到空的alarm，然後跳continue
            event = model[fault_type]['alarm'][index]['event']
            # 關閉相應設備，如果連alarm event都沒有，一定也沒有protection，因此就不需要進保護環節
            protect_level =  model[fault_type]['alarm'][index]['protection']
        except:
            continue #進入下一圈for
        same_alarm = db.alarm.find_one({'ID':ID,'event':event,'fault_type':fault_type},sort=([("time",-1)]))
        try:
            # 目前有相同的alarm_event，已經復歸
            if (same_alarm['returntime'] != ""):
                event = {
                    'time' : datetime.datetime.now(),
                    'ID' : ID,
                    'event':event,
                    'eventType' : model[fault_type]['alarm'][index]['eventType'],
                    'show' : 1,
                    'level' : model[fault_type]['alarm'][index]['level'],
                    'returntime':'',
                    'fault_type' : fault_type,
                    'check' : 0
                }
            # 目前有相同的alarm_event，但尚未復歸
            else:
                continue #進入下一圈for
        except:
            # 目前無相同的alarm_event(find_one回來是None)
            event = {
                'time' : datetime.datetime.now(),
                'ID' : ID,
                'event':event,
                'eventType' : model[fault_type]['alarm'][index]['eventType'],
                'show' : 1,
                'level' : model[fault_type]['alarm'][index]['level'],
                'returntime':'',
                'fault_type' : fault_type,
                'check' : 0
            }
            # 進入保護
            try:
                # 先查看該告警有無mode這flag，若無，正常保護(因抓不到，所以跳except)
                mode = model[fault_type]['alarm'][index]['mode']
            except:
                pass
            else:
                pcs_status = db.pcs.find_one({"ID":"delta_pcs"},{'_id':0,'status_pcs':1},sort=([("time",-1)])).get('status_pcs')
                if (pcs_status >= 6):
                    protect_level = 0
                else:
                    pass
            if (protect_level >= 1):
                eqpt_curr_state = db.equipment_control.find_one({},{'_id':0,'time':0},sort=([("time",-1)]))
                if (eqpt_curr_state['pcs_on_off'] == 1):
                    eqpt_curr_state['pcs_on_off'] = 0
                    eqpt_curr_state['pcs_set_flag'] = 1
                    eqpt_curr_state['time'] = datetime.datetime.now()
                    db.equipment_control.insert_one(eqpt_curr_state)
            else:
                pass
        db.alarm.insert_one(event)
# ================================================================================================
def check_alarm():
    global mbms_model
    global pcs_model

    bms_1_fault_type = [        
        'flag1',
        'flag2',
        'flag3',
        'flag4',
        'flag5',
        'flag6',
        'flag9',
    ]
    bms_2_fault_type = [        
        'flag1',
        'flag2',
        'flag3',
        'flag4',
        'flag5',
        'flag6',
        'flag9',
    ]
    pcs_1_fault_type = [
        'fault1',
        'fault2',
        'fault3',
        'fault4',
        'dam_fault1',
        'dam_fault2',
        'dam_fault3',
        'dam_fault4',
    ]
    bms_1_fault = get_alarm_event(db=db,collection='mbms',ID ='gus_bms_1',fault_type = bms_1_fault_type)
    bms_2_fault = get_alarm_event(db=db,collection='mbms',ID ='gus_bms_2',fault_type = bms_2_fault_type)
    pcs_1_fault = get_alarm_event(db=db,collection='pcs',ID ='delta_pcs',fault_type = pcs_1_fault_type)
    try:
        for bms1_fault_type,bms2_fault_type,pcs_fault_type in zip_longest(bms_1_fault_type,bms_2_fault_type,pcs_1_fault_type):
            # bms_1
            # 當現在狀態為0，自動填入復歸時間
            if ( (bms_1_fault[0].get(bms1_fault_type)) == 0 ):
                give_alarm_return_time(ID='gus_bms_1',fault_type=bms1_fault_type)
            else :
                try:
                    insert_new_alarm_protect(ID='gus_bms_1',fault_dict=bms_1_fault,fault_type=bms1_fault_type,model=mbms_model)
                except:
                    # 當bms跑完，bms1_fault_type會為None,因此進去insert_new_alarm_protect()會有error，但無須處理 ，bms2同此
                    pass
            # bms_2
            # 當現在狀態為0，自動填入復歸時間
            if ( (bms_2_fault[0].get(bms2_fault_type)) == 0 ):
                give_alarm_return_time(ID='gus_bms_2',fault_type=bms2_fault_type)
            else :
                try:
                    insert_new_alarm_protect(ID='gus_bms_2',fault_dict=bms_2_fault,fault_type=bms2_fault_type,model=mbms_model)
                except:
                    pass
            # 當現在狀態為0，自動填入復歸時間
            if ( (pcs_1_fault[0].get(pcs_fault_type)) == 0 ):
                give_alarm_return_time(ID='delta_pcs',fault_type=pcs_fault_type)
            else:
                try:
                    insert_new_alarm_protect(ID='delta_pcs',fault_dict=pcs_1_fault,fault_type=pcs_fault_type,model=pcs_model)
                except:
                    pass
    except:
        error_message = traceback_func()
        print('Time:{}, info:{}'.format(datetime.datetime.now(), error_message))
    else:
        pass
# ================================================================================================ 
if __name__ == '__main__':
    global mbms_model
    global pcs_model
    mbms_model = get_model('mbms_model')
    pcs_model = get_model('pcs_model')
    print('---------------------------------------------------------')
    print('Time:{}, start!'.format(datetime.datetime.now()))
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    print('---------------------------------------------------------')
    scheduler = BackgroundScheduler(timezone='Asia/Taipei')
    
    # alarm偵測與保護
    scheduler.add_job(check_alarm,'cron', hour='*',minute='*',second='*')
    # 日報
    scheduler.add_job(genReport,'cron',hour='0',minute='0',second='1',args=["day"],misfire_grace_time=3600)
    #月報
    scheduler.add_job(genReport,'cron', day='1',hour='0',minute='0',second='1',args=["month"],misfire_grace_time=3600)
    #年報
    scheduler.add_job(genReport,'cron', month='1',day='1',hour='0',minute='0',second='1',args=["year"],misfire_grace_time=3600)
    scheduler.start()
    try:
    # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(1) 
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()
        print('Exit The Job!')
    # ===============================================================================================

