from .tree import * 
import json
from pathlib import Path
import copy
from transitions import Machine

# それぞれのモジュールは個別の状態機械として管理する
# それぞれの状態からの取りうる状態遷移を記述(詳しくは，手書きで作った状態遷移図を参照)．
STATES =['NoTreatment','ProvidingFluids','MixerOnPMD','WaitingProvidedFluids','PlacementSkipped','Done']
TRANSITIONS = [
        # トリガーとなる関数名，元の状態，遷移先の状態
        ['MixerOnPMD',['NoTreatment','WaitingProvidedFluids','PlacementSkipped'],'MixerOnPMD'],
        ['ProvidingFluids',['NoTreatment','PlacementSkipped','MixerOnPMD'],'ProvidingFluids'],
        ['WaitingProvidedFluids','MixerOnPMD','WaitingProvidedFluids'],
        ['PlacementSkipped',['NoTreatment','PlacementSkipped'],'PlacementSkipped'],
        ['Done','ProvidingFluids','Done'],
        ['_RollBack','*','NoTreatment']
]

# Mixerと試薬液滴両方で利用する．
class Module: 
    def __init__(self,node,ParentHash): 
        global RootHash,ModuleStates,STATES,TRANSITIONS
        self.name = node.name 
        self.hash = node.hash 
        self.ParentHash = ParentHash 

        self.AncestorHash = [RootHash]
        ptr = ParentHash
        while(ptr>0 and ptr!=RootHash ):
            self.AncestorHash.append(ptr)
            ptr = ModuleStates.getModule(ptr).ParentHash

        self.ChildrenHash = []
        for c in node.children:
            self.ChildrenHash.append(c.hash)
        self.size = node.size
        self.ProvNum = node.provide_vol
        #本来のプログラム 
        self.kind = "Reagent" if self.ProvNum == self.size else "Mixer" ;
        #追記:おそらくバグが発生したので泣く泣く書き換えたのだと思う．
        # self.kind = "Mixer"  if self.name[0]=="M" else "Reagent"
        self.machine = Machine(model=self,states=STATES,transitions=TRANSITIONS,initial='NoTreatment',\
                before_state_change='delete_state',after_state_change='add_state') 

        ### 配置先が決定してから決まる情報
        #self.RefCell = None
        #self.BaseMixerShape = []
        self.ProvCell = []
        self.FlushCell = []
        self.CoveringCell = []
        self.MixedTimeStep = -1 
        # 試薬のための変数
        self.PlacedTimeStep = -1
    
    def delete_state(self):
        global ModuleStates 
        ModuleStates.ModulesStatesAt[self.state].remove(self.hash)
    def add_state(self):
        global ModuleStates 
        ModuleStates.ModulesStatesAt[self.state].append(self.hash)

    def IsMixer(self):
        if self.kind == "Mixer":
            return True 
        else: 
            return False
    
    def EstimateCelluseNum(self):
        global ModuleStates
        q = []
        q.append(self)
        num = 0
        while(q): 
            module = q.pop(0)
            if module.IsMixer():
                for ChildHash in module.ChildrenHash:
                    child = ModuleStates.getModule(ChildHash)
                    if child.IsMixer():
                        q.append(child)
                    else: 
                        num+=child.size
            else : 
                num += module.size
        return num 

    # Hashに紐づけられたモジュールのECNの大きい順に並び替えて，ChildrenHashを返す.
    def ChildrenHashSortedByECN(self):
        global ModuleStates 
        INF = 1000000
        l = []
        for ChildHash in self.ChildrenHash:
            child = ModuleStates.getModule(ChildHash)
            ecn = 0 
            if child.IsMixer():
                # 親と子ミキササイズによるが，あとで書く
                if child.ProvNum > 2 and child.ProvNum % 2:
                    ecn += INF 
                else : 
                    ecn = child.EstimateCelluseNum()
            else: 
                # 試薬液滴は配置方法に融通が効きやすいから，後の方に配置場所を決めたい．
                ecn = child.EstimateCelluseNum()/1000
            s = (ecn,ChildHash)
            l.append(s)
        l.sort(reverse=True)
        res = [] 
        for ecn,ChildHash in l:
            res.append(ChildHash) 
        return res

# 各モジュールの状態を管理するための構造体
class ModuleStateManage:
    def __init__(self):
        global STATES
        # Hashでミキサー情報に直接アクセスできる(スケーリングで更新が必要)
        self.ModuleInfo = {}
        # モジュールの状態で，モジュールをグループ分けしている
        self.ModulesStatesAt = {}
        for state in STATES: 
            self.ModulesStatesAt[state] = []
        # key:親ミキサーのhash,value:選択した子のレイアウト．
        # 配置を再開する際は，モジュールの状態を見てどのモジュールを配置するか決める
        self.PlacementSkippedLayout = []
        self.UsedLayout = {}
    
    def getModule(self,hash):
        return self.ModuleInfo[str(hash)]

    def showModuleNames(self):
        for module in self.ModuleInfo.values():
            if module.IsMixer():
                print("hash:{},name:{}".format(module.hash,module.name))
            else : 
                print("hash:{},name:{},parent:{}".format(module.hash,module.name,self.getModule(module.ParentHash).name))
     
        
