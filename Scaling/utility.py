import os
def create_directory(dir_name):
    if not os.path.exists(dir_name):
        print ('Creating directory: ', dir_name)
        os.makedirs(dir_name)

def Translate(name): 
    subscript = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    return name.translate(subscript)

from PIL import Image,ImageDraw,ImageFont

sep = 30
Width = 20
class SlideCell: 
    global draw,SlideCellWidth,blank
    def __init__(self,y,x,color="",state=""): 
        self.color = color if color else "White"
        self.state = state if state else ""
        draw.rectangle([(x,y),(x+SlideCellWidth,y+SlideCellWidth)],fill = self.color,outline="Black")
        dropfontsize = 15
        dropfont = ImageFont.truetype("Times New Roman.ttf", dropfontsize)
        fromy,fromx = x+sep,y+sep 
        toy,tox = fromy+Width,fromx+Width
        
        self.sy = y
        self.sx = x 
        self.ey = y+SlideCellWidth
        self.ex = x+SlideCellWidth

        self.LTopY = y
        self.LTopX = x
        self.LBottomY = y+SlideCellWidth
        self.LBottomX = x
        self.RTopY = y
        self.RTopX = x+SlideCellWidth
        self.RBottomY = y+SlideCellWidth
        self.RBottomX = x+SlideCellWidth

    def change(self,color,state):
        self.color = color 
        self.state = state 
        draw.rectangle([(self.sx,self.sy),(self.sx+SlideCellWidth,self.sy+SlideCellWidth)],fill = self.color,outline="Black")
        dropfontsize = 15
        dropfont = ImageFont.truetype("Times New Roman.ttf", dropfontsize)
        fromy,fromx = self.sy,self.sx
        toy,tox = fromy+SlideCellWidth,fromx+SlideCellWidth
        draw.text(((fromx+tox)//2-9,(fromy+toy)//2-9),self.state,font=dropfont,fill="Black")

SlideCellWidth,blank =40,10
def genSlideGrid(PMD): 
    global draw,SlideCellWidth,blank
    img = Image.new("RGB",(PMD.pmdHsize*SlideCellWidth+2*blank,(PMD.pmdVsize+1)*SlideCellWidth+blank),"White")
    draw = ImageDraw.Draw(img)
    Grid = []
    for i in range(PMD.pmdVsize): 
        row = []
        for j in range(PMD.pmdHsize): 
            y = i*SlideCellWidth+blank
            x = j*SlideCellWidth+blank
            cell = SlideCell(y,x) 
            row.append(cell)
        Grid.append(row) 
    return Grid,img 

MixerLineWidth = 10
def getOutlineOfMixerShape(MixerCells,Grid):
    global MixerLineWidth
    res = []
    lines = []
    dy,dx = [0,1,0,-1],[-1,0,1,0] 
    for way in range(0,4): 
        line = []
        for cell in MixerCells: 
            y,x = cell 
            OffsetMixerLineWidth = MixerLineWidth//5
            #　セルの四隅の座標
            LeftSet = [(Grid[y][x].LTopY+OffsetMixerLineWidth,Grid[y][x].LTopX+OffsetMixerLineWidth),(Grid[y][x].LBottomY-OffsetMixerLineWidth,Grid[y][x].LBottomX+OffsetMixerLineWidth)]
            TopSet = [(Grid[y][x].LTopY+OffsetMixerLineWidth,Grid[y][x].LTopX+OffsetMixerLineWidth),(Grid[y][x].RTopY+OffsetMixerLineWidth,Grid[y][x].RTopX-OffsetMixerLineWidth)]
            RightSet = [(Grid[y][x].RTopY+OffsetMixerLineWidth,Grid[y][x].RTopX-OffsetMixerLineWidth),(Grid[y][x].RBottomY-OffsetMixerLineWidth,Grid[y][x].RBottomX-OffsetMixerLineWidth)]
            BottomSet = [(Grid[y][x].LBottomY-OffsetMixerLineWidth,Grid[y][x].LBottomX+OffsetMixerLineWidth),(Grid[y][x].RBottomY-OffsetMixerLineWidth,Grid[y][x].RBottomX-OffsetMixerLineWidth)]

            addcoords = [LeftSet,BottomSet,RightSet,TopSet]
            ny,nx = y+dy[way],x+dx[way]
            if (ny,nx) not in MixerCells:
                for coord in addcoords[way]: 
                    if mdfCoordForPIL(coord) not in line:
                        line.append(mdfCoordForPIL(coord))
        lines.append(line)
        
    
    # ミキサーの左，下，右，上の順番で辺が入っている
    # 各辺上の点をyの小さい順，xの小さい順，yの大きい順，xの大きい順に集めていくことによって，
    # draw.lineでの描画順を一筆書き順になるよう調整する
    OrderModifiedLines = []
    SortByX = [False,True,False,True]
    Reverse = [False,False,True,True]
    for way in range(4):
        if SortByX[way]: 
            mdfline = sorted(lines[way],reverse=Reverse[way],key=lambda coord:coord[0])
            for idx in range(0,len(mdfline)-3):
                first = mdfline[idx]
                second = mdfline[idx+1]
                third = mdfline[idx+2]
                fourth = mdfline[idx+3]
                x1,y1 = first
                x2,y2 = second
                x3,y3 = third
                x4,y4 = fourth
                if x2==x3 and y1!=y2 and y2!=y3 and y3!=y4 :
                    # 2番目と3番目の点を入れ替える 
                    tmp = mdfline[idx+2]
                    mdfline[idx+2] = mdfline[idx+1]
                    mdfline[idx+1] = tmp 
            for coord in mdfline: 
                res.append(coord)
        else: 
            mdfline = sorted(lines[way],reverse=Reverse[way],key=lambda coord:coord[1])
            for idx in range(0,len(mdfline)-3):
                first = mdfline[idx]
                second = mdfline[idx+1]
                third = mdfline[idx+2]
                fourth = mdfline[idx+3]
                x1,y1 = first
                x2,y2 = second
                x3,y3 = third
                x4,y4 = fourth
                if y2==y3 and x1!=x2 and x2!=x3 and x3!=x4 :
                    # 2番目と3番目の点を入れ替える 
                    tmp = mdfline[idx+2]
                    mdfline[idx+2] = mdfline[idx+1]
                    mdfline[idx+1] = tmp 
            for coord in mdfline: 
                res.append(coord)
    return res

def mdfCoordForPIL(coord): 
    y,x = coord 
    return (x,y)

def getMixerGeneralForm(MixerCells):
    LeftTopY,LeftTopX = 10000,10000
    RightBottomY,RightBottomX = 0,0
    for cell in MixerCells: 
        y,x = cell
        RightBottomY = max(y,RightBottomY)
        RightBottomX = max(x,RightBottomX)
        LeftTopY = min(y,LeftTopY)
        LeftTopX = min(x,LeftTopX)
    RightBottomCell = (RightBottomY,RightBottomX)
    LeftTopCell = (LeftTopY,LeftTopX)
    return (LeftTopCell,RightBottomCell)

Grid = []    
draw = None
import random
from pathlib  import Path
def PMDnowSlideImage(filename,ColorList,PMD,ModuleStates):
    global draw,SlideCellWidth ,MixerLineWidth
    MixerColorList,ReagentColorDict = ColorList
    grid,img = genSlideGrid(PMD)
    draw = ImageDraw.Draw(img)
    drop = []
    for i in range(PMD.pmdVsize): 
        for j in range(PMD.pmdHsize): 
            if PMD.State[i][j] == 0: 
                continue 
            elif PMD.State[i][j] <0:
                name = "" 
                color = "" 
                hash = abs(PMD.State[i][j])

                if ModuleStates.ModuleInfo[str(hash)].kind == "Mixer": 
                    idx = int(ModuleStates.ModuleInfo[str(hash)].name[1:])
                    color = MixerColorList[idx]
                else : 
                    key = ModuleStates.ModuleInfo[str(hash)].name 
                    if key[0] == "M":
                        print("バグってる",key,ModuleStates.ModuleInfo[str(hash)].ProvNum,ModuleStates.ModuleInfo[str(hash)].size,ModuleStates.ModuleInfo[str(hash)].kind)
                    color = ReagentColorDict[key]
                    ### 何も書かない
                    name = ""
                grid[i][j].change(color,name)

            elif PMD.State[i][j] > 0 :
                hash = PMD.State[i][j]
                Module = ModuleStates.ModuleInfo[str(hash)]
                cells = Module.CoveringCell
                skip = False
                for y,x in cells: 
                    if PMD.State[y][x] != hash : 
                        skip = True 
                if skip : 
                    continue 
            else: 
                continue 
            for hash in ModuleStates.ModulesStatesAt["WaitingProvidedFluids"]: 
                Module = ModuleStates.ModuleInfo[str(hash)]
                Children = Module.ChildrenHash 
                skip = False
                for y,x in Module.CoveringCell: 
                    if PMD.State[y][x]<0 and abs(PMD.State[y][x]) not in Children: 
                        skip = True
                if skip : 
                    continue
                else: 
                    MixerIdx = int(Module.name[1:])
                    color = MixerColorList[MixerIdx]
                    cells = Module.CoveringCell
                    LeftTop,RightBottom = getMixerGeneralForm(cells)
                    sy,sx  = LeftTop
                    ey,ex = RightBottom

                    fromy,fromx =grid[sy][sx].sy ,grid[sy][sx].sx
                    toy,tox = grid[ey][ex].ey,grid[ey][ex].ex

                    lines = getOutlineOfMixerShape(cells,grid)
                    draw.line(lines,fill=color,width=MixerLineWidth,joint="curve")

            for hash in ModuleStates.ModulesStatesAt["MixerOnPMD"]: 
                Module = ModuleStates.ModuleInfo[str(hash)]
                Children = Module.ChildrenHash 
                skip = False
                for y,x in Module.CoveringCell:
                    if PMD.State[y][x]<0 and abs(PMD.State[y][x]) not in Children: 
                        skip = True
                if skip : 
                    continue
                else: 
                    MixerIdx = int(Module.name[1:]) 
                    color = MixerColorList[MixerIdx] 
                    cells = Module.CoveringCell
                    LeftTopCell,RightBottomCell = getMixerGeneralForm(cells)
                    sy,sx  = LeftTopCell
                    ey,ex = RightBottomCell

                    fromy,fromx =grid[sy][sx].sy ,grid[sy][sx].sx
                    toy,tox = grid[ey][ex].ey,grid[ey][ex].ex
                    w = 10

                    ### 見やすく
                    cx,cy = (tox+fromx)//2,(fromy+toy)//2
                    mdf = 4
                    fontsize = 32
                    div = 2.1
                    
                    draw.rectangle([(cx-SlideCellWidth//div+mdf,cy-SlideCellWidth//div+mdf),(cx+SlideCellWidth//div-mdf,cy+SlideCellWidth//div-mdf)],fill = "White",width=0)

                    lines = getOutlineOfMixerShape(cells,grid)
                    draw.line(lines,fill=color,width=MixerLineWidth,joint="curve")
                    font = ImageFont.truetype("Times New Roman.ttf", fontsize)
                    draw.text(((fromx+tox)//2-12-mdf,(fromy+toy)//2-13-mdf),Module.name[1:],font=font,fill="Black")
                    
                    mix = True
                    for child in Children: 
                        if ModuleStates.ModuleInfo[str(child)].state != "OnlyProvDrop": 
                            mix = False 
                        if mix : 
                            cx,cy = (tox+fromx)//2,(fromy+toy)//2
                            draw.arc([(cx-SlideCellWidth//2,cy-SlideCellWidth//2),(cx+SlideCellWidth//2,cy+SlideCellWidth//2)],30,0,fill="Black",width=3)
                            tri_x,tri_y= cx+SlideCellWidth//2,(fromy+toy)//2
                            draw.regular_polygon((tri_x,tri_y,(9)),3,rotation=75,fill="Black")

    create_directory("image")
    path = Path("image/",filename+".png")
    img.save(path)

# 混合手順が全て求め終わってから，混合プロセスをタイムステップ毎に図にする
def ResultSlideImage(filename,ColorList,TimeStep,FlushCount,PMDsimulation,PMDGeneralInfo,Mixer,ModuleStates):
    global SlideCellWidth,draw,blank,MixerLineWidth
    MixerColorList,ReagentColorDict = ColorList
    SlideCellWidth = 40
    grid,img = genSlideGrid(PMDGeneralInfo)
    draw = ImageDraw.Draw(img)
    drop = []
    for i in range(PMDGeneralInfo.pmdVsize): 
        for j in range(PMDGeneralInfo.pmdHsize): 
            if PMDsimulation[i][j] == 0: 
                continue 
            elif PMDsimulation[i][j] <0:
                name = "" 
                color = "" 
                hash = abs(PMDsimulation[i][j])
                if ModuleStates.ModuleInfo[str(hash)].kind == "Mixer": 
                    idx = int(ModuleStates.ModuleInfo[str(hash)].name[1:])
                    color = MixerColorList[idx]
                else : 
                    key = ModuleStates.ModuleInfo[str(hash)].name
                    color = ReagentColorDict[key]
                    ### 何も書かない
                    name = ""
                grid[i][j].change(color,name)

    for hash in Mixer:
        Module = ModuleStates.ModuleInfo[str(hash)]
        Children = Module.ChildrenHash 
        MixerIdx = int(Module.name[1:])
        color = MixerColorList[MixerIdx]
        cells = Module.CoveringCell
        LeftTop,RightBottom = getMixerGeneralForm(cells)
        sy,sx  = LeftTop
        ey,ex = RightBottom
        
        fromy,fromx =grid[sy][sx].sy ,grid[sy][sx].sx
        toy,tox = grid[ey][ex].ey,grid[ey][ex].ex
        ### 見やすく
        fontsize = 32
        mdf = 4
        div = 2.1
        cx,cy = (tox+fromx)//2,(fromy+toy)//2
        draw.rectangle([(cx-SlideCellWidth//div+mdf,cy-SlideCellWidth//div+mdf),(cx+SlideCellWidth//div-mdf,cy+SlideCellWidth//div-mdf)],fill = "White",width=0)

        lines = getOutlineOfMixerShape(cells,grid)
        draw.line(lines,fill=color,width=MixerLineWidth,joint="curve")
        font = ImageFont.truetype("Times New Roman.ttf", fontsize)
       
        tri_x,tri_y= cx+SlideCellWidth//2,(fromy+toy)//2
        draw.regular_polygon((tri_x,tri_y,(9)),3,rotation=75,fill="Black")
        draw.arc([(cx-SlideCellWidth//2,cy-SlideCellWidth//2),(cx+SlideCellWidth//2,cy+SlideCellWidth//2)],30,0,fill="Black",width=3)
        draw.text(((fromx+tox)//2-12-mdf,(fromy+toy)//2-13-mdf),Module.name[1:],font=font,fill="Black")
        

    S = "T={},F={}".format(TimeStep,FlushCount)
    fontsize = 40
    font = ImageFont.truetype("Times New Roman.ttf", fontsize)
    draw.text((0,PMDGeneralInfo.pmdHsize*SlideCellWidth+blank),S,font=font,fill="Black")
    create_directory("image")
    path = Path("image/","result"+filename+".png")
    img.save(path)

