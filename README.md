# Create database with IPv4 addresses and its availability

Utility to checks ping, opened port 25 (smtp) and 80 (http) of all IPv4 addresses.
Depending on amount of workers works slow or fast.
For example it took 90 minutes to check 65535 addresses (/16 subnet) on single core Raspberry Pi 2 Model B+ with 50 workers (LA~1).

Important parameters are:
```
checking_params = { 'ping': 1, 'port25': 1, 'port80': 1 }
workers = 50
db = '/mnt/storage/share/projects/ips_db/data/ips_integer.db'
```

Connection timeouts also could be configured inside specific functions.
Currently storing into SQLite3 DB only supported.

