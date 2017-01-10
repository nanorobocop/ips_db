#!/usr/bin/env python3

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# Table description:
#
# ips:
# ip: 1.2.3.4
# ping: null|1
# connect_80: null|1
# connect_25: null|1
# 

from multiprocessing import Process, Queue
import time

workers = 25 
checking_params = { "ping": 1, "port25": 1, "port80": 1 }
run_from_start = 1

class IP:

    def __init__(self, ip, from_db=0):
        if from_db:
            self.ip = self.from_db(ip)
        else:
            self.ip = ip
        self.to_db = self.to_db()
        self.octet = self.octet()

    def octet(self):
        return [int(i) for i in self.ip.split('.')]

    def from_db(self,string):
        octet_with_zeroes = string.split('.')
        return '.'.join([str(int(i)) for i in octet_with_zeroes.split('.')])

    def to_db(self):
        ip_octet = self.ip.split('.')
        ip_octet_to_db = list()
        for i in ip_octet:
            if int(i) < 10:
                ip_octet_to_db.append('00'+i)
            elif int(i) < 100:
                ip_octet_to_db.append('0'+i)
            else:
                ip_octet_to_db.append(i)
        return '.'.join(ip_octet_to_db)
    
    def nextip(self):
        nextip_octet = self.octet
        nextip_octet[3] += 1
        if self.octet[3] > 255:
            nextip_octet[3] = 0
            nextip_octet[2] += 1
        if self.octet[2] > 255:
            nextip_octet[2] = 0
            nextip_octet[1] += 1
        if self.octet[1] > 255:
            nextip_octet[1] = 0
            nextip_octet[0] += 1
        if self.octet[0] > 255:
            nextip_octet = None
            return None
        return '.'.join([str(i) for i in nextip_octet])

def IP_class_test():
    ip = IP('1.2.3.4')
    if ip.to_db != '001.002.003.004':
        print("Self test FAILED: "+ip.to_db)
        raise SystemExit(1)
    ip = IP('0.1.22.255')
    if ip.to_db != '000.001.022.255':
        print("Self test FAILED: "+ip.to_db)
        raise SystemExit(1)
    print("Self test OK")

IP_class_test()

def prepare_db():
    import sqlite3
    conn = sqlite3.connect('/mnt/storage/share/projects/ips_db/data/ips.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ips_db (ip text, ping integer, port25 integer, port80 integer)''')
    conn.commit()
    
def proc_task_creator(TaskQueue):
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
    ips_per_worker = 1
    import sqlite3
    conn = sqlite3.connect('/mnt/storage/share/projects/ips_db/data/ips.db')
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute('''SELECT * from ips_db order by ip desc limit 1''')
    last_ip = c.fetchone()
    conn.close()
    if last_ip == None:
        print("Getting last ip: None (db probably empty)")
        to_queue = IP('1.1.1.1').ip
    else:
        print("Getting last ip: {0}".format(last_ip))
        to_queue = IP(IP(last_ip["ip"]).nextip()).ip
    print("Starting with: {}".format(to_queue))
    while True:
        queue_size = TaskQueue.qsize()
        #print("Task Queue size: {0}".format(queue_size))
        if queue_size < 100:
            #print("Put to TaskQueue: {}".format(to_queue))
            TaskQueue.put(to_queue)
            to_queue = IP(to_queue).nextip()
        else:
            time.sleep(1)
    

def proc_connect_checker(TaskQueue, ResultQueue):
    import os
    import socket
    try:
        while True:
            to_check = TaskQueue.get()
            #print("Get from TaskQueue: {0}".format(to_check))
            result = dict()
            result["ip"] = to_check
            if "ping" in checking_params and checking_params["ping"]:
                response = os.system("ping -c 1 -W 1 " + to_check + " >/dev/null")
                if response == 0:
                    result["ping"] = 1
                else:
                    result["ping"] = 0
            if "port25" in checking_params and checking_params["port25"]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                res = sock.connect_ex((to_check, 25))
                if res == 0:
                    result["port25"] = 1
                else:
                    result["port25"] = 0
            if "port80" in checking_params and checking_params["port80"]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                res = sock.connect_ex((to_check, 80))
                if res == 0:
                    result["port80"] = 1
                else:
                    result["port80"] = 0
            #print("Put to ResultsQueue: {0}".format(result))
            ResultQueue.put(result)
    except KeyboardInterrupt:
        pass
    except:
        pass

def db_worker(ResultQueue):
    import sqlite3, sys
    collect_inserts = 100
    conn = sqlite3.connect('/mnt/storage/share/projects/ips_db/data/ips.db', timeout=120)
    cur = conn.cursor()
    while True:
        #print("ResultQueue size: {0}".format(ResultQueue.qsize()))
        result = ResultQueue.get()
        #print("Get from ResultQueue: {0}".format(result))
        inserts = 0
        try:
            #while inserts < collect_inserts:
            #    cur.execute('''insert into ips_db(ip, ping, port25, port80) values (?,?,?,?)''', [IP(result["ip"]).to_db, result["ping"], result["port25"], result["port80"]])
            #    inserts += 1
            #conn.commit()
            with conn:
                conn.execute('''insert into ips_db(ip, ping, port25, port80) values (?,?,?,?)''', [IP(result["ip"]).to_db, result["ping"], result["port25"], result["port80"]])
        except sqlite3.OperationalError:
            print("Exception: {0}".format(sys.exc_info()))
            pass
        except:
            print("Exception: {0}".format(sys.exc_info()))
            conn.commit()
            conn.close()

def proc_stats(TaskQueue, ResultsQueue):
    import sqlite3, os, sys, datetime
    try:
        while True:
            print("Datetime: {0}".format(datetime.datetime.now().isoformat(' ')))
            print("TaskQueue: {0}; ResultQueue: {1}".format(TaskQueue.qsize(), ResultQueue.qsize()))
            #conn = sqlite3.connect('/mnt/storage/share/projects/ips_db/data/ips.db')
            #cur = conn.cursor()
            #cur.execute('''select count(1) from ips_db''')
            #print("ips_db items: {0}".format(cur.fetchone()[0]))
            #cur.execute('''select ip from ips_db order by ip desc limit 1''')
            #print("Latest ip: {0}".format(cur.fetchone()[0]))
            print("DB size: {0:.2f} MB".format(os.stat('/mnt/storage/share/projects/ips_db/data/ips.db').st_size / 1024 / 1024))
            print("")
            time.sleep(60)
    except:
        print("Exception: {0}".format(sys.exc_info()))
        conn.close()


if __name__ == '__main__':
    prepare_db()
    TaskQueue = Queue()
    ResultQueue = Queue()
    task_creator = Process(target=proc_task_creator, args=(TaskQueue,))
    task_creator.start()
    connect_checker = list()
    for i in range(workers):
        connect_checker.append(Process(target=proc_connect_checker, args=(TaskQueue, ResultQueue,)))
        connect_checker[i].start()
    db_workder = Process(target=db_worker, args=(ResultQueue,))
    db_workder.start()
    stats = Process(target=proc_stats, args=(TaskQueue, ResultQueue,))
    stats.start()
