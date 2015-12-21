# -*- coding: utf-8 -*-
# coding=utf-8


import time
import re
import os
import datetime, paramiko

# nutcracker文件位置
_nutcracker_file = "/etc/nutcracker/nutcracker.yml"
# _nutcracker_file = "alpha.xml"
# 启动sentinel
_redis_sentinel_start = "redis-sentinel /export/sentinel/sentinel.conf"
# 关闭sentinel
_redis_sentinel_end = "kill -s 9 `ps -aux | grep redis-sentinel | awk '{print $2}'`"
# 启动nutcracker
_redis_nutcracker_start = "nutcracker -d -p /var/log/nutcracker.pid -c " + _nutcracker_file
# 关闭nutcracker
_redis_nutcracker_end = "cat /var/log/nutcracker.pid |xargs kill -9 && rm -rf /var/log/nutcracker.pid"
# 查看当前主从信息
_redis_sentinel_info = "redis-cli -p 26379 info Sentinel|grep status"
_redis_name_command="redis-cli -p 26379 info Sentinel |awk -F\",\" \'/address/ {print $1}\'|awk -F\":name=\" '{printf(\"%s,\",$2)}'"


# 检查配置时间，单位秒
check_time = 5

_redis_server = None
# 检查各个进程的存活情况


redis_sentinel_cehck = "netstat -antp|awk  '/26379/ &&  /LISTEN/'"
redis_nutcracker_check = "netstat -antp|awk  '/22121/ &&  /LISTEN/'"

host=None
# host = {}
# host["ip"] = "10.237.xx.xx"
# host["name"] = "root"
# host["password"] = "xxxxxxx"
# host["port"] = 22


def ssh_pkey_pwd(hostname, username, password, privatekey=None, port=22):
    paramiko.util.log_to_file('pkey.log')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password, key_filename=privatekey)
    return ssh


if host is None or {}:
    _redis_server = None
else:
    _redis_server = ssh_pkey_pwd(host["ip"], host["name"], host["password"], port=host["port"])


def run_command(check_command):
    if _redis_server is None:
        command_result = os.popen(check_command).read()
    else:
        command_result = _redis_server.exec_command(check_command)[1].read()
    return command_result

def get_reids_names():
    _redis_master_names=re.split(",", run_command(_redis_name_command))
    key=len(_redis_master_names)-1
    del _redis_master_names[key]
    return tuple(_redis_master_names)
_redis_master_name=get_reids_names()


def check_redis_sentinel():
    redis_sentinel_status = run_command(redis_sentinel_cehck)
    if redis_sentinel_status == '':
        print redis_sentinel_status
        log("[ERROR]", "redis_sentinel is not running,start redis_sentinel")
        redis_sentinel_status = run_command(_redis_sentinel_start)
        print redis_sentinel_status
        if redis_sentinel_status is not '':
            log("[INFO]", "redis_sentinel Start success!")
        else:
            print datetime.datetime.now(), "INFO redis_sentinel_cehck status is OK!"
    else:
        log("[INFO]", "redis_sentinel is running")


def check_nutcracker_status():
    # nutcracker_status=os.popen(redis_nutcracker_check).read()
    nutcracker_status = run_command(redis_nutcracker_check)
    if nutcracker_status == '':
        print datetime.datetime.now(), "ERROR redis nutcracker is not running,auto start nutcracker"
        run_command(_redis_nutcracker_start)
        if nutcracker_status != 0 :
            print time.ctime(), "redis nutcracker start succsess"


def log(loglevel, loginfo):
    time_info = time.ctime()
    print time_info, loglevel, loginfo