# PMDの状態を管理するための構造体
class PMDStateManage:
    def __init__(self,PMDsize):
        self.pmdVsize,self.pmdHsize = PMDsize
        self.State = [[0 for j in range(self.pmdHsize)] for i in range(self.pmdVsize)]
        self.CellForFlushing = []
        self.CellForProtectFromFlushing = []
        self.RegisteredAsProvCell = [[[] for j in range(self.pmdHsize)] for i in range(self.pmdVsize)]
        self.RegisteredAsPlacementCell = [[[] for j in range(self.pmdHsize)] for i in range(self.pmdVsize)]
        # 混合手順の紙芝居を作るために必要な変数TimeStep
        # 混合を行うタイミングを1単位として見ると，ミキサの展開，試薬の配置とWaitingからの復帰try→(混合&フラッシングの後に，試薬の配置とWaitingからの復帰try)→(混合&フラッシングの後に，試薬の配置とWaitingからの復帰try)→...→混合(最後だけ例外)
        # ミキサの展開を例外的にT=0とし，それ以降のタイムステップは混合から始まる
        # タイムステップのインクリメントのタイミングは，混合の始め
        self.TimeStep = 0
        # PlacementTimeStepは，試薬の場合はPMD上への配置タイミング，ミキサの場合はWaitingからの復帰タイミングを示してる

    # モジュールを指定した配置場所でPMDに配置できるかどうか確認する
    def IsPlacableNow(self,placement): 
        for cell in placement.CoveringCell: 
            y,x = cell
            if not (self.State[y][x] == placement.ParentHash or self.State[y][x] == 0): 
                return False 
        return True 

    def Flushing(self): 
        for cell in self.CellForFlushing: 
            y,x = cell
            self.State[y][x] = 0 
        self.CellForFlushing = []

def IsInsidePMD(Y,X): 
    global PMD
    if 0 <= Y and Y < PMD.pmdVsize and  0 <= X and X < PMD.pmdHsize : 
        return True 
    else : 
        return False

def getMixerShapeLib(MixerSize):
    dir = "./Scaling/MixerShapeLib/"
    filename = str(MixerSize)+"mixer.json"
    LibPath = Path(dir,filename)
    readfile = open(LibPath,'r')
    Lib = json.load(readfile)
    return Lib

def TransformMixerShapelibJsonIntoList(mixershape):
    l = []
    for cell in mixershape:
        y,x = cell["y"],cell["x"]
        l.append((y,x))
    return l

# ミキサーをすっぽり覆うような長方形の右下セルから，ミキサーの概形の大きさを知る．
def getMixerOutlineSize(mixershape):
    RightBottomY,RightBottomX = 0,0
    for cell in mixershape: 
        y,x = cell 
        RightBottomY = max(y,RightBottomY)
        RightBottomX = max(x,RightBottomX)
    return (RightBottomY+1,RightBottomX+1)

# ミキサーの形状をdV,dH分並行移動させて，配置されるセルを求める．
def Translation(mixershape,dVdH):
    l = []
    dV,dH = dVdH 
    for cell in mixershape: 
        y,x = cell 
        ny,nx = y+dV,x+dH 
        l.append((ny,nx))
    return l

# 二つのミキサーが共有しているセル数を数え上げる．
def getInterSectionCells(PShape,CShape):
    cells = []
    for cell in CShape: 
        if cell in PShape: 
            cells.append(cell)
    return cells 

def getCornerCells(cells):
    dy,dx = [1,-1],[-1,1] 
    corner = []
    for cell in cells: 
        NextNum = 0
        y,x = cell 
        dxVacant,dyVacant = False,False
        for way in range(2): 
            if (y+dy[way],x) not in cells: 
                dyVacant = True
            if (y,x+dx[way]) not in cells: 
                dxVacant = True 
        # 縦横いずれの方向にも隣接した空きセルがある場合，cellsの内では隅のセルである．
        if dyVacant and dxVacant:
            corner.append(cell)
    return corner

def swap(x,y): 
    return (y,x)

# 二つのミキサーが共有しているセルから，ProvNum個分の提供液滴を渡すセルの候補を探索する．
def getProvCellsAlt(InterSectionCells,ProvNum):
    CornerCells = getCornerCells(InterSectionCells) 
    if ProvNum == 0 or len(InterSectionCells)==0:
        print("やってられませんわ")
    elif len(InterSectionCells) == ProvNum: 
        return [InterSectionCells]
    else: 
        # 左右，上下どの角かを判別する．
        # 左上の角なら，右下 or 下右に移動できる．
        dy,dx = [0,1,0,-1],[-1,0,1,0] 
        AvailableWay = []
        for cell in CornerCells: 
            available = []
            y,x = cell 
            for way in range(4): 
                ny,nx = y+dy[way],x+dx[way]
                if (ny,nx) in InterSectionCells: 
                    available.append(way)
            res = (cell,available)
            AvailableWay.append(res)
        res = []
        for cell,ways in AvailableWay: 
            for swapUsual in range(2): 
                sign = 1
                Usual,EncounteringWall = None,None 
                if len(ways)==2:
                    Usual,EncounteringWall = ways
                    if swapUsual: 
                        Usual,EncounteringWall = swap(Usual,EncounteringWall)
                elif len(ways)==1: 
                    Usual = ways.pop()
                else: 
                    continue
                
                ProvCells = [cell]
                y,x = ProvCells[0]
                WatchingCell = cell
                while(len(ProvCells)!=ProvNum):
                    y,x = WatchingCell 
                    ny,nx = y+sign*dy[Usual],x+sign*dx[Usual]
                    ncell = (ny,nx)
                    if ncell not in ProvCells: 
                        if ncell in InterSectionCells: 
                            ProvCells.append(ncell)
                            WatchingCell = ncell 
                        else: 
                            # 壁にぶつかってみてから，対処として使える道が見つかる場合もある
                            if EncounteringWall == None: 
                                SearchDY,SearchDX = False,False
                                if abs(dy[Usual]): 
                                    SearchDX = True 
                                else: 
                                    SearchDY = True
                                for way in range(4): 
                                    # 縦方向の移動を通常しているなら，横方向の移動を壁にぶつかったら行う
                                    if SearchDX : 
                                        if abs(dx[way]): 
                                            Alty,Altx = y+dy[way],x+dx[way]
                                            if (Alty,Altx) in InterSectionCells: 
                                                EncounteringWall = way
                                    else: 
                                        if abs(dy[way]): 
                                            Alty,Altx = y+dy[way],x+dx[way]
                                            if (Alty,Altx) in InterSectionCells: 
                                                EncounteringWall = way
                            # 一旦探しても曲がる方向が見つからないなら現在の探索法ではもう無理
                            if EncounteringWall==None:  
                                break 
                            else:
                                # 曲がる
                                ny,nx = y+dy[EncounteringWall],x+dx[EncounteringWall]
                                # 蛇のようにくねくねセルを集めるので，
                                # 壁に当たったら進行方向を逆にするために符号の切り替え
                                sign *= -1
                                ncell = (ny,nx)
                                if ncell not in ProvCells: 
                                    if ncell in InterSectionCells:
                                        ProvCells.append(ncell)
                                        WatchingCell = ncell 
                    else : 
                        # 同じセルを2回参照する場合，今回は無理
                        break
                ProvCells.sort()
                if len(ProvCells)==ProvNum and ProvCells not in res:
                    res.append(ProvCells) 
        return res

