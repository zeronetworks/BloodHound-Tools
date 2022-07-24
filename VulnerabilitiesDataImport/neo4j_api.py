from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from log_utils import logger


class Neo4jLoader(object):

    def __init__(self, neo4j_url, neo4j_user, neo4j_pass, neo4j_encrypt):
        self.neo4j_url = neo4j_url
        self.neo4j_user = neo4j_user
        self.neo4j_pass = neo4j_pass
        self.neo4j_encrypt = neo4j_encrypt
        self.connected = False
        self._connect_to_neo4j()

    def _connect_to_neo4j(self):
        try:
            self.driver = GraphDatabase.driver(self.neo4j_url,
                                               auth=(self.neo4j_user, self.neo4j_pass),
                                               encrypted=self.neo4j_encrypt)
            with self.driver.session() as session:
                session.run('Match () Return 1 Limit 1')
                self.connected = True
        except ServiceUnavailable:
            logger.error('Can\'t connect to Neo4j server')
        except AuthError:
            logger.error('Neo4j authentication failed')

    def load_data_to_neo4j(self, vulnerabilities_data):
        logger.debug(f'Loading vulnerabilities to Neo4j server ({self.neo4j_url})')
        with self.driver.session() as session:
            result = session.run('WITH $vulnerabilities_data AS vulnerabilities_data '
                                 'UNWIND vulnerabilities_data as vulnerability_data '
                                 'MATCH (c:Computer {name: vulnerability_data[0]}) '
                                 'SET c.is_vulnerable = TRUE, c.cves = vulnerability_data[1] '
                                 'RETURN c.name',
                                 vulnerabilities_data=vulnerabilities_data)
            inserted_hosts = len([computer_name for computer_name in result])
            logger.info(f'Matched {inserted_hosts} hosts in Neo4j')
