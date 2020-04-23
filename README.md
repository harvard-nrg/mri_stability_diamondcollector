# HOPS

The HOPS Harvard Online Phantom Statistics architecture is a server setup that facilitates easy visualization of phantom statistics. It generates phantom statistics using an MGH-stability package for Siemens IDEA-licensed scanners, and visualizes this data through the Grafana platform.                                                                                                                         
 
Grafana is an established tool for timeseries data visualization widely used in the IT world. It allows for easy adjustment of graphs, redrawing them on demand. You can add as many data sources as you like, and visualize in arbitrary combinations. Grafana also allows you to save dashboards of graphs for at-a-glance monitoring. It uses Graphite as a backend. There are existing [guides on setting up grafana](https://www.linode.com/docs/uptime/monitoring/install-graphite-and-grafana/) and tools for [sizing whisper databases](https://github.com/hhoke/whisper-calculator).
 
The initial data source for HOPS is the MGH stability sequence. You can obtain this MRI sequence through a c2p request to MGH. Before you transfer the sequence to your site, you will need a Master Research Agreement with Siemens and an IDEA license on your scanner. In order to actually obtain the sequence, you must contact your site's Siemens collaborations manager to tell them they are requesting the Stability sequence from MGH, after which they will have to sign a document for Siemens to keep on file. You must also fill out the c2p request form [here](https://martinos.org/c2p) and select "Stability" in the drop-down menu.
 
When you run this sequence on a phantom, it will produce a file similar to the one found in the 'sample_statfiles' directory of this repository. In order to visualize this data, we must first parse the text file, and then send the data to Graphite's whisper database. This brings us to the mri stability diamondcollector, a parser developed specifically for this project.
 
We use [stability_collector.py](https://github.com/fasrc/mri_stability_diamondcollector), along with the python daemon [diamond](https://github.com/python-diamond/Diamond), to ingest our data into Graphite. For our setup at Harvard, this runs on a service VM that can read the statistics files from a network drive shared with the scanner.
 
Stability_collector.py ingests stability files from a user-specified directory or directories. For ease of auditing and re-ingesting, ingested files are moved to a user-specified subfolder of their origin folder.
 
Our site already uses Graphite/Grafana for IT visualizations, and the stability data is not sensitive. We visualize the stability data on the Harvard FASRC grafana page as part of a custom dashboard.