class EdgeManagement: 
    def __init__(self): 
        # ミキサーの配置セルに，他のミキサーの提供液滴配置セルがある場合，そのミキサーよりも先に混合する必要がある．
        # 混合順を表すために，そのエッジへとOutEdgeを張る．
        self.InEdge = []
        self.OutEdge = []

class Placement: 
    def __init__(self,Hash,ParentHash,CoveringCell,ProvCell,FlushCell): 
        self.hash = Hash
        self.ParentHash = ParentHash
        self.CoveringCell = CoveringCell
        self.ProvCell = ProvCell 
        self.FlushCell = FlushCell 
    
    def show(self): 
        # 必要ならあとで書く
        print("Hash:",self.hash)
        print("CoveringCell:",end="")
        printCells(self.CoveringCell)
        print("ProvCell:",end="")
        printCells(self.ProvCell)

def printCells(cells):
    print("(x,y)=",end="")
    mdfcells = []
    for cell in cells : 
        y,x = cell
        mdfcells.append((x,y))
    for cell in sorted(mdfcells):
        x,y = cell
        print(" ({},{}),".format(x,y),end="")
    print("\n")

class Layout: 
    def __init__(self,PMD,PMixerCells,CorrectMixingOrder): 
        self.Placements = {}
        self.PMD = copy.deepcopy(PMD)
        self.RestProvCell = copy.deepcopy(PMixerCells)
        self.CorrectMixingOrder = copy.deepcopy(CorrectMixingOrder)
        self.layer = None
    
    # オーバーラップの状況から兄弟ミキサーの混合順を求める
    def IsMixableInECNOrder(self):
        Layer = self.getLayer()
        if Layer: 
            return True 
        else : 
            return False

    # オーバーラップの状況から兄弟ミキサーの混合順を求める
    def getLayer(self):
        if self.layer == None:
            Graph = {}
            LayerManage = {}
            for hash in self.CorrectMixingOrder: 
                Graph[str(hash)] = EdgeManagement()
                LayerManage[str(hash)] = -1
            for hash in self.CorrectMixingOrder: 
                placement = self.Placements[str(hash)]
                for cell in placement.CoveringCell: 
                    y,x = cell 
                    for OverlappingHash in self.PMD.RegisteredAsProvCell[y][x]: 
                        if hash != OverlappingHash and OverlappingHash in self.CorrectMixingOrder:   
                            Graph[str(hash)].OutEdge.append(OverlappingHash)
                            Graph[str(OverlappingHash)].InEdge.append(hash)
            for hash in self.CorrectMixingOrder: 
                WhichLayer = 0
                for brotherHash in Graph[str(hash)].InEdge:
                    if brotherHash in Graph[str(hash)].OutEdge:
                        # 両方にエッジが張られていて，ループが発生している
                        # →デッドロックが発生している
                        return {}
                    elif LayerManage[str(brotherHash)] == -1:
                        # このレイアウトを採用した場合，混合順が入れ替わることになる
                        return {}
                    else : 
                        WhichLayer = max(WhichLayer,LayerManage[str(brotherHash)]+1)
                LayerManage[str(hash)] = WhichLayer 
            self.layer = LayerManage
        return self.layer
        
    def getMaxLayer(self,layer): 
        MaxLayer = -1
        for v in layer.values(): 
            MaxLayer = max(v,MaxLayer) 
        return MaxLayer

    def getPlacingLayer(self): 
        global ModuleStates 
        MinLayer = 100000
        for hash in self.CorrectMixingOrder: 
            if ModuleStates.getModule(hash).state == "PlacementSkipped":
                MinLayer = min(MinLayer,self.layer[str(hash)])
        return MinLayer
    
    # 遅すぎる泣
    def eval(self):
        global ModuleStates
        score = 0
        layer = self.getLayer()
        NeedFlushNum = self.getMaxLayer(layer)
        # 現在置かれている，兄弟以外のミキサーとのオーバーラップをチェック 
        # オーバーラップをしている場合，その対象ミキサーの
        # 先祖ミキサー&自身の先祖ミキサーの子ミキサーであるミキサーの提供液滴配置セルとオーバーラップがあれば配置不可．
        for hash in self.CorrectMixingOrder: 
            if ModuleStates.getModule(hash).IsMixer():
                placement = self.Placements[str(hash)]
                tmpPMD = copy.deepcopy(self.PMD)
                # 仮置き
                tmpPMD = self.TemporalyPlaceMixer(tmpPMD,placement)
                GrandchildLayoutAlt = getChildrenLayoutAlt(tmpPMD,placement.CoveringCell,hash)
                score += len(GrandchildLayoutAlt)/(NeedFlushNum+1) 
        return score 

    def NewEval(self):
        global ModuleStates
        layer = self.getLayer()
        NeedFlushNum = self.getMaxLayer(layer)
        return 1/(NeedFlushNum+1)

    def show(self): 
        for hash in self.CorrectMixingOrder:
            self.Placements[str(hash)].show() 
        print("残った提供セルは",self.RestProvCell)
        print("正しい混合順は",self.CorrectMixingOrder)

    def IFNum(self):
        global ModuleStates,PMD
        Layer = self.getLayer()
        maxLayer = 0
        if Layer: 
            for hash in self.CorrectMixingOrder: 
                maxLayer = max(Layer[str(hash)],maxLayer)
            return maxLayer 
        else : 
            return -1
    
    def TemporalyPlaceMixer(self,PMD,placement):
        global ModuleStates
        for cell in placement.ProvCell: 
            y,x = cell
            PMD.RegisteredAsProvCell[y][x].append(placement.hash)
        for cell in placement.CoveringCell: 
            y,x = cell 
            PMD.RegisteredAsPlacementCell[y][x].append(placement.hash) 
            PMD.State[y][x] = placement.hash
        return PMD

