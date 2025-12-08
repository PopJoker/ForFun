from equip import PCS, Meter  #,ADAM
import pymongo
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from modbus_tk import modbus_tcp # ,modbus_rtu
import modbus_tk.defines as cst
# import serial
import time
import threading

import traceback #找出錯誤行數
import sys       #找出錯誤行數

# 追蹤哪一行程式出問題
def traceback_func():
    error_class, error_detail, tb = sys.exc_info()  # 取得Call Stack
    error_class = error_class.__name__              # 取得錯誤類型
    error_detail = error_detail.args[0]             # 取得詳細內容
    lastCallStack = traceback.extract_tb(tb)[-1]    # 取得Call Stack的最後一筆資料
    fileName = lastCallStack[0]                     # 取得發生的檔案名稱
    lineNum = lastCallStack[1]                      # 取得發生的行號
    funcName = lastCallStack[2]                     # 取得發生的函數名稱
    errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(fileName, lineNum, funcName, error_class, error_detail)
    return errMsg

# 資料庫連線
def Connect_database(host="192.168.10.1", port=27017, user="root", pwd="admin",db_name="gus"):
    try:              
        # conn = pymongo.MongoClient('mongodb://%s:%s@%s:%s' % (user, pwd, host, port))         
        conn = pymongo.MongoClient(host, port, serverSelectionTimeoutMS=5000)        
        conn.admin.authenticate(user,pwd)
        db = conn[db_name]
        return db    
    except Exception as e:
        print('Function of "Connect_database" errors:', e) 

# 計算 mongo資料到期時間，時間到自動刪除 (預設一年)
def Create_Expire_Data_time(nowtime, years=1, months=0, days=0, hours=0):
    return nowtime + relativedelta(years=years, months=months, days=days, hours=hours)     

# 上傳PCS資料 預計用於自動執行
def Insert_PCS_data_to_Mongo():
    try:
        pcs.Insert_Mongo_Data(db, "pcs", Create_Expire_Data_time(datetime.now()) )
    except Exception as e:
        print('Function of "Insert_PCS_data_to_Mongo" errors:', e)    

# 通用版 將資料寫進資料庫 (database, collection, 資料)
def Data_to_Mongo(db,collection,data):
    try:
        if "_id" in data:
            del data["_id"]       
        data["time"] = datetime.now() 
        db[collection].insert(data)
    except Exception as e:
        print('Function of "Data_to_mongo" errors:', e)

# ---------- PCS ---------
def PCS_work():
    pcs_counter = 0
    while True:
        try:
            if pcs_counter == 1:
                pcs.Read_PCS_Info(0)                
            elif pcs_counter == 3:
                pcs.Read_PCS_Info(1)                
            elif pcs_counter == 5:
                pcs.Read_PCS_Info(2)                
            elif pcs_counter == 7:
                pcs.Read_PCS_Info(3)               
            elif pcs_counter == 9:
                pcs.Read_PCS_Info(4)                
            # time.sleep(0.02)
            if pcs_counter >= 9:
                Insert_PCS_data_to_Mongo()
                pcs_site_control()           # PCS 輸出 
                pcs_counter = 0
            else:
                pcs_counter += 1              
        except Exception as e:
            print('Function of "PCS_work" errors:', e)

