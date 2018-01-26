#!/usr/bin/python

'''
A script that parses stability session logs
'''

import os
import re
import logging
import diamond.collector
from diamond.metric import Metric

logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')

class StabilityCollector(diamond.collector.Collector):

    def __init__(self, config=None, handlers=[], name=None, configfile=None):
        diamond.collector.Collector.__init__(self, config=config,
        handlers=handlers, name=name, configfile=configfile)
        self.ingest_dir = '-Ingested'
        self.scanner_location = 'Harvard/Northwest/TestBay2' ##for testing
        self.base_dir = '/ncf/dicom-backups/_Scanner'
        self.logfiles = [os.path.join(self.base_dir,self.scanner_location,'Stability_20180110T165545.txt')]
        fh = logging.FileHandler(os.path.join(self.base_dir,self.scanner_location,'graphite.log'))
        logger.addHandler(fh)

    def dotlocation(self):
        return self.scanner_location.replace('/','.')
    
    def new_logfiles(self, logdir):
        '''
        updates self.logfiles with new files, returns 'True' if new files exist
        '''
        newfiles = [os.path.join(logdir,file) for file in os.listdir(logdir) if 'Stability' in file]
        if newfiles:
            self.logfiles = newfiles
            return True
        else:
            return False
        
    def collect(self):
        if not self.new_logfiles(os.path.join(self.base_dir,self.scanner_location)):
            logger.info('no new files found')
            return
        for file in self.logfiles:
            ctime = os.path.getctime(file)
            with open(file, 'r') as input:
                first_line = input.readline()
                try:
                    channel_no = re.match('Stability configuration: 16 slices, 500 measurements, (32|48) channels\n', first_line).group(1)
                    coil = self._resolve_channels(channel_no)
                except AttributeError as e:
                    logger.info('error {} for file {}, line {}'.format(e,file,first_line))
                    continue
                lines = input.read()
                # divide document into sections
                sections = re.findall('Stability (\w+) results:\n\nslice#(.*)\n 1(.*)\n 2(.*)\n 3(.*)\n 4(.*)\n 5(.*)\n 6(.*)\n 7(.*)\n 8(.*)\n 9(.*)\n10(.*)\n11(.*)\n12(.*)\n13(.*)\n14(.*)\n15(.*)\n16(.*)\n', lines, re.MULTILINE)
                # parse each section
                for section in sections:
                    section = list(section)
                    section_type = section.pop(0)
                    header = section.pop(0)
                    header_list = header.split()
                    section = [r.split() for r in section]
                    # tableType.columnName.rowNum value
                    metricnames = [('{}.{}.{}.{}.{}'.format(self.dotlocation(),coil,section_type,header_list[i],s+1),v) for s,r in enumerate(section) for i,v in enumerate(r)]
                    for metricname,value in metricnames:
                        self.publish(metricname,value,timestamp=ctime)
            # mark file as ingested
            head,tail = os.path.split(file)
            new_file = os.path.join(head,self.ingest_dir,tail)
            if not os.path.exists(os.path.join(head,self.ingest_dir):
                    os.mkdir(os.path.join(head,self.ingest_dir))
            os.rename(file,new_file)
            logger.info('processed {} with coil {}'.format(file,coil))

    def _resolve_channels(self, channel):
        channelmap = {
            '32': '32',
            '48': '64'
            }
        return channelmap[channel]

    def publish(self, name, value, raw_value=None, precision=0,
               metric_type='GAUGE', instance=None, timestamp=None):
        '''
        Publish a metric with the given name (monkey patch for creating the metric with a timestamp)
        '''
        # Check whitelist/blacklist
        if self.config['metrics_whitelist']:
            if not self.config['metrics_whitelist'].match(name):
                return
        elif self.config['metrics_blacklist']:
            if self.config['metrics_blacklist'].match(name):
                return
        
        # Get metric Path
        path = self.get_metric_path(name, instance=instance)
        
        # Get metric TTL
        ttl = float(self.config['interval']) * float(
            self.config['ttl_multiplier'])
        
        # Create Metric
        try:
            metric = Metric(path, value, raw_value=raw_value, timestamp=timestamp,
                            precision=precision, host=self.get_hostname(),
                            metric_type=metric_type, ttl=ttl)
        except DiamondException:
            self.log.error(('Error when creating new Metric: path=%r, '
                            'value=%r'), path, value)
            raise
        
        # Publish Metric
        self.publish_metric(metric)
        #print(metric) ##for testing

if __name__ == '__main__':
    instance = StabilityCollector()
    instance.collect()