def getMyAncestor(ParentHash,MyAncestorHashes): 
    global ModuleStates 
    for chash in ModuleStates.getModule(ParentHash).ChildrenHash: 
        if chash in MyAncestorHashes:
            return chash

def PlaceModule(placement):
    global ModuleStates
    if ModuleStates.getModule(placement.hash).IsMixer():
        PlaceMixer(placement.hash,placement.CoveringCell,placement.ProvCell)
    else : 
        PlaceReagent(placement.hash,placement.CoveringCell,placement.ProvCell)

# 親ミキサーの配置場所を仮決めして引数に与えた場合，
# その子のモジュールはどのようなレイアウトを取ることができるか探索する．
# 孫ミキサー（子ミキサーの子）のレイアウト個数を数え上げさせる場合があるので，
# この関数がPMDの状態はglobalのPMDとは異なる場合もある
def getChildrenLayoutAlt(PMD,PMixerCellsAlt,PMixerHash):
    global ModuleStates,MixerShapeKind

    PMixer = ModuleStates.getModule(PMixerHash)
    # ECNのおかげで，ミキサー→試薬の順番で配置場所を探索できる．
    # 試薬は，余ってる提供セルを適当に割り当てる. 
    GeneratingLayouts = [[] for i in range(len(PMixer.ChildrenHash)+1)]
    LayoutSeed = Layout(PMD,PMixerCellsAlt,PMixer.ChildrenHashSortedByECN())
    GeneratingLayouts[0].append(LayoutSeed)
    for Childidx,chash in enumerate(PMixer.ChildrenHashSortedByECN()):
        child = ModuleStates.getModule(chash)
        for layout in GeneratingLayouts[Childidx]:
            # 配置する子がミキサーの場合
            if child.IsMixer():
                MixerShapeLib = getMixerShapeLib(child.size)
                for mixerkind in MixerShapeKind:
                    if MixerShapeLib[mixerkind]:
                        for Shapeidx in range(len(MixerShapeLib[mixerkind])):
                            # 適当にミキサーの概形の左上の参照セル(ref_y,ref_x)を選ぶ
                            for ref_y in range(PMD.pmdVsize): 
                                for ref_x in range(PMD.pmdHsize): 
                                    ref_cell = (ref_y,ref_x)
                                    # ref_cellを基準とした位置に，子ミキサーのライブラリを平行移動
                                    CMixerCellsAlt = Translation(TransformMixerShapelibJsonIntoList(MixerShapeLib[mixerkind][str(Shapeidx)]),ref_cell)
                                    # 子のミキサーの配置セル候補がPMDからはみ出していたら候補から弾く
                                    NotInsidePMD = False 
                                    for cell in CMixerCellsAlt: 
                                        y,x = cell 
                                        if not IsInsidePMD(y,x): 
                                            NotInsidePMD = True 
                                    if NotInsidePMD:
                                        continue
                                    # 子ミキサーの配置セル候補と，親ミキサーが共有しているセルを求める.
                                    # これらが提供液滴配置セルの候補となる
                                    InterSectionCells = getInterSectionCells(PMixerCellsAlt,CMixerCellsAlt)
                                    # 適当な参照セルで子ミキサーを置いた時，親ミキサと重なるセル数が提供液滴数よりも多い場合処理を続行
                                    if len(InterSectionCells)>=child.ProvNum:
                                        ProvCellsAlt = getProvCellsAlt(InterSectionCells,child.ProvNum)
                                        for provcells in ProvCellsAlt:
                                            # 適当に提供液滴の配置パターンを書き出してみただけやから，
                                            # それが使えるのか逐一チェックする必要あり.Passが真のままなら合格
                                            # 枝切りの役割も兼ねる
                                            Pass = True
                                            LayoutProcess= copy.deepcopy(layout)
                                            for cell in provcells: 
                                                y,x = cell
                                                # 提供液滴の配置セルが他の兄弟ミキサーにもう取られているかのチェック
                                                if cell not in LayoutProcess.RestProvCell:
                                                    Pass = False 
                                            # 本格的なチェックを行い，有効なレイアウトか確認する.チェック項目は以下の通り．
                                                # デッドロックが発生していないか
                                                ## まずは，配置セルに提供液滴を配置する他のミキサーの内，先祖ミキサーでないもの(A)を調査
                                            suspicion = []
                                            for cell in CMixerCellsAlt: 
                                                y,x = cell
                                                for mhash in LayoutProcess.PMD.RegisteredAsProvCell[y][x]: 
                                                    if mhash not in child.AncestorHash: 
                                                        suspicion.append(mhash) 
                                            ## 逆に，提供液滴を配置するセルに配置される他のミキサーで，先祖ミキサーでないもの(B)を調査
                                            for cell in provcells: 
                                                y,x = cell 
                                                for mhash in LayoutProcess.PMD.RegisteredAsPlacementCell[y][x]: 
                                                    if (mhash in suspicion) and (ModuleStates.getModule(mhash).state != "PlacementSkipped" ): 
                                                        # AかつBの関係になる様なミキサーの内，
                                                        # 相手が配置されている(ECNのより大きい部分木に属する)ミキサーならデッドロックが発生
                                                        Pass = False
                                            # 先祖の子だが，自身の先祖には含まれないモジュールの内，
                                            # 自身の先祖よりECNの大きいモジュールに対しては，提供液滴の配置予定セルでもオーバーラップしていたらダメ
                                            # 自身の先祖よりECNの小さいモジュールに対しては，もう配置されている提供液滴にオーバーラップしていたらダメ
                                            for cell in CMixerCellsAlt: 
                                                y,x = cell 
                                                for mhash in LayoutProcess.PMD.RegisteredAsProvCell[y][x]: 
                                                    if mhash not in child.AncestorHash and ModuleStates.getModule(mhash).ParentHash in child.AncestorHash and ModuleStates.getModule(mhash).ParentHash != child.ParentHash:
                                                        MyAncestorAndHisBrotherHash = getMyAncestor(ModuleStates.getModule(mhash).ParentHash,child.AncestorHash)
                                                        TheirParent = ModuleStates.getModule(ModuleStates.getModule(mhash).ParentHash)
                                                        CmpPosition = TheirParent.ChildrenHash.index(mhash)
                                                        MyAncestorPosition = TheirParent.ChildrenHash.index(MyAncestorAndHisBrotherHash)
                                                        if CmpPosition < MyAncestorPosition: 
                                                            Pass = False  
                                                        else : 
                                                            if ModuleStates.getModule(mhash).state != "PlacementSkipped" : 
                                                                Pass = False
                                                             
                                            ## 兄弟ミキサーとのオーバーラップが発生している場合，混合順はECN順になるか?
                                            suspicion = []
                                            for cell in CMixerCellsAlt: 
                                                y,x = cell 
                                                # 配置セル内に，兄弟ミキサー(自分よりECNが大きい)の提供セルがある場合，
                                                # 自分の方がミキサーを先に混合する必要が出る．それはECNの概念に矛盾するので不合格．
                                                for mhash in LayoutProcess.PMD.RegisteredAsProvCell[y][x]: 
                                                    if mhash in PMixer.ChildrenHash:
                                                        Pass = False 
                                            # ここまできたら合格なので，次の子モジュールの配置方法の探索に渡す
                                            if Pass:
                                                for cell in provcells: 
                                                    y,x = cell
                                                    LayoutProcess.PMD.RegisteredAsProvCell[y][x].append(chash)
                                                    LayoutProcess.RestProvCell.remove((y,x))
                                                # Placementのインスタンス生成のために必要やから作ってる
                                                #print("provcells:{},RestProvCell:{}".format(provcells,LayoutProcess.RestProvCell))
                                                flushcells = []
                                                for mixercell in CMixerCellsAlt: 
                                                    y,x = mixercell
                                                    LayoutProcess.PMD.RegisteredAsPlacementCell[y][x].append(chash)
                                                    if mixercell not in provcells: 
                                                        flushcells.append(mixercell) 
                                                placement = Placement(chash,PMixerHash,CMixerCellsAlt,provcells,flushcells)
                                                LayoutProcess.Placements[str(chash)] = placement
                                                # 次の子の配置に回す．
                                                GeneratingLayouts[Childidx+1].append(LayoutProcess)
            else:
                # 試薬の配置場所は余った提供セルから適当に選ぶ
                LayoutProcess = copy.deepcopy(layout)
                CoveringCells = []
                ProvCells = []
                FlushCells = []
                for cnt in range(child.ProvNum):
                    y,x = LayoutProcess.RestProvCell.pop(0)
                    LayoutProcess.PMD.RegisteredAsProvCell[y][x].append(chash)
                    LayoutProcess.PMD.RegisteredAsPlacementCell[y][x].append(chash)
                    CoveringCells.append((y,x))
                    ProvCells.append((y,x))
                placement = Placement(chash,PMixerHash,CoveringCells,ProvCells,FlushCells)
                LayoutProcess.Placements[str(chash)] = placement
                GeneratingLayouts[Childidx+1].append(LayoutProcess)

    return GeneratingLayouts[len(PMixer.ChildrenHash)]