# 程式一啟動，初始化site_control參數
def init_site_control():
    global db
    try:
        site_control_get = list(db.site_control.find({},{"_id":0}).sort("time",-1).limit(1) ) [0]
        equipment_control_get = list(db.equipment_control.find({},{"_id":0}).sort("time",-1).limit(1) )[0]     

        # 如果資料庫無資料，先初始化
        if site_control_get == []:
            data = {
                "ID": "delta_pcs",
                "time" : datetime.now(),
                "mode" : 0,             # {"0":"STOP","6":"PQ"}
                "control" :  "Remote",  # {"EMS" : "Remote","GC" : "Local"}
                "soc_max" : 90,         # %
                "soc_min" : 10,         # %
                "System_p_max" : 1,     # kW
                "System_p_min" : 0,     # kVAR
                "System_q_max" : 1,     # kW
                "System_q_min" : 0,     # kVAR
                "pq_p_ref" : 0,         # kW
                "pq_q_ref" : 0,         # kVAR
                "isAntiFeedBack" : 1,   # 防逆送
                "CancelSocLimit" : 0    # 關閉SOC限制條件判斷  (1:取消SOC判斷， 0: 有SOC判斷)
            }
            Data_to_Mongo(db,"site_control",data)            
        else:            
            site_control_get["mode"], site_control_get["pq_p_ref"], site_control_get["pq_q_ref"] = 0, 0, 0    # 將mode先切回待機 (P Q不輸出)
            Data_to_Mongo(db,"site_control",site_control_get) 
            #------------
            equipment_control_get["pcs_on_off"] = 0
            Data_to_Mongo(db, "equipment_control", equipment_control_get)                       
        time.sleep(0.2)
        site_control_get = list(db.site_control.find({}).sort("time",-1).limit(1) ) [0] 
        print(site_control_get)  
        return site_control_get["_id"]      
    except Exception as e:
        print('Function of "init_site_control" errors:', e)
        return False
 