class __tw_monit:
    _redis_master_names = None
    _redis_master_info = None

    def __init__(self, redis_master_name):
        self._redis_master_names = redis_master_name
        # self._redis_sentinel_info=self.redis_master()
        #self.redis_master() = self.redis_master()

    def get_sentinel_info(self, sentinel_info):
        if self._redis_master_names is not None:
            for master_name in self._redis_master_names:
                master_name_line = re.findall("name=" + master_name + ",", sentinel_info)
                redis_master_name = None
                if master_name_line is not None:
                    for x in master_name_line:
                        redis_master_name = str.replace(x, "name=", "").replace(",", "")
                    if redis_master_name is None:
                        continue
                    master_ip = re.findall("address=[\w\.:]+", sentinel_info)
                    redis_master_ip = None
                    if master_ip is not None:
                        for x in master_ip:
                            redis_master_ip = str.replace(x, "address=", "")
                        if redis_master_ip is None:
                            continue
                        redis_master = redis_master_ip + " " + redis_master_name
                        return {"redis_master": redis_master, "redis_master_ip": redis_master_ip,
                                "redis_master_name": redis_master_name}
            return None

    def getfile(self, filename, mode="r+"):
        if _redis_server is None:
            file = open(filename, "r+")
        else:
            redis_sftp = _redis_server.open_sftp()
            file = redis_sftp.open(filename, "r+")
        return file

    def check_nutcracker(self):
        check_nutcracker_status()
        f = self.getfile(_nutcracker_file)
        file = f.read()
        if self.redis_master() != '':
            tmp_file = file
            for redis_master in self.redis_master():
                # 匹配10.237.81.102:7000:1 master
                if redis_master is None: continue;
                config = re.findall("\d+\.\d+\.\d+\.\d+:\d+\:\d+\s*" + redis_master["redis_master_name"] + "\s*\"",file)
                if config is []:
                    continue
                config_array = re.split(':|\s*', config[0])
                if len(config_array) < 4:
                    continue
                # print nutcracker_file+":"+config[0]
                config_re = {"config_redis": config_array[0] + ":" + config_array[1], "config_right": config_array[2],
                             "config_name": config_array[3]}
                config_now = config_re['config_redis'] + config_re['config_name']
                 # 备份文件
                tmp_file = str(tmp_file).replace(config[0],redis_master["redis_master_ip"] + ":" + config_re["config_right"] + " " +

                            redis_master["redis_master_name"] + "\"")
            f.close()
            if tmp_file != file:
                print(time.ctime(), "[INFO]"+"cp "+_nutcracker_file+"{,."+time.strftime("%Y%m%d-%H%M%S")+"}")
                run_command("cp "+_nutcracker_file+"{,."+time.strftime("%Y%m%d-%H%M%S")+"}")
                # 替换新文件
                f = self.getfile(_nutcracker_file, "w+")
                f.write(tmp_file)
                f.close()
                return 1
            return 0

    def redis_master(self):
        # sentinel_info=os.popen(_redis_sentinel_info).read()
        sentinel_info = run_command(_redis_sentinel_info)
        # master0:name=master1,status=ok,address=10.160.0.8:6370,slaves=2,sentinels=1
        sentinel_info_list = re.findall(
            "master\d+:name=\w+,status=\w+,address=\d+\.\d+\.\d+\.\d+:\d+,slaves=\d+.sentinels=\d+", sentinel_info)
        redis_list = []
        if (sentinel_info_list is not None):
            for s in sentinel_info_list:
                redis_list.append(self.get_sentinel_info(s))
        return redis_list

    def print_master_ip(self):
        if self.redis_master() != '':
            for _redis_info in self.redis_master():
                if _redis_info is None: continue
                print time.ctime(), "[INFO] The redis master ip is---->", _redis_info["redis_master_ip"]

print "---" * 20
log("[INFO]", "Start to monit redis status !")
# 检查Redis、Sentinel、nutcracker
log("[INFO]", "check redis_sentinel !!!")

while (True):
    check_redis_sentinel()
    _redis = __tw_monit(get_reids_names())
    #_redis.print_master_ip()
    time.sleep(check_time)              #程序休息10秒
    print "==="*20 
    # 检查redis_sentinel 以及TwemProxy
    file_info = 5
    try:
        file_info = _redis.check_nutcracker()
    except:
        file_info = 5
    # 判断是否需要重启nutcracker
    if (file_info == 5):
        print time.ctime(), "[ERROR] Can't get nutcracker information;", _redis.check_nutcracker()
        break
    if (file_info == 0):
        _redis.print_master_ip()
        continue
    else:
        log("[INFO]", "restart nutcracker")
        run_command(_redis_nutcracker_end)
        time.sleep(1)
        run_command(_redis_nutcracker_start)
        log("INFO", "restart nutcracker over！")
        _redis.print_master_ip()