MixerShapeKind = ["Rectangle","LShaped"]
def PlaceRootMixer():
    global PMD,ScalingUsable,MixerShapeKindBestMixerShape,ModuleStates,RootHash
    # ルートミキサーの配置場所を決める必要がある．
    # スケーリングなし&IFありの状況にも対応する必要がある．(あとで書く)
    MaxAltnum = 0
    BestMixerShape = None
    MixerShapeLib = getMixerShapeLib(ModuleStates.getModule(RootHash).size)
    for mixerkind in MixerShapeKind:
        if MixerShapeLib[mixerkind]==None:
            continue
        else:
            for idx in range(len(MixerShapeLib[mixerkind])):
                stridx = str(idx)
                mixershape = TransformMixerShapelibJsonIntoList(MixerShapeLib[mixerkind][stridx])
                ### ミキサーをすっぽり収めるような長方形のサイズを求め，極力PMDの中心になるよう配置位置を決める.
                OutlineV,OutlineH = getMixerOutlineSize(mixershape)
                if OutlineV>PMD.pmdVsize or OutlineH>PMD.pmdHsize:
                    continue
                ref_y,ref_x = (PMD.pmdVsize-OutlineV)//2,(PMD.pmdHsize-OutlineH)//2
                # ミキサーの基準セル（概形の左上セル）を(ref_y,ref_x)とした場合でミキサーがPMD上に収まる場合，
                # ミキサーの形状の候補として処理を進める．
                if IsInsidePMD(ref_y,ref_x) and IsInsidePMD(ref_y+OutlineV-1,ref_x+OutlineH-1):
                    # mixershapeを(ref_y,ref_x)分平行移動させる．
                    dVdH = (ref_y,ref_x)
                    RootMixerCells = Translation(mixershape,dVdH)
                    LayoutAlternatives = getChildrenLayoutAlt(PMD,RootMixerCells,RootHash)
                    if len(LayoutAlternatives)>MaxAltnum:
                        MaxAltnum = len(LayoutAlternatives)
                        BestMixerShape = RootMixerCells 
                else: 
                    continue 
    if BestMixerShape == None or MaxAltnum==0: 
        print("M0，もしくはその子のレイアウト方法が見つかりませんでした．",file=sys.stderr)
    else : 
        # ルートミキサーの提供液滴を無しとした理由は，Goodnotesを参照
        PlaceMixer(RootHash,BestMixerShape,[])

