# Requirements - pip install neo4j-driver
# This script is used to create randomized sample databases.
# Commands
# 	dbconfig - Set the credentials and URL for the database you're connecting too
#	connect - Connects to the database using supplied credentials
# 	setnodes - Set the number of nodes to generate (defaults to 500, this is a safe number!)
# 	setdomain - Set the domain name
# 	cleardb - Clears the database and sets the schema properly
#	generate - Generates random data in the database
#	clear_and_generate - Connects to the database, clears the DB, sets the schema, and generates random data

from neo4j import GraphDatabase
import cmd
import os
import sys
import random
import pickle
import math
import itertools
from collections import defaultdict
import uuid
import time


class Messages():
    def title(self):
        print("================================================================")
        print("BloodHound Sample Database Creator")
        print("================================================================")

    def input_default(self, prompt, default):
        return input("%s [%s] " % (prompt, default)) or default

    def input_yesno(self, prompt, default):
        temp = input(prompt + " " + ("Y" if default else "y") + "/" + ("n" if default else "N") + " ")
        if temp == "y" or temp == "Y":
            return True
        elif temp == "n" or temp == "N":
            return False
        return default


class MainMenu(cmd.Cmd):
    def __init__(self):
        self.m = Messages()
        self.url = "bolt://localhost:7687"
        self.username = "neo4j"
        self.password = "neo4jj"
        self.use_encryption = False
        self.driver = None
        self.connected = False
        self.num_nodes = 500
        self.avg_conn = 10
        self.avg_vulnerable = 50
        self.domain = "TESTLAB.LOCAL"
        self.current_time = int(time.time())
        self.base_sid = "S-1-5-21-883232822-274137685-4173207997"
        with open('first.pkl', 'rb') as f:
            self.first_names = pickle.load(f)

        with open('last.pkl', 'rb') as f:
            self.last_names = pickle.load(f)

        cmd.Cmd.__init__(self)

    def cmdloop(self):
        while True:
            self.m.title()
            self.do_help("")
            try:
                cmd.Cmd.cmdloop(self)
            except KeyboardInterrupt:
                if self.driver is not None:
                    self.driver.close()
                raise KeyboardInterrupt

    def help_dbconfig(self):
        print("Configure database connection parameters")

    def help_connect(self):
        print("Test connection to the database and verify credentials")

    def help_setnodes(self):
        print("Set base number of nodes to generate (default 500)")

    def help_setdomain(self):
        print("Set domain name (default 'TESTLAB.LOCAL')")

    def help_cleardb(self):
        print("Clear the database and set constraints")

    def help_generate(self):
        print("Generate random data")

    def help_clear_and_generate(self):
        print("Connect to the database, clear the db, set the schema, and generate random data")

    def help_setavgcon(self):
        print("Set the average number of nodes each node will have network access to")

    def help_setavgvulnerable(self):
        print("Set the average number of vulnerable hosts")

    def help_exit(self):
        print("Exits the database creator")

    def do_dbconfig(self, args):
        print("Current Settings:")
        print("DB Url: {}".format(self.url))
        print("DB Username: {}".format(self.username))
        print("DB Password: {}".format(self.password))
        print("Use encryption: {}".format(self.use_encryption))
        print("")
        self.url = self.m.input_default("Enter DB URL", self.url)
        self.username = self.m.input_default(
            "Enter DB Username", self.username)
        self.password = self.m.input_default(
            "Enter DB Password", self.password)

        self.use_encryption = self.m.input_yesno(
            "Use encryption?", self.use_encryption)
        print("")
        print("New Settings:")
        print("DB Url: {}".format(self.url))
        print("DB Username: {}".format(self.username))
        print("DB Password: {}".format(self.password))
        print("Use encryption: {}".format(self.use_encryption))
        print("")
        print("Testing DB Connection")
        self.test_db_conn()

    def do_setnodes(self, args):
        passed = args
        if passed != "":
            try:
                self.num_nodes = int(passed)
                return
            except ValueError:
                pass

        self.num_nodes = int(self.m.input_default(
            "Number of nodes of each type to generate", self.num_nodes))

    def do_setavgcon(self, args):
        passed = args
        if passed != "":
            try:
                self.avg_conn = int(passed)
                return
            except ValueError:
                pass

        self.avg_conn = int(self.m.input_default(
            "Average number of network connnected nodes per node", self.avg_conn))

    def do_setavgvulnerable(self, args):
        passed = args
        if passed != "":
            try:
                self.avg_vulnerable = int(passed)
                return
            except ValueError:
                pass

        self.avg_vulnerable = int(self.m.input_default(
            "Average number of vulnerable hosts", self.avg_vulnerable))

    def do_setdomain(self, args):
        passed = args
        if passed != "":
            try:
                self.domain = passed.upper()
                return
            except ValueError:
                pass

        self.domain = self.m.input_default("Domain", self.domain).upper()
        print("")
        print("New Settings:")
        print("Domain: {}".format(self.domain))

    def do_exit(self, args):
        raise KeyboardInterrupt

    def do_connect(self, args):
        self.test_db_conn()

    def do_cleardb(self, args):
        if not self.connected:
            print("Not connected to database. Use connect first")
            return

        print("Clearing Database")
        d = self.driver
        session = d.session()
        num = 1
        while num > 0:
            result = session.run(
                "MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(n)")
            for r in result:
                num = int(r['count(n)'])

        print("Resetting Schema")
        for constraint in session.run("CALL db.constraints"):
            session.run("DROP {}".format(constraint['description']))

        for index in session.run("CALL db.indexes"):
            if index.get('description'):
                session.run("DROP {}".format(index['description']))
            else:
                session.run("DROP INDEX {}".format(index['name']))

        session.run(
            "CREATE CONSTRAINT id_constraint ON (c:Base) ASSERT c.objectid IS UNIQUE")
        session.run("CREATE INDEX name_index FOR (n:Base) ON (n.name)")

        session.close()

        print("DB Cleared and Schema Set")

    def test_db_conn(self):
        self.connected = False
        if self.driver is not None:
            self.driver.close()
        try:
            self.driver = GraphDatabase.driver(
                self.url, auth=(self.username, self.password), encrypted=self.use_encryption)
            self.connected = True
            print("Database Connection Successful!")
        except:
            self.connected = False
            print("Database Connection Failed. Check your settings.")

    def do_generate(self, args):
        self.generate_data()

    def do_clear_and_generate(self, args):
        self.test_db_conn()
        self.do_cleardb("a")
        self.generate_data()

    def split_seq(self, iterable, size):
        it = iter(iterable)
        item = list(itertools.islice(it, size))
        while item:
            yield item
            item = list(itertools.islice(it, size))

    def generate_timestamp(self):
        choice = random.randint(-1, 1)
        if choice == 1:
            variation = random.randint(0, 31536000)
            return self.current_time - variation
        else:
            return choice

    def generate_data(self):
        if not self.connected:
            print("Not connected to database. Use connect first")
            return

        computers = []
        groups = []
        users = []
        gpos = []
        ou_guid_map = {}

        used_states = []

        states = ["WA", "MD", "AL", "IN", "NV", "VA", "CA", "NY", "TX", "FL"]
        user_partitions = ["IT", "HR", "MARKETING", "OPERATIONS", "BUSINESS"]
        user_partitions_weight = [10,5,30,30,20]
        user_weighted_parts = []
        for i in range(len(user_partitions)):
            user_weighted_parts += [user_partitions[i]] * user_partitions_weight[i]

        computer_partitions = user_partitions + ["APPS_IT", "APPS_HR", "APPS_MARKETING", "APPS_BUSINESS","APPS_OPERATIONS"]
        comp_partitions_weight = [5, 5, 20, 20, 20, 5, 5, 5, 5, 10]
        comp_weighted_parts = []
        for i in range(len(computer_partitions)):
            comp_weighted_parts += [computer_partitions[i]] * comp_partitions_weight[i]

        os_list = ["Windows Server 2003"] * 1 + ["Windows Server 2008"] * 15 + ["Windows 7"] * 35 + \
            ["Windows 10"] * 28 + ["Windows XP"] * 1 + \
            ["Windows Server 2012"] * 8 + ["Windows Server 2008"] * 12
        session = self.driver.session()

        def cn(name):
            return f"{name}@{self.domain}"

        def cs(relative_id):
            return f"{self.base_sid}-{str(relative_id)}"

        def cws(security_id):
            return f"{self.domain}-{str(security_id)}"

        print("Starting data generation with nodes={}".format(self.num_nodes))

        print("Populating Standard Nodes")
        base_statement = "MERGE (n:Base {name: $gname}) SET n:Group, n.objectid=$sid"
        session.run(f"{base_statement},n.highvalue=true",
                    sid=cs(512), gname=cn("DOMAIN ADMINS"))
        session.run(base_statement, sid=cs(515), gname=cn("DOMAIN COMPUTERS"))
        session.run(base_statement, gname=cn("DOMAIN USERS"), sid=cs(513))
        session.run(f"{base_statement},n.highvalue=true",
                    gname=cn("DOMAIN CONTROLLERS"), sid=cs(516))
        session.run(f"{base_statement},n.highvalue=true", gname=cn(
            "ENTERPRISE DOMAIN CONTROLLERS"), sid=cws("S-1-5-9"))
        session.run(base_statement, gname=cn(
            "ENTERPRISE READ-ONLY DOMAIN CONTROLLERS"), sid=cs(498))
        session.run(f"{base_statement},n.highvalue=true",
                    gname=cn("ADMINISTRATORS"), sid=cs(544))
        session.run(f"{base_statement},n.highvalue=true",
                    gname=cn("ENTERPRISE ADMINS"), sid=cs(519))
        session.run(
            "MERGE (n:Base {name:$domain}) SET n:Domain, n.highvalue=true", domain=self.domain)
        ddp = str(uuid.uuid4())
        ddcp = str(uuid.uuid4())
        dcou = str(uuid.uuid4())
        base_statement = "MERGE (n:Base {name:$gpo, objectid:$guid}) SET n:GPO"
        session.run(base_statement, gpo=cn("DEFAULT DOMAIN POLICY"), guid=ddp)
        session.run(base_statement, gpo=cn(
            "DEFAULT DOMAIN CONTROLLERS POLICY"), guid=ddp)
        session.run("MERGE (n:Base {name:$ou, objectid:$guid, blocksInheritance: false}) SET n:OU", ou=cn(
            "DOMAIN CONTROLLERS"), guid=dcou)

        print("Adding Standard Edges")

        # Default GPOs
        gpo_name = "DEFAULT DOMAIN POLICY@{}".format(self.domain)
        session.run(
            'MERGE (n:GPO {name:$gpo}) MERGE (m:Domain {name:$domain}) MERGE (n)-[:GpLink {isacl:false, enforced:toBoolean(false)}]->(m)', gpo=gpo_name, domain=self.domain)
        session.run(
            'MERGE (n:Domain {name:$domain}) MERGE (m:OU {objectid:$guid}) MERGE (n)-[:Contains {isacl:false}]->(m)', domain=self.domain, guid=dcou)
        gpo_name = "DEFAULT DOMAIN CONTROLLERS POLICY@{}".format(self.domain)
        session.run(
            'MERGE (n:GPO {name:"DEFAULT DOMAIN CONTROLLERS POLICY@$domain"}) MERGE (m:OU {objectid:$guid}) MERGE (n)-[:GpLink {isacl:false, enforced:toBoolean(false)}]->(m)', domain=self.domain, guid=dcou)

        # Ent Admins -> Domain Node
        group_name = "ENTERPRISE ADMINS@{}".format(self.domain)
        session.run(
            'MERGE (n:Domain {name:$domain}) MERGE (m:Group {name:$gname}) MERGE (m)-[:GenericAll {isacl:true}]->(n)', domain=self.domain, gname=group_name)

        # Administrators -> Domain Node
        group_name = "ADMINISTRATORS@{}".format(self.domain)
        session.run(
            'MERGE (n:Domain {name:$domain}) MERGE (m:Group {name:$gname}) MERGE (m)-[:Owns {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:WriteOwner {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:WriteDacl {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:DCSync {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:GetChanges {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:GetChangesAll {isacl:true}]->(n)', domain=self.domain, gname=group_name)

        # Domain Admins -> Domain Node
        group_name = "DOMAIN ADMINS@{}".format(self.domain)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:WriteOwner {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:WriteDacl {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:DCSync {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:GetChanges {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:GetChangesAll {isacl:true}]->(n)', domain=self.domain, gname=group_name)

        # DC Groups -> Domain Node
        group_name = "ENTERPRISE DOMAIN CONTROLLERS@{}".format(self.domain)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:GetChanges {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        group_name = "ENTERPRISE READ-ONLY DOMAIN CONTROLLERS@{}".format(
            self.domain)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:GetChanges {isacl:true}]->(n)', domain=self.domain, gname=group_name)
        group_name = "DOMAIN CONTROLLERS@{}".format(self.domain)
        session.run(
            'MERGE (n:Domain {name:$domain}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:GetChangesAll {isacl:true}]->(n)', domain=self.domain, gname=group_name)

        print("Generating User Group Nodes")
        ridcount = 1000
        props = []
        for i in range(1, self.num_nodes + 1):
            dept = random.choice(user_weighted_parts)
            group_name = "{}{:05d}@{}".format(dept, i, self.domain)
            if group_name not in groups:
                groups.append(group_name)
            sid = cs(ridcount)
            ridcount += 1
            props.append({'name': group_name, 'id': sid})
            if len(props) > 500:
                session.run(
                    'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Group, n.name=prop.name', props=props)
                props = []

        session.run(
            'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Group, n.name=prop.name', props=props)

        print("Generating Computer Group Nodes")
        props = []
        cgroups = []

        for dept in computer_partitions:
            group_name = "{}@{}".format(dept, self.domain)

            if group_name not in cgroups:
                cgroups.append(group_name)
                sid = cs(ridcount)
                ridcount += 1
                props.append({'name': group_name, 'id': sid})

            if len(props) > 500:
                session.run(
                    'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Group, n.name=prop.name', props=props)
                props = []

        session.run(
            'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Group, n.name=prop.name', props=props)

        print("Generating Computer Nodes")
        # group_name = "DOMAIN COMPUTERS@{}".format(self.domain)
        props = []
        for i in range(1, self.num_nodes + 1):
            dept = random.choice(comp_weighted_parts)
            group_name = "{}@{}".format(dept, self.domain)
            comp_name = "COMP{:05d}.{}".format(i, self.domain)
            computers.append(comp_name)
            os = random.choice(os_list)
            enabled = True
            props.append({'id': cs(ridcount), 'props': {
                'name': comp_name,
                'operatingsystem': os,
                'enabled': enabled,
            }})
            ridcount += 1

            session.run('UNWIND $props as prop MERGE (n:Base {objectid: prop.id}) SET n:Computer, n += prop.props WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)',props=props, gname=group_name)
            props = []

        # session.run(
        #     'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Computer, n += prop.props WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)',
        #     props=props, gname=group_name)

        print("Creating Domain Controllers")
        for state in states:
            comp_name = cn(f"{state}LABDC")
            group_name = cn("DOMAIN CONTROLLERS")
            sid = cs(ridcount)
            session.run(
                'MERGE (n:Base {objectid:$sid}) SET n:Computer,n.name=$name WITH n MATCH (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', sid=sid, name=comp_name, gname=group_name)
            session.run(
                'MATCH (n:Computer {objectid:$sid}) WITH n MATCH (m:OU {objectid:$dcou}) WITH n,m MERGE (m)-[:Contains]->(n)', sid=sid, dcou=dcou)
            session.run(
                'MATCH (n:Computer {objectid:$sid}) WITH n MATCH (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', sid=sid, gname=cn("ENTERPRISE DOMAIN CONTROLLERS"))
            session.run(
                'MERGE (n:Computer {objectid:$sid}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:AdminTo]->(n)', sid=sid, gname=cn("DOMAIN ADMINS"))

        used_states = list(set(used_states))

        print("Generating network access with average of {}".format(self.avg_conn))
        src_names = []
        dest_names = []
        for src_comp in computers:
            dests = random.sample(computers, k=min(random.randint(0, 2 * self.avg_conn), self.num_nodes))
            if src_comp in dests: dests.remove(src_comp)
            src_names.append(src_comp)
            dest_names.append(dests)

            if (len(src_names) > 500):
                res = session.run(
                    'WITH $srcnames AS srcnames,$destnamelist AS destnamelist UNWIND srcnames AS srcname WITH srcnames,srcname,destnamelist,reduce(ix = -1, i IN RANGE(0,SIZE(srcnames)-1) | CASE srcnames[i] WHEN srcname THEN i ELSE ix END) AS six  MATCH (src {name:srcname}) MATCH (dst:Computer) WHERE dst.name IN destnamelist[six] MERGE (src)-[:Open]->(dst)',
                srcnames=src_names,destnamelist=dest_names)
                src_names = []
                dest_names = []

        session.run(
            'WITH $srcnames AS srcnames,$destnamelist AS destnamelist UNWIND srcnames AS srcname WITH srcnames,srcname,destnamelist,reduce(ix = -1, i IN RANGE(0,SIZE(srcnames)-1) | CASE srcnames[i] WHEN srcname THEN i ELSE ix END) AS six  MATCH (src {name:srcname}) MATCH (dst:Computer) WHERE dst.name IN destnamelist[six] MERGE (src)-[:Open]->(dst)',
            srcnames=src_names, destnamelist=dest_names)

        print("Generating vulnerable hosts with average of {}".format(self.avg_vulnerable))
        cves = ['CVE-2010-0022', 'CVE-2017-0144', 'CVE-2008-4114', 'CVE-2017-0146', 'CVE-2017-0147', 'CVE-2017-0143',
                'CVE-2017-0145', 'CVE-2010-0020', 'CVE-2008-4835', 'CVE-2017-0148', 'CVE-2010-0231', 'CVE-2010-0021',
                'CVE-2008-4834', 'CVE-2008-4250']
        vulnerable_hosts = random.sample(computers, k=min(random.randint(1, 2 * self.avg_vulnerable), self.num_nodes))
        for vulnerable_host in vulnerable_hosts:
            host_cves = random.sample(cves, k=random.randint(1, len(cves)))
            session.run('MATCH (c:Computer {name: $host}) SET c.is_vulnerable = true, c.cves = $cves', host=vulnerable_host, cves=host_cves)

        print("Generating User Nodes")
        current_time = int(time.time())
        group_name = "DOMAIN USERS@{}".format(self.domain)
        props = []
        for i in range(1, self.num_nodes+1):
            first = random.choice(self.first_names)
            last = random.choice(self.last_names)
            user_name = "{}{}{:05d}@{}".format(
                first[0], last, i, self.domain).upper()
            user_name = user_name.format(first[0], last, i).upper()
            users.append(user_name)
            dispname = "{} {}".format(first, last)
            enabled = True
            pwdlastset = self.generate_timestamp()
            lastlogon = self.generate_timestamp()
            ridcount += 1
            objectsid = cs(ridcount)

            props.append({'id': objectsid, 'props': {
                'displayname': dispname,
                'name': user_name,
                'enabled': enabled,
                'pwdlastset': pwdlastset,
                'lastlogon': lastlogon
            }})
            if (len(props) > 500):
                session.run(
                    'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:User, n += prop.props WITH n MATCH (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', props=props, gname=group_name)
                props = []

        session.run(
            'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:User, n += prop.props WITH n MATCH (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', props=props, gname=group_name)



        print("Adding Domain Admins to Local Admins of Computers")
        session.run(
            'MATCH (n:Computer) MATCH (m:Group {objectid: $id}) MERGE (m)-[:AdminTo]->(n)', id=cs(512))

        dapctint = random.randint(3, 5)
        dapct = float(dapctint) / 100
        danum = int(math.ceil(self.num_nodes * dapct))
        danum = min([danum, 30])
        print("Creating {} Domain Admins ({}% of users capped at 30)".format(
            danum, dapctint))
        das = random.sample(users, danum)
        for da in das:
            session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=da, gname=cn("DOMAIN ADMINS"))

        print("Applying random group nesting")
        max_nest = int(round(math.log10(self.num_nodes)))
        props = []
        for group in groups:
            if (random.randrange(0, 100) < 10):
                num_nest = random.randrange(1, max_nest)
                dept = group[0:-19]
                dpt_groups = [x for x in groups if dept in x]
                if num_nest > len(dpt_groups):
                    num_nest = random.randrange(1, len(dpt_groups))
                to_nest = random.sample(dpt_groups, num_nest)
                for g in to_nest:
                    if not g == group:
                        props.append({'a': group, 'b': g})

            if (len(props) > 500):
                session.run(
                    'UNWIND $props AS prop MERGE (n:Group {name:prop.a}) WITH n,prop MERGE (m:Group {name:prop.b}) WITH n,m MERGE (n)-[:MemberOf]->(m)', props=props)
                props = []

        session.run(
            'UNWIND $props AS prop MERGE (n:Group {name:prop.a}) WITH n,prop MERGE (m:Group {name:prop.b}) WITH n,m MERGE (n)-[:MemberOf]->(m)', props=props)

        print("Adding users to groups")
        props = []
        a = math.log10(self.num_nodes)
        a = math.pow(a, 2)
        a = math.floor(a)
        a = int(a)
        num_groups_base = a
        variance = int(math.ceil(math.log10(self.num_nodes)))
        it_users = []

        print("Calculated {} groups per user with a variance of - {}".format(num_groups_base, variance*2))

        for user in users:
            dept = random.choice(user_weighted_parts)
            if dept == "IT":
                it_users.append(user)
            possible_groups = [x for x in groups if dept in x]

            sample = num_groups_base + random.randrange(-(variance*2), 0)
            if (sample > len(possible_groups)):
                sample = int(math.floor(float(len(possible_groups)) / 4))

            if (sample == 0):
                continue

            to_add = random.sample(possible_groups, sample)

            for group in to_add:
                props.append({'a': user, 'b': group})

            if len(props) > 500:
                session.run(
                    'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Group {name:prop.b}) WITH n,m MERGE (n)-[:MemberOf]->(m)', props=props)
                props = []

        session.run(
            'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Group {name:prop.b}) WITH n,m MERGE (n)-[:MemberOf]->(m)', props=props)

        it_users = it_users + das
        it_users = list(set(it_users))

        print("Adding local admin rights")
        it_groups = [x for x in groups if "IT" in x]
        random.shuffle(it_groups)
        super_groups = random.sample(it_groups, 4)
        super_group_num = int(math.floor(len(computers) * .85))

        it_groups = [x for x in it_groups if not x in super_groups]

        total_it_groups = len(it_groups)

        dista = int(math.ceil(total_it_groups * .6))
        distb = int(math.ceil(total_it_groups * .3))
        distc = int(math.ceil(total_it_groups * .07))
        distd = int(math.ceil(total_it_groups * .03))

        distribution_list = [1] * dista + [2] * \
            distb + [10] * distc + [50] * distd

        props = []
        for x in range(0, total_it_groups):
            g = it_groups[x]
            dist = distribution_list[x]

            to_add = random.sample(computers, dist)
            for a in to_add:
                props.append({'a': g, 'b': a})

            if len(props) > 500:
                session.run(
                    'UNWIND $props AS prop MERGE (n:Group {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (n)-[:AdminTo]->(m)', props=props)
                props = []

        for x in super_groups:
            for a in random.sample(computers, super_group_num):
                props.append({'a': x, 'b': a})

            if len(props) > 500:
                session.run(
                    'UNWIND $props AS prop MERGE (n:Group {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (n)-[:AdminTo]->(m)', props=props)
                props = []

        session.run(
            'UNWIND $props AS prop MERGE (n:Group {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (n)-[:AdminTo]->(m)', props=props)

        print("Adding RDP/ExecuteDCOM/AllowedToDelegateTo")
        count = int(math.floor(len(computers) * .1))
        props = []
        for i in range(0, count):
            comp = random.choice(computers)
            user = random.choice(it_users)
            props.append({'a': user, 'b': comp})

        session.run(
            'UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:CanRDP]->(m)', props=props)

        props = []
        for i in range(0, count):
            comp = random.choice(computers)
            user = random.choice(it_users)
            props.append({'a': user, 'b': comp})

        session.run(
            'UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:ExecuteDCOM]->(m)', props=props)

        props = []
        for i in range(0, count):
            comp = random.choice(computers)
            user = random.choice(it_groups)
            props.append({'a': user, 'b': comp})

        session.run(
            'UNWIND $props AS prop MERGE (n:Group {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:CanRDP]->(m)', props=props)

        props = []
        for i in range(0, count):
            comp = random.choice(computers)
            user = random.choice(it_groups)
            props.append({'a': user, 'b': comp})

        session.run(
            'UNWIND $props AS prop MERGE (n:Group {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:ExecuteDCOM]->(m)', props=props)

        props = []
        for i in range(0, count):
            comp = random.choice(computers)
            user = random.choice(it_users)
            props.append({'a': user, 'b': comp})

        session.run(
            'UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:AllowedToDelegate]->(m)', props=props)

        props = []
        for i in range(0, count):
            comp = random.choice(computers)
            user = random.choice(computers)
            if (comp == user):
                continue
            props.append({'a': user, 'b': comp})

        session.run(
            'UNWIND $props AS prop MERGE (n:Computer {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:AllowedToDelegate]->(m)', props=props)

        print("Adding sessions")
        max_sessions_per_user = int(math.ceil(math.log10(self.num_nodes)))

        props = []
        for user in users:
            num_sessions = random.randrange(0, max_sessions_per_user)
            if (user in das):
                num_sessions = max(num_sessions, 1)

            if num_sessions == 0:
                continue

            for c in random.sample(computers, num_sessions):
                props.append({'a': user, 'b': c})

            if (len(props) > 500):
                session.run(
                    'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
                props = []

        session.run(
            'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)

        print("Adding Domain Admin ACEs")
        group_name = "DOMAIN ADMINS@{}".format(self.domain)
        props = []
        for x in computers:
            props.append({'name': x})

            if len(props) > 500:
                session.run(
                    'UNWIND $props as prop MATCH (n:Computer {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)
                props = []

        session.run(
            'UNWIND $props as prop MATCH (n:Computer {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)

        for x in users:
            props.append({'name': x})

            if len(props) > 500:
                session.run(
                    'UNWIND $props as prop MATCH (n:User {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)
                props = []

        session.run(
            'UNWIND $props as prop MATCH (n:User {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)

        for x in groups:
            props.append({'name': x})

            if len(props) > 500:
                session.run(
                    'UNWIND $props as prop MATCH (n:Group {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)
                props = []

        session.run(
            'UNWIND $props as prop MATCH (n:Group {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)

        print("Creating OUs")
        temp_comps = computers
        random.shuffle(temp_comps)
        split_num = int(math.ceil(self.num_nodes / 10))
        split_comps = list(self.split_seq(temp_comps, split_num))
        props = []
        for i in range(0, 10):
            state = states[i]
            ou_comps = split_comps[i]
            ouname = "{}_COMPUTERS@{}".format(state, self.domain)
            guid = str(uuid.uuid4())
            ou_guid_map[ouname] = guid
            for c in ou_comps:
                props.append({'compname': c, 'ouguid': guid, 'ouname': ouname})
                if len(props) > 500:
                    session.run(
                        'UNWIND $props as prop MERGE (n:Computer {name:prop.compname}) WITH n,prop MERGE (m:Base {objectid:prop.ouguid, name:prop.ouname, blocksInheritance: false}) SET m:OU WITH n,m,prop MERGE (m)-[:Contains]->(n)', props=props)
                    props = []

        session.run(
            'UNWIND $props as prop MERGE (n:Computer {name:prop.compname}) WITH n,prop MERGE (m:Base {objectid:prop.ouguid, name:prop.ouname, blocksInheritance: false}) SET m:OU WITH n,m,prop MERGE (m)-[:Contains]->(n)', props=props)

        temp_users = users
        random.shuffle(temp_users)
        split_users = list(self.split_seq(temp_users, split_num))
        props = []

        for i in range(0, 10):
            state = states[i]
            ou_users = split_users[i]
            ouname = "{}_USERS@{}".format(state, self.domain)
            guid = str(uuid.uuid4())
            ou_guid_map[ouname] = guid
            for c in ou_users:
                props.append({'username': c, 'ouguid': guid, 'ouname': ouname})
                if len(props) > 500:
                    session.run(
                        'UNWIND $props as prop MERGE (n:User {name:prop.username}) WITH n,prop MERGE (m:Base {objectid:prop.ouguid, name:prop.ouname, blocksInheritance: false}) SET m:OU WITH n,m,prop MERGE (m)-[:Contains]->(n)', props=props)
                    props = []

        session.run(
            'UNWIND $props as prop MERGE (n:User {name:prop.username}) WITH n,prop MERGE (m:Base {objectid:prop.ouguid, name:prop.ouname, blocksInheritance: false}) SET m:OU WITH n,m,prop MERGE (m)-[:Contains]->(n)', props=props)

        props = []
        for x in list(ou_guid_map.keys()):
            guid = ou_guid_map[x]
            props.append({'b': guid})

        session.run(
            'UNWIND $props as prop MERGE (n:OU {objectid:prop.b}) WITH n MERGE (m:Domain {name:$domain}) WITH n,m MERGE (m)-[:Contains]->(n)', props=props, domain=self.domain)

        print("Creating GPOs")

        for i in range(1, 20):
            gpo_name = "GPO_{}@{}".format(i, self.domain)
            guid = str(uuid.uuid4())
            session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=gpo_name, guid=guid)
            gpos.append(gpo_name)

        ou_names = list(ou_guid_map.keys())
        for g in gpos:
            num_links = random.randint(1, 3)
            linked_ous = random.sample(ou_names, num_links)
            for l in linked_ous:
                guid = ou_guid_map[l]
                session.run(
                    "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {objectid:$guid}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=g, guid=guid)

        num_links = random.randint(1, 3)
        linked_ous = random.sample(ou_names, num_links)
        for l in linked_ous:
            guid = ou_guid_map[l]
            session.run(
                "MERGE (n:Domain {name:$gponame}) WITH n MERGE (m:OU {objectid:$guid}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=self.domain, guid=guid)

        gpos.append("DEFAULT DOMAIN POLICY@{}".format(self.domain))
        gpos.append("DEFAULT DOMAIN CONTROLLER POLICY@{}".format(self.domain))

        acl_list = ["GenericAll"] * 10 + ["GenericWrite"] * 15 + ["WriteOwner"] * 15 + ["WriteDacl"] * \
            15 + ["AddMember"] * 30 + ["ForceChangePassword"] * \
            15 + ["ReadLAPSPassword"] * 10

        num_acl_principals = int(round(len(it_groups) * .1))
        print("Adding outbound ACLs to {} objects".format(num_acl_principals))

        acl_groups = random.sample(it_groups, num_acl_principals)
        all_principals = it_users + it_groups
        props = []
        for i in acl_groups:
            ace = random.choice(acl_list)
            ace_string = '[r:' + ace + '{isacl:true}]'
            if ace == "GenericAll" or ace == 'GenericWrite' or ace == 'WriteOwner' or ace == 'WriteDacl':
                p = random.choice(all_principals)
                p2 = random.choice(gpos)
                session.run(
                    'MERGE (n:Group {name:$group}) MERGE (m {name:$principal}) MERGE (n)-' + ace_string + '->(m)', group=i, principal=p)
                session.run('MERGE (n:Group {name:$group}) MERGE (m:GPO {name:$principal}) MERGE (n)-' +
                            ace_string + '->(m)', group=i, principal=p2)
            elif ace == 'AddMember':
                p = random.choice(it_groups)
                session.run(
                    'MERGE (n:Group {name:$group}) MERGE (m:Group {name:$principal}) MERGE (n)-' + ace_string + '->(m)', group=i, principal=p)
            elif ace == 'ReadLAPSPassword':
                p = random.choice(all_principals)
                targ = random.choice(computers)
                session.run(
                    'MERGE (n {name:$principal}) MERGE (m:Computer {name:$target}) MERGE (n)-[r:ReadLAPSPassword]->(m)', target=targ, principal=p)
            else:
                p = random.choice(it_users)
                session.run(
                    'MERGE (n:Group {name:$group}) MERGE (m:User {name:$principal}) MERGE (n)-' + ace_string + '->(m)', group=i, principal=p)

        print("Marking some users as Kerberoastable")
        i = random.randint(10, 20)
        i = min(i, len(it_users))
        for user in random.sample(it_users, i):
            session.run(
                'MATCH (n:User {name:$user}) SET n.hasspn=true', user=user)

        print("Adding unconstrained delegation to a few computers")
        i = random.randint(10, 20)
        i = min(i, len(computers))
        session.run(
            'MATCH (n:Computer {name:$user}) SET n.unconstrainteddelegation=true', user=user)

        session.run('MATCH (n:User) SET n.owned=false')
        session.run('MATCH (n:Computer) SET n.owned=false')
        session.run('MATCH (n) SET n.domain=$domain', domain=self.domain)

        # print("Creating network connections between groups")
        # open_network_access = [("APPS_IT", "OPERATIONS"), ("APPS_IT","HR"),("APPS_IT","MARKETING"),("APPS_IT","BUSINESS"),("IT","APPS_IT"),
        #                         ("APPS_IT", "APPS_HR"), ("APPS_IT", "APPS_MARKETING"), ("APPS_IT", "APPS_BUSINESS"),
        #                        ("APPS_IT", "APPS_OPERATIONS"),("HR", "APPS_HR"), ("OPERATIONS", "APPS_OPERATIONS"),
        #                        ("MARKETING", "APPS_MARKETING"),("BUSINESS", "APPS_BUSINESS")]
        #                        # ("APPS_IT","APPS_IT"),("APPS_BUSINESS", "APPS_BUSINESS"),("APPS_OPERATIONS", "APPS_OPERATIONS"),
        #                        # ("APPS_HR", "APPS_HR"),("APPS_MARKETING", "APPS_MARKETING")]
        #
        #
        # for access in open_network_access:
        #     source_group = access[0] + '@' + self.domain
        #     dest_group = access[1] + '@' + self.domain
        #
        #     result = session.run('MATCH (g1:Group {name:$source_group}) WITH g1 MATCH (g2:Group {name:$dest_group}) WITH g1,g2 MERGE (g1)-[:Open]-(g2)',source_group=source_group,dest_group=dest_group)

        print("Connecting all hosts to the DCs")
        session.run('MATCH (dc:Computer)-[:MemberOf]->(:Group {name:"DOMAIN CONTROLLERS@$domain"}) MATCH (c:Computer) WHERE c <> dc WITH c,dc MERGE (c)-[:Open]->(dc)',domain=self.domain)

        # print("Creating open edges between hosts that are members of connected groups")
        # session.run('MATCH (c1:Computer)-[:MemberOf]->(g1:Group) MATCH (c2:Computer)-[:MemberOf]->(g2:Group) WHERE c1 <> c2 WITH c1,c2,g1,g2 MATCH (c1)-[:MemberOf]->(g1)-[:Open]->(g2)<-[:MemberOf]-(c2) MERGE (c1)-[:Open]->(c2)')


        print("Closing session...")
        session.close()

        print("Database Generation Finished!")


if __name__ == '__main__':
    try:
        MainMenu().cmdloop()
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit()
