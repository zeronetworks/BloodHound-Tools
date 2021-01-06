# What is ShotHound?
ShotHound is a standalone script that integrates with BloodHound's Neo4j database and [CornerShot](https://github.com/zeronetworks/cornershot).
It allows security teams to validate **logical paths** discovered by BloodHound against **physical network access**.

![ShotHound demo](./demos/shothound.gif)  

# Use Cases
## Blue Teams
Because a typical environment can yield millions of logical paths by BloodHound, it is crucial for blue teams to focus their mitigation efforts on **practical paths**, which may pose a fraction of all logical paths in a Least Privilege Network.

ShotHound helps blue teams filter out impractical paths discovered by BloodHound.   

## Red Teams
Red teams that run BloodHound in a network, are often "blind" to network access. This can cause them to follow an impractical path, only to discover it somewhere along the path.

ShotHound can assist red teams to discover practical paths when network visibility is noy possible through other means. 

# Getting Started

## Installation
All that is required to run ShotHound is *cornershot* and *neo4j* packages for Python: 
 ```bash
pip install cornershot neo4j
```

## Basic Usage
Basic command line arguments for ShotHound 
```bash
ShotHound [-h] [--dbuser DBUSER] [--dbpass DBPASS] [--dburl DBURL] [-s SOURCE] [-t TARGET] [-v] [-w THREADS] domain_user domain_password domain
```
While ShotHound requires only domain, domain username and domain password, additional credentials should be provided for the neo4j database (otherwise default values are used): 
 
A basic execution line will look like this: 
 ```bash
python shothound.py --dbuser neo4j --dbpass neo4j username pass*** mycorp.local
``` 

By default, ShotHound will perform a Cypher query for *allShortestPaths* to the DOMAIN ADMINS group.

## Custom Queries
ShotHound supports customised *source* and *target* entities from command line. If a source, target or both are provided, ShotHound will againt query for *allShortestPaths* between a source and a target, only from a source, or only to a target.  
  
For example, the following command will query for all paths to a user named: "dadmin@mycorp.local"     
```bash
python shothound.py -t dadmin@mycorp.local --dbpass neo4j username pass*** mycorp.local
```
The same can be done for a source "comp_1234.mycorp.local"
```bash
python shothound.py -s comp_1234.mycorp.local --dbpass neo4j username pass*** mycorp.local
```
A specific path can also be located between the source computer and target user:
```bash
python shothound.py -s comp_1234.mycorp.local -t dadmin@mycorp.local --dbpass neo4j username pass*** mycorp.local
```

# How ShotHound Works

ShotHound goes through the following steps: 
1. Query neo4j for all **logical paths** discovered by BloodHound
2. Test network access between source and destination hosts along a **logical path** using [CornerShot](https://github.com/zeronetworks/cornershot)
3. An attcker is able to move between two hosts if at least one port is *"open"* between them (by default, CornerShot uses ports that allow for lateral movement) 
4. A path is considered **practical** if network access enables an attacker to propagate along the path
5. Only **practical** paths are returned by ShotHound  

# Future Work
Currently ShotHound only prints results to the console. 
In future versions it will integrate information back to BloodHound's database, so paths can be discovered and viewed by BloodHound.
       
