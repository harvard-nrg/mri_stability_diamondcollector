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
        self.scanner_locations = ['sample','sample2']
        self.base_dir = '/ncf/cnl06/nrgadmin/collector_test/mri_stability_diamondcollector/'
        self.search_dirs = {scanloc:os.path.join(self.base_dir,scanloc) for scanloc in self.scanner_locations}
        self.slices = 16
        self.measurements = 500
        # default location of files to process
        self.logfiles = []
        # set up logging
        self.log.setLevel(logging.INFO)
        for scanner_location in self.scanner_locations:
            fh = logging.FileHandler(os.path.join(self.base_dir,self.scanner_location,'diamond_collector.log'))
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            fh.setFormatter(formatter)
            self.log.addHandler(fh)

    def dotlocation(self,scanner_location):
        return scanner_location.replace('/','.')

    def new_logfiles(self, logdir):
        '''
        updates self.logfiles with new files, returns 'True' if new files exist
        '''
        newfiles = [os.path.join(logdir,f) for f in os.listdir(logdir)
                if f[0:10] == 'Stability_' ]
        if newfiles:
            self.log.debug(self.logfiles)
            self.logfiles = newfiles
            self.log.debug('after newfiles:')
            self.log.debug(self.logfiles)
            return True
        else:
            return False
    def collect(self):
        for scanloc,searchdir in self.search_dirs.items():
            _collect(scanloc,searchdir)

    def _collect(self,scanloc,searchdir):
        if not self.new_logfiles(searchdir):
            self.log.info('no new files found')
            return
        for f in self.logfiles:
            epoch = self.parse_epoch(f)
            with open(f, 'r') as infile:
                first_line = infile.readline()
                try:
                    header_regex = 'Stability configuration: {} slices, {} measurements, ([0-9]{2}) channels\n'.format(SLICES=self.slices,MEAS=self.measurements)
                    channel_no = re.match(header_regex, first_line).group(1)
                    coil = self._resolve_channels(channel_no)
                except (AttributeError,KeyError) as e:
                    self.log.info('error \'{}\' for file \'{}\', line {}'.format(e,f,first_line))
                    # you may occasionally run across a file with only 1 slice.
                    # the below section partition will only process stability configurations with 16 slices.
                    continue
                lines = infile.read()
                # divide document into sections
                section_regex = 'Stability (\w+) results:\n\nslice#(.*)\n'
                for slice_no in range(1,self.slices+1):
                    slice_row_header = '{SLICENO: >{fill}}(.*)\n'.format(SLICENO=slice_no,fill=2)
                    section_regex += slice_row_header
                sections = re.findall(section_regex, lines, re.MULTILINE)
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
#                    metricnames =[('{}.{}.{}.{}.{}'.format(self.dotlocation(scanloc),coil,section_type,header_list[i],s+1),v) for s,r in enumerate(section) for i,v in enumerate(r)]
#                    dotloc = self.dotlocation(scanloc)
                    for slicenum,row in enumerate(section,start=1):
                        for i,value in enumerate(row):
                            metricname = '{DOTLOC}.{COIL}.{METRIC}.{STAT}.{INDEX}'.format(
                                    DOTLOC=dotloc,
                                    COIL=coil,
                                    METRIC=section_type,
                                    STAT=header_list[i],
                                    INDEX=slicenum)
                            metricnames.append((metricname,value))
                    

                    for metricname,value in metricnames:
                        self.publish(metricname,value,timestamp=epoch,dry_run=True)
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
            '48': '64',
            '64': '64'
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
