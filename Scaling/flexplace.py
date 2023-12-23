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
        self.PlaceTimeStep = -1
    
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
            module = q.pop()
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
        l = []
        for ChildHash in self.ChildrenHash:
            child = ModuleStates.getModule(ChildHash)
            ecn = 0 
            if child.IsMixer():
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
        self.PlacementSkippedLib = []
    
    def getModule(self,hash):
        return self.ModuleInfo[str(hash)]
        
# PMDの状態を管理するための構造体
class PMDStateManage:
    def __init__(self,PMDsize):
        self.pmdVsize,self.pmdHsize = PMDsize
        self.State = [[0 for j in range(self.pmdHsize)] for i in range(self.pmdVsize)]
        self.CellForFlushing = []
        self.CellForProtectFromFlushing = []
        self.RegisteredAsProvCell = [[[] for j in range(self.pmdHsize)] for i in range(self.pmdVsize)]
        self.RegisteredAsPlacementCell = [[[] for j in range(self.pmdHsize)] for i in range(self.pmdVsize)]

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
    dy,dx = [0,1,0,-1],[-1,0,1,0] 
    corner = []
    for cell in cells: 
        NextNum = 0
        y,x = cell
        for way in range(4): 
            ny,nx = y+dy[way],x+dx[way]
            if (ny,nx) in cells: 
                NextNum+=1
        if NextNum == 2:
            corner.append(cell)
    return corner

def swap(x,y): 
    return (y,x)

# 二つのミキサーが共有しているセルから，ProvNum個分の提供液滴を渡すセルの候補を探索する．
def getProvCellsAlt(InterSectionCells,ProvNum):
    CornerCells = getCornerCells(InterSectionCells) 
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
            Usual,EncounteringWall = ways 
            if swapUsual: 
                Usual,EncounteringWall = swap(Usual,EncounteringWall)
            ProvCells = [cell]
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
                        ny,nx = y+dy[EncounteringWall],x+dx[EncounteringWall]
                        # 蛇のようにくねくねセルを集めるので，
                        # 壁に当たったら進行方向を逆にするために符号の切り替え
                        sign *= -1
                        ncell = (ny,nx)
                        if ncell not in ProvCells: 
                            if ncell in InterSectionCells:
                                ProvCells.append(ncell)
                                WatchingCell = ncell 
            sort(ProvCells)
            if ProvCells not in res:
                res.append(ProvCells) 
    return res

class EdgeManagement: 
    def __init__(self): 
        self.InEdge = []
        self.OutEdge = []

class Placement: 
    def __init__(self,Hash,CoveringCell,ProvCell,FlushCell): 
        self.hash = Hash
        self.CoveringCell = CoveringCell
        self.ProvCell = ProvCell 
        self.FlushCell = FlushCell 
    def show(self): 
            # 必要ならあとで書く
        print("MixerHash:",self.MixerHash)

class Layout: 
    def __init__(self,PMixerCells,MixingOrder): 
        global PMD
        self.Placements = []
        self.RestProvCell = copy.deepcopy(PMixerCells)
        self.PMD = copy.deepcopy(PMD)
        self.MixingOrder = copy.deepcopy(MixingOrder)

    def MixingOrderSolver(self):
        for mhash in self.MixingOrder:
            #if ModuleStatesnow[mhash].
            # 必要ならあとで書く
            return

