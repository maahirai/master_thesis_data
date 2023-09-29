import random
import sys

Registered_Hash = []

class node(object):
    def __init__(self, name, size=6, provide_vol=0, children = None ):
        self.name = name 
        self.size = size
        self.provide_vol = provide_vol
        self.children = children if children else []
        hash_v = 1
        while(hash_v in Registered_Hash):
            hash_v = random.randint(1,100001)
        Registered_Hash.append(hash_v)
        self.hash = hash_v 

def IsMixerNode(Node):
    if IsMixerName(Node.name):
        return True
    else :
        return False

def IsMixerName(name):
    if name[0]=='M':
        return True
    else :
        return False

def cntMixer(root): 
    q = []
    MixerNum = 0
    if root.children: 
        q.append(root)
        MixerNum += 1
    while q: 
        mn = q.pop()
        for cn in mn.children: 
            if cn.children: 
                MixerNum += 1
                q.append(cn)
    return MixerNum

######################################################################################
MIX_COUNTER = 0

def InputToTree(Input):
    root = _InputToTree(Input,0)
    tree = LabelingMixers(root)
    tree = WeakTransformTree(tree)
    return tree

def _InputToTree(Input,provide_vol):
    global MIX_COUNTER
    RootNodeSize = sum(Input[0])
    if RootNodeSize == 6 or RootNodeSize == 4:
        root = node('M',size=sum(Input[0]),provide_vol=provide_vol)
        MIX_COUNTER += 1 
        for idx,item in enumerate(Input[1:]):
            ### mixer
            if type(item) == list:
                root.children.append(_InputToTree(item,Input[0][idx]))
            ### droplet of reagent
            elif type(item) == str:
                root.children.append(node(item,size=Input[0][idx],provide_vol=Input[0][idx]))
            else :
                print("不正な入力です:{}".format(item))
                pass
        return root
    else :
        print("入力された希釈木データに異常あり．希釈木に含まれるミキサーのサイズは4，もしくは，6のみです．",file=sys.stderr)

# M9などの名前の埋め込み
def LabelingMixers(root):
    q = []
    q.append(root)
    idx = 0
    while not len(q)==0:
        n = q.pop(0)
        n.name = n.name + str(idx)
        idx += 1
        for item in n.children :
            if item.name[0] == "M":
                q.append(item)
    return root

######################################################################################
# transform the input tree
from copy import deepcopy
import itertools
import math

# Sum of Number of children-mixer in the subtree
lNumChildMixer = []

def TransformTree(root):
    global lNumChildMixer,MIX_COUNTER 
    lNumChildMixer = list(itertools.repeat(-1,MIX_COUNTER))
    cpTree = deepcopy(root)
    transformed_tree = _old_TransformTree(cpTree)
    return transformed_tree

def WeakTransformTree(root):
    global lNumChildMixer,MIX_COUNTER 
    lNumChildMixer = list(itertools.repeat(-1,MIX_COUNTER))
    cpTree = deepcopy(root)
    transformed_tree = _weak_TransformTree(cpTree)
    return transformed_tree

def OctTransformTree(root):
    global lNumChildMixer,MIX_COUNTER 
    lNumChildMixer = list(itertools.repeat(-1,MIX_COUNTER))
    cpTree = deepcopy(root)
    transformed_tree = _Oct_old_TransformTree(cpTree)
    return transformed_tree

def _weak_TransformTree(root):
    Children = []
    for item in root.children:
        ecv = 0
        if IsMixerNode(item):
            #put mixer on the left-side
            ecv = 1
            # we must place tht item firstly if (item.provide_vol == (ParentMixer.size - 1))
            if item.provide_vol == root.size - 1:
                # so large value
                INF = 1000000000000
                ecv += INF 
            # if 4Mixer provides 3-fluids
            elif item.provide_vol%2 and item.provide_vol>1 and item.size//2<=2: 
                ecv += 100000000
        Children.append((item,ecv))
    SortedByECV = sorted( Children, key = lambda x: x[1], reverse = True)
    res = []
    for item in SortedByECV:
        Subtree = _weak_TransformTree(item[0])
        res.append(Subtree)
    root.children = res
    return root

