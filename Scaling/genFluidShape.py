import json
import sys
import copy 
import os

# ミキサーの水平，垂直方向の幅の最大値(最小2)
hvMAX = 3
# 液滴数の最大値
fluidNumMax = 10
# 生成したデータを保存するディレクトリのパス
path = './FluidShapeLib'

def isInsideBoundary(i,j):
    if 0<=i and i< hvMAX and 0<=j and j<hvMAX:
        return True 
    else :
        return False 

def main():
    ### 液滴1個は，2個の場合以降の元となるので，最初に単独で生成
    json_data = {}
    for i in range(hvMAX):
        for j in range(hvMAX):
            # 2x2ミキサーが最小探索領域
            SearchSpaceSize = str(max(i+1,j+1,2))
            if SearchSpaceSize not in json_data:
                json_data[SearchSpaceSize] = {}
            stridx = str(len(json_data[SearchSpaceSize]))
            coords = []
            coord = {"y":i,"x":j}
            coords.append(coord)
            json_data[SearchSpaceSize][stridx] = coords

    try:
        os.mkdir(path)
        print("Folder %s created!" % path)
    except FileExistsError:
        print("Folder %s already exists" % path)

    with open("FluidShapeLib/1fluid.json", "w") as f:
        json.dump(json_data, f,  ensure_ascii=False, indent=4,  separators=(',', ': '))
    
    dy = [0,-1,0,1]
    dx = [1,0,-1,0]
    
    # n個の液滴によって構成される形を元に，n+1個の液滴から構成される液滴の形を探索する．
    for fluidnum in range(2,fluidNumMax+1):
        SetOfNewShape = set()
        former = str(fluidnum-1)+"fluid.json"
        new = str(fluidnum)+"fluid.json"
       
        with open(os.path.join(path,former), "r") as f:
            FormerFluidShapes = json.load(f)
            for formerSearchSpace in range(2,hvMAX+1):
                strfss = str(formerSearchSpace)
                if strfss in FormerFluidShapes:
                    for fluididx in range(len(FormerFluidShapes[strfss])):
                        strfluididx = str(fluididx)
                        FluidShape = FormerFluidShapes[strfss][strfluididx]
                        shape = []
                        # shapeの形の情報を冗長なjson形式から圧縮して扱いやすくした（簡易的な座標形式）配列
                        # 液滴はいかなるx,y断面においても，整数の長さの線分とならなくてはならない（飛び地になったらダメ）
                        lowerY,upperY= [-100 for i in range(hvMAX)],[-100 for i in range(hvMAX)]
                        lowerX,upperX = [-100 for i in range(hvMAX)],[-100 for i in range(hvMAX)]
                        for coord in FluidShape:
                            y,x = coord["y"],coord["x"]
                            if lowerX[x]==-1 and upperX[x]==-1:
                                lowerX[x] = y 
                                upperX[x] = y 
                            else: 
                                lowerX[x] = min(y,lowerX[x])
                                upperX[x] = max(y,upperX[x])
                            if lowerY[y]==-1 and upperY[y]==-1:
                                lowerY[y] = x
                                upperY[y] = x
                            else: 
                                lowerY[y] = min(x,lowerY[y])
                                upperY[y] = max(x,upperY[y])
                            shape.append(tuple((y,x)))

                        for coordidx in range(len(shape)):
                            y,x = shape[coordidx]
                            for way in range(4):
                                ny,nx = y+dy[way],x+dx[way]
                                ncoord = (ny,nx)
                                if isInsideBoundary(ny,nx) and ncoord not in shape:
                                    nshape = copy.deepcopy(shape)
                                    nshape.append(ncoord)
                                    nshape.sort()
                                    # セットで扱えないのでnshapeをリストからタプルに詰め替える
                                    TupNShape = tuple(nshape)
                                    # (ny,nx)をshapeに加えたnshapeが有効な形（飛地のない形）かどうかを確認
                                    # ~FirstTime = その行/列に座標を置かれるのが初めて
                                    # ~NextToFormer = その座標の上下/左右の座標がすでに使われている
                                    # xf,xn,yf,ynとすると，((not xf) and (not xn)) or ((not yf) and (not yn)) がTrueになる場合を防ぎたい
                                    # また，アルゴリズム的にないはずだが，(not xf) and (not yf)がTrueになっていないことも確認
                                    nxFirstTime = lowerX[nx]==-100 and upperX[nx]==-100
                                    nxNextToFormer = abs(ny-lowerX[nx])<=1 or abs(ny-upperX[nx])<=1
                                    nyFirstTime = lowerY[ny]==-100 and upperY[ny]==-100
                                    nyNextToFormer = abs(nx-lowerY[ny])<=1 or abs(nx-upperY[ny])<=1
                                    if TupNShape not in SetOfNewShape \
                                        and (((not nxFirstTime) or (not nyFirstTime)) and (nxFirstTime or nxNextToFormer) and (nyFirstTime or nyNextToFormer)) :
                                        SetOfNewShape.add(TupNShape)

        with open(os.path.join(path,new), "w") as nf:
            json_data = {}
            for nshape in SetOfNewShape: 
                SearchSpace = -1
                OutputFormedData = []
                for ncoord in nshape: 
                    y,x = ncoord 
                    SearchSpace = max(SearchSpace,y+1,x+1)
                    res = {"y":y,"x":x}
                    OutputFormedData.append(res)
                # isInsideBoundaryでチェックしているが念のため再度チェック
                if 2<= SearchSpace and SearchSpace <= hvMAX:
                    strss = str(SearchSpace)
                    idx = 0
                    if strss not in json_data: 
                        json_data[strss] = {}
                    else: 
                        idx = len(json_data[strss])
                    json_data[strss][str(idx)] = OutputFormedData 
                else :
                    print("探索領域を超えたサイズの液滴です",nshape,SearchSpace,hvMAX,file=sys.stderr)
            json.dump(json_data, nf,  ensure_ascii=False, indent=4,  separators=(',', ': '))
   
if __name__ == "__main__":
    main()
