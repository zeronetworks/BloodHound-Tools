from argparse import ArgumentParser
from cornershot.cornershot import CornerShot
from neo4j import GraphDatabase
from cornershot import logger
import logging

DEFAULT_NUM_THREADS = 200

class NeoConnector(object):
    def __init__(self,db_user,db_pass,db_url,domain,domain_user,domain_password,wthreads,use_encryption=False):
        self.url = db_url
        self.db_user = db_user
        self.db_password = db_pass
        self.domain_user = domain_user
        self.domain_password = domain_password
        self.domain = domain
        self.use_encryption = False
        self.driver = None
        self.connected = False
        self.use_encryption = use_encryption
        self.paths = []
        self.wthreads = wthreads

    def connect(self):
        self.connected = False
        if self.driver is not None:
            self.driver.close()
        try:
            self.driver = GraphDatabase.driver(self.url, auth=(self.db_user, self.db_password), encrypted=self.use_encryption)
            self.connected = True
            logger.info("Database Connection Successful!")
            return True
        except Exception as err:
            self.connected = False
            logger.info(f"Database Connection Failed - {err}")
            return False

    def find_paths(self,srcname=None,trgtname=None):
        try:
            session = self.driver.session()
            if not (srcname or trgtname):
                dadmin_group = "DOMAIN ADMINS@{}".format(self.domain)
                query = "MATCH p=shortestPath((n:Computer)-[:MemberOf|HasSession|AdminTo*1..]->(m:Group {name:$dadmin_group})) WHERE NOT n=m RETURN p"
                result = session.run(query, dadmin_group=dadmin_group)
                self.parse_paths(result)
        except Exception as err:
            logger.info(f'error during neo4j query - {err}')
            return False

        return True

    def generate_shots(self):
        shots = []
        for p in self.paths:
            comp_in_path = [x.replace('Computer:','').replace('@','.') for x in p if 'Computer:' in x]
            total_computers = len(comp_in_path)
            if total_computers > 1:
                for src_ix in range(total_computers):
                    if src_ix + 1 < total_computers:
                        for dst_ix in range(src_ix + 1,len(comp_in_path)):
                            shots.append((comp_in_path[src_ix],comp_in_path[dst_ix]))

        # Removing duplicates
        no_dup_shots = []
        for shot in shots:
            if shot not in no_dup_shots:
                no_dup_shots.append(shot)

        return no_dup_shots

    def validate_paths(self):
        logger.info('Validating paths with ** CornerShot **')
        shots = self.generate_shots()
        cs = CornerShot(self.domain_user, self.domain_password, self.domain, workers=self.wthreads)
        for shot in shots:
            cs.add_shots([shot[0]],[shot[1]])
        cs.open_fire()

    def _get_node_name_or_id(self,obj,field_name):
        name = obj[field_name] if field_name in obj else obj.id
        if obj.labels and "Computer" in obj.labels:
            name = "Computer:" + name
        return name

    def path_to_str(self,path):
        pstr = ''
        for idx in range(len(path)):
            if idx % 2 == 0:
                pstr += f'({path[idx]})'
            else:
                pstr += f'-[{path[idx]}]->'
        return pstr


    def parse_paths(self,paths):
        total_paths = 0
        if paths:
            for path in paths:
                p = []
                for indx in range(len(path[0].relationships)):
                    src_node = path[0].nodes[indx]
                    rel = path[0].relationships[indx]

                    src_name = self._get_node_name_or_id(src_node,'name')
                    rel_name = rel.type

                    p.append(src_name)
                    p.append(rel_name)

                final_node = self._get_node_name_or_id(path[0].nodes[-1],'name')
                p.append(final_node)
                total_paths += 1
                logger.debug(f"Logical path: {self.path_to_str(p)}")
                self.paths.append(p)
        logger.info(f'Query returned {total_paths} logical paths')


def parse_args():
    parser = ArgumentParser(prog="ShotHound", prefix_chars="-/", add_help=False, description=f'Finding practical paths in BloodHound')

    parser.add_argument('-h', '--help', '/?', '/h', '/help', action='help', help='show this help message and exit')
    parser.add_argument("domain_user", help="provide any authenticated user in the domain", type=str)
    parser.add_argument("domain_password", help="domain password", type=str)
    parser.add_argument("domain", help="a FQDN", type=str)
    parser.add_argument("--dbuser",dest="dbuser",default="neo4j",help="neo4j db user name",type=str)
    parser.add_argument("--dbpass", dest="dbpass", default="neo4j", help="neo4j db password", type=str)
    parser.add_argument("--dburl", dest="dburl", default="bolt://localhost:7687", help="neo4j db url", type=str)
    parser.add_argument('-v', dest='verbose', action='store_true', help='enable verbose logging')
    parser.add_argument("-w", "--workerthreads", dest='threads', help="number of threads to perform shots", default=DEFAULT_NUM_THREADS, type=int)

    args = parser.parse_args()

    return args

def set_logger(is_verbose):
    log_level = logging.DEBUG if is_verbose else logging.INFO

    logger.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

if __name__ == '__main__':
    try:
        cs = None
        nc = None
        args = parse_args()
        set_logger(args.verbose)
        logger.info('ShotHound starting...')

        nc = NeoConnector(db_user=args.dbuser,db_pass=args.dbpass,db_url=args.dburl,domain=args.domain,domain_user=args.domain_user,domain_password=args.domain_password,wthreads=args.threads)
        if nc.connect():
            if nc.find_paths():
                nc.validate_paths()




        #
        # cs.add_shots(parse_ip_ranges(args.destination), parse_ip_ranges(args.target), target_ports=parse_port_ranges(args.tports))
        # cs.open_fire()

    except KeyboardInterrupt:
        logger.info("Interrupted!")
    except Exception as err:
        logger.error(f"ShotHound got exception - {err}")
        logger.debug(f"ShotHound unexpected exception!", exc_info=True)
    finally:
        logger.info('ShotHound finished...')