def _old_TransformTree(root):
    Children = []
    for item in root.children:
        ecv = 0
        if IsMixerNode(item):
            # Sum of Number of children-mixer in the subtree
            ecv += NumChildMixer(item)
            # providing volume 
            ecv += item.provide_vol
            # we must place tht item firstly if (item.provide_vol == (ParentMixer.size - 1))
            if item.provide_vol == root.size - 1:
                # so large value
                INF = 1000000000000
                ecv += INF 
            # if 4Mixer provides 3-fluids,3:2:1とかのとき,3を優先する必要あり
            elif item.provide_vol%2 and item.provide_vol>1 and item.size//2<=2: 
                ecv += 100000000
        Children.append((item,ecv))
    SortedByECV = sorted( Children, key = lambda x: x[1], reverse = True)
    res = []
    for item in SortedByECV:
        Subtree = _old_TransformTree(item[0])
        res.append(Subtree)
    root.children = res
    return root

def __old_TransformTree(root):
    Children = []
    for item in root.children:
        ecv = 0
        if IsMixerNode(item):
            # Sum of Number of children-mixer in the subtree
            ecv += NumChildMixer(item)
            # providing volume 
            #ecv += item.provide_vol
            # we must place tht item firstly if (item.provide_vol == (ParentMixer.size - 1))
            if item.provide_vol == root.size - 1:
                # so large value
                INF = 1000000000000
                ecv += INF 
            # if 4Mixer provides 3-fluids,3:2:1とかのとき,3を優先する必要あり
            elif item.provide_vol%2 and item.provide_vol>1 and item.size//2<=2: 
                ecv += 100000000
        Children.append((item,ecv))
    SortedByECV = sorted( Children, key = lambda x: x[1], reverse = True)
    res = []
    for item in SortedByECV:
        Subtree = __old_TransformTree(item[0])
        res.append(Subtree)
    root.children = res
    return root

### 配置優先度の式を変えた
def _Oct_old_TransformTree(root): 
    Children = []
    INF = 100000000
    for item in root.children:
        ### 試薬液滴を配置するのは，後回し
        ecv = 0
        if IsMixerNode(item):
            # Sum of Number of children-mixer in the subtree
            ecv += NumChildMixer(item)
            # providing volume 
            #　提供液滴が多いほど，後の配置に邪魔になるから後回し.
            # 並列度を高くするのには効くかも
            ecv /= item.provide_vol
            # we must place tht item firstly if (item.provide_vol == (ParentMixer.size - 1))
            # 5:1の5や，3:1の3
            if item.provide_vol == root.size - 1:
                ecv = INF 
            # どんなパターンでも3from4Mを優先する必要があり.
            # 例えば，1:1:1:3の場合，3from4を優先せんと適応できるパターンがない
            elif item.provide_vol%2 and item.provide_vol>1 and item.size//2<=2: 
                ecv = INF
        Children.append((item,ecv))
    SortedByECV = sorted( Children, key = lambda x: x[1], reverse = True)
    res = []
    for item in SortedByECV:
        Subtree = _Oct_old_TransformTree(item[0])
        res.append(Subtree)
    root.children = res
    return root

def _new_TransformTree(root):
    root = split_flash_needed_pattern(root)
    return _old_TransformTree(root)

def split_flash_needed_pattern(root):
    global MIX_COUNTER,Registered_Hash
    # 6Mixerの5や4Mixerの3など必ずフラッシングが発生する提供比率を，4:1や2:1に分割することで回避する．
    fragments = []
    skip = False
    #全部ミキサーノードの場合のみ対象
    for item in root.children:
        if not IsMixerNode(item):
           skip = True 

    for item in root.children:
        if (not skip) and item.provide_vol == root.size - 1:
            item.provide_vol = item.provide_vol - 1
            fragment = generate_fragment(item)
            fragments.append(fragment)
    for item in fragments: 
        root.children.append(item)
    res = []
    for item in root.children: 
        Subtree = split_flash_needed_pattern(item)
        res.append(Subtree)
    root.children = res 
    return root

