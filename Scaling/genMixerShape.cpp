#include "json.hpp"
#include <algorithm>
#include <fstream>
#include <ios>
#include <iostream>
#include <iterator>
#include <map>
#include <math.h>
#include <set>
#include <sstream>
#include <string.h>
#include <string>
#include <sys/stat.h>
#include <utility>
#include <vector>

using json = nlohmann::json;
using namespace std;
int base_mixer[2] = {4, 6};
const int MixerSizeMax =  192;
// 液滴の水平&垂直方向の長さの最大値（max(垂直方向の長さ,水平方向の長さ)）
const string path = "./MixerShapeLib/";

// 長方形のミキサーの最右下のセルを探索する．
// 最右下セルが(1,2)なら，0-indexedを打ち消し，(2,3)に変換する．
// →2x3の長方形のミキサーだと分かる
pair<int, int> SearchRectSize(vector<pair<int, int>> rectangle) {
  int mi = 0, mj = 0;
  for (auto coord : rectangle) {
    // c++-17以降
    int i = get<0>(coord), j = get<1>(coord);
    // 1を足しているのは，ミキサーサイズを求めるために
    // 0-indexedを打ち消す必要があるから．
    mi = max(i + 1, mi);
    mj = max(j + 1, mj);
  }
  pair<int, int> size = make_pair(mi, mj);
  return size;
}

using pii = pair<int, int>;
vector<vector<pair<int, int>>> _genLShapedMixer(pii base_size, pii delete_start_coord, pii delete_size) {
  vector<vector<pair<int, int>>> res;
  // まずは，削除するセルも含めた大きな長方形をbaseに格納.
  int base_rect_h = get<0>(base_size), base_rect_w = get<1>(base_size);
  vector<pair<int, int>> base;
  for (int i = 0; i < base_rect_h; i++) {
    for (int j = 0; j < base_rect_w; j++) {
      pair<int, int> cell = make_pair(i, j);
      base.push_back(cell);
    }
  }

  int bigger_dsy = get<0>(delete_start_coord),
      bigger_dsx = get<1>(delete_start_coord);
  int delete_startY[2] = {0, bigger_dsy}, delete_startX[2] = {0, bigger_dsx};
  int delete_rect_h = get<0>(delete_size), delete_rect_w = get<1>(delete_size);
  // baseの長方形から，4種類のdelete_start_coordを起点にdelete_size分の長方形を切り取ることで，4種類のL字型のミキサーを作る．
  // 引いた後の長さが自然数になる様に，大小条件を確認する．
  if (base_rect_h > delete_rect_h && base_rect_w > delete_rect_w) {
    for (int si = 0; si < size(delete_startY); si++) {
      for (int sj = 0; sj < size(delete_startX); sj++) {
        vector<pair<int, int>> deletedCell;
        for (int diff_y = 0; diff_y < delete_rect_h; diff_y++) {
          for (int diff_x = 0; diff_x < delete_rect_w; diff_x++) {
            int delete_y = delete_startY[si] + diff_y,
                delete_x = delete_startX[sj] + diff_x;
            if ((0 <= delete_y && delete_y < base_rect_h) &&
                (0 <= delete_x && delete_x < base_rect_w)) {
              pair<int, int> dcell = make_pair(delete_y, delete_x);
              deletedCell.push_back(dcell);
            } else {
              cerr << "はみ出しています.1" << endl;
            }
          }
        }
        vector<pair<int, int>> LShapedMixer = base;
        for (auto cell : deletedCell) {
          auto ptr = find(LShapedMixer.begin(), LShapedMixer.end(), cell);
          LShapedMixer.erase(ptr);
        }
        // 被りがなければ，ミキサーの形として登録
        if (count(res.begin(), res.end(), LShapedMixer) == 0)
          res.push_back(LShapedMixer);
      }
    }
  }
  return res;
}