# 親ミキサーの配置場所を仮決めして引数に与えた場合，
# その子のモジュールはどのようなレイアウトを取ることができるか探索する．
def getChildrenLayoutAlt(PMixerCellsAlt,PMixerHash):
    global PMD,ModuleStates 
    PMixer = ModuleStates.getModule(PMixerHash)
    # ECNのおかげで，ミキサー→試薬の順番で配置場所を探索できる．
    # 試薬は，余ってる提供セルを適当に割り当てる. 
    GeneratingLayouts = [[] for i in range(len(PMixer.ChildrenHash)+1)]
    LayoutSeed = Layout(PMixerCellsAlt,PMixer.ChildrenHashSortedByECN())
    GeneratingLayouts[0].append(LayoutSeed)
    for idx,chash in enumerate(PMixer.ChildrenHashSortedByECN()):
        child = ModuleStates.getModule(chash)
        for layout in GeneratingLayouts[idx]:
            # 配置する子がミキサーの場合
            if child.IsMixer():
                # まだ子が試薬のパターンのみなのでチェックできない
                # あとで⭐️
                # あとで⭐️
                # あとで⭐️
                # あとで⭐️
                # あとで⭐️
                # あとで⭐️
                # あとで⭐️
                shapes = getMixerShapeLib(child.size)
                childmixeralts = []
                # 適当にミキサーの概形の左上の参照セル(ref_y,ref_x)を選ぶ
                for ref_y in range(PMD.pmdVsize): 
                    for ref_x in range(PMD.pmdHsize): 
                        ref_cell = (ref_y,ref_x)
                        for shape in shapes:
                            CMixerCellsAlt = Translation(shape,ref_cell)
                            InterSectionCells = getInterSection(PMixerCellsAlt,CMixerCellsAlt)
                            # 適当な参照セルで子ミキサーを置いた時，親ミキサと重なるセル数が提供液滴数よりも多い場合処理を続行
                            if len(InterSectionCells)>=child.ProvNum:
                                ProvCellsAlt = getProvCellsAlt(InterSectionCells,child.ProvNum)
                                for provcells in ProvCellsAlt:
                                    # 適当に提供液滴の配置パターンを書き出してみただけやから，
                                    # それが使えるのか逐一チェックする必要あり
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
                                    for cell in ProvCellsAlt: 
                                        y,x = cell 
                                        for mhash in LayoutProcess.PMD.RegisteredAsPlacementCell[y][x]: 
                                            if (mhash in suspicion) and ModuleStates.getModule(mhash).current_state.name != "PlacementSkipped" : 
                                                # AかつBの関係になる様なミキサーの内，
                                                # 相手が配置されている(ECNのより大きい部分木に属する)ミキサーならデッドロックが発生
                                                Pass = False
                                    # 先祖の子だが，自身の先祖には含まれず，自身の先祖よりECNの大きいミキサーの提供液滴に
                                    ##オーバーラップしていないかのチェック
                                    for cell in CMixerCellsAlt: 
                                        y,x = cell 
                                        for mhash in LayoutProcess.PMD.RegisteredAsProvCell[y][x]: 
                                            if mhash not in child.AncestorHash and ModuleStates.getNode(mhash).ParentHash in child.AncestorHash:
                                                if ModuleStates.getModule(mhash).current_state.name != "PlacementSkipped" : 
                                                    Pass = False  
                                    # 兄弟ミキサーとのオーバーラップが発生している場合，混合順はECN順になるか?
                                    suspicion = []
                                    for cell in CMixerCellsAlt: 
                                        y,x = cell 
                                        # 配置セル内に，兄弟ミキサー(自分よりECNが大きい)の提供セルがある場合，
                                        # 自分の方がミキサーを先に混合する必要が出る．それはECNの概念に矛盾するので不合格．
                                        for mhash in LayoutProcess.PMD.RegisteredAsProvCell[y][x]: 
                                            if mhash in PMixer.ChildrenHash:
                                                Pass = False 
                                    if Pass:
                                        for cell in provcellsAlt: 
                                            y,x = cell
                                            LayoutProcess.PMD.RegisteredAsProvCell[y][x].append(chash)
                                            LayoutProcess.RestProvCell.remove((y,x))
                                        for mixercell in CMixerCellsAlt: 
                                            y,x = mixercell
                                            LayoutProcess.PMD.RegisteredAsPlacementCell[y][x].append(chash)
                                        # 次の子の配置に回す．
                                        GeneratingLayouts[idx+1].append(LayoutProcess)
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
                placement = Placement(chash,CoveringCells,ProvCells,FlushCells)
                LayoutProcess.Placements.append(placement)
                GeneratingLayouts[idx+1].append(LayoutProcess)
    res = []
    # データを返り値の形式に直す
    for layout in GeneratingLayouts[len(PMixer.ChildrenHash)]:
        res.append(layout.Placements) 
    return res


MixerShapeKind = ["Rectangle","LShaped"]
def PlaceRootMixer():
    global PMD,ScalingUsable,MixerShapeKind,ModuleStates,RootHash
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
                    LayoutAlternatives = getChildrenLayoutAlt(RootMixerCells,RootHash)
                    if len(LayoutAlternatives)>MaxAltnum:
                        MaxAltnum = len(LayoutAlternatives)
                        BestMixerShape = RootMixerCells 
                else: 
                    continue 
    # ルートミキサーの提供液滴を無しとした理由は，Goodnotesを参照
    PlaceMixer(RootHash,BestMixerShape,[])

# PMDやミキサの状態の書き換えのための関数
def PlaceMixer(MixerHash,PlacedCells,ProvCell):
    global PMD,ModuleStates
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
    ModuleStates.ModuleInfo[str(MixerHash)].MixerOnPMD()

