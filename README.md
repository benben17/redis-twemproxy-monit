Redis-Twemproxy monit
Intro

A simple python script which will connect to Redis-Sentinel and monitor for the master-change event. It will then update TwemProxy (nutcracker) and restart it.

The basic idea behind it, is so that you have redundancy in your redis shards, when your master dies, a slave is promoted to Master by Redis Sentinel, and then this agent updates your TwemProxy config to point to the new master.

            TwemProxy
        __________|__________
        |                   |
    Master1             Master N
Slave1  SlaveN      Slave 1 Slave N

            Redis Sentinel

脚本运行：
nohup redis-twemproxy-monit.py &

配置文件路径
TwemProxy  /etc/nutcracker/nutcracker.yml

1、本机redis_Sentinel监控 ,注释以下几行
host={}
host["ip"] = "10.10.10.1"
host["name"] = "******"
host["password"] = "******"
host["port"] = 22
2、监控远程redis_Sentinel
配置对应的服务器信息即可

脚本运行：
nohup redis-twemproxy-monit.py &