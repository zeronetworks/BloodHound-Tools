from neo4j import GraphDatabase
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor,as_completed,thread
import sys
import csv

PRACTICAL = 'practical'
LOGICAL = 'logical'
NETONLY = 'netonly'
rans = None

class ransomulator(object):
    def __init__(self,user,password,url,maxwaves,edges,simulate,workers=25):
        self.url = url
        self.username = user
        self.password = password
        self.use_encryption = False
        self.driver = None
        self.connected = False
        self.maxwaves = 1 if LOGICAL in simulate else maxwaves
        self.session = None
        self.edges = edges
        self.simulate = simulate
        self.workers = workers
        self.executor = ThreadPoolExecutor(max_workers=workers)

    def connect(self):
        self.connected = False
        if self.driver is not None:
            self.driver.close()
        try:
            self.driver = GraphDatabase.driver(
                self.url, auth=(self.username, self.password), encrypted=self.use_encryption)
            self.connected = True
            print("Database Connection Successful.")
        except:
            self.connected = False
            print("Database Connection Failed.")

        return self.connected

    def get_all_computers(self):
        print("Collecting all computer nodes from database...")
        result = self.session.run("MATCH (c:Computer) RETURN DISTINCT c.name AS computer_name")
        computers = []
        for record in result:
            computers.append(record["computer_name"])

        return computers

    def generate_wave_query_string(self):
        if LOGICAL in self.simulate:
            # return 'MATCH (src)-[:HasSession]->(u:User) WHERE src.name IN $last_wave WITH src,u MATCH shortestPath((u)-[:MemberOf|AdminTo*1..]->(dest:Computer)) WHERE NOT dest IN $last_wave RETURN COLLECT(DISTINCT(dest.name)) AS next_wave'
            return 'MATCH shortestPath((src:Computer)-[: HasSession | MemberOf | AdminTo * 1..]->(dest:Computer)) WHERE src <> dest AND src.name IN $last_wave AND NOT dest IN $last_wave RETURN COLLECT(DISTINCT(dest.name)) AS next_wave'
        elif NETONLY in self.simulate:
            return 'MATCH (src:Computer)-[:Open]->(dest:Computer) WHERE src.name IN $last_wave AND NOT dest.name IN $last_wave RETURN COLLECT(DISTINCT(dest.name)) AS next_wave'
        elif PRACTICAL in self.simulate:
            return 'MATCH (src:Computer)-[:Open]->(dest:Computer) WHERE src.name IN $last_wave AND NOT dest.name IN $last_wave WITH src,dest MATCH (src)-[:HasSession]->(u:User) WITH dest,u MATCH shortestPath((u)-[:MemberOf|AdminTo*1..]->(dest)) RETURN COLLECT(DISTINCT(dest.name)) AS next_wave'
        else:
            return None

    def simulate_wave_for_computer(self,computer_name):
        last_wave = [computer_name]
        computer_waves = [computer_name]
        waves = []
        total = 0
        for wave in range(self.maxwaves):
            w_str = self.generate_wave_query_string()
            mysession = self.driver.session()
            result = mysession.run(w_str,last_wave=last_wave)
            for record in result:
                next_wave = record["next_wave"]
                wave_size = len(next_wave)
                total += wave_size
                waves.append(str(wave_size))
                last_wave += next_wave
                if wave_size == 0:
                    mysession.close()
                    return total,waves

            computer_waves.append(last_wave.copy())
            mysession.close()
        return total,waves

    def somulate(self):
        waves_dict = {}
        max_wavelen = 0
        avg_wavelen = 0
        max_total = 0
        total_comps= 0
        try:
            if not self.connected:
                print("Can't simulate without a valid DB connection!")
            else:
                self.session = self.driver.session()
                computers = self.get_all_computers()
                print("Running simulation for each computer...")
                future_to_totals_waves_pairs = {self.executor.submit(self.simulate_wave_for_computer,computer): computer for computer in computers}
                # for computer in computers:
                #     total,waves = self.simulate_wave_for_computer(computer)
                for future in as_completed(future_to_totals_waves_pairs):
                    computer = future_to_totals_waves_pairs[future]
                    try:
                        total_waves_pair = future.result()
                        total = total_waves_pair[0]
                        waves = total_waves_pair[1]
                        if total > 0:
                            total_comps += 1
                            if len(waves) > max_wavelen:
                                max_wavelen = len(waves)

                            if total > max_total: max_total = total
                            avg_wavelen += len(waves)

                            waves_dict[computer] = {"total":total,"waves":waves}
                            print("{},{},{}".format(computer,str(total),",".join(waves)))
                        else:
                            waves_dict[computer] = {"total": 0, "waves": ['0']}
                            print("{} - no waves".format(computer))
                    except Exception as exc:
                        print('Exception while processing %s: %s' % (computer, exc))

                if total_comps > 0:
                    avg_wavelen = avg_wavelen / total_comps
                else: avg_wavelen = 0
                sorted_waves = {k: v for k,v in sorted(waves_dict.items(),key=lambda item: item[1]["total"],reverse=True)}
                return sorted_waves,max_wavelen,avg_wavelen,max_total,total_comps

        except Exception as err:
            print("Error during simulation: {}".format(err))

    def get_waves_for_computer(self, computer):
        try:
            if not self.connected:
                print("Can't create query without a valid DB connection!")
            else:
                self.session = self.driver.session()
                total,waves,computer_waves = self.simulate_wave_for_computer(computer)
                return computer_waves

        except Exception as err:
            print("Error during simulation: {}".format(err))

    def stop(self):
        print("Stopping execution...")
        # self.executor.shutdown(wait=False,cancel_futures=True)
        self.executor._threads.clear()
        thread._threads_queues.clear()
        print("Execution stopped...")

