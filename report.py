from weasyprint import HTML
from bs4 import BeautifulSoup
import datetime
import pymongo
from dateutil.relativedelta import relativedelta
import os
import psutil
import traceback #找出錯誤行數
import sys       #找出錯誤行數

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
#----------------------------------------------------------------------------------------------------------------------------------------
def GetLocalIPByPrefix(prefix='192.168.10.1'):
    localIP = 0
    dic = psutil.net_if_addrs()
    for adapter in dic:
        snicList = dic[adapter]
        for snic in snicList:
            if not snic.family.name.startswith('AF_INET'):
                continue                
            ip = snic.address
            if ip.startswith(prefix):
                localIP = 1
    return localIP
#----------------------------------------------------------------------------------------------------------------------------------------
conn = pymongo.MongoClient('mongodb://root:admin@127.0.0.1:27017',serverSelectionTimeoutMS=1000)
db = conn['gus']
def genReport(mode):
    if(GetLocalIPByPrefix()!=0):
        ###SET DATE RANGE
        try:
            date=datetime.datetime.now() 
            # print("start Report",mode,date)
            if mode == "month":
                end = datetime.datetime(year=date.year, month=date.month, day=1, hour=0, minute=0, second=0, microsecond=0)
                date = date-relativedelta(months=1)
                start= datetime.datetime(year=date.year, month=date.month, day=1, hour=0, minute=0, second=0, microsecond=0)
                rowStart=1
                rowEnd=31
                DataInterval = "日期"
                title="{}年度{}月份報表".format(date.year,date.month-1)
            elif mode == "day":
                end = datetime.datetime(year=date.year, month=date.month,day=date.day, hour=0, minute=0, second=0, microsecond=0)
                start = datetime.datetime(year=date.year, month=date.month, day=date.day-1, hour=0, minute=0, second=0, microsecond=0)
                rowStart=0
                rowEnd=23
                DataInterval = "小時"
                title="{}年度{}月{}日報表".format(date.year,date.month,(date.day-1))
            elif mode == "year":
                start = datetime.datetime(year=date.year-1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end = datetime.datetime(year=date.year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                rowStart=1
                rowEnd=12
                DataInterval = "月份"
                title="{}年度報表".format(date.year-1)
            """Generate a PDF file from a string of HTML."""

            dirpath=os.path.dirname(__file__)
            soup = BeautifulSoup(
                open(os.path.join(dirpath,"templates/reportTemplate.html"), encoding="utf-8"), 'html.parser')
            table = soup.find('tbody')
            soup.find(id="genDate").string='產出日期 : '+date.strftime('%Y{y}%m{m}%d{d}').format(y='年', m='月', d='日')
            soup.find(id="title").string=title
            soup.find(id="data_interval").string = DataInterval
            # 生成對應報表(日報月報年報)的行
            for i in range(rowEnd,rowStart-1, -1):
                table.insert(6, soup.new_tag('tr', id="dataRow{}".format(i)))
                for x in range(4):
                    table.find(id="dataRow{}".format(i)).insert(
                        1, soup.new_tag('td', attrs={"class": "dataCol"}))
                    table.find(id="dataRow{}".format(i)).find(
                        class_="dataCol").string = str(i)

            # 高壓側輸出電能
            # 高壓側輸入電能
            # 高壓側損失電能
            ID = 'bess'
            # print("start:",start)
            # print("end:",end)
            match = {"ID": ID, "time": {"$gte": start, "$lt": end}}
            project = {
                            "hour" : {"$hour": "$time"},
                            "day": {"$dayOfMonth": "$time"},
                            "month": {"$month": "$time"},
                            "imp_kwh": 1,
                            "exp_kwh": 1,
                            "tot_kwh": 1,
                        }
            group = {
                "_id": None,
                "last_imp_kwh": {"$last": "$imp_kwh"},
                "first_imp_kwh": {"$first": "$imp_kwh"},
                "last_exp_kwh": {"$last": "$exp_kwh"},
                "first_exp_kwh": {"$first": "$exp_kwh"},
                "last_tot_kwh": {"$last": "$tot_kwh"},
                "first_tot_kwh": {"$first": "$tot_kwh"}
            }
            if mode == "day":
                group["_id"]="$hour"  #設定一小時為單位的做一筆資料的統計
            elif mode == "month":
                group["_id"]="$day"   #設定一天為單位的做一筆資料的統計
            else:
                group["_id"]="$month" #設定一個月為單位的做一筆資料的統計

            # every hour 、 day or month
            dataList = list(db.meter.aggregate(   [
                        {'$match': match},
                        {"$project":project},  
                        {'$group': group},
                    ]))
            for data in dataList:
                try:
                    table.find(id="dataRow{}".format(data["_id"])).find_all(class_="dataCol")[
                            1].string = str(round(data["last_exp_kwh"]-data["first_exp_kwh"], 1))
                    table.find(id="dataRow{}".format(data["_id"])).find_all(class_="dataCol")[
                            2].string = str(round(data["last_imp_kwh"]-data["first_imp_kwh"], 1))
                    table.find(id="dataRow{}".format(data["_id"])).find_all(class_="dataCol")[
                            3].string = str(round(data["last_tot_kwh"]-data["first_tot_kwh"], 1))
                except Exception as e :  
                    # print(e)
                    print('Time:{}, info:{}'.format(datetime.datetime.now(), str(e)))
                    pass
            #### AVG
            group["_id"]=None
            dataList = list(db.meter.aggregate(   [
                        {'$match': match},
                        {"$project":project},  
                        {'$group': group},
                    ])) 
            
            for data in dataList:
                try:
                    table.find(id="h_exp_kwh").string = str(
                        round(data["last_exp_kwh"]-data["first_exp_kwh"], 1))
                    table.find(id="h_imp_kwh").string = str(
                        round(data["last_imp_kwh"]-data["first_imp_kwh"], 1))
                    table.find(id="h_tot_kwh").string = str(
                        round(data["last_tot_kwh"]-data["first_tot_kwh"], 1))
                except Exception as e :  
                    print('Time:{}, info:{}'.format(datetime.datetime.now(), str(e)))
                    # print(e)
                    pass

            # 電池soh資料
            rack1Data=db.mbms.find_one({"ID":"gus_bms_1"},{"_id":0,"soh":1}, sort=[('time', -1)])
            rack2Data=db.mbms.find_one({"ID":"gus_bms_2"},{"_id":0,"soh":1}, sort=[('time', -1)])
            if ((rack1Data is not None) and (rack2Data is not None)) :
                rack1soh = str(round(rack1Data['soh']))
                rack2soh = str(round(rack2Data['soh']))
                table.find(id="soh_sys").string = rack1soh + '/' + rack2soh 
            # else:
            #     print(rack1Data)
            #     print(rack2Data)
            output = soup.encode(formatter="html5")
            output = output.decode("utf-8")

            htmldoc = HTML(string=output, base_url="")
            pdf=htmldoc.write_pdf(stylesheets=[os.path.join(dirpath,"./static/css/reportTemplate.css")])

            db.report.insert({"time":end,"FileName":title,"type":mode,"file":pdf})
            # return pdf
        except:
            error_Msg=traceback_func()
            print('Time:{}, info:{}'.format(datetime.datetime.now(), error_Msg))
            # print(error_Msg)
        else:
            print("Successful!Time : ",datetime.datetime.now())
            print("--------------------------------------------------------------- ")

    else:
        print("Time:{}, status不在本機執行!!".format(datetime.datetime.now()))

# if __name__ == '__main__':
#     genReport(mode="day")