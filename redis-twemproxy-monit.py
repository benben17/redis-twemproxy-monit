# -*- coding: utf-8 -*-
#coding=utf-8
import sys
import re
import time,datetime
import paramiko


#nutcracker文件位置
nutcracker_file="/etc/nutcracker.yml"
#启动sentinel
redis_sentinel_start="nohup redis-sentinel /root/redis-3.0.3/sentinel.conf &"
#关闭sentinel
redis_sentinel_end="kill -s 9 `ps -aux | grep redis-sentinel | awk '{print $2}'`"
#启动nutcracker
redis_nutcracker_start="nutcracker -d -p  /var/log/nutcracker.pid -c "+nutcracker_file
#关闭nutcracker
redis_nutcracker_end="cat /var/log/nutcracker.pid |xargs kill -9 && rm -rf /var/log/nutcracker.pid"
#查看当前主从信息
redis_sentinel_info="redis-cli -p 26379 info Sentinel|grep status"

#检查配置时间，单位秒
check_time=10

#配置相关服务器信息
host={}
host["ip"]="10.237.81.xxx"
host["name"]="****
host["password"]="*******"
host["port"]=22
#检查各个进程的存活情况
redis_check="netstat -antp|awk  '/7000/ &&  /LISTEN/'"
redis_sentinel_cehck="netstat -antp|awk  '/26379/ &&  /LISTEN/'"
redis_nutcracker_check="netstat -antp|awk  '/22121/ &&  /LISTEN/'"
#redis相关信
print "==="*30

def log(loglevel,loginfo):
    time_info=datetime.datetime.now()
    print time_info,loglevel,loginfo

def ssh_pwd(hostname,username,password,port=22):
    paramiko.util.log_to_file('pwd.log')
    ssh=paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname,port,username,password)
    return ssh
redis_server=ssh_pwd(host["ip"],host["name"],host["password"],host["port"])

def check_redis_sentinel(redis_server):
    redis_sentinel_status=redis_server.exec_command(redis_sentinel_cehck)[1].read()
    if redis_sentinel_status is "":
        log("ERROR", "redis_sentinel is not running,start redis_sentinel")
        redis_server.exec_command(redis_sentinel_start)
        if redis_sentinel_status is not "":
           log("INFO", "redis_sentinel Start success!")
    # else:
    #    print datetime.datetime.now(),"INFO redis_sentinel_cehck status is OK!"
def check_nutcracker_status(redis_server):
    nutcracker_status=redis_server.exec_command(redis_nutcracker_check)[1].read()
    if nutcracker_status is "":
        print datetime.datetime.now(),"ERROR redis nutcracker is not running,auto start nutcracker"
        redis_server.exec_command(redis_nutcracker_start)
        if nutcracker_status is not "":
            print datetime.datetime.now(),"redis nutcracker start succsess"

def get_sentinel_info(sentinel_info):
    master_name=re.findall("name=\w+",sentinel_info)
    redis_master_name=None
    for x in master_name:
        redis_master_name= str.replace(x,"name=","")
    if redis_master_name is None:
        return None
    master_ip=re.findall("address=[\w\.:]+",sentinel_info)
    redis_master_ip=None
    for x in master_ip:
        redis_master_ip= str.replace(x,"address=","")
    if redis_master_ip is None:
        return None
    redis_master=redis_master_ip+" "+redis_master_name
    return {"redis_master":redis_master,"redis_master_ip":redis_master_ip,"redis_master_name":redis_master_name}

def check_nutcracker(ssh,redis_master):
    check_nutcracker_status(redis_server)
    redis_sftp=ssh.open_sftp()
    file=redis_sftp.open(nutcracker_file).read()
    #匹配10.237.81.102:7000:1 master
    config=re.findall("\d+\.\d+\.\d+\.\d+:\d+"+":\d+\s+"+redis_master["redis_master_name"]+"\s*\"",file)
    if config is []:
        return None
    config_array= re.split("[:|\s]",config[0])
    if len(config_array) <4:
        return None
    #print nutcracker_file+":"+config[0]
    config_redis={"config_redis":config_array[0]+":"+config_array[1],"config_right":config_array[2],"config_name":config_array[3]}
    #干掉空格和双引号与权重进行比较是否相同
    if (config_redis["config_redis"]+config_redis["config_name"].replace("\"","")).replace(" ","") == redis_master["redis_master"].replace(" ",""):
        return "success"
    #备份文件
    f=open(sys.path[0]+"/nutcracker_file","w")
    f.write(str(file))
    f.close()
    redis_sftp.put(sys.path[0]+"/nutcracker_file",nutcracker_file+"_"+time.strftime("%Y%m%d-%H%M%S"))
    #替换新文件
    f=open(sys.path[0]+"/nutcracker_file","w")
    f.write(str(file).replace(config[0],redis_master["redis_master_ip"]+":"+config_redis["config_right"]+" "+redis_master["redis_master_name"]+"\""))
    f.close()
    redis_sftp.put(sys.path[0]+"/nutcracker_file",nutcracker_file)
    return "wait_for_restart"

def redis_master():
    sentinel_info=redis_server.exec_command(redis_sentinel_info)[1].read()
    return get_sentinel_info(sentinel_info)

log("INFO","Start to monit redis status !")
#检查Redis、Sentinel、nutcracker
log("INFO","check redis_sentinel !!!")
check_redis_sentinel(redis_server)
print "The redis master ip is",redis_master()["redis_master_ip"]
while(True):
    time.sleep(check_time)              #程序休息10秒
    check_redis_sentinel(redis_server)
    #检查redis_sentinel 以及TwemProxy 
    file_info=None
    try:
        file_info=check_nutcracker(redis_server,redis_master())
    except:
        file_info=None
    #判断是否需要重启nutcracker
    if file_info is None:
        print "ERROR Can't get nutcracker infomation;",check_nutcracker(redis_server,redis_master())
        break
    if file_info == "success":
        continue
    if file_info =="wait_for_restart":
        log("INFO","restart nutcracker")
        redis_server.exec_command(redis_nutcracker_end)
        time.sleep(2)
        redis_server.exec_command(redis_nutcracker_start)
        log("INFO","restart nutcracker over！")
        print "The redis master ip is",redis_master()["redis_master_ip"]