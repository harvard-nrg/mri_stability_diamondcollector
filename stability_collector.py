#!/usr/bin/python

"""
A script that parses stability session logs
"""

import os
import re
import diamond.collector

class StabilityCollector(diamond.collector.Collector):
    def collect(self,location):
        with open('/ncf/dicom-backups/_Scanner/{}/Stability_20180110T165545.txt'.format(location), 'r') as input:
            location = location.replace('/','.')
            lines = input.read()
        # divide document into sections
            sections = re.findall("Stability (\w+) results:\n\nslice#(.*)\n 1(.*)\n 2(.*)\n 3(.*)\n 4(.*)\n 5(.*)\n 6(.*)\n 7(.*)\n 8(.*)\n 9(.*)\n10(.*)\n11(.*)\n12(.*)\n13(.*)\n14(.*)\n15(.*)\n16(.*)\n", lines, re.MULTILINE)
            # parse each section
            for section in sections:
                section = list(section)
                section_type = section.pop(0)
                header = section.pop(0)
                header_list = header.split()
                section = [r.split() for r in section]
                # type.columnName.rowNum value
                metricnames = [("{}.{}.{}.{}".format(location,section_type,header_list[i],s+1),v) for s,r in enumerate(section) for i,v in enumerate(r)]
                for metricname,value in metricnames:
                    self.publish(metricname,value)
                    #print(metricname,value)

if __name__ == '__main__':
    instance = StabilityCollector()
    instance.collect("Harvard/Northwest/Bay1")