def generate_fragment(root): 
    global MIX_COUNTER,Registered_Hash
    fragment = deepcopy(root)
    fragment.provide_vol = 1
    q = []
    q.append(fragment)
    while(q): 
        Node = q.pop()
        hash_v = 1
        while(hash_v in Registered_Hash):
            hash_v = random.randint(1,100001)
        Registered_Hash.append(hash_v)
        Node.hash = hash_v
        if IsMixerNode(Node): 
            MIX_COUNTER += 1
            for child in Node.children: 
                q.append(child)
    return fragment

def NumChildMixer(root):
    global lNumChildMixer
    if not IsMixerNode(root):
        return 0
    else :
        mixeridx = int(root.name[1:])
        if not lNumChildMixer[mixeridx] == -1:
            return lNumChildMixer[mixeridx]
            print(root.name,v)
        else :
            v = 0
            psize = root.size
            pweight = 1.0
            if psize == 6:
                pweight = 1.5 
            for item in root.children:
                if IsMixerNode(item):
                    weight = 1.0
                    if item.size == 6: 
                        weight = 1.5
                    v += pweight*weight*(1+NumChildMixer(item))
            lNumChildMixer[mixeridx] = v
            return lNumChildMixer[mixeridx]

def Scaling(root,target_mixer_name,scale_factor):
    if not isinstance(scale_factor, int) or scale_factor <= 0 : 
        print("入力が不正です.スケーリングの倍率:{}".format(scale_factor),file=sys.stderr)
        return root
    q = [] 
    root_mixer = deepcopy(root)
    q.append(root_mixer)
    
    while(q):
        e = q.pop(0)
        if e.name == target_mixer_name:
            # 子は試薬液滴ノードでもスケーリングの対象
            for child in e.children: 
                # 全ての提供比率をsacle_factor倍する
                child.provide_vol = child.provide_vol * scale_factor 

        # スケーリングによって提供液滴数がミキサーサイズ以上 になったミキサーには，
        # そのミキサーサイズをceil(変更後の提供液滴数/元のミキサーサイズ)倍する
        for child in e.children: 
            if child.provide_vol >= child.size :
                # 提供液滴数が子の元のサイズの自然数倍→さらにその子の液滴提供能力を確保し，
                # 子は削除
                if IsMixerName(child.name):
                    child_scale_factor = math.ceil(child.provide_vol/child.size)
                    child.size *= child_scale_factor
                    for grandchild in child.children: 
                       grandchild.provide_vol = grandchild.provide_vol * child_scale_factor 
                else:
                    # 試薬液滴は元からサイズ==提供液滴数
                    child.size = child.provide_vol 
        for child in e.children: 
            if IsMixerName(child.name): 
                q.append(child)
    
    q.append(root_mixer)
    
    #　各ミキサーノードについて，どこまで子孫ノードを削除していいか深さ優先探索で調べて，削除
    q.append(root_mixer)
    while(q): 
        e = q.pop(0)
        new_children = []
        reagent_dict = {}
        # 飛ばされるミキサーノードが格納される
        dfsq = []
        for child in e.children: 
            if IsMixerName(child.name) and child.size == child.provide_vol: 
                dfsq.append(child)
            else: 
                # 試薬液滴の場合，液滴数を合算してから最後に子として登録
                if not IsMixerName(child.name) :
                    if child.name not in reagent_dict: 
                        reagent_dict[child.name] = child 
                    else : 
                        reagent_dict[child.name].provide_vol += child.provide_vol
                        reagent_dict[child.name].size += child.size
                else: 
                    new_children.append(child)
                    q.append(child)
        while(dfsq): 
            target = dfsq.pop(0)
            #print(target.name,target.size,target.provide_vol)
            for child in target.children: 
                if child.provide_vol == child.size: 
                    # 削除すべき無意味なミキサノードなので，飛ばしてさらにその子が無意味か探索
                    if IsMixerName(child.name): 
                        dfsq.append(child) 
                    # 試薬液滴はそのまま子に入れる
                    else: 
                        if child.name not in reagent_dict: 
                            reagent_dict[child.name] = child 
                        else : 
                            reagent_dict[child.name].provide_vol += child.provide_vol
                            reagent_dict[child.name].size += child.size
                # 無意味ではないミキサーノードなので，子に追加 
                else: 
                    new_children.append(child)
                    q.append(child)
        for reagent in reagent_dict.values(): 
            new_children.append(reagent)
        e.children = new_children 

    while(q): 
        e = q.pop(0)
        for c in e.children: 
            if IsMixerName(c.name): 
                q.append(c)
                print(c.name,c.size,c.provide_vol)
    return root_mixer

