import sys 
import csv
import os 
from pathlib import Path 


# test.pyの上位モジュール
tree_height = ["2","3","4"]
result_key = ["FreqCelluseWithoutPPValue","FreqCelluseWithPPValue","FreqCelluseWithoutScaling","FreqCelluseWithScaling","CelluseNumWithoutPPValue","CelluseNumWithPPValue","CelluseNumWithoutScaling","CelluseNumWithScaling","FlushingWithoutPPValue","FlushingWithPPValue","FlushingWithoutScaling","FlushingWithScaling"]
add_key = ["ReductionRateByPPValue","ReductionRateByScaling"]
totalising_dict = {}
datanum_cnt = {}

# 集計を行う変数の初期化
for height in tree_height: 
    totalising_dict[height] = {}
    datanum_cnt[height] = (0,{"ReductionRateByPPValue":0,"ReductionRateByScaling":0})
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
                            totalising_dict[height]["ReductionRateByPPValue"] += (1-(int(row["FlushingWithPPValue"])/int(row["FlushingWithoutPPValue"])))*100
                            overallnum,dict = datanum_cnt[height] 
                            dict["ReductionRateByPPValue"] += 1
                            datanum_cnt[height] = (overallnum,dict)
                        if int(row["FlushingWithoutScaling"])>0:
                            totalising_dict[height]["ReductionRateByScaling"] += (1-(int(row["FlushingWithScaling"])/int(row["FlushingWithoutScaling"])))*100
                            overallnum,dict = datanum_cnt[height] 
                            dict["ReductionRateByScaling"] += 1
                            datanum_cnt[height] = (overallnum,dict)
        else : 
            print(full_path) 

for height in tree_height: 
    cnt,dict = datanum_cnt[height]
    for key in result_key: 
        totalising_dict[height][key] /= cnt 
    for akey in add_key: 
        totalising_dict[height][akey] /= dict[akey]
    print(totalising_dict[height])
