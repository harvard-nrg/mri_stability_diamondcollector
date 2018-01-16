## progress

Parsing should be working. When tested, this prints strings of the desired format.

## todos

Want to make sure this actually works as a diamond collector. Currently output just looks like:

```
nrgadmin@ncfservice01:~$ diamond -c /ncf/nrg/etc/diamond/diamond.conf -f  -l
1516131839.18   [MainProcess:15533:INFO]        Changed UID: 5147 () GID: 5014 ().
1516131842.0    [MainProcess:15533:DEBUG]       metric_queue_size: 16384
1516131842.01   [MainProcess:15533:DEBUG]       Loading Handler diamond.handler.graphite.GraphiteHandler
1516131842.12   [MainProcess:15533:DEBUG]       GraphiteHandler: Established connection to graphite server graph.rc.fas.harvard.edu:200
3.
1516131842.12   [MainProcess:15533:DEBUG]       Loading Handler diamond.handler.archive.ArchiveHandler
1516131842.97   [Handlers:15546:DEBUG]  Starting process Handlers
```

and hangs there. Currently there are no custom process handlers, so unclear what is causing this.