######################################################################################

def _getNodesEdges(node):
    '''
    returns list of nodes and edges of a tree from NODE data structure
    '''
    nodelist = [(node.hash, node.name)]
    edgelist = []
    for child in node.children:
        edgelist.append(((node.hash, node.name, node.provide_vol), (child.hash, child.name, child.provide_vol)))
        temp_nodelist, temp_edgelist = _getNodesEdges(child)
        nodelist += temp_nodelist
        edgelist += temp_edgelist
    
    return nodelist, edgelist

import pydot
from .utility import Translate
ColorList = []
def _createTree(root, label=None):
    '''
    convert a tree from NODE data structure to Pydot Graph for visualisation
    '''
    global MIX_COUNTER,ColorList 
    MixerColorList = []
    ReagentColorDict = {}
    #print("にゃん",ColorList)
    if not ColorList:
        MixerColorList = list(itertools.repeat("#000000",MIX_COUNTER))
    elif len(ColorList)==2: 
        MixerColorList = ColorList[0]
        ReagentColorDict = ColorList[1]
    else :  
        MixerColorList = ColorList
    #print("正",MixerColorList,ReagentColorDict,MIX_COUNTER,len(MixerColorList))
    P = pydot.Dot(graph_type='digraph', label=label, labelloc='top', labeljust='left')#, nodesep="1", ranksep="1")
    P.set_node_defaults(style='filled',fixedsize='false',fontsize='28',fontname='Time New Roman Italic')
    P.set_graph_defaults(bgcolor="#00000000")
    P.set_edge_defaults(fontsize = '30',arrowsize = '0.5')

    nodelist, edgelist = _getNodesEdges(root)
    
    for i,node in enumerate(nodelist):
        RGB = 0
        for d in range(3):
            RGB = RGB * 256 + random.randint(128,255)

        ### 試薬液滴ノードの出力設定
        shape,color,width='plaintext',"#FFFFFF","0.3" 
        ### ミキサーノードの出力設定
        if node[1][0]=="M" :
            mixeridx = int(node[1][1:])
            if MixerColorList[mixeridx] == "#000000":
                MixerColorList[mixeridx] = "#"+hex(RGB)[2:]
            shape,color,width = 'circle',MixerColorList[mixeridx],"0.75"
        else: 
            reagentname = node[1]
            if not reagentname in ReagentColorDict: 
                ReagentColorDict[reagentname] = "#"+hex(RGB)[2:]
            color = ReagentColorDict[reagentname] 
        #n = pydot.Node(node[0], shape = shape,label=Translate(node[1]),fillcolor=color,width= width)
        n = pydot.Node(node[0], shape = shape,label=node[1],fillcolor=color,width= width)
        P.add_node(n)
    ColorList = [MixerColorList,ReagentColorDict]
    
    # Edges
    for edge in edgelist:
        e = pydot.Edge(*(edge[0][0], edge[1][0]), label=edge[1][2], dir='back')
        P.add_edge(e)
    return P


from IPython.display import Image, display
def _viewPydot(pydot):
    '''
    generates a visual plot of Pydot Graph
    '''
    plt = Image(pydot.create_png(prog='dot'))
    display(plt)
    
### pngデータを返す
def viewTree(root):
    _viewPydot(_createTree(root))
    

import os
from .utility import create_directory
def saveTree(root, save):
    save = save.split('/')
    dir_name = '/'.join(save[:-1])
    if not save[-1].endswith('.png'):
        file_name = save[-1] + '.png'
    else:
        file_name = save[-1]
    create_directory(dir_name)
        
    _createTree(root).write_png(os.path.join(dir_name, file_name))

######################################################################################    