# PMDやミキサの状態の書き換えのための関数
def PlaceMixer(MixerHash,PlacedCells,ProvCell):
    global PMD,ModuleStates,StateTransitions
    for cell in ProvCell: 
        y,x = cell
        PMD.RegisteredAsProvCell[y][x].append(MixerHash)
    for cell in PlacedCells: 
        y,x = cell 
        PMD.RegisteredAsPlacementCell[y][x].append(MixerHash) 
        PMD.State[y][x] = MixerHash
    ModuleStates.ModuleInfo[str(MixerHash)].CoveringCell = PlacedCells
    ModuleStates.ModuleInfo[str(MixerHash)].ProvCell = ProvCell 
    for cell in PlacedCells: 
        if cell not in ProvCell:
            ModuleStates.ModuleInfo[str(MixerHash)].FlushCell.append(cell)
    # 状態遷移
    StateTransitions.append(ModuleStates.ModuleInfo[str(MixerHash)].MixerOnPMD)

def PlaceReagent(Hash,PlacedCells,ProvCell):
    global PMD,ModuleStates,StateTransitions
    for cell in ProvCell: 
        y,x = cell
        PMD.RegisteredAsProvCell[y][x].append(Hash)
        PMD.CellForProtectFromFlushing.append(cell)
    for cell in PlacedCells: 
        y,x = cell 
        PMD.RegisteredAsPlacementCell[y][x].append(Hash) 
        # 中間液滴や試薬液滴の置かれているセルは，負の値を書き込む
        PMD.State[y][x] = -1*Hash
    ModuleStates.ModuleInfo[str(Hash)].CoveringCell = PlacedCells
    ModuleStates.ModuleInfo[str(Hash)].ProvCell = ProvCell 
    ModuleStates.ModuleInfo[str(Hash)].PlacedTimeStep = PMD.TimeStep
    # 状態遷移
    StateTransitions.append(ModuleStates.ModuleInfo[str(Hash)].ProvidingFluids)

def PlaceChildren(ParentMixerHash): 
    global PMD,ModuleStates,StateTransitions
    PMixer = ModuleStates.getModule(ParentMixerHash)
    ChildrenLayoutAlt = getChildrenLayoutAlt(PMD,PMixer.CoveringCell,PMixer.hash)
    
    Layout= []
    IsNoFlusing = False
    for LayoutAlt in ChildrenLayoutAlt: 
        # レイアウトの評価式，あとで書く
        if LayoutAlt.IsMixableInECNOrder():
            # 遅すぎて使い物にならない泣
            #EvalV = LayoutAlt.eval()
            EvalV = LayoutAlt.NewEval()
            # print("よくやった！！",EvalV)
            Layout.append((EvalV,LayoutAlt))

    # 厳しめにECN順での配置を守る 
    # 同じステージでよりECNの大きいモジュールが配置できない場合，それ以降は全て配置スキップ
    # →　めちゃ混合の並列性が低くなるのでやめた方が良い
    IsPlacementSkipped = False
    # あとで2番目以降で評価値が高いレイアウトの選択も可能にして良いかも
    evalv,layout = sorted(Layout,reverse=True,key=lambda x:x[0]).pop(0)
    ModuleStates.UsedLayout[str(ParentMixerHash)] = layout
    for hash in layout.CorrectMixingOrder:
        placement = layout.Placements[str(hash)]
        # 現在のPMDに，該当モジュールを配置することができるか(配置セルが空いているか)チェック
        if layout.layer[str(hash)]==0 and PMD.IsPlacableNow(placement):
            PlaceModule(placement)
        else : 
            IsPlacementSkipped = True 
            # 配置できないから，配置を延期
            StateTransitions.append(ModuleStates.ModuleInfo[str(hash)].PlacementSkipped)
    if IsPlacementSkipped:
        ModuleStates.PlacementSkippedLayout.append(layout) 
    # 子を置いたら，親ミキサーは子からの提供液滴を待つ状態に遷移する. 
    StateTransitions.append(ModuleStates.ModuleInfo[str(ParentMixerHash)].WaitingProvidedFluids)

def Mix(MixerHash):
    global ModuleStates,PMD,StateTransitions
    mixer = ModuleStates.getModule(MixerHash)
    print(mixer.name,"を混合します")
    # 親ミキサーに提供液滴を渡していた子ミキサー達は役割を終える．
    for chash in mixer.ChildrenHash: 
        ModuleStates.ModuleInfo[str(chash)].Done()
        cmixer = ModuleStates.ModuleInfo[str(chash)]
        for cell in ModuleStates.getModule(chash).CoveringCell: 
            y,x = cell
            PMD.RegisteredAsPlacementCell[y][x].remove(chash)
        for cell in ModuleStates.getModule(chash).ProvCell:
            y,x = cell
            PMD.RegisteredAsProvCell[y][x].remove(chash)
            PMD.CellForProtectFromFlushing.remove(cell)
    # 親ミキサーを混合し，液滴を提供できる状態に状態遷移．
    for cell in mixer.CoveringCell: 
        y,x = cell
        PMD.State[y][x] = -1*MixerHash 
        if cell in mixer.ProvCell:
            PMD.CellForProtectFromFlushing.append(cell)
        else: 
            PMD.CellForFlushing.append(cell)
    ModuleStates.ModuleInfo[str(MixerHash)].MixedTimeStep = PMD.TimeStep
    StateTransitions.append(ModuleStates.ModuleInfo[str(MixerHash)].ProvidingFluids)

def globalInit(PMDsize,root,IsScalingUsable):
    global PMD,ModuleStates,ScalingUsable,StateTransitions#,CntRollBack,RollBackHash,PrevRollBackPMHash 
    PMD = PMDStateManage(PMDsize)
    ModuleStates = ModuleStateManage()
    ModuleInfoInit(root)
    ScalingUsable = IsScalingUsable 
    StateTransitions = []
    #CntRollBack = 0
    #RollBackHash={}
    #PrevRollBackPMHash = []

