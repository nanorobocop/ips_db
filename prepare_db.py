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

def ips_generator():
    for ip in range(255*255*255*255):
        yield (ip,)

def prepare_db():
    import sqlite3
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ips_db (ip integer primary key, ping integer, port25 integer, port80 integer)''')
    conn.commit()
    c.executemany("""insert into ips_db ('ip') values (?)""", ips_generator())
    conn.commit()

prepare_db()

