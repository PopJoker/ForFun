# from typing import Collection

# from werkzeug.datastructures import Range
from typing import Collection
from numpy.lib import financial
import pymongo
# from bson.objectid import ObjectId
import datetime
import time
import numpy as np
# from apscheduler.schedulers.background import BackgroundScheduler
import os
# from dateutil.relativedelta import relativedelta
import random
# import sys
# import psutil
# import socket
# conn = pymongo.MongoClient('mongodb://root:pc152@127.0.0.1:27017/',serverSelectionTimeoutMS=10)
# conn = pymongo.MongoClient( 'mongodb://root:pc152@140.118.172.163:27017')

conn = pymongo.MongoClient( 'mongodb://root:admin@140.118.172.244:27017')
print(conn)
db = conn['gus_test']  #跟睿彬用的資料庫

# --- 建立index ---
def create_collection_index(collection, type="simple"):
    global db
    try:
        if type  == "simple":
            condition = [
                [("time",-1)],
                [("time",1)],                
            ]
        else:
            condition = [
                [("time",-1)],
                [("time",1)],
                [("time",-1), ("id",1)],
                [("time",1), ("id",1)]        
            ]
        for i in collection:
            for j in condition:
                db[i].create_index(j)        
    except Exception as e:
        print('function of "create_collection_index" errors:', e)
  
# 將資料寫進mongo
def insert_data(collection, data):
    global db
    try:
        db[collection].insert(data)
    except Exception as e:
        print('function of "insert_data" errors:', e)


def add_mbms_data():
    collection = "mbms"

    for i in range(1,3):
        mod_cell_v = [round(random.uniform(0,200),3)]*22
        mod_cell_t = [round(random.uniform(0,100),3)]*12
        data = {
            "ID": "",
            "time" : datetime.datetime.now(),
            "mod_1_cell_v" : mod_cell_v,
            "mod_2_cell_v" : mod_cell_v,
            "mod_3_cell_v" : mod_cell_v,       
            "mod_4_cell_v" : mod_cell_v,
            "mod_5_cell_v" : mod_cell_v,
            "mod_6_cell_v" : mod_cell_v,
            "mod_7_cell_v" : mod_cell_v,
            "mod_8_cell_v" : mod_cell_v,
            "mod_9_cell_v" : mod_cell_v,
            "mod_10_cell_v" : mod_cell_v,
            "mod_11_cell_v" : mod_cell_v,
            "mod_12_cell_v" : mod_cell_v,
            "mod_v" : mod_cell_v[:12],
            "mod_1_cell_t" : mod_cell_t,
            "mod_2_cell_t" : mod_cell_t,
            "mod_3_cell_t" : mod_cell_t,
            "mod_4_cell_t" : mod_cell_t,
            "mod_5_cell_t" : mod_cell_t,
            "mod_6_cell_t" : mod_cell_t,
            "mod_7_cell_t" : mod_cell_t,
            "mod_8_cell_t" : mod_cell_t,
            "mod_9_cell_t" : mod_cell_t,
            "mod_10_cell_t" : mod_cell_t,
            "mod_11_cell_t" : mod_cell_t,
            "mod_12_cell_t" : mod_cell_t,
            "soc" : round(random.uniform(10,90),3),
            "soh" : round(random.uniform(0,100),3),
            "Status_of_sys" : random.randint(0,65535), #
            "IRU_State" : random.randint(0,255), #
            "v" : round(random.uniform(0,100),3),
            "i" : round(random.uniform(0,10),3),
            "flag1" : 0,
            "flag2" : 0,
            "flag3" : 0,
            "flag4" : 0,
            "flag5" : 0,
            "flag6" : 0,
            # "flag7" : 0,
            # "flag8" : 0,
            "flag9" : 0,        
            # "expireAt": 0
        }
        if i == 1:
            data_1 = data
            data_1["ID"] = "gus_bms_1"
            insert_data(collection, data_1)
        elif i == 2:
            data_2 = data
            data_2["ID"] = "gus_bms_2"
            insert_data(collection, data_2)
        else:
            pass
    data_sys = {
        "ID" : "gus_mbms",
        "time": datetime.datetime.now(),
        "cv_max_sys" : max(np.max(data_1["mod_1_cell_v"]), np.max(data_2["mod_1_cell_v"])),
        "cv_min_sys" : min(np.min(data_1["mod_1_cell_v"]), np.min(data_2["mod_1_cell_v"])),
        "ct_max_sys" : max(np.max(data_1["mod_1_cell_t"]), np.max(data_2["mod_1_cell_t"])),
        "ct_min_sys" : min(np.min(data_1["mod_1_cell_t"]), np.min(data_2["mod_1_cell_t"]))
    }
    # print(data_sys)
    insert_data(collection, data_sys)