def ModuleInfoInit(root):
    global ModuleStates,PMD,RootHash,STATES 
    RootHash = root.hash
    q = []
    # mixerのhash値は1~1001だから，親ミキサーのhashとして存在しない0を指定．
    q.append((root,0))
    while(q):
        node,PMHash = q.pop(0)
        module = Module(node,PMHash)
        ModuleStates.ModuleInfo[str(node.hash)] = module 
        ModuleStates.ModulesStatesAt[module.state].append(node.hash)
        for child in node.children: 
            q.append((child,node.hash))
    return 

#　絶対に呼び出す関数なので，画像出力機能が邪魔になる場合もある．なので，オンオフ機能が必要．
def CountFlushing(savefileName,ColorList,ImageOut=False): 
    global PMD,RootHash,ModuleStates
    PMDsimulation = [[0 for j in range(PMD.pmdHsize)]for i in range(PMD.pmdVsize)]
    ReagentPlacedAt = {}
    MixedAt = {}
    q = []
    q.append(RootHash)
    while(q): 
        hash = q.pop(0)
        Module = ModuleStates.getModule(hash)
        ts = 0
        if Module.kind=="Mixer":
            ts = Module.MixedTimeStep
            if str(ts) not in MixedAt:
                MixedAt[str(ts)] = []
            MixedAt[str(ts)].append(hash)
            for chash in Module.ChildrenHash: 
                q.append(chash)
        else : 
            ts = Module.PlacedTimeStep 
            if str(ts) not in ReagentPlacedAt:
                ReagentPlacedAt[str(ts)] = []
            ReagentPlacedAt[str(ts)].append(hash)
         
    FlushCount = 0
    # ロールバックに対応するために，ややこしいが試薬の配置と混合を追っている．
    # 混合を行っているタイムステップは1以降だが，試薬などの配置は0でも行う
    for TimeStep in range(0,PMD.TimeStep+1):
        # 混合を行う
        if str(TimeStep) in MixedAt:
            if ImageOut: 
                ResultSlideImage(savefileName+"_"+str(TimeStep),ColorList,TimeStep,FlushCount,PMDsimulation,PMD,MixedAt[str(TimeStep)],ModuleStates)
            for mhash in MixedAt[str(TimeStep)]: 
                for wy,wx in ModuleStates.getModule(mhash).CoveringCell: 
                    PMDsimulation[wy][wx] = -1*mhash
        if str(TimeStep) in ReagentPlacedAt:
            for rhash in ReagentPlacedAt[str(TimeStep)]:
                for y,x in ModuleStates.getModule(rhash).ProvCell: 
                    if PMDsimulation[y][x]!= 0: 
                        FlushCount += 1
                        flushed = []
                        for i in range(PMD.pmdVsize): 
                            for j in range(PMD.pmdHsize): 
                                hash = -1*PMDsimulation[i][j]
                                if PMDsimulation[i][j]!= 0 and hash not in flushed:
                                    Module = ModuleStates.getModule(hash)
                                    if Module.kind=="Mixer":
                                        provcell = Module.ProvCell 
                                        covering_cell = Module.CoveringCell 
                                        for cell in covering_cell: 
                                            ty,tx = cell
                                            if cell in provcell : 
                                                continue 
                                            else : 
                                                # 提供セルでないなら，中間液滴をフラッシングして良い
                                                if PMDsimulation[ty][tx]==-1*hash:
                                                    PMDsimulation[ty][tx] = 0 
                                        flushed.append(hash)
                                    else: 
                                        #試薬の場合，全てが提供セルなのでゲームオーバー
                                        pass
                        # フラッシングできなかった場合
                        if PMDsimulation[y][x]!= 0:
                            return [-2,-1]
                    PMDsimulation[y][x] = -1*rhash  
    return FlushCount

def CountCellUsedByMixerNum(): 
    global PMD,ModuleStates,RootHash
    ### Setにセル情報を格納することで，重複を防ぐ
    cells = {}
    q = []
    q.append(RootHash)
    while(q): 
        hash = q.pop(0)
        Module = ModuleStates.getModule(hash)
        if Module.kind=="Mixer":
            for cell in Module.CoveringCell: 
                if str(cell) not in cells: 
                    cells[str(cell)] = 0
                cells[str(cell)]+=1
        for chash in Module.ChildrenHash: 
            q.append(chash) 
    freq = 0
    for v in cells.values(): 
        freq += v 
    return [len(cells),freq/len(cells)]

def ExcuteStateTransitions():
    global StateTransitions
    for transition in StateTransitions:
        transition()
    StateTransitions = []

# Mixerとその子以下の状態はNoTreatmentにする．
def RollBack(MixerHash):
    global PMD,ModuleStates,StateTransitions
    PMixer = ModuleStates.getModule(PMixerHash)
    q = []
    RollBackHash = []
    q.append(MixerHash)
    while(q): 
        ModuleHash = q.pop(0)
        RollBackHash.append(ModuleHash)
        if ModuleStates.getModule(ModuleHash).state != "NoTreatment": 
            StateTransitions.append(ModuleStates.ModuleInfo[str(MixerHash)]._RollBack)

        Module = ModuleStates.getModule(ModuleHash)
        for CHash in Module.ChildrenHash: 
            q.append(CHash)

    RollBackCell = []
    for y in range(PMD.pmdVsize): 
        for x in range(PMD.pmdHsize): 
            cell = (y,x)
            if abs(PMDState[y][x]) in RollBackHash: 
                RollBackCell.append(cell)
                if cell in PMD.CellForFlushing:
                    PMD.CellForFlushing.remove(cell)
                elif cell in PMD.CellForProtectFromFlushing:
                    PMD.CellForProtectFromFlushing.remove(cell)   
    for y,x in RollBackCell: 
        PMD.State[y][x] = 0


