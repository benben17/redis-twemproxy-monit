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
A more detailed explanation can be found on an article on my site.