def add_pcs_data():
    collection = "pcs"
    data = {
        "ID": "pcs",        
        "time": datetime.datetime.now(),        
        "status_pcs" : 0,
        "state_qs" : 0,
        "p_sum" : round(random.uniform(0,200),3),
        "q_sum" : round(random.uniform(0,200),3),
        "v1_grid" : round(random.uniform(0,200),3),
        "v2_grid" : round(random.uniform(0,200),3),
        "v3_grid" : round(random.uniform(0,200),3),
        "i1_pcs" : round(random.uniform(0,200),3),
        "i2_pcs" : round(random.uniform(0,200),3),
        "i3_pcs" : round(random.uniform(0,200),3),
        "f_grid" : round(random.uniform(0,200),3),
        "inner_temp" : round(random.uniform(0,200),3),
        "sink_temp" : round(random.uniform(0,200),3),
        "v_dc" : round(random.uniform(0,200),3),
        "i_dc" : round(random.uniform(0,200),3),
        "v_bat" : round(random.uniform(0,200),3),
        "fault1" : 0,
        "fault2" : 0,
        "fault3" : 0,
        "fault4" : 0,
        "dam_fault1" : 0,
        "dam_fault2" : 0,
        "dam_fault3" : 0,
        "dam_fault4" : 0,
        "dam_fault5" : 0,
        # "expireAt" : 0
    }
    # db[collection].insert(data)
    insert_data(collection, data)

def add_meter_data():
    collection = "meter"
    info = ["acb", "building", "place", "bess"]
    for i in info:
        data = {
            "ID": i,
            "time": datetime.datetime.now(),            
            "v_a": round(random.uniform(0,200),3),
            "v_b": round(random.uniform(0,200),3),
            "v_c": round(random.uniform(0,200),3),
            "v": round(random.uniform(0,200),3),
            "vl_ab": round(random.uniform(0,200),3),
            "vl_bc": round(random.uniform(0,200),3),
            "vl_ca": round(random.uniform(0,200),3),
            "vl": round(random.uniform(0,200),3),
            "i_a": round(random.uniform(0,200),3),
            "i_b": round(random.uniform(0,200),3),
            "i_c": round(random.uniform(0,200),3),
            "i": round(random.uniform(0,200),3),
            "p_a": round(random.uniform(0,200),3),
            "p_b": round(random.uniform(0,200),3),
            "p_c": round(random.uniform(0,200),3),
            "p": round(random.uniform(0,200),3),
            "q_a": round(random.uniform(0,200),3),
            "q_b": round(random.uniform(0,200),3),
            "q_c": round(random.uniform(0,200),3),
            "q": round(random.uniform(0,200),3),
            "s_a": round(random.uniform(0,200),3),
            "s_b": round(random.uniform(0,200),3),
            "s_c": round(random.uniform(0,200),3),
            "s": round(random.uniform(0,200),3),
            "pf_a": round(random.uniform(0,200),3),
            "pf_b": round(random.uniform(0,200),3),
            "pf_c": round(random.uniform(0,200),3),
            "pf": round(random.uniform(0,200),3),
            "f": round(random.uniform(59,61),3),
            # "imp_kwh": round(random.uniform(0,200),3),
            # "exp_kwh": round(random.uniform(0,200),3),
            # "tot_kwh": round(random.uniform(0,200),3),
            # "net_kwh": round(random.uniform(0,200),3),
            # "imp_kvarh": round(random.uniform(0,200),3),
            # "exp_kvarh": round(random.uniform(0,200),3),
            # "tot_kvarh": round(random.uniform(0,200),3),
            # "net_kvarh": self.net_kvarh,
            # "imp_kvah": round(random.uniform(0,200),3),
            # "exp_kvah": round(random.uniform(0,200),3),
            # "tot_kvah": round(random.uniform(0,200),3),
            # "net_kvah": round(random.uniform(0,200),3),
            # "SBSPM": round(random.uniform(0,200),3),
            # "expireAt": delete_time,
            # db[collection].insert(data)
        }
        insert_data(collection, data)

