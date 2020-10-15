from argparse import ArgumentParser
from cornershot.cornershot import CornerShot
from neo4j import GraphDatabase
from cornershot import logger
import logging

DEFAULT_NUM_THREADS = 200

class ShotHound(object):
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
        self.logical_paths = []
        self.practical_paths = []
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

    def find_logical_paths(self, srcname=None, trgtname=None):
        try:
            session = self.driver.session()
            if not (srcname or trgtname):
                dadmin_group = "DOMAIN ADMINS@{}".format(self.domain)
                query = "MATCH p=allShortestPaths((n:Computer)-[:MemberOf|HasSession|AdminTo*1..]->(m:Group {name:$dadmin_group})) WHERE NOT n=m RETURN p"
                result = session.run(query, dadmin_group=dadmin_group)
            elif srcname and trgtname:
                query = "MATCH p=allShortestPaths((n {name:$srcname})-[:MemberOf|HasSession|AdminTo*1..]->(m {name:$trgtname})) WHERE NOT n=m RETURN p"
                result = session.run(query, srcname=srcname,trgtname=trgtname)
            elif trgtname:
                query = "MATCH p=allShortestPaths((n:Computer)-[:MemberOf|HasSession|AdminTo*1..]->(m {name:$trgtname})) WHERE NOT n=m RETURN p"
                result = session.run(query, trgtname=trgtname)
            elif srcname:
                query = "MATCH p=allShortestPaths((n {name:$srcname})-[:MemberOf|HasSession|AdminTo*1..]->(m)) WHERE NOT n=m RETURN p"
                result = session.run(query, srcname=srcname)

            self.parse_paths(result)

        except Exception as err:
            logger.info(f'error during neo4j query - {err}')
            return False

        return True

    def get_valid_paths(self):
        return self.practical_paths

    def get_logical_paths(self):
        return self.logical_paths

    def get_computers_from_path(self,path):
        return [x.replace('Computer:','').replace('@','.') for x in path if 'Computer:' in x]

    def generate_shots(self):
        shots = []
        for p in self.logical_paths:
            comp_in_path = self.get_computers_from_path(p)
            total_computers = len(comp_in_path)
            if total_computers > 1:
                for src_ix in range(total_computers):
                    if src_ix + 1 < total_computers:
                        for dst_ix in range(src_ix + 1,total_computers):
                            shots.append((comp_in_path[src_ix],comp_in_path[dst_ix]))

        no_dup_shots = []
        for shot in shots:
            if shot not in no_dup_shots:
                no_dup_shots.append(shot)

        return no_dup_shots

    def remove_impractical_paths(self,open_pairs):
        practical_paths = []
        if open_pairs:
            for path in self.logical_paths:
                valid_hops = 0
                comp_in_path = self.get_computers_from_path(path)
                total_computers = len(comp_in_path)
                comp_in_path.reverse()
                if total_computers > 1:
                    for dst_ix in range(total_computers):
                        if dst_ix + 1 < total_computers:
                            for src_ix in range(dst_ix + 1, total_computers):
                                pair_to_check = (comp_in_path[src_ix],comp_in_path[dst_ix])
                                if pair_to_check in open_pairs:
                                    valid_hops += 1
                                    break
                    if valid_hops >= total_computers - 1:
                        practical_paths.append(path)
                else:
                    logger.info(f'Practical Path: {self.path_to_str(path)}')
                    practical_paths.append(path)

        return practical_paths

    def cs_dict_to_open_pairs(self,cs_results):
        open_pairs = []
        if cs_results:
            for src_host in cs_results.keys():
                for dest_host in cs_results[src_host].keys():
                    if 'open' in cs_results[src_host][dest_host].values():
                        open_pairs.append((src_host, dest_host))
        return open_pairs

    def validate_paths(self):
        shots = self.generate_shots()
        if shots:
            logger.info('Validating paths with ** CornerShot **')
            cs = CornerShot(self.domain_user, self.domain_password, self.domain, workers=self.wthreads)
            for shot in shots:
                cs.add_shots([shot[0]],[shot[1]])
            cs.open_fire()
            logger.info('Parsing CornerShot results...')
            open_pairs = self.cs_dict_to_open_pairs(cs.read_results())
            self.practical_paths = self.remove_impractical_paths(open_pairs)
        else:
            logger.warning('No paths that involve more that 1 computer were found, no need to invoke CornerShot...')
            self.practical_paths = self.logical_paths
        return len(self.practical_paths)

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
                logger.info(f"Logical path: {self.path_to_str(p)}")
                self.logical_paths.append(p)
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
    parser.add_argument("-s", dest="source", default=None, help="source entity to start query from", type=str)
    parser.add_argument("-t", dest="target", default=None, help="target entity to end query at", type=str)
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
        sh = None
        args = parse_args()
        set_logger(args.verbose)
        logger.info('ShotHound starting...')

        sh = ShotHound(db_user=args.dbuser, db_pass=args.dbpass, db_url=args.dburl, domain=args.domain, domain_user=args.domain_user, domain_password=args.domain_password, wthreads=args.threads)
        if sh.connect():
            if sh.find_logical_paths(srcname=args.source,trgtname=args.target):
                validated = sh.validate_paths()
                total = len(sh.get_logical_paths())
                percent = 0
                if total > 0:
                    percent = round((validated / total) * 100)
                logger.info(f'---------------------------------------')
                logger.info(f'ShotHound found {validated} practical paths, which is {percent}% of total paths')

    except KeyboardInterrupt:
        logger.info("Interrupted!")
    except Exception as err:
        logger.error(f"ShotHound got exception - {err}")
        logger.debug(f"ShotHound unexpected exception!", exc_info=True)
    finally:
        logger.info('ShotHound finished...')
