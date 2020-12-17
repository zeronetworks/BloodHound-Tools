# What is Ransomulator?
Ransomulator is a ransom simulator for BloodHound database. It can be used to measure a network resilience for ransomare infections, and identify "weak links" in the network.

![Ransomulator demo](./demos/ransomulator.gif)  

Read more [here](https://zeronetworks.com/blog/adversary-resilience-via-least-privilege-networking-part-1/).

# How Ransomulator Works
For each computer node, Ransomulator will try to propagate to other computers through infection waves.
Propagation to other computers is possible when there is a **logical** path between them, and there is also a network path. 
Network access is assumed to exist in the database, and should be represented with "Open" edges in the data.

Ransomulator will generate for each computer, a wave map, showing how many hosts will be compromised by each infection wave.
This information can also be exported to csv. 

# Getting Started
1. Integrate network data to your BloodHound database (or start with a [simulated one](../DBCreator))
2. Run ransomulator: 
```bash
python ransomulator.py -p <dbpass>
```