vector<vector<pair<int, int>>> genLShapedMixer(pair<int, int> rect_size) {
  vector<vector<pair<int, int>>> res;
  // 横長長方形ならx断面で，縦長長方形ならy断面で長方形を2分割する．
  int height = get<0>(rect_size), width = get<1>(rect_size);
  if (height <= width) {
    for (int split_w = 1; split_w * 2 < width; split_w++) {
      // split_wが1のとき，こちらはミキサーの形として不適当.
      if (split_w != 1) {
        // 2*height x
        // (width-split_w)から，(0,0),(height-1,0),(0,split_w-1),(height-1,sw-1)のそれぞれを起点とした
        // height * (width-2*split_w) の長方形を削除し4つのL型のミキサーを作る

        // まずは，削除するセルも含めた大きな長方形baseのサイズを指定.
        int base_rect_h = 2 * height;
        int base_rect_w = width - split_w;
        // baseから4種類の長方形のそれぞれを引き，4つのL字型ミキサーを作成．
        int larger_deleteSY= height; 
        int larger_deleteSX= split_w;
        int delete_rect_h = height;
        int delete_rect_w = width - 2 * split_w;
        if (base_rect_h>0 && base_rect_w>0 && delete_rect_h>0 && delete_rect_w>0 && 
                base_rect_h>delete_rect_h && base_rect_w>delete_rect_w &&
                base_rect_h > delete_rect_h && base_rect_w > delete_rect_w) {
            pair<int, int> base_size = make_pair(base_rect_h, base_rect_w);
            pair<int, int> delete_start_info = make_pair(larger_deleteSY,larger_deleteSX);
            pair<int, int> delete_size = make_pair(delete_rect_h, delete_rect_w);
            vector<vector<pair<int, int>>> LShapes =
                _genLShapedMixer(base_size, delete_start_info, delete_size);
            for (auto lshape : LShapes) {
              if (count(res.begin(), res.end(), lshape) == 0)
                res.push_back(lshape);
            }
        }
      }
      // こちらは，split_wが1の時でも生成する．
      // (height+split_w) x
      // (width-split_w)の長方形から，(0,0),(0,h-1),(h-1,0),(h-1,h-1)のそれぞれを起点とした
      // split_w * (w-split_w-h) の長方形を削除し4つのL型のミキサーを作る

      // まずは，削除するセルも含めた大きな長方形をbaseに格納.
      int base_rect_h = height + split_w;
      int base_rect_w = width - split_w;
      // baseから4種類の長方形のそれぞれを引き，4つのL字型ミキサーを作成． 
      int larger_deleteSY= height; 
      int larger_deleteSX= height;
      int delete_rect_h = split_w;
      int delete_rect_w = width - split_w - height;
        if (base_rect_h>0 && base_rect_w>0 && delete_rect_h>0 && delete_rect_w>0 && 
                base_rect_h>delete_rect_h && base_rect_w>delete_rect_w) {
            pair<int, int> base_size = make_pair(base_rect_h, base_rect_w);
            pair<int, int> delete_start_info = make_pair(larger_deleteSY,larger_deleteSX);
            pair<int, int> delete_size = make_pair(delete_rect_h, delete_rect_w);
            vector<vector<pair<int, int>>> LShapes =
                _genLShapedMixer(base_size, delete_start_info, delete_size);
            for (auto lshape : LShapes) {
              if (count(res.begin(), res.end(), lshape) == 0)
                res.push_back(lshape);
            }
        }
    }
  } else {
    for (int split_h = 1; split_h * 2 < height; split_h++) {
      // split_hが1のとき，こちらはミキサーの形として不適当.
      if (split_h != 1) {
        // (height-split_h) x 2*width
        // から，(0,0),(split_h-1,0),(0,width-1),(sw-1,width-1)のそれぞれを起点とした
        // (height-2*split_h) * width の長方形を削除し4つのL型のミキサーを作る

        // まずは，削除するセルも含めた大きな長方形をbaseに格納.
        int base_rect_h = height - split_h;
        int base_rect_w = 2 * width;
        // baseから4種類の長方形のそれぞれを引き，4つのL字型ミキサーを作成．
        int larger_deleteSY= split_h; 
        int larger_deleteSX= width; 
        int delete_rect_h = height-2*split_h;
        int delete_rect_w = width;
        if (base_rect_h>0 && base_rect_w>0 && delete_rect_h>0 && delete_rect_w>0 && 
                base_rect_h>delete_rect_h && base_rect_w>delete_rect_w) {
            pair<int, int> base_size = make_pair(base_rect_h, base_rect_w);
            pair<int, int> delete_start_info = make_pair(larger_deleteSY,larger_deleteSX);
            pair<int, int> delete_size = make_pair(delete_rect_h, delete_rect_w);
            vector<vector<pair<int, int>>> LShapes =
                _genLShapedMixer(base_size, delete_start_info, delete_size);
            for (auto lshape : LShapes) {
              if (count(res.begin(), res.end(), lshape) == 0)
                res.push_back(lshape);
            }
        }
      }
      // こちらは，split_hが1の時でも生成する．
      // (height+split_h) x
      // (width-split_h)の長方形から，(0,0),(0,h-1),(h-1,0),(h-1,h-1)のそれぞれを起点とした
      // split_h * (w-split_h-h) の長方形を削除し4つのL型のミキサーを作る

      // まずは，削除するセルも含めた大きな長方形をbaseに格納.
      int base_rect_h = height - split_h;
      int base_rect_w = width + split_h;
      // baseから4種類の長方形のそれぞれを引き，4つのL字型ミキサーを作成．
      int larger_deleteSY= width; 
      int larger_deleteSX= width; 
      int delete_rect_h= height - split_h - width; 
      int delete_rect_w= split_h;
      if (base_rect_h>0 && base_rect_w>0 && delete_rect_h>0 && delete_rect_w>0 && 
                base_rect_h>delete_rect_h && base_rect_w>delete_rect_w) {
            pair<int, int> base_size = make_pair(base_rect_h, base_rect_w);
            pair<int, int> delete_start_info = make_pair(larger_deleteSY,larger_deleteSX);
            pair<int, int> delete_size = make_pair(delete_rect_h, delete_rect_w);
            vector<vector<pair<int, int>>> LShapes =
                _genLShapedMixer(base_size, delete_start_info, delete_size);
            for (auto lshape : LShapes) {
              if (count(res.begin(), res.end(), lshape) == 0)
                res.push_back(lshape);
            }
        }
    }
  }
  return res;
}

