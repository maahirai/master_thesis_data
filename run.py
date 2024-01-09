import subprocess 

# test.pyの上位モジュール
tree_height = [2,3,4]
# 1個のプロセスで実行する試薬合成の数
try_num = 10
# 生成するプロセス数
run_num = 20
for height in tree_height: 
    for idx in range(run_num):
        ResultFileName = str(height)+"_"+str(idx)
        redirect = '1>log'+ResultFileName+'.txt'
        ErrorRedirect = '2>&1'
        subprocess.Popen(['nohup','python3','test.py',str(height),str(try_num),ResultFileName,redirect,ErrorRedirect,'&'],stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