# pcs 控制
def pcs_site_control():    
    global now_pcs_site_control_id, db, set_doing, pcs_status_list, schedule_id, recover_counter 
    try:
        # 避免頻繁寫值控制PCS，所以當資料庫收到新一筆資料再執行即可  (判斷條件: mongo的預設_id)
        get =  list(db["site_control"].find({}).sort("time",-1).limit(1) )[0]        
        equipment_control_data = list(db["equipment_control"].find({}).sort("time",-1).limit(1) )[0]
        get_acb_meter = list(db["meter"].find({"ID":"acb"}).sort("time",-1).limit(1) )[0]       
        
        # pcs.SA_status= 1時(孤島)不能控制 PQ
        if (pcs.status_pcs == 1 or pcs.status_pcs == 3) and pcs.SA_status == 0:  
            print(datetime.now(), " pcs_status:", pcs.status_pcs, " mongo:", equipment_control_data["pcs_on_off"])
            if ( equipment_control_data["pcs_on_off"] == 1 and pcs.status_pcs == 3 ) or ( equipment_control_data["pcs_on_off"] == 0 and pcs.status_pcs == 1 ):
                if equipment_control_data["pcs_set_flag"] == 1:                    
                    db["equipment_control"].update({"_id": equipment_control_data["_id"]}, {"$set": { "pcs_set_flag": 0 }})                    
                    equipment_control_data = list(db["equipment_control"].find({}).sort("time",-1).limit(1) )[0]
                    set_doing = 0
                    print("update mongo, clear 'pcs_set_flag' to ", equipment_control_data["pcs_set_flag"])
                else:
                    pass
            else: # 現在狀態與資料庫不相同
                print("!!!-----now: ", pcs.status_pcs, ", mongo", equipment_control_data["pcs_on_off"])
                if equipment_control_data["pcs_set_flag"] == 1:
                    set_doing = 1
                    print("PCS will change pcs_stauts ! ")
                else: # 更新資料庫資料                   
                    if pcs.status_pcs == 3:
                        equipment_control_data["pcs_on_off"] = 1
                        Data_to_Mongo(db, "equipment_control", equipment_control_data)   
                        print("insert mongo, renew 'pcs_on_off' to 1 ")
                    elif pcs.status_pcs == 1:
                        equipment_control_data["pcs_on_off"] = 0
                        Data_to_Mongo(db, "equipment_control", equipment_control_data)   
                        print("insert mongo, renew 'pcs_on_off' to 0 ")
                    else:
                        print("now:", pcs.status_pcs)
            if now_pcs_site_control_id != get["_id"] or set_doing == 1: 
                if equipment_control_data["pcs_on_off"] == 1:
                    if get['mode'] == 0 :
                        pcs.PCS_ON_OFF_Set(1)
                        pcs.PCS_Set_PQ(0, 0, get)
                        print(datetime.now(), "--- PCS mode: 0 ---")
                    elif get['mode'] == 6 and get['control'] == "Remote" :                        
                        print("PCS_state: PQ Mode RUN")                              
                        pcs.PCS_ON_OFF_Set(1)
                        pcs.PCS_Set_PQ(get['pq_p_ref']*10, get['pq_q_ref']*10, get)   # pcs單位: 0.1k
                        print(datetime.now(), "--- PCS mode: 6 ---", "output:", [get['pq_p_ref'], get['pq_q_ref']] )                                
                    else:
                        pcs.PCS_Stop()                         
                else :
                    pcs.PCS_Stop() 
                    get["mode"], get["pq_p_ref"], get["pq_q_ref"] = 0, 0, 0    # 將mode先切回待機 (P Q不輸出)                              
                    Data_to_Mongo(db,"site_control",get)
                    print("insert mongo, pcs_stop => renew site_control data")
                    time.sleep(0.1)
                    get =  list(db["site_control"].find({}).sort("time",-1).limit(1) )[0]
                set_doing = 0
                now_pcs_site_control_id = get["_id"]
            
                        
            # 1. 電池充電時(p<0)，不能大於 max_v。 電池放電時(p>0)，不能小於 min_v。
            # 2. 電池充電時(p<0)，需注意soc_max。 電池放電時(p>0)，需注意soc_min。 # 2022/06/15 
            # 3. 輸出超過設定值 # 2022/06/15
            # 4. 新增關閉SOC限制條件判斷功能 #2022/06/27
            if get['mode'] == 6 and get['control'] == "Remote":
                if check_bms_v(pcs.p_sum, pcs.v_bat) or check_soc(pcs.p_sum, get["soc_max"], get["soc_min"], get["CancelSocLimit"]) or check_output(pcs.p_sum,pcs.q_sum, get):
                    pcs.PCS_Stop() 
                    get["mode"], get["pq_p_ref"], get["pq_q_ref"],  = 0, 0, 0    # 將mode先切回待機 (P Q不輸出)
                    Data_to_Mongo(db,"site_control",get)
                    if schedule_id != None:
                        db["schedule"].update({"_id": schedule_id}, {"$set": { "status": 3 }})
                        schedule_id = None
                    # print("soc over limit")
                    # print("battery's voltage over limit")


            # 新增防逆送 => PCS輸出不得大於總實功
            if get["isAntiFeedBack"] == 1 :
                # print(meter_acb.p , pcs.p_sum)
                if get['mode'] == 6 and get['control'] == "Remote":
                    # 防逆送保護
                    if meter_acb.p < 0 and pcs.p_sum > 0 :                          
                        # ----- 以下為原程式 -----
                        # print(datetime.now(), "PCS輸出功率大於電網功率", "meter_acb", meter_acb.p, "PCS:", pcs.p_sum)
                        # if pcs.p_sum - abs(meter_acb.p) > 0 :
                        #     get["pq_p_ref"] = int(pcs.p_sum - abs(meter_acb.p))                                                                
                        # else:
                        #     get["pq_p_ref"] = 0
                        # print("告警: 高壓測電表的實功 逆送回電網 => 將 P 降為", get["pq_p_ref"], "kW")   
                        # Data_to_Mongo(db,"site_control",get)  
                        # -------------------------------------------
                        # --- 06/10 修改 ---
                        text_question = "PCS輸出功率大於電網功率, meter_acb:{}, PCS:{}".format(meter_acb.p, pcs.p_sum)
                        print(datetime.now(), text_question)
                        if pcs.p_sum - abs(meter_acb.p) > 0 :
                            modify_p = (pcs.p_sum - abs(meter_acb.p))                                                               
                        else:
                            modify_p = 0.2    # 這邊寫0會有bug
                        text_solve =  "告警: 高壓側電表的實功 逆送回電網 => 將 P 降為{} kW ".format(modify_p)
                        print(text_solve)                       
                        
                        pcs.PCS_Set_PQ(modify_p*10, get['pq_q_ref']*10, get)   # pcs單位: 0.1k
                        print(datetime.now(), "--- PCS mode: 6 ---", "output:", [modify_p, get['pq_q_ref']])

                        record_data = {
                            "ID": "protect",
                            "time": datetime.now(),
                            "text_question": text_question,
                            "text_solve": text_solve
                        }
                        Data_to_Mongo(db,"AntiFeedBack", record_data)
                        time.sleep(0.3)
                    
                    # 防逆送後，因負載增加，將輸出提高    
                    if get["pq_p_ref"] > 0 and pcs.p_sum > 0 and (get["pq_p_ref"] > (pcs.p_sum + 0.3)) :  
                        if meter_acb.p > 0.5 :
                            recover_counter +=  1
                            if recover_counter >=  5:
                                modify_p = pcs.p_sum + 0.3
                                if get["pq_p_ref"] <= modify_p:
                                    modify_p = get["pq_p_ref"]                            
                                text_recover = "負載增加，將輸出功率提升至{} kW,  防逆送前之輸出設定為 {} kW".format(modify_p, get["pq_p_ref"])
                                print(text_recover)              

                                pcs.PCS_Set_PQ(modify_p*10, get['pq_q_ref']*10, get)   # pcs單位: 0.1k
                                print(datetime.now(), "--- PCS mode: 6 ---", "output:", [modify_p, get['pq_q_ref']] )

                                record_data = {
                                    "ID": "recover",
                                    "time": datetime.now(),
                                    "text_recover": text_recover
                                }
                                Data_to_Mongo(db,"AntiFeedBack", record_data)  
                                recover_counter = 0
                        else:
                            recover_counter = 0                                
                    else:
                        recover_counter = 0                          
        
            # 新增排程
            if datetime.now().minute == 59 and datetime.now().second > 50 :   # 59分50秒時，檢查排程是否有需動作
                if schedule_id != None:
                    get_schedule = list(db["schedule"].find({"_id": schedule_id}).limit(1) ) [0]
                    if (get_schedule["end"] < datetime.now() + timedelta(minutes=1) ) and get_schedule["status"] == 1:                        
                        db["schedule"].update({"_id": schedule_id}, {"$set": { "status": 2 }})  # 執行完成
                        new_control_data = list(db["equipment_control"].find({}).sort("time",-1).limit(1) )[0]
                        new_control_data["pcs_on_off"] = 0
                        new_control_data["pcs_set_flag"] = 1                        
                        Data_to_Mongo(db, "equipment_control", new_control_data)
                        schedule_id = None
                        print(datetime.now(), "--- Schedule end ---")
                    else:
                        print(datetime.now(), "--- Schedule still run ---")

                start = datetime.now()
                end = start + timedelta(minutes=1)                
                get_schedule = list(db["schedule"].find({ "start": {'$gt': start, '$lte': end}, "status":0, "show":1 }).limit(1))               
                if get_schedule != []:
                    get_schedule = get_schedule[0]
                    schedule_id = get_schedule["_id"]
                    data = {
                        "ID" : "delta_pcs",  
                        "control" : "Remote", 
                        "mode" : get_schedule["mode"],                 
                        "System_p_max" : get_schedule["System_p_max"],
                        "System_p_min" : get_schedule["System_p_min"],
                        "System_q_max" : get_schedule["System_q_max"],
                        "System_q_min" : get_schedule["System_q_min"], 
                        "pq_p_ref" : get_schedule["pq_p_ref"],
                        "pq_q_ref" : get_schedule["pq_q_ref"],
                        "soc_max" : get_schedule["soc_max"],
                        "soc_min" : get_schedule["soc_min"],                         
                        "isAntiFeedBack" : get_schedule["isAntiFeedBack"],
                        "CancelSocLimit" : get_schedule["CancelSocLimit"]
                    }
                    Data_to_Mongo(db,"site_control", data)
                    # -- 啟動PCS ---
                    new_control_data = list(db["equipment_control"].find({}).sort("time",-1).limit(1) )[0]
                    new_control_data["pcs_on_off"] = 1
                    new_control_data["pcs_set_flag"] = 1                        
                    Data_to_Mongo(db, "equipment_control", new_control_data)
                    # --------------
                    db["schedule"].update({"_id": schedule_id}, {"$set": { "status": 1 }})
                    print(datetime.now(), "--- schedule start ---")
                else:
                    print("no schedule run !!")    

        # SA Normal 孤島模式，  6 (SA Soft-Start)
        elif pcs.SA_status == 1  and  False  : 
            # 判斷ACB_meter電壓何時復電，一旦復電要將模式切離孤島           
            print(datetime.now(), "--- 孤島模式 ---")             
            # print("get_acb_meter: ", get_acb_meter["v"], "acb_on_off: ", equipment_control_data["acb_on_off"])
            # if  (get_acb_meter["v"] > offset_v) and (equipment_control_data["acb_on_off"] == 1) :  #孤島模式時，台電端復電  (在學校測試)
            if  (get_acb_meter["v"] > offset_v) and (equipment_control_data["acb_on_off"] == 1) and (acb_status == 1):  #孤島模式時，台電端復電
                get["mode"], get["pq_p_ref"], get["pq_q_ref"] = 0, 0, 0                 
                Data_to_Mongo(db,"site_control",get) 
                print(datetime.now(), "--- 市電回來了，關閉孤島模式 ---")
                pcs.Set_SA_Mode(0) 
            # 注意電池SOC => 若低於SOC下限時，強制將pcs停止孤島(輸出)。  battery_avg < get["soc_min"] 
            # if check_soc(10, get["soc_max"], get["soc_min"]):
            #     pcs.Set_SA_Mode(0)
            #     pcs.PCS_Stop()  

            # 注意電池電壓 => 若低於電壓下限時，強制將pcs停止孤島(輸出)。  pcs.v_bat < bms_min_v
            if check_bms_v(10, pcs.v_bat):
                pcs.Set_SA_Mode(0)
                pcs.PCS_Stop()
                 
        
        # pcs狀態不為1、3、7時的動作
        else:  
            # { "0":"Initial", "1":"Standby", "2":"Soft-start", "3":"Normal", "4":"Fault", "5":"Sleep", "6":"SA Soft-Start", "7":"SA Normal" }
            print(datetime.now(), "pcs status:", pcs_status_list[pcs.status_pcs])           

        # 進孤島模式的條件 (acb電壓低於指定值、acb狀態為0) => 更改為 讀取pcs抓取的電網頻率(因斷電時acb_meter也會沒電)
        # if (get_acb_meter["v"] < offset_v) and (equipment_control_data["acb_on_off"] == 0) and  (pcs.status_pcs != 7) and (pcs.SA_status == 0):  #孤島模式  (在學校測試)
        # if (get_acb_meter["v"] < offset_v) and (pcs.status_pcs != 7) and (pcs.SA_status == 0) and (acb_status == 0):  #孤島模式   
        if (pcs.f_grid < offset_f) and (pcs.status_pcs != 7) and (pcs.SA_status == 0) and (acb_status == 0) and False:  #孤島模式 
            pcs.Set_SA_Mode(1)            
            print(datetime.now(), "---進入孤島模式---")
            # pcs.PCS_ON_OFF_Set(1)  # 100kW pcs 需要, 125kW好像不用
        else: 
            pass
        time.sleep(0.5)        #之後看是否有需要
        
    except Exception as e:
        error_message = traceback_func()
        print(error_message)
        print('Function of "PCS_site_control" errors:', e) 