json _TransformIntoJson(vector<vector<pair<int, int>>> shapes) {
  json res;
  int idx = 0;
  for (auto shape : shapes) {
    vector<json> OutputFormedData;
    for (auto ncoord : shape) {
      int y = get<0>(ncoord), x = get<1>(ncoord);
      map<string, int> res{{"y", y}, {"x", x}};
      json coord(res);
      OutputFormedData.push_back(coord);
    }
    res[to_string(idx)] = OutputFormedData;
    idx++; 
  }
  return res;
}

// vector<vector<pair<int,int>>をjson形式に変換.
json TransformIntoJson(vector<vector<pair<int, int>>> rects,
                       vector<vector<pair<int, int>>> lshapes) {
  json json_data;
  json_data["Rectangle"] = _TransformIntoJson(rects);
  json_data["LShape"] = _TransformIntoJson(lshapes);
  return json_data;
}

int main() {
    vector<int> MixerSize; 
    for(int bi=0;bi<size(base_mixer);bi++){
        for(int exp=0;pow(2,exp)*base_mixer[bi]<=MixerSizeMax;exp++)
            if(count(MixerSize.begin(),MixerSize.end(),pow(2,exp)*base_mixer[bi])==0)
                MixerSize.push_back(pow(2,exp)*base_mixer[bi]); 
    }
    sort(MixerSize.begin(),MixerSize.end()); 
    for (int mixersize : MixerSize) {
      cout<<mixersize<<endl; 
    vector<vector<pair<int, int>>> rect_mixer_shapes;
    // 長方形のミキサーを生成
    for (int length = floor(sqrt(mixersize)+0.01); length >= 2 ; length--) {
      if (mixersize % length == 0) {
        int shorter_side = length;
        int longer_side = mixersize / shorter_side;
        {
          // まずは，短辺が垂直方向の辺，長辺が水平方向の辺となる長方形から生成
          vector<pair<int, int>> used_cells;
          for (int i = 0; i < shorter_side; i++) {
            for (int j = 0; j < longer_side; j++) {
              pair<int, int> cell = make_pair(i, j);
              used_cells.push_back(cell);
            }
          }
          sort(used_cells.begin(),used_cells.end()); 
          rect_mixer_shapes.push_back(used_cells);
        }
        if (shorter_side != longer_side) {
          // 短辺が水平方向の辺，長辺が方向の辺となる長方形を生成
          vector<pair<int, int>> used_cells;
          for (int i = 0; i < longer_side; i++) {
            for (int j = 0; j < shorter_side; j++) {
              pair<int, int> cell = make_pair(i, j);
              used_cells.push_back(cell);
            }
          }
          sort(used_cells.begin(),used_cells.end()); 
          rect_mixer_shapes.push_back(used_cells);
        }
      }
    }
    for(auto rect:rect_mixer_shapes){
        for(auto coord:rect){
            int i = get<0>(coord), j = get<1>(coord);
            cout<<i<<","<<j<<" "; 
        }
        cout<<endl; 
    }
    // 長方形のミキサーを2つに切り離した後，切り離された小さい方を (そのまま or
    // 90度回転させた）のものを
    // base_height<base_widthなら上下方向，base_height>base_widthなら左右方向に持ってきて再結合することで，
    // L字型のミキサーを生成する．
    vector<vector<pair<int, int>>> LShaped_mixer_shapes;
    for (auto rect : rect_mixer_shapes) {
      pair<int, int> rect_size = SearchRectSize(rect);  
      vector<vector<pair<int, int>>> LShapedMixers = genLShapedMixer(rect_size);
      for (auto lshape : LShapedMixers) {
        sort(lshape.begin(),lshape.end()); 
        if (count(LShaped_mixer_shapes.begin(), LShaped_mixer_shapes.end(),lshape) == 0 && 
        count(rect_mixer_shapes.begin(), rect_mixer_shapes.end(),lshape) == 0) {
            LShaped_mixer_shapes.push_back(lshape);
        }
      }
    }
    cout<<"Lshape"<<endl; 
    for(auto rect:LShaped_mixer_shapes){
        for(auto coord:rect){
            int i = get<0>(coord), j = get<1>(coord);
            cout<<i<<","<<j<<" "; 
        }
        cout<<endl; 
    }
    if(mkdir(path.c_str(), 0777)==-1)
        cout<<path<<"を作成しようとしましたが，もうすでに同名のディレクトリが存在しました（特に問題ない場合は無視してください）.\n";
    json json_data = TransformIntoJson(rect_mixer_shapes, LShaped_mixer_shapes);
    // ファイルに書く
    string WriteFilePath = path + to_string(mixersize) + "mixer.json";
    ofstream writing_file;
    writing_file.open(WriteFilePath, ios::out);
    writing_file << json_data << endl;
    writing_file.close();
  }
  return 0;
}
