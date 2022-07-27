# What is this?
A standalone script that adds information about unpatched vulnerabilities to BloodHound based on parsed vulnerability scanners reports.
Security teams can then use this data to define starting points for paths (e.g. paths to Domain Admins from vulnerable hosts) or write queries that consider lateral movement to vulnerable hosts.

![demo](./demos/demo.gif)  

# Supported Scanners
* [Tenable Nessus](https://www.tenable.com/products/nessus)
* [Qualys](https://www.qualys.com/)
* [Greenbone OpenVAS](https://github.com/greenbone/openvas-scanner)
* [Nmap Vuln NSE Script](https://nmap.org/book/nse-usage.html#nse-category-vuln)

# Getting Started

## Installation
The required Python modules can be installed using the standard *requirements.txt* file. 
 ```bash
pip install -r requirements.txt
```

## Basic Usage
Basic command line arguments
```bash
python main.py [--dbuser DBUSER] [--dbpass DBPASS] [--dburl DBURL] [--dbencrypt] [-d DOMAIN] [-db] [-n [NESSUS]] [-q [QUALYS]] [-o [OPENVAS]] [-nm [NMAP]] [-rs [{1,2,3,4,5}]]
``` 
 
A basic execution line will look like this: 
 ```bash
main.py --dbpass **** --nessus nessus_report.csv --qualys qualys_report.csv --nmap nmap_scan.xml --openvas openvas_report.csv -d company.com
``` 

By default, only vulnerabilities with a critical risk score (i.e. can be exploited to gain code execution) are considered. The minimum risk score can be lowered using the *--risk-score* argument.<br>
The script automatically attempts to determine the organizational domain; the *--domain* flag can be used to eforce the domain. This is needed for linking the report hosts to the nodes in the Neo4j database.


## Custom Queries
After loading the data to the Neo4j database, new properties will be added to the nodes of vulnerable hosts: *is_vulnerable* and *cves*.
These can be used where writing custom queries.

For example, the following query will look for paths from any vulnerable host to the Domain Admins group:   
```bash
MATCH p=shortestPath((c:Computer)-[r*1..]->(g:Group)) 
WHERE c.is_vulnerable = true 
AND g.objectid =~ "(?i)S-1-5-.*-512"
RETURN p
```

# Supporting additional scanners
If you wish to add support for additional scanners, all you need to do is implement a new class that inherits from **ReportParser** (located in *report_parses.py*).
The new class will need to overload the abstract method *get_vulnerabilities* which must return a DataFrame with the columns: *'Hostname', 'CVE', 'IP'*.
You can use the base class' methods *_load_csv_report* and *_load_xml_report* to load your report file.