# ------------------------ 

def check_soc(p, max_soc, min_soc, CancelSocLimit_flag):    
    # 電池充電時(p<0)，需注意soc_max。 電池放電時(p>0)，需注意soc_min。
    try:
        # 是否取消SOC限制條件
        if CancelSocLimit_flag == 1:
            return False
        else:
            get_battery1_soc =  list(db["mbms"].find({"ID": "gus_bms_1" },{"_id":0,"soc":1}).sort("time",-1).limit(1) )[0].get('soc')
            get_battery2_soc =  list(db["mbms"].find({"ID": "gus_bms_2" },{"_id":0,"soc":1}).sort("time",-1).limit(1) )[0].get('soc')
            
            if ( (p < 0) and ((max_soc <= get_battery1_soc) or (max_soc <= get_battery2_soc)))  or \
            ( (p > 0) and ((min_soc >= get_battery1_soc) or (min_soc >= get_battery2_soc))):
                data = {                
                    "event": "SOC over limit",
                    "p": p,
                    "soc": [max_soc, min_soc],
                    "soc_rack1": get_battery1_soc,
                    "soc_rack2": get_battery2_soc                   
                }
                Data_to_Mongo(db, "limit_event", data)
                print(datetime.now(), "--- SOC over limit ---")
                return True
            else:
                return False
    except Exception as e:
        print('Function of "check_soc" errors:', e) 
        return False

