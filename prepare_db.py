#!/usr/bin/env python3

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# DESCRIPTION: Just prepare DB with IPs from 0 to 255*255*255*255 in Integer format

# Table description:
#
# ips:
# ip: 1.2.3.4
# ping: null|1
# connect_80: null|1
# connect_25: null|1
# 

checking_params = { "ping": 1, "port25": 1, "port80": 1 }
db = '/mnt/storage/share/projects/ips_db/data/ips_integer.db'

def ips_generator(cmax):
    for ip in range(cmax, 255*255*255*255):
    #for ip in range(255*255):
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
    c.execute('''CREATE TABLE IF NOT EXISTS ips_db (ip integer primary key, ping integer, port25 integer, port80 integer)''')
    conn.commit()
    try:
        c.executemany("""insert or ignore into ips_db ('ip') values (?)""", ips_generator(cmax))
    except:
        conn.commit()
    conn.commit()

prepare_db()

