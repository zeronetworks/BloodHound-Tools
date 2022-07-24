from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from log_utils import logger, setup_logging, logging
from report_parsers import parse_all_vulnerabilities
from neo4j_api import Neo4jLoader


def parse_args():
    parser = ArgumentParser(prog='Scanner Data Importer', formatter_class=ArgumentDefaultsHelpFormatter,
                            description='Load Vulnerability Scanners data into BloodHound')
    parser.add_argument('--dbuser', dest='dbuser', default='neo4j', help='neo4j user name', type=str)
    parser.add_argument('--dbpass', dest='dbpass', default='neo4j', help='neo4j db password', type=str)
    parser.add_argument('--dburl', dest='dburl', default='bolt://localhost:7687', help='neo4j db url')
    parser.add_argument('--dbencrypt', dest='dbencrypt', action='store_true', help='neo4j set encrypted connection')
    parser.add_argument('-d', '--domain', dest='domain', default=None, help='domain to append for hosts without FQDN',
                        type=str)
    parser.add_argument('-db', '--debug', dest='debug', action='store_true', help='enable debug level logging')
    parser.add_argument('-n', '--nessus', nargs='?', help='Nessus csv report filename')
    parser.add_argument('-q', '--qualys', nargs='?', help='Qualys csv report filename')
    parser.add_argument('-o', '--openvas', nargs='?', help='OpenVAS csv report filename')
    parser.add_argument('-nm', '--nmap', nargs='?', help='Nmap vuln xml report filename')
    parser.add_argument('-rs', '--risk-score', nargs='?', default=5, type=int, choices=list(range(1, 5+1)),
                        help='Minimum risk score to consider a host as vulnerable')

    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(logging_level=logging.DEBUG if args.debug else logging.INFO)

    if not args.qualys and not args.nessus and not args.openvas and not args.nmap:
        logger.error('No report files supplied, add using --nessus / --qualys / --openvas / --nmap')
        return

    print('Starting...')
    print('^(;,;)^\n')

    found_vulnerabilities = parse_all_vulnerabilities(args)
    if not found_vulnerabilities:
        logger.info('No exploitable hosts found in reports')
        return

    neo4j_loader = Neo4jLoader(args.dburl, args.dbuser, args.dbpass, args.dbencrypt)
    if neo4j_loader.connected:
        logger.info(f'Found a total of {len(found_vulnerabilities)} vulnerable hosts in the reports')
        neo4j_loader.load_data_to_neo4j(found_vulnerabilities)
        logger.info('Done.')


if __name__ == '__main__':
    main()
