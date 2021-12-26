from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import logging
import json
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from cornershot import logger


def parse_args():
    parser = ArgumentParser(prog='BloodHound Data Loader', formatter_class=ArgumentDefaultsHelpFormatter,
                            description='Load Cornershot data into BloodHound')
    parser.add_argument('--dbuser', dest='dbuser', default='neo4j', help='neo4j user name', type=str)
    parser.add_argument('--dbpass', dest='dbpass', default='neo4j', help='neo4j db password', type=str)
    parser.add_argument('--dburl', dest='dburl', default='bolt://localhost:7687', help='neo4j db url')
    parser.add_argument('--dbencrypt', dest='dbencrypt', action='store_true', help='neo4j set encrypted connection')
    parser.add_argument('filename', nargs='?', default='cornershot.json', help='cornershot output filename')

    return parser.parse_args()


def get_data_from_json(filename):
    with open(filename) as json_file:
        return json.load(json_file)


def get_network_access_pairs(cornershot_data):
    sources = []
    destinations = []
    for source_host in cornershot_data.keys():
        destinations_for_host = []
        for destination_host in cornershot_data[source_host].keys():
            if 'open' in cornershot_data[source_host][destination_host].values():
                destinations_for_host.append(destination_host)

        if destinations_for_host:
            sources.append(source_host)
            destinations.append(destinations_for_host)
    return sources, destinations


def connect_to_neo4j(neo4j_url, neo4j_user, neo4j_pass, neo4j_encrypt):
    try:
        driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_user, neo4j_pass), encrypted=neo4j_encrypt)
        with driver.session() as session:
            session.run('Match () Return 1 Limit 1')
    except ServiceUnavailable:
        logger.error('Can\'t connect to Neo4j server')
    except AuthError:
        logger.error('Neo4j authentication failed')
    else:
        return driver


def load_data_to_neo4j(hosts_connectivity_data, neo4j_driver):
    src_names, dst_names = hosts_connectivity_data
    with neo4j_driver.session() as session:
        session.run('WITH $srcnames AS srcnames,$destnamelist AS destnamelist '
                    'UNWIND srcnames AS srcname '
                    'WITH srcnames,srcname,destnamelist,reduce(ix = -1, i IN RANGE(0,SIZE(srcnames)-1) '
                    '| CASE srcnames[i] WHEN srcname THEN i ELSE ix END) AS six  '
                    'MATCH (src {name:srcname}) '
                    'MATCH (dst:Computer) WHERE dst.name IN destnamelist[six] '
                    'MERGE (src)-[:Open]->(dst)',
                    srcnames=src_names, destnamelist=dst_names)


def setup_logging():
    logging_level = logging.INFO
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging_level)

    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)


def main():
    setup_logging()
    args = parse_args()
    logger.info(f'Loading data from {args.filename}...')
    cornershot_data = get_data_from_json(args.filename)
    hosts_connectivity_data = get_network_access_pairs(cornershot_data)
    logger.info(f'Found data for {len(hosts_connectivity_data[0])} sources')

    neo4j_driver = connect_to_neo4j(args.dburl, args.dbuser, args.dbpass, args.dbencrypt)
    if not neo4j_driver:
        return

    logger.info(f'Loading data to Neo4j server ({args.dburl})')
    load_data_to_neo4j(hosts_connectivity_data, neo4j_driver)
    logger.info('Done.')


if __name__ == '__main__':
    main()
