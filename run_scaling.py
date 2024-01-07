# -*- coding: utf-8 -*-
from Scaling import *
from Scaling import tree
from Scaling import flexplace
from importlib import reload 
from pathlib import Path
import sys 
import csv
import os 
def create_directory(dir_name):
    if not os.path.exists(dir_name):
        print ('Creating directory: ', dir_name)
        os.makedirs(dir_name)

R1,R2,R3,R4,R5 = "R1","R2","R3","R4","R5"
import pathlib 
from copy import deepcopy
import datetime 

# デフォルトの木の高さ 3,デフォルトのPMDサイズ 20x20
height, size = 3,20
height,num22,num23,TREE = genInputTree(int(height),0.8,4,fair=True)

#********************* tmp.pyの動かし方（How to）*****************************#
# python3 tmp.py #1 
# 入力パターン1: #1_混合木を表すリストの文字列
# 入力パターン2: #1_混合木の高さ

# python3 tmp.py #1 #2 
# 入力パターン1: #1_混合木を表すリスト文字列，#2_PMDのサイズ
# 入力パターン2: #1_混合木の高さ，#2_PMDのサイズ

# python3 tmp.py #1 #2 #3 
# 入力パターン1: #1_混合木を表すリスト，#2_ノードカラーの配列，#3_PMDのサイズ
#******************************************************************************#


# tmp.py　が一つ目の引数
# python3 tmp.py #1 
# 入力パターン1: #1_混合木を表すリストの文字列
# 入力パターン2: #1_混合木の高さ
if len(sys.argv) == 2: 
    input_value = eval(sys.argv[1])
    # 入力で混合木（リストのインスタンス）が与えられている場合は，そのデータで試薬合成を行う
    if isinstance(input_value,list):
        TREE = input_value 
    else: 
        while(height!=input_value): 
            height,num22,num23,TREE = genInputTree(input_value,0.8,4,fair=True)
# python3 tmp.py #1 #2 
# 入力パターン1: #1_混合木を表すリスト文字列，#2_PMDのサイズ
# 入力パターン2: #1_混合木の高さ，#2_PMDのサイズ
if len(sys.argv) == 3: 
    input_value = eval(sys.argv[1])
    if isinstance(input_value,list):
        TREE = input_value 
    else: 
        while(height!=input_value): 
            height,num22,num23,TREE = genInputTree(input_value,0.8,4,fair=True)
    size = eval(sys.argv[2])
color = []
# python3 tmp.py #1 #2 #3 
# 入力パターン1: #1_混合木を表すリスト，#2_ノードカラーの配列，#3_PMDのサイズ
if len(sys.argv) == 4: 
    num22 = -1
    num23 = -1
    input_value = eval(sys.argv[1])
    TREE = input_value 
    color = eval(sys.argv[2])
    size = eval(sys.argv[3])


Tree = tree.InputToTree(TREE)
if color : 
    tree.ColorList = color
create_directory("image")
tree.saveTree(Tree,"image/Tree"+"slide.png")
#TransformedTree = tree.TransformTree(Tree)
#tree.saveTree(TransformedTree,"image/TransformedTree"+"slide.png")
ColorList = tree.ColorList 
print("\n同じ条件で再実行する場合は>>\npython3 run_scaling.py \"",TREE,"\" \"",ColorList,"\" ",size,"\n",sep="")

ScaledTree = deepcopy(Tree)
# 一つスケーリングをキャンセルする機能をつける
formerTree = deepcopy(Tree)
#while(True): 
#    print("スケーリングの対象ミキサーのインデックスを入力してください\n（前回分のキャンセルなら\'c\'を，使用セル数の推定には\'e\'を打ち込んでください)")
#    idx = input('>> ')
#    if idx == 'c':
#        print("前回の一回分のスケーリングがキャンセルされました")
#        ScaledTree = formerTree
#        tree.saveTree(ScaledTree,"image/ScaledTree"+"slide.png")
#        continue 
#    if idx == 'e': 
#        print("使用セル数推定の対象ミキサーのインデックスを入力してください")
#        idx = input('>> ')
#        print("M{}を根とする部分木の推定使用セル数は{}セルです.".format(idx,tree.EstimateCelluseNum(tree.getNode(ScaledTree,"M{}".format(idx)))))
#        continue
#    print("M{}を何倍スケーリングしますか".format(idx))
#    scale_factor = int(input('>> '))
#        
#    target = "M{}".format(idx)
#    formerTree = ScaledTree
ScaledTree = tree.preLayout_Scaling(ScaledTree)
tree.saveTree(ScaledTree,"image/ScaledTree"+"slide.png")

#ColorList = ['#4ccdd1', '#ec8f8a', '#41ee85', '#957470', '#89a772', '#f3bad0', '#d5b38b', '#e3c283', '#5a58e3', '#e59545']

#WithoutTransform,cmpOverlappNum,cmpFootPrint,cmpFreq = xntm(Tree,[size,size],ColorList=ColorList,ImageName="slide",ImageOut=True,ProcessOut=False) 
#Transformed,OverlappNum,FootPrint,Freq = xntm(TransformedTree,[size,size],ColorList=ColorList,ImageName="slide"+"_transformed",ImageOut=True,ProcessOut=False)
flexplace.SamplePreparation(Tree,[size,size],ColorList=ColorList,ImageName="slide",ImageOut=True,ProcessOutput=False)
flexplace.SamplePreparation(ScaledTree,[size,size],ColorList=ColorList,ImageName="slide"+"_transformed",ImageOut=True,ProcessOutput=False)

#WithoutTransform,cmpOverlappNum,cmpFootPrint,cmpFreq = xntm(Tree,[size,size],ColorList=ColorList,ImageName="slide",ImageOut=True,ProcessOut=True) 
#Transformed,OverlappNum,FootPrint,Freq = xntm(TransformedTree,[size,size],ColorList=ColorList,ImageName="slide"+"_transformed",ImageOut=True,ProcessOut=True)
    #WithoutTransform = xntm(Tree,[20,20],ColorList=ColorList,ImageName="slide",ImageOut=True,ProcessOut=True) 
    #Transformed = xntm(TransformedTree,[20,20],ColorList=ColorList,ImageName="slide"+"_transformed",ImageOut=True,ProcessOut=True)
#result = [height,cmpOverlappNum,OverlappNum,WithoutTransform,Transformed]
#print(result)
#print("変形なしFlushing:{},変形ありFlushing:{}".format(WithoutTransform,Transformed))
#print("変形なしFootPrint:{},変形ありFootPrint:{}".format(cmpFootPrint,FootPrint))
#print("変形なしFreq:{:.3f},変形ありFreq:{:.3f}".format(cmpFreq,Freq))

#print(num22,num23)
reload(tree)