def PlaceReagent(Hash,PlacedCells,ProvCell):
    global PMD,ModuleStates
    for cell in ProvCell: 
        y,x = cell
        PMD.RegisteredAsProvCell[y][x].append(Hash)
    for cell in PlacedCells: 
        y,x = cell 
        PMD.RegisteredAsPlacementCell[y][x].append(Hash) 
        # 中間液滴や試薬液滴の置かれているセルは，負の値を書き込む
        PMD.State[y][x] = -1*Hash
    ModuleStates.ModuleInfo[str(Hash)].CoveringCell = PlacedCells
    ModuleStates.ModuleInfo[str(Hash)].ProvCell = ProvCell 
    # 状態遷移
    ModuleStates.ModuleInfo[str(Hash)].ProvidingFluids()

def PlaceChildren(ParentMixerHash): 
    global ModuleStates
    PMixer = ModuleStates.getModule(ParentMixerHash)
    ChildrenLayoutAlt = getChildrenLayoutAlt(PMixer.CoveringCell,PMixer.hash)

    Layout= []
    IsNoFlusing = False
    for LayoutAlt in ChildrenLayoutAlt: 
        # レイアウトの評価式，あとで書く
        EvalV = 1
        #EvalV = EvalLayout(LayoutAlt)
        Layout.append((EvalV,LayoutAlt))
    for evalv,layout in sorted(Layout,reverse=True):
        for placement in layout: 
            if ModuleStates.getModule(placement.hash).IsMixer():
                PlaceMixer(placement.hash,placement.CoveringCell,placement.ProvCell)
            else : 
                PlaceReagent(placement.hash,placement.CoveringCell,placement.ProvCell)
        #if IsPlacable(layout):
        #else : 
        #    # あとで書く
        #    # 配置ができない場合，PlacementSkippedに入れる
        #    pass 
    # 子を置いたら，親ミキサーは子からの提供液滴を待つ状態に遷移する.
    ModuleStates.ModuleInfo[str(ParentMixerHash)].WaitingProvidedFluids()

def Mix(MixerHash):
    global ModuleStates,PMD 
    mixer = ModuleStates.getModule(MixerHash)
    for cell in mixer.CoveringCell: 
        y,x = cell
        PMD.State[y][x] = -1*MixerHash 
    ModuleStates.ModuleInfo[str(MixerHash)].ProvidingFluids()
    for chash in mixer.ChildrenHash: 
        ModuleStates.ModuleInfo[str(chash)].Done()


def globalInit(PMDsize,root,IsScalingUsable):
    global PMD,ModuleStates,ScalingUsable#,CntRollBack,RollBackHash,PrevRollBackPMHash 
    PMD = PMDStateManage(PMDsize)
    ModuleStates = ModuleStateManage()
    ModuleInfoInit(root)
    ScalingUsable = IsScalingUsable
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

PMD,ModuleStates,RootHash = None,None,None
IsScalingUsable = False 
def SamplePreparation(root,PMDsize,ColorList=None,IsScalingUsable=False,ProcessOutput=False,ImageName="",ImageOut=False):
    global PMD,ModuleStates,ScalingUsable,RootHash
    globalInit(PMDsize,root,IsScalingUsable)
    print(ModuleStates.getModule(RootHash).state)
    PlaceRootMixer()
    print("にゃん",ModuleStates.getModule(RootHash).state)
    print("にゃん",ModuleStates.ModulesStatesAt)
    print("にゃん",PMD.RegisteredAsPlacementCell)
    
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
                ModuleStates.ModuleInfo[str(MixerHash)].MixerOnPMD()
        
        #　ここまでに配置してきたミキサーで混合できるものはないか確認
        ChangedTimeStep = False 
        if CannotDoAnything: 
            for MixerHash in ModuleStates.ModulesStatesAt["MixerOnPMD"]: 
                mixer = ModuleStates.getModule(MixerHash)
                isReadyForMixing = True
                for ChildHash in mixer.ChildrenHash:
                    if ModuleStates.getModule(ChildHash).state != "ProvidingFluids": 
                       isReadyForMixing = False 
                if isReadyForMixing : 
                    CannotDoAnything = False 
                    if not ChangedTimeStep: 
                        ChangedTimeStep = True 
                        #TimeStep += 1
                    # 処理はあとで書く
                    Mix(MixerHash)
                else : 
                    continue 
        
        # 3. 1,2番に該当するミキサーがなければ，フラッシング.PlacementSkippedを配置できるなら配置．
        if CannotDoAnything: 
            # フラッシングを行い，置けるミキサーがPlacementSkippedに無いか見る．
            # あとで書く
            pass; 

    print("にゃん",ModuleStates.ModulesStatesAt)
    #親のミキサーと提供液滴分のセルを選択する．
    ## 現時点のPMDの状況で，IFが必要ない子のレイアウトとIFが必要な子のレイアウトを分けて数え上げる．
