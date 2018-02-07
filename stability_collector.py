#!/usr/bin/python

'''
A script that parses stability session logs
'''

import os
import re
import logging
import time
import diamond.collector
from diamond.metric import Metric

class StabilityCollector(diamond.collector.Collector):

    def __init__(self, config=None, handlers=[], name=None, configfile=None):
        diamond.collector.Collector.__init__(self, config=config,
        handlers=handlers, name=name, configfile=configfile)
        self.ingest_dir = 'Ingested'
        self.scanner_location = 'Harvard/Northwest/TestBay8'
        self.base_dir = '/ncf/dicom-backups/_Scanner'
        ##self.scanner_location = 'sample'
        ##self.base_dir = '/Users/hhoke1/mri_stability_diamondcollector'
        # default location of files to process
        self.logfiles = [os.path.join(self.base_dir,self.scanner_location,'Stability_20180124T133423.txt')]
        # set up logging
        self.log.setLevel(logging.INFO)
        fh = logging.FileHandler(os.path.join(self.base_dir,self.scanner_location,'graphite.log'))
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh.setFormatter(formatter)
        self.log.addHandler(fh)

    def dotlocation(self):
        return self.scanner_location.replace('/','.')

    def new_logfiles(self, logdir):
        '''
        updates self.logfiles with new files, returns 'True' if new files exist
        '''
        newfiles = [os.path.join(logdir,f) for f in os.listdir(logdir)
                if f[0:10] == 'Stability_' ]
        if newfiles:
            self.logfiles = newfiles
            return True
        else:
            return False

    def collect(self):
        if not self.new_logfiles(os.path.join(self.base_dir,self.scanner_location)):
            self.log.info('no new files found')
            return
        for f in self.logfiles:
            epoch = self.parse_epoch(f)
            with open(f, 'r') as input:
                first_line = input.readline()
                try:
                    channel_no = re.match('Stability configuration: 16 slices, 500 measurements, (32|48) channels\n', first_line).group(1)
                    coil = self._resolve_channels(channel_no)
                except AttributeError as e:
                    self.log.info('error {} for file {}, line {}'.format(e,f,first_line))
                    continue
                lines = input.read()
                # divide document into sections
                sections = re.findall('Stability (\w+) results:\n\nslice#(.*)\n 1(.*)\n 2(.*)\n 3(.*)\n 4(.*)\n 5(.*)\n 6(.*)\n 7(.*)\n 8(.*)\n 9(.*)\n10(.*)\n11(.*)\n12(.*)\n13(.*)\n14(.*)\n15(.*)\n16(.*)\n', lines, re.MULTILINE)
                # parse each section
                for section in sections:
                    section = list(section)
                    section_type = section.pop(0)
                    header = section.pop(0)
                    # to conform to graphic metric name standards
                    header_list = [c.replace('[%]','pct') for c in header.split()]
                    header_list = [re.sub(r'\W+', '', s) for s in header_list]
                    section = [r.split() for r in section]
                    # tableType.columnName.rowNum value
                    metricnames = [('{}.{}.{}.{}.{}'.format(self.dotlocation(),coil,section_type,header_list[i],s+1),v) for s,r in enumerate(section) for i,v in enumerate(r)]
                    self.publish(metricnames[0][0],metricnames[0][1],timestamp=epoch,dry_run=True)
                    for metricname,value in metricnames:
                        self.publish(metricname,value,timestamp=epoch)
            # mark file as ingested
            head,tail = os.path.split(f)
            new_file = os.path.join(head,self.ingest_dir,tail)
            if not os.path.exists(os.path.join(head,self.ingest_dir)):
                    os.mkdir(os.path.join(head,self.ingest_dir))
            os.rename(f,new_file)
            self.log.info('processed {} with coil {}'.format(f,coil))

    def _resolve_channels(self, channel):
        channelmap = {
            '32': '32',
            '48': '64'
            }
        return channelmap[channel]

    def parse_epoch(self, s):
        date_time = re.search('Stability_([0-9]{8}T[0-9]{6}).txt',s).group(1)
        pattern = '%Y%m%dT%H%M%S'
        epoch = int(time.mktime(time.strptime(date_time, pattern)))
        assert(epoch)
        return epoch

    def publish(self, name, value, raw_value=None, precision=2,
               metric_type='GAUGE', instance=None, timestamp=None, dry_run=False):
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
        if dry_run:
            self.log.info('dry run sample: {}'.format(metric))
        else:
            self.publish_metric(metric)

if __name__ == '__main__':
    instance = StabilityCollector()
    instance.collect()
