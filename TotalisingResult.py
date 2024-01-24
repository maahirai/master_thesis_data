import sys 
import csv
import os 
from pathlib import Path 


# test.pyの上位モジュール
tree_height = ["2","3","4"]
result_key = ["MixerCnt","FreqCelluseWithoutPPValue","FreqCelluseWithPPValue","FreqCelluseWithoutScaling","FreqCelluseWithScaling","CelluseNumWithoutPPValue","CelluseNumWithPPValue","CelluseNumWithoutScaling","CelluseNumWithScaling","OverlappWithoutPPValue","OverlappWithPPValue","OverlappWithoutScaling","OverlappWithScaling","FlushingWithoutPPValue","FlushingWithPPValue","FlushingWithoutScaling","FlushingWithScaling"]
add_key = ["OverlappReductionRateByPPValue","OverlappReductionRateByScaling","FlushingReductionRateByPPValue","FlushingReductionRateByScaling"]

totalising_dict = {}
datanum_cnt = {}

# 集計を行う変数の初期化
for height in tree_height: 
    totalising_dict[height] = {}
    datanum_cnt[height] = (0,{"OverlappReductionRateByPPValue":0,"OverlappReductionRateByScaling":0,"FlushingReductionRateByPPValue":0,"FlushingReductionRateByScaling":0})
    for key in result_key: 
        totalising_dict[height][key] = 0
    for akey in add_key: 
        totalising_dict[height][akey] = 0

result_path = "./result/"
files = os.listdir(result_path)
for filename in files:
    if os.path.isfile(os.path.join(result_path, filename)):
        full_path = os.path.join(result_path, filename)
        file_size = os.path.getsize(full_path)
        if file_size != 0:
            with open(full_path,newline='') as file: 
                reader = csv.DictReader(file)
                # dictのキーを取得
                #path, ext = os.path.splitext(filename) 
                #height,idx = path.split("_")
                #filelist.append((path,file_size))
                for row in reader:
                    # 有効なデータかチェック
                    if int(row["FlushingWithoutPPValue"])>=0 and int(row["FlushingWithPPValue"])>=0 and int(row["FlushingWithoutScaling"])>=0 and int(row["FlushingWithScaling"])>=0:
                        height = row["InitialHeightOfTree"]
                        overallnum,dict = datanum_cnt[height] 
                        overallnum += 1
                        datanum_cnt[height] = (overallnum,dict)
                        for key in result_key: 
                            if "." in row[key]:
                                totalising_dict[height][key] += float(row[key])
                            else : 
                                totalising_dict[height][key] += int(row[key])
                        
                        if int(row["FlushingWithoutPPValue"])>0:
                            totalising_dict[height]["FlushingReductionRateByPPValue"] += (1-(int(row["FlushingWithPPValue"])/int(row["FlushingWithoutPPValue"])))*100
                            overallnum,dict = datanum_cnt[height] 
                            dict["FlushingReductionRateByPPValue"] += 1
                            datanum_cnt[height] = (overallnum,dict)
                        if int(row["OverlappWithoutPPValue"])>0:
                            totalising_dict[height]["OverlappReductionRateByPPValue"] += (1-(int(row["OverlappWithPPValue"])/int(row["OverlappWithoutPPValue"])))*100
                            overallnum,dict = datanum_cnt[height] 
                            dict["OverlappReductionRateByPPValue"] += 1
                            datanum_cnt[height] = (overallnum,dict)

                        if int(row["FlushingWithoutScaling"])>0:
                            totalising_dict[height]["FlushingReductionRateByScaling"] += (1-(int(row["FlushingWithScaling"])/int(row["FlushingWithoutScaling"])))*100
                            overallnum,dict = datanum_cnt[height] 
                            dict["FlushingReductionRateByScaling"] += 1
                            datanum_cnt[height] = (overallnum,dict)
                        if int(row["OverlappWithoutScaling"])>0:
                            totalising_dict[height]["OverlappReductionRateByScaling"] += (1-(int(row["OverlappWithScaling"])/int(row["OverlappWithoutScaling"])))*100
                            overallnum,dict = datanum_cnt[height] 
                            dict["OverlappReductionRateByScaling"] += 1
                            datanum_cnt[height] = (overallnum,dict)
        #else : 
        #    print(full_path) 

print(datanum_cnt)
for height in tree_height: 
    cnt,dict = datanum_cnt[height]
    for key in result_key: 
        totalising_dict[height][key] = round(totalising_dict[height][key]/cnt,3)
    for akey in add_key: 
        totalising_dict[height][akey] = round(totalising_dict[height][akey]/dict[akey],3) 

dir_path = "./"
outputfile = "TotalisedResult.csv"
OutputPath = Path(dir_path,outputfile)
with open(OutputPath,'w',newline="") as f: 
    writer = csv.writer(f)
    writer.writerow(["Height","#MixerNum","#FreqWithoutPPV","#FreqWithPPV","#FreqWithoutScaling","#FreqWithScaling","#CelluseWithoutPPV","#CelluseWithPPV","#CelluseWithoutScaling","#CelluseWithScaling","#OverlappWithoutPPV","#OverlappWithPPV","#OverlappWithoutScaling","#OverlappWithScaling","#FlushingWithoutPPV","#FlushingWithPPV","#FlushingWithoutScaling","#FlushingWithScaling","OverlappReductionRateByPPValue","OverlappReductionRateByScaling","FlushingReductionRateByPPValue","FlushingReductionRateByScaling"])
    for height in tree_height: 
        res  = [height]
        for key in result_key: 
            res.append(totalising_dict[height][key])
        for akey in add_key: 
            res.append(totalising_dict[height][akey])
        writer.writerow(res)
