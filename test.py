#from XNTM import  *
#from XNTM import tree
#from XNTM import xntm
import XNTM.tree
import XNTM.xntm
import Scaling.tree 
import Scaling.flexplace
from importlib import reload 
from pathlib import Path
import sys 
import csv
import os 
def create_directory(dir_name):
    if not os.path.exists(dir_name):
        print ('Creating directory: ', dir_name)
        os.makedirs(dir_name) 

gomi,MaxDepth,datanum,filename = "","","",""
if len(sys.argv ) == 4:
    gomi,MaxDepth,datanum,filename = sys.argv 
else : 
    gomi,MaxDepth = sys.argv 

import datetime
if not filename : 
    filename = MaxDepth+"_"+str(datetime.datetime.now())
if not datanum : 
    ### 生成する入力希釈木数
    datanum = "10"

import pathlib 
result_dir = './result/'
create_directory(result_dir)
path = Path(result_dir,filename+'.csv')
with open(path,'w',newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["InitialHeightOfTree","FreqCelluseWithoutPPValue","FreqCelluseWithPPValue","FreqCelluseWithoutScaling","FreqCelluseWithScaling","CelluseNumWithoutPPValue","CelluseNumWithPPValue","CelluseNumWithoutScaling","CelluseNumWithScaling","FlushingWithoutPPValue","FlushingWithPPValue","FlushingWithoutScaling","FlushingWithScaling"])
    for i in range(int(datanum)):
        height,num22,num23,TREE = Scaling.InputTree.genInputTree(int(MaxDepth),0.8,4,fair=True)
        while(height!=int(MaxDepth)): 
            height,num22,num23,TREE = Scaling.InputTree.genInputTree(int(MaxDepth),0.8,4,fair=True) 
            print(str(TREE).replace(" ",""))

        pmdsize = (int(MaxDepth)+1)//2*10

        # PPValue
        Tree = XNTM.tree.InputToTree(TREE)
        #saveTree　もしくは　viewTree無しではカラーリストが設定されない
        XNTM.tree.viewTree(Tree)
        #viewTree(Tree)
        TransformedByPPValue = XNTM.tree.TransformTree(Tree)
        #viewTree(TransformedTree)
        XNTM.tree.viewTree(TransformedByPPValue)
        #ColorList = tree.ColorList
        #print("カラーリスト",tree.ColorList)
        FlushingWithoutPPValue,CelluseNumWithoutPPValue,FreqCelluseNumWithoutPPValue = XNTM.xntm(Tree,[pmdsize,pmdsize],ColorList=XNTM.tree.ColorList,ImageName=str(i+1)+"_WithoutPPValue",ImageOut=False) 
        FlushingWithPPValue,CelluseNumWithPPValue,FreqCelluseNumWithPPValue = XNTM.xntm(TransformedByPPValue,[pmdsize,pmdsize],ColorList=XNTM.tree.ColorList,ImageName=str(i+1)+"_PPValue",ImageOut=False)
        
        # Scaling
        Tree = Scaling.tree.InputToTree(TREE)
        Scaling.tree.ColorList = XNTM.tree.ColorList
        print(Scaling.tree.ColorList)
        
        dir = "./image/"
        create_directory(dir)
        #saveTree　もしくは　viewTree無しではカラーリストが設定されない
        Scaling.tree.viewTree(Tree)
        #viewTree(Tree)
        TransformedByScaling = Scaling.tree.preLayout_Scaling(Tree)
        filename = dir+"ScaledTree"+str(i+1)+".png"
        Scaling.tree.saveTree(TransformedByScaling,filename)
        #viewTree(TransformedTree)
        Scaling.tree.viewTree(TransformedByScaling)
        #ColorList = tree.ColorList
        FlushingWithoutScaling,CelluseNumWithoutScaling,FreqCelluseNumWithoutScaling = Scaling.flexplace.SamplePreparation(Tree,[pmdsize,pmdsize],ColorList=Scaling.tree.ColorList,IsScalingUsable=False,ImageName=str(i+1)+"_WithoutScaling",ImageOut=True) 
        FlushingWithScaling,CelluseNumWithScaling,FreqCelluseNumWithScaling = Scaling.flexplace.SamplePreparation(TransformedByScaling,[pmdsize,pmdsize],ColorList=Scaling.tree.ColorList,IsScalingUsable=True,ImageName=str(i+1)+"_Scaling",ImageOut=True)

        result = [height,FreqCelluseNumWithoutPPValue,FreqCelluseNumWithPPValue,FreqCelluseNumWithoutScaling,FreqCelluseNumWithScaling,CelluseNumWithoutPPValue,CelluseNumWithPPValue,CelluseNumWithoutScaling,CelluseNumWithScaling,FlushingWithoutPPValue,FlushingWithPPValue,FlushingWithoutScaling,FlushingWithScaling]
        writer.writerow(result)
        print(result)

        ### ノードの色などグローバル変数の初期化
        reload(XNTM.tree)
        reload(Scaling.tree)