from .utility import PMDnowSlideImage
from .utility import ResultSlideImage
PMD,ModuleStates,RootHash = None,None,None
IsScalingUsable = False 
#  状態遷移は逐次でなく，節目節目でまとめて行う． 
#  逐次でやってると，イテレート元のリストの長さが動的に変更されてプログラミングが難しくなる
StateTransitions = []
def SamplePreparation(root,PMDsize,ColorList=None,IsScalingUsable=False,ProcessOutput=False,ImageName="",ImageOut=False):
    global PMD,ModuleStates,ScalingUsable,RootHash,StateTransitions
    globalInit(PMDsize,root,IsScalingUsable)
    PlaceRootMixer()
    ImageCount = 0
    
    # これ以上ミキサーの配置ができない→液滴の混合 & フラッシングを行う．
    while(ModuleStates.getModule(RootHash).state != "ProvidingFluids"): 
        CannotDoAnything = True 
        # 1. MixerOnPMDの子を配置できるか確認し，可能なら配置．
        for MixerHash in ModuleStates.ModulesStatesAt["MixerOnPMD"]: 
            mixer = ModuleStates.getModule(MixerHash)
            shouldPlaceChildren = True 
            for ChildHash in mixer.ChildrenHash: 
                childstate = ModuleStates.getModule(ChildHash).state 
                # 子が配置され，中間液滴を提供している場合も親は"MixerOnPMD"になる
                if childstate != 'NoTreatment' : 
                    shouldPlaceChildren = False 
            if shouldPlaceChildren: 
                CannotDoAnything = False 
                PlaceChildren(MixerHash)
            else: 
                continue 

        # 2. WaitingProvidedFluidsの全ての子がProvidingFluidsになってたら，MixerOnPMDに復帰
        for MixerHash in ModuleStates.ModulesStatesAt["WaitingProvidedFluids"]: 
            isDropsProvidedByChildrenReady = True 
            for ChildHash in ModuleStates.getModule(MixerHash).ChildrenHash: 
                if ModuleStates.getModule(ChildHash).state != "ProvidingFluids": 
                    isDropsProvidedByChildrenReady = False
            if isDropsProvidedByChildrenReady : 
                CannotDoAnything = False 
                StateTransitions.append(ModuleStates.ModuleInfo[str(MixerHash)].MixerOnPMD)

        ChangedTimeStep = False
        #　これ以上ミキサーを配置できない状況になったら
        #　ここまでに配置してきたミキサーで混合を行う．
        if CannotDoAnything: 
            #print("にゃん",ModuleStates.ModulesStatesAt)
            for MixerHash in ModuleStates.ModulesStatesAt["MixerOnPMD"]: 
                #print("長さ",len(ModuleStates.ModulesStatesAt["MixerOnPMD"]))
                mixer = ModuleStates.getModule(MixerHash)
                isReadyForMixing = True 
                #print(mixer.hash,mixer.ChildrenHash,"これが親子")
                for ChildHash in mixer.ChildrenHash:
                    if ModuleStates.getModule(ChildHash).state != "ProvidingFluids": 
                       isReadyForMixing = False 
                if isReadyForMixing : 
                    if not ChangedTimeStep:
                        PMD.TimeStep += 1
                        ChangedTimeStep = True
                    CannotDoAnything = False 
                    Mix(MixerHash)
                else : 
                    continue 
        
        # 3. 1,2番に該当するミキサーがなければ，フラッシング.PlacementSkippedを配置できるなら配置．
        if CannotDoAnything: 
            # レイアウト決定のロールバックを行う場合，ここでタイムステップを変えると処理がややこしくなるかも
            # あとで考え直す
            # フラッシングを行い，置けるミキサーがPlacementSkippedに無いか見る．
            PMD.Flushing()
            #　配置はBFS順，混合は葉からなので，後入れから配置を行えるか確認
            for layout in reversed(ModuleStates.PlacementSkippedLayout): 
                PlacingLayer = layout.getPlacingLayer()
                for hash in layout.CorrectMixingOrder:
                    if layout.layer[str(hash)] == PlacingLayer and ModuleStates.getModule(hash).state == "PlacementSkipped": 
                        if PMD.IsPlacableNow(layout.Placements[str(hash)]):
                            PlaceModule(layout.Placements[str(hash)])
                # PlacementSkippedLayoutから削除すべきか確認
                IsAllModulePlaced = True
                for hash in layout.CorrectMixingOrder:
                    if  ModuleStates.getModule(hash).state == "PlacementSkipped": 
                        IsAllModulePlaced = False 
                if IsAllModulePlaced: 
                    ModuleStates.PlacementSkippedLayout.remove(layout)

        # 何もできないならロールバックするしかない
        if not StateTransitions:
            if ImageOut and ImageName and ColorList:
                ImageCount += 1
                imageName = ImageName+"_"+str(ImageCount)
                PMDnowSlideImage(imageName,ColorList,PMD,ModuleStates)
            print("手詰まりかも", ModuleStates.ModulesStatesAt)
            ModuleStates.showModuleNames()
            return -1,-1,-1
            # 現在のミキサーの配置方法では手詰まりなので，該当ミキサーの親ミキサーの配置法を考え直す
            RollBackHash = ModuleStates.PlacementSkippedLayout.pop()
            RollBack(RollBackHash)
            # RollBackでは，RollBackHashのMixerとそれ以下のミキサーの状態をNoTreatmentにして，ParentMixerの配置法を再探索後，状態をMixerOnPMDにする．
            
        else :
            ExcuteStateTransitions()
            if ImageOut and ImageName and ColorList:
                ImageCount += 1
                imageName = ImageName+"_"+str(ImageCount)
                PMDnowSlideImage(imageName,ColorList,PMD,ModuleStates)

    # 試薬合成完了したので，結果の出力
    if ProcessOutput :
        print("混合手順生成完了")
    ### フラッシングの発生回数の数え上げ
    FlushNum = CountFlushing(ImageName,ColorList,ImageOut=ImageOut)
    ### ミキサーによって使用されたセル数の数え上げ
    CellUsedByMixerNum,FreqCellUsed = CountCellUsedByMixerNum()
    return [FlushNum,CellUsedByMixerNum,FreqCellUsed]