def check_bms_v(p, pcs_v_bat):    
    # 電池充電時(p<0)，不能大於 max_v。 電池放電時(p>0)，不能小於 min_v。    
    try:        
        if ( (p < 0) and (bms_max_v < pcs_v_bat) )  or ( (p > 0) and (bms_min_v > pcs_v_bat) ):           
            data = {                
                "event": "battery's voltage over limit",
                "p": p,
                "bms_v": [bms_max_v, bms_min_v],
                "pcs_v_bat": pcs_v_bat
            }
            Data_to_Mongo(db, "limit_event", data)
            print(datetime.now(), "--- battery's voltage over limit ---")
            return True
        else:
            return False
    except Exception as e:
        print('Function of "check_bms_v" errors:', e) 
        return False

def check_output(p, q, limit):
    try:
        if  ( (limit["System_p_min"]-0.5) < p < (limit["System_p_max"]+0.5) ) and \
            ( (limit["System_q_min"]-0.5) < q < (limit["System_q_max"]+0.5) ) :
            return False
        else:
            data = {                
                "event": "output_PQ over limit",
                "p": p,
                "q": q,
                "system_p": [ limit["System_p_min"], limit["System_p_max"] ],
                "system_q": [ limit["System_q_min"], limit["System_q_max"] ]
            }
            Data_to_Mongo(db, "limit_event", data)     
            print(datetime.now(), "--- output_PQ over limit ---")
            return False # 僅記錄，不強制跳脫
    except Exception as e:
        print('Function of "check_output" errors:', e) 
        return False

