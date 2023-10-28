#include "json.hpp"
#include <sys/stat.h>
#include <algorithm>
#include <fstream>
#include <ios>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <sstream>
#include <string.h>
#include <string>
#include <typeinfo>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
#include <chrono>

using json = nlohmann::json;
using namespace std;

const int fluidNumMax = 10; 
const int hvMAX = 2;
const string path = "./FluidShapeLib/";

bool isInsideBoundary(int y,int x){
    if (0<=y && y< hvMAX && 0<=x && x<hvMAX)
        return true;
    else 
        return false;
}

bool hasKey(string key, json object) {
  auto itr_check = object.find(key);
  if (itr_check != object.end())
    return true;
  else
    return false;
}

bool SameArray(json array, json cmp_array) {
  if (array.size() == cmp_array.size()) {
    for (int i = 0; i < array.size(); i++) {
      if (array[i] != cmp_array[i])
        return false;
    }
    return true;
  }
  return false;
}


bool ArrayContainsValue(json value, json Array) {
  for (auto v : Array) {
    if (v == value) {
      return true;
    }
  }
  return false;
}

// genFluidShape.pyのアルゴリズムをC++に書き直した．
// genFluidShape.pyの方が詳しくコメントを書いている.参照されたし！！
int main() {
    // 液滴1個のデータを作成
    json json_data; 
    for (int i=0; i<hvMAX; i++){
        for(int j=0; j<hvMAX; j++){
            string SearchSpaceSize = to_string(max(max(i+1,j+1),2)); 
            if(!json_data.contains(SearchSpaceSize))
                json_data[SearchSpaceSize] = json::object();
            string stridx = to_string(json_data[SearchSpaceSize].size()); 
            vector<json> coords; 
            map<string,int> res{{"y",i},{"x",j}};
            json coord(res); 
            coords.push_back(coord); 
            json_data[SearchSpaceSize][stridx] = coords; 
        }
    }
    if(mkdir(path.c_str(), 0777)==-1)
        cout<<path<<"を作成しようとしましたが，もうすでに同名のディレクトリが存在しました（特に問題ない場合は無視してください）.\n";
    string WriteFileName = path+"1fluid.json"; 
    ofstream writing_file;
    writing_file.open(WriteFileName,ios::out); 
    writing_file << json_data <<endl; 
    writing_file.close();

    vector<int> dy{0,-1,0,1};  
    vector<int> dx{-1,0,1,0};
    // n個の液滴によって構成される形を元に，n+1個の液滴から構成される液滴の形を探索する．
    for (int fluidnum=2;fluidnum<=fluidNumMax;fluidnum++ ){
        string FormerFilePath = path+to_string(fluidnum-1)+"fluid.json"; 
        string NewFilePath = path+to_string(fluidnum)+"fluid.json"; 

        ifstream reading1(FormerFilePath, ios::in);
        json FormerFluidShapes; 
        reading1 >> FormerFluidShapes;

        set<vector<pair<int,int>> > SetOfNewShape; 
        //set< vector<int> > SetOfNewShape; 
        for (int formerSearchSpace=2;formerSearchSpace<=hvMAX;formerSearchSpace++){
            string strfss = to_string(formerSearchSpace); 
            if (hasKey(strfss,FormerFluidShapes)){
                for(int fluididx=0; fluididx<size(FormerFluidShapes[strfss]);fluididx++){
                    string strfluididx = to_string(fluididx); 
                    vector<json> FluidShape = FormerFluidShapes[strfss][strfluididx]; 
                    // より扱いやすいデータ型に変換
                    vector<pair<int,int>> shape ; 
                    vector<int> lowerY(hvMAX,-100),upperY(hvMAX,-100),lowerX(hvMAX,-100),upperX(hvMAX,-100); 
                    for(json coord:FluidShape){
                        int y=coord["y"],x=coord["x"]; 
                        if (lowerX[x]==-100 && upperX[x]==-100)
                            lowerX[x] = y,upperX[x] = y; 
                        else 
                            lowerX[x] = min(y,lowerX[x]),upperX[x] = max(y,upperX[x]); 
                        if (lowerY[y]==-100 && upperY[y]==-100)
                            lowerY[y] = x,upperY[y] = x; 
                        else
                            lowerY[y] = min(x,lowerY[y]),upperY[y] = max(x,upperY[y]); 
                        pair<int,int> p{y,x}; 
                        shape.push_back(p); 
                    }

                    for(int coordidx=0; coordidx<size(shape); coordidx++){
                        int y=get<0>(shape[coordidx]),x=get<1>(shape[coordidx]); 
                    for(int way=0; way<4; way++){
                        int ny=y+dy[way],nx=x+dx[way]; 
                        pair<int,int> ncoord{ny,nx}; 
                        if(isInsideBoundary(ny,nx) && count(shape.begin(),shape.end(),ncoord)==0){
                            auto nshape = shape; 
                            nshape.push_back(ncoord); 
                            sort(nshape.begin(),nshape.end()); 
                            bool nxFirstTime = (lowerX[nx]==-100&&upperX[nx]==-100); 
                            bool nxNextToFormer = (abs(ny-lowerX[nx])<=1 || abs(ny-upperX[nx])<=1); 
                            bool nyFirstTime = (lowerY[ny]==-100 || upperY[ny]==-100); 
                            bool nyNextToFormer = (abs(nx-lowerY[ny])<=1 || abs(nx-upperY[ny])<=1); 
                            if (!SetOfNewShape.contains(nshape)
                                && ((!nxFirstTime || !nyFirstTime) && (nxFirstTime || nxNextToFormer) && (nyFirstTime || nyNextToFormer)) ){
                                SetOfNewShape.emplace(nshape); 
                            }
                        }
                    }
                    }
                }
            }
        }
        ofstream new_file;
        new_file.open(NewFilePath,ios::out); 
        json new_data; 
        for (auto nshape : SetOfNewShape){
            int SearchSpace = -1; 
            vector<json> OutputFormedData ; 
            for(auto ncoord : nshape){
                int y=get<0>(ncoord),x=get<1>(ncoord); 
                SearchSpace = max(SearchSpace,max(y+1,x+1));
                map<string,int> res{{"y",y},{"x",x}}; 
                json coord(res); 
                OutputFormedData.push_back(coord); 
            }
            if(2<=SearchSpace && SearchSpace<=hvMAX){
                string strss = to_string(SearchSpace); 
                int idx = 0; 
                if(!hasKey(strss,new_data))
                    new_data[strss] = json::object(); 
                else  
                    idx = size(new_data[strss]);
                new_data[strss][to_string(idx)] = OutputFormedData; 
            }
            else  
                cerr<<"探索領域を超えたサイズの液滴です"<<SearchSpace<<hvMAX<<endl; 
        }
        new_file << new_data <<endl; 
        new_file.close();
    }
    cout<<"データの生成完了"<<endl; 
    return 0;
}
