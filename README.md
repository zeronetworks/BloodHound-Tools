# What is this?
A collection of tools that can be use with conjuction with [BloodHound](https://github.com/BloodHoundAD/BloodHound).

Bloodhound is the defacto standard that both blue and red security teams use to find lateral movement and privilege escalation paths that can potentially be exploited inside an enterprise environment. 
A typical environment can yield millions of paths, representing almost endless opportunities for red teams to attack and creating a seemingly insurmountable number of attack vectors for blue teams to tackle. 

However, a critical dimension that Bloodhound ignores, namely network access, could hold the key to shutting down excessive lateral movement.
This repository contains tools that integrate with Bloodhound’s database in order to reflect network access, for the benefit of both red and blue teams. 
 
# Tools List
## ShotHound
Validate practical paths discovered by BloodHound with [CornerShot](https://github.com/zeronetworks/cornershot).  