# --------- MBMS ---------
# 因為使用CAN傳輸，新的程式寫在其他資料夾
# ------------------------ 
    
# --------- Meter ---------
def Meter_work():
    # 有五個電表因不要求讀取速度，所以一個一個讀取就好，若有要求速度在用線程分別執行
    while True:
        try:
            # meter_acb
            try:        
                meter_acb.Read_Meter_Info()
                meter_acb.Insert_Mongo_Data(db, "meter", Create_Expire_Data_time(datetime.now()) )
                time.sleep(0.05)
            except Exception as e:
                print("--- meter_acb ---",' errors:', e)
                time.sleep(0.05)
            # meter_building
            try:
                meter_building.Read_Meter_Info_2()
                meter_building.Insert_Mongo_Data(db, "meter", Create_Expire_Data_time(datetime.now()) )
                time.sleep(0.05)
            except Exception as e:
                print("--- meter_building ---",' errors:', e)
                time.sleep(0.05)
            # meter_place
            try:
                meter_place.Read_Meter_Info()
                meter_place.Insert_Mongo_Data(db, "meter", Create_Expire_Data_time(datetime.now()) )
                time.sleep(0.05)
            except Exception as e:
                print("--- meter_place ---",' errors:', e)
                time.sleep(0.05)
            # meter_bess
            try:
                meter_bess.Read_Meter_Info()
                meter_bess.Insert_Mongo_Data(db, "meter", Create_Expire_Data_time(datetime.now()) )
                time.sleep(0.05)
            except Exception as e:
                print("--- meter_bess ---",' errors:', e)
                time.sleep(0.05)
            # pv
            try:
                meter_pv.Read_Meter_Info()    
                meter_pv.Insert_Mongo_Data(db, "pv", Create_Expire_Data_time(datetime.now()) )
                time.sleep(0.05)
            except Exception as e:
                print("--- pv ---",' errors:', e)
                time.sleep(0.05)     
        except Exception as e:            
            # print(traceback_func())
            print('Function of "Meter_work" errors:', e)
            time.sleep(0.05)
# ------------------------ 