def add_pv_data():
    collection = "pv"    
    data = {
        "ID": "pv",
        "time": datetime.datetime.now(),            
        "v_a": round(random.uniform(0,200),3),
        "v_b": round(random.uniform(0,200),3),
        "v_c": round(random.uniform(0,200),3),
        "v": round(random.uniform(0,200),3),
        "vl_ab": round(random.uniform(0,200),3),
        "vl_bc": round(random.uniform(0,200),3),
        "vl_ca": round(random.uniform(0,200),3),
        "vl": round(random.uniform(0,200),3),
        "i_a": round(random.uniform(0,200),3),
        "i_b": round(random.uniform(0,200),3),
        "i_c": round(random.uniform(0,200),3),
        "i": round(random.uniform(0,200),3),
        "p_a": round(random.uniform(0,200),3),
        "p_b": round(random.uniform(0,200),3),
        "p_c": round(random.uniform(0,200),3),
        "p": round(random.uniform(0,200),3),
        "q_a": round(random.uniform(0,200),3),
        "q_b": round(random.uniform(0,200),3),
        "q_c": round(random.uniform(0,200),3),
        "q": round(random.uniform(0,200),3),
        "s_a": round(random.uniform(0,200),3),
        "s_b": round(random.uniform(0,200),3),
        "s_c": round(random.uniform(0,200),3),
        "s": round(random.uniform(0,200),3),
        "pf_a": round(random.uniform(0,200),3),
        "pf_b": round(random.uniform(0,200),3),
        "pf_c": round(random.uniform(0,200),3),
        "pf": round(random.uniform(0,200),3),
        "f": round(random.uniform(59,61),3),
        # "imp_kwh": round(random.uniform(0,200),3),
        # "exp_kwh": round(random.uniform(0,200),3),
        # "tot_kwh": round(random.uniform(0,200),3),
        # "net_kwh": round(random.uniform(0,200),3),
        # "imp_kvarh": round(random.uniform(0,200),3),
        # "exp_kvarh": round(random.uniform(0,200),3),
        # "tot_kvarh": round(random.uniform(0,200),3),
        # "net_kvarh": self.net_kvarh,
        # "imp_kvah": round(random.uniform(0,200),3),
        # "exp_kvah": round(random.uniform(0,200),3),
        # "tot_kvah": round(random.uniform(0,200),3),
        # "net_kvah": round(random.uniform(0,200),3),
        # "SBSPM": round(random.uniform(0,200),3),
        # "expireAt": delete_time,
        # db[collection].insert(data)
    }
    insert_data(collection, data)

def init_pcs_work():
    collection = "site_control"
    data = {
        "ID": "delta_pcs",
        "time" : datetime.datetime.now(),
        "mode" : 0,  #{"0":"STOP","6":"PQ"}
        "control" :  "Remote", # {"EMS" : "Remote","GC" : "Local"}
        "soc_max" : 90,
        "soc_min" : 10,
        "System_p_max" : 6, #kW
        "System_p_min" : 0, #kVAR
        "System_q_max" : 5, #kW
        "System_q_min" : 0, #kVAR
        "pq_p_ref" : 0, #kW
        'pq_q_ref' : 0, #kVAR
    }
    insert_data(collection, data)


if __name__ == '__main__':

    print('---------------------------------------------------------')
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    print('---------------------------------------------------------')   


    # --- 建立index ---
    # info = ["pcs","mbms"]
    # create_collection_index(info,"simple")

    # add_acm_data() 
    # add_acm2_data()
    # add_battery_data()
    # add_breaker_data()
    # add_pcs_data()

    add_mbms_data()  
    add_pcs_data() 
    add_meter_data()
    add_pv_data()
    init_pcs_work()

    # scheduler = BackgroundScheduler()
    # scheduler.start()
    # # #Status
    # scheduler.add_job(add_mbms_data,'cron', hour='*',minute='*',second='*')
    # scheduler.add_job(add_pcs_data,'cron', hour='*',minute='*',second='*')
    # scheduler.add_job(add_meter_data,'cron', hour='*',minute='*',second='*')
    # scheduler.add_job(add_pv_data,'cron', hour='*',minute='*',second='*')
    # ------
    
    
    # #scheduler.add_job(info,'cron', hour='*',minute='*',second='*/5')  
    # #scheduler.add_job(index_24hr_gen_update,'cron',hour='*',minute='*',second='0')  #測試1分鐘執行一次   
    print("finish")    
       
    # try:
    # # This is here to simulate application activity (which keeps the main thread alive).       
    #     while True:
    #         time.sleep(1) 
    # except (KeyboardInterrupt, SystemExit):
    #     # Not strictly necessary if daemonic mode is enabled but should be done if possible
    #     scheduler.shutdown()        
    #     print('Exit The Job!')
    # finally:
    #     print('done!')
       