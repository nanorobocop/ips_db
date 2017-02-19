#!/usr/bin/env python3

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# Table description:
#
# ips:
# ip: 16909060 (integer of 1.2.3.4)
# update_time: null| unix_timestamp
# ping: null|1
# port25: null|1
# port80: null|1
# 

from multiprocessing import Process, Queue, cpu_count
import time
import traceback

checking_params = { 'ping': 1, 'port25': 1, 'port80': 1 }
workers = 30
db = '/mnt/storage/share/projects/ips_db/data/ips_integer.db'

def ips_generator(cmax):
    for ip in range(cmax, 255*255*255*255):
        yield (ip,)

def num2ip(ip_num):
    oct3 = ip_num // ( 256 * 256 * 256 ) % 256
    oct2 = ip_num // ( 256 * 256 ) % 256
    oct1 = ip_num // ( 256 ) % 256
    oct0 = ip_num % 256
    return("{0}.{1}.{2}.{3}".format(oct3, oct2, oct1, oct0))

def prepare_db():
    import sqlite3
    conn = sqlite3.connect(db)
    c = conn.cursor()
    cmax = c.execute('''select ip from ips_db order by ip desc limit 1''').fetchone()[0]
    print("Current maximum IP num: {0}".format(cmax))
    print("Current maximum IP: {0}".format(num2ip(cmax)))
    c.execute('''CREATE TABLE IF NOT EXISTS ips_db (ip integer primary key, update_time integer, ping integer, port25 integer, port80 integer)''')
    conn.commit()
    try:
        c.executemany("""insert or ignore into ips_db ('ip') values (?)""", ips_generator(cmax))
    except:
        conn.commit()
    conn.commit()
    
def proc_connect_checker(TaskQueue, ResultQueue):
    import os, sys, time, datetime
    import socket
    try:
        while True:
            while os.getloadavg()[0] > cpu_count:
                time.sleep(5)
            to_check = TaskQueue.get()
            result = dict()
            result["ip"] = to_check
            if "ping" in checking_params and checking_params["ping"]:
                response = os.system("ping -c 1 -W 1 " + num2ip(to_check) + " >/dev/null 2>&1")
                if response == 0:
                    result["ping"] = 1
                else:
                    result["ping"] = 0
            if "port25" in checking_params and checking_params["port25"]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                res = sock.connect_ex((num2ip(to_check), 25))
                sock.close()
                if res == 0:
                    result["port25"] = 1
                else:
                    result["port25"] = 0
            if "port80" in checking_params and checking_params["port80"]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                res = sock.connect_ex((num2ip(to_check), 80))
                sock.close()
                if res == 0:
                    result["port80"] = 1
                else:
                    result["port80"] = 0
            result["update_time"] = int(datetime.datetime.timestamp(datetime.datetime.now()))
            ResultQueue.put(result)
    except KeyboardInterrupt:
        print("Checker Exception: " + traceback.format_exc())
        pass
    except:
        print("Checker Exception: " + traceback.format_exc())
        pass

def db_worker(TaskQueue, ResultQueue):
    import sqlite3, sys, time, datetime, os
    from pprint import pprint
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    stat_ips_processed = 0
    start_with = conn.execute('''select ip from ips_db order by ip desc limit 1''').fetchone()[0]
    print("Starting with IP: {0}".format(num2ip(start_with)))
    time_delta = datetime.timedelta(minutes=5)
    time_a = datetime.datetime.utcnow() - time_delta
    time_start = datetime.datetime.utcnow() 
    try:
        while True:
            time_b = datetime.datetime.utcnow()
            if (time_b - time_a > time_delta):
                print("Datetime: {0}".format(datetime.datetime.now().isoformat(' ')))
                cmax = conn.execute('''select ip from ips_db order by ip desc limit 1''').fetchone()[0]
                print("Current maximum IP: {0}".format(num2ip(cmax)))
                print("TaskQueue: {0}; ResultQueue: {1}".format(TaskQueue.qsize(), ResultQueue.qsize()))
                print("IPs processed: {0}".format(stat_ips_processed))
                if (time_b - time_start).seconds != 0:
                    print("Speed from start: {0} IPs/min".format(stat_ips_processed / (time_b - time_start).seconds / 60)) 
                print("DB size: {0:.2f} MB".format(os.stat(db).st_size / 1024 / 1024))
                print()
                time_a = datetime.datetime.utcnow()
            if TaskQueue.qsize() < 5000:
                for i in range(start_with, start_with+10000):
                     TaskQueue.put(i)
                start_with += 10001
            if ResultQueue.qsize() > 1000:
                values = list()
                while ResultQueue.qsize() > 0:
                    result = ResultQueue.get()
                    values.append( (result["ip"], result["update_time"], result["ping"], result["port25"], result["port80"]) )
                stat_ips_processed_prev = stat_ips_processed
                stat_ips_processed += len(values)
                with conn:
                    conn.executemany('''insert or replace into ips_db(ip, update_time, ping, port25, port80) values (?, ?, ?, ?, ?)''', values)
            time.sleep(30)
    except:
        print("Exception: " + traceback.format_exc())
        print("DB worker exception")
        conn.close()
    conn.close()
    print("DB worker finished")

if __name__ == '__main__':
    #prepare_db()
    cpu_count = cpu_count()
    TaskQueue = Queue()
    ResultQueue = Queue()
    db_worker = Process(target=db_worker, args=(TaskQueue, ResultQueue,))
    db_worker.start()
    connect_checker = list()
    for i in range(workers):
        connect_checker.append(Process(target=proc_connect_checker, args=(TaskQueue, ResultQueue,)))
        connect_checker[i].start()
    try:
        db_worker.join()
        for i in range(workers):
            connect_checker[i].join()
    except KeyboardInterrupt:
        print("Main process Exception: " + traceback.format_exc())
        print("Main process finished")
    print("Main process finished")