# --------- ADAM-6050 ---------
def ACB_work():
    global db, acb_status    
    master = modbus_tcp.TcpMaster("192.168.10.11", 502)  # ACB乾接點
    # master = modbus_rtu.RtuMaster(serial.Serial(port='com4', baudrate=9600, bytesize=8, parity='N', stopbits=1))
    master.set_timeout(3.0)
    master.set_verbose(True)    
    while True:
        try:            
            get_db = list(db.equipment_control.find({},{"_id":0}).sort("time",-1).limit(1) )[0]
            acb_status = master.execute(slave=1, function_code=cst.READ_COILS, starting_address=0, quantity_of_x=1)[0]
            print("acb_status:", acb_status, ",flag:", get_db["acb_set_flag"], ",db:" ,get_db["acb_on_off"]) 

            if (acb_status == get_db["acb_on_off"]) :
                if (get_db["acb_set_flag"] == 1):
                    get_db["acb_set_flag"] = 0
                    # get_db["time"] = datetime.now()
                    Data_to_Mongo(db, "equipment_control", get_db)
                    print("update mongo, clear 'acb_set_flag' to ", get_db["acb_set_flag"])                    
                else:
                    pass
            else:  # 現在狀態與資料庫不同
                if (get_db["acb_set_flag"] == 1):
                    # 做控制動作    DO 0: 投入的線圈， DO 1:跳脫的線圈    => 兩個線圈皆為自保持電路，記得不能同時on 或 off
                    if get_db["acb_on_off"] == 0:  # ACB斷電 (孤島)
                        # master.execute(slave=1, function_code=cst.WRITE_MULTIPLE_COILS, starting_address=17, quantity_of_x=2, output_value=[0,1])
                        master.execute(slave=1, function_code=cst.WRITE_MULTIPLE_COILS, starting_address=17, output_value=[0,1])
                    # elif get_db["acb_on_off"] == 1 and meter_acb.v > offset_v :
                    elif get_db["acb_on_off"] == 1 and pcs.f_grid > offset_f :                    
                        master.execute(slave=1, function_code=cst.WRITE_MULTIPLE_COILS, starting_address=17, output_value=[1,0])
                    else:
                        print("ACB_meter 電壓:", meter_acb.v)  # 檢查用    
                        print("PCS 電網頻率:", pcs.f_grid)                         

                    time.sleep(1)  
                else:   
                    #更新資料庫資料                    
                    get_db["acb_on_off"] = acb_status
                    Data_to_Mongo(db, "equipment_control", get_db)
                    print("ACB_work(), BBBBB")
            time.sleep(1)            
            
        except Exception as e:
            print('Function of "ACB_work" errors:', e)
# ------------------------ 


if __name__ == '__main__':    
  
    print("System start")       
    # db = Connect_database(db_name="gus_test", host="140.118.172.244")      # 學校
    # ------------------------------ 
    db = Connect_database(db_name="gus") 
    pcs = PCS()  

    meter_acb = Meter("acb", "192.168.10.10", 502)            # Meter(id, ipAddress, port)
    meter_building = Meter("building", "192.168.10.12", 502)  # Meter(id, ipAddress, port)
    meter_place = Meter("place", "192.168.10.13", 502)        # Meter(id, ipAddress, port)
    meter_bess = Meter("bess", "192.168.10.14", 502)          # Meter(id, ipAddress, port)
    meter_pv = Meter("pv", "192.168.10.15", 502)              # Meter(id, ipAddress, port)
    
    # # 線程
    thread_PCS_work = threading.Thread(target = PCS_work)
    thread_Meter_work = threading.Thread(target = Meter_work)
    # thread_ACB_work = threading.Thread(target = ACB_work)  

    #init 記錄資料庫最新一筆資料的_id
    now_pcs_site_control_id = init_site_control()    
    print(now_pcs_site_control_id)
    time.sleep(1)    
    #                       0        1          2           3       4       5            6           7
    pcs_status_list = ["Initial","Standby","Soft-start","Normal","Fault","Sleep","SA Soft-Start","SA Normal"]
    set_doing = 0    
    acb_status = 1
    offset_v = 100   # 電壓低於多少視為斷電 (孤島判斷ACB_meter電壓用)
    offset_f = 45    # 頻率低於多少視為斷電 (孤島判斷 PCS讀電網頻率)
    bms_max_v = 933  # 格斯電池 最高電壓  (由pcs中 bat_v 抓的值為主) 
    bms_min_v = 810  # 格斯電池 最低電壓  (由pcs中 bat_v 抓的值為主)

    schedule_id = None   
    recover_counter = 0  

    # PCS_work()        
    # Meter_work()

    thread_PCS_work.start()   # 啟用線程
    thread_Meter_work.start() # 啟用線程
    # thread_ACB_work.start()   # 啟用線程


    while True:
        time.sleep(0.5)
   
    print("end")
        
 