def output_csv(file_path,wv_dict,max_wave_len):
    print("Writing results to file {}".format(file_path))
    with open(file_path,'w',encoding="utf-8",newline='') as csvfile:
        wave_headers = ['wave_' + str(x + 1) for x in range(max_wave_len)]
        header = ['Hostname','Total'] + wave_headers
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(header)
        for k in wv_dict:
            row = [k,wv_dict[k]["total"]] + wv_dict[k]["waves"]
            writer.writerow(row)

def simulate(user,password,url,maxwaves,edges,simulate,workers):
    global rans
    rans = ransomulator(user, password, url, maxwaves, edges, simulate,workers)
    if rans.connect():
        sorted_waves, max_wavelen, avg_wavelen, max_total, total_comps = rans.somulate()
        if outfile:
            output_csv(outfile, sorted_waves, max_wavelen)
    else:
        print("Error during connection...")

    print("Ransomulator done.      ")
    print("-----------------------------")
    print("Total computers with paths:\t{}".format(total_comps))
    print("Max compromised :\t{}".format(max_total))
    print("Avg wave length:\t{}".format(round(avg_wavelen, 1)))
    print("Max wave length:\t{}".format(max_wavelen))

def create_query(computer,user, password, url, maxwaves, edges, simulate):
    if LOGICAL in simulate:
        # return 'MATCH (src)-[:HasSession]->(u:User) WHERE src.name IN $last_wave WITH src,u MATCH shortestPath((u)-[:MemberOf|AdminTo*1..]->(dest:Computer)) WHERE NOT dest IN $last_wave RETURN COLLECT(DISTINCT(dest.name)) AS next_wave'
        return 'MATCH shortestPath((src:Computer)-[:HasSession|MemberOf|AdminTo* 1..]->(dest:Computer)) WHERE src <> dest AND src.name IN $last_wave AND NOT dest IN $last_wave RETURN COLLECT(DISTINCT(dest.name)) AS next_wave'
    elif NETONLY in simulate:
        return 'MATCH (src:Computer)-[:Open]->(dest:Computer) WHERE src.name IN $last_wave AND NOT dest.name IN $last_wave RETURN COLLECT(DISTINCT(dest.name)) AS next_wave'
    elif PRACTICAL in simulate:
        return 'MATCH (src:Computer)-[:Open]->(dest:Computer) WHERE src.name IN $last_wave AND NOT dest.name IN $last_wave WITH src,dest MATCH (src)-[:HasSession]->(u:User) WITH dest,u MATCH shortestPath((u)-[:MemberOf|AdminTo*1..]->(dest)) RETURN COLLECT(DISTINCT(dest.name)) AS next_wave'
    else:
        return None

def parse_args():
    parser = ArgumentParser(prog=ArgumentParser().prog,prefix_chars="-/",add_help=False,description="Simulate ransomware infection through Bloodhound's database")
    parser.add_argument('-h', '--help', '/?', '/h', '/help', action='help', help='show this help message and exit')
    parser.add_argument('-s', '--simulate', metavar='', dest='simulate', choices=[PRACTICAL, LOGICAL, NETONLY],default=PRACTICAL,help='type of lateral movement to simulate. choices: [%(choices)s], (default: practical).')
    parser.add_argument("-u", "--user", dest='user', metavar='', help="Neo4j DB user name", type=str, default="neo4j")
    parser.add_argument("-p", "--pass", dest='password', metavar='', help="Neo4j DB password", type=str,default="neo4j")
    parser.add_argument("-l", "--url", dest="url", metavar="", help="Neo4j URL", default="bolt://localhost:7687",type=str)
    parser.add_argument("-m", "--maxwaves", dest="maxwaves", type=int, default=3,help="maximal number of simulated attack waves")
    parser.add_argument("-o", "--output", dest='out_file', metavar='', help="output file name", type=str,default=None)
    parser.add_argument("-e","--edges", dest="edges", type=str,default="MemberOf",help="Logical edges between hosts")
    parser.add_argument("-w","--workers",dest="workers",type=int,default=25,help="Number of paraller queries to the database")

    subprasers = parser.add_subparsers(dest="command")
    # sim_parser = subprasers.add_parser('simulate',help='simulate infection waves')

    q_parser = subprasers.add_parser('query',help='generate Cypher query')
    q_parser.add_argument("computer", type=str, help="starting from computer name")

    # parser.add_argument("-a", "--all", dest="do_all", action="store_true", help="Run through all nodes")

    args = parser.parse_args()

    return args

if __name__ == '__main__':
    try:
        args = parse_args()

        command = args.command
        sim = args.simulate
        user = args.user
        password = args.password
        url = args.url
        maxwaves = args.maxwaves
        edges = args.edges
        outfile = args.out_file
        workers = args.workers

        if command and "query" in command:
            computer = args.computer
            print(create_query(computer,user, password, url, maxwaves, edges, sim))
        else:
            simulate(user, password, url, maxwaves, edges, sim,workers)


    except KeyboardInterrupt:
        print("Interrupted! exiting...")
        if rans:
            rans.stop()
    except Exception as err:
        print("Exception thrown: {}".format(err))
    finally:
        sys.exit()
