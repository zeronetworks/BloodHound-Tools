import traceback
from abc import ABC, abstractmethod
import ipaddress
from enum import Enum
import xml.etree.ElementTree as ET
import pandas as pd
from log_utils import logger


vulnerabilities = pd.DataFrame(columns=['Hostname', 'CVE'])
ip_host_mapping = {}


class NessusRisk(Enum):
    Critical = 5
    High = 4
    Medium = 3
    Low = 2
    Info = 1


def is_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


class ReportParser(ABC):
    """
    Parent abstract class for vulnerability scanners report parsers
    Subclasses must implement a get_vulnerabilities method which returns a pandas DataFrame with columns:
    [Hostname', 'CVE', 'IP']
    """

    def __init__(self, args):
        self.args = args

    @staticmethod
    def _merge_cves(cves):
        all_cves = []
        for cve in cves:
            all_cves += cve.split(', ')
        unique_cves = list(set(all_cves))
        return ', '.join([cve for cve in unique_cves if cve])

    @property
    def _scanner_name(self):
        return type(self).__name__[:-len('Parser')]

    def _is_report_file(self):
        if not getattr(self.args, self._scanner_name.lower()):
            return False
        else:
            return True

    @staticmethod
    def _add_ip_host_mapping(df):
        for row in df.groupby('Hostname', as_index=False).agg({'IP': 'unique'}).iterrows():
            hostname = row[1].Hostname
            if is_ip(hostname):
                continue

            for ip in row[1].IP:
                ip_host_mapping[ip] = hostname

    @staticmethod
    def _ip_to_hostname(hostname):
        if is_ip(hostname):
            mapped_hostname = ip_host_mapping.get(hostname)
            if mapped_hostname:
                logger.debug(f'Converted IP to host: {hostname} -> {mapped_hostname}')
                return mapped_hostname
        return hostname

    def _convert_to_fqdn(self, hostname):
        domain = '.' + self.args.domain.upper() if self.args.domain else None
        if is_ip(hostname) or not domain or hostname.endswith(domain):
            return hostname
        fqdn = hostname + domain
        logger.debug(f'Updated FQDN for host {hostname} -> {fqdn}')
        return fqdn

    def add_vulnerabilities(self):
        if not self._is_report_file():
            return

        logger.debug(f'Parsing {self._scanner_name} report: {self._report_path}')
        global vulnerabilities
        pd.options.mode.chained_assignment = None
        try:
            report_vulnerabilities = self.get_vulnerabilities()
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(stack_trace)
            logger.info(f'Failed parsing {self._scanner_name} report: {e}')
            return

        if report_vulnerabilities is None or report_vulnerabilities.empty:
            return

        pd.options.mode.chained_assignment = 'warn'

        report_vulnerabilities['Hostname'] = report_vulnerabilities['Hostname'].str.upper()
        self._add_ip_host_mapping(report_vulnerabilities)
        vulnerabilities_df = pd.concat([vulnerabilities, report_vulnerabilities])
        vulnerabilities_df.Hostname = vulnerabilities_df.Hostname.map(self._ip_to_hostname)
        vulnerabilities_df.Hostname = vulnerabilities_df.Hostname.map(self._convert_to_fqdn)
        grouped_df = vulnerabilities_df.groupby('Hostname', as_index=False).agg({'CVE': 'unique'})
        grouped_df.CVE = grouped_df.CVE.map(self._merge_cves)

        logger.debug(f'Found {report_vulnerabilities.Hostname.nunique()} vulnerable hosts from {self._scanner_name} '
                     f'report')
        vulnerabilities = grouped_df

    @property
    def _report_path(self):
        return getattr(self.args, self._scanner_name.lower())

    def _load_csv_report(self, **kwargs):
        try:
            return pd.read_csv(self._report_path, **kwargs)
        except (FileNotFoundError, UnicodeDecodeError):
            logger.info(f'Failed loading {self._scanner_name} report file {self._report_path}')

    def _load_xml_report(self):
        try:
            tree = ET.parse(self._report_path)
            return tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            logger.info(f'Failed loading {self._scanner_name} report file {self._report_path}')

    @abstractmethod
    def get_vulnerabilities(self):
        pass


class QualysParser(ReportParser):

    def get_vulnerabilities(self):
        report_df = self._load_csv_report(skiprows=7)
        if report_df is None or report_df.empty:
            return

        report_df = report_df[report_df.Severity != '']
        report_df.Severity = report_df.Severity.map(lambda severity: float(severity))
        vulnerabilities_df = report_df[(report_df.Severity >= self.args.risk_score) & (report_df.Type == 'Vuln')]
        vulnerabilities_df.fillna('', inplace=True)
        vulnerabilities_df['Hostname'] = vulnerabilities_df.DNS.map(lambda dns: dns.upper())
        vulnerabilities_df.rename(columns={'CVE ID': 'CVE'}, inplace=True)
        return vulnerabilities_df[['Hostname', 'CVE', 'IP']]


class NessusParser(ReportParser):

    @staticmethod
    def convert_nessus_fqdn_plugin_to_hostname(plugin_output):
        return plugin_output.split(' resolves as ')[1].rstrip('.\n').upper()

    @staticmethod
    def _get_nessus_ip_to_hostname_dataframe(report):
        host_to_ip = []
        for row in report.iterrows():
            try:
                if row[1].Name == 'Host Fully Qualified Domain Name (FQDN) Resolution':
                    hostname = row[1]['Plugin Output'].split(' resolves as ')[1].rstrip('.\n').upper()
                    host_to_ip.append([row[1].Host, hostname])
                elif row[1].Name == 'Windows NetBIOS / SMB Remote Host Information Disclosure':
                    hostname = row[1]['Plugin Output'].split('\n\n ')[1].split(' ')[0]
                    host_to_ip.append([row[1].Host, hostname])
                elif row[1].Name == 'Microsoft Windows SMB LanMan Pipe Server Listing Disclosure':
                    hostname = row[1]['Plugin Output'].split('\n\n')[1].split(' ')[0]
                    host_to_ip.append([row[1].Host, hostname])
                elif row[1].Name == 'Microsoft Windows SMB NativeLanManager Remote System Information Disclosure':
                    if 'Nessus was able to obtain the following information about the host' in row[1]['Plugin Output']:
                        hostname = row[1]['Plugin Output'].split('NetBIOS Domain Name: ')[1].split('\n')[0]
                    else:
                        hostname = row[1]['Plugin Output'].split('The remote SMB Domain Name is : ')[1].rstrip('\n')
                    host_to_ip.append([row[1].Host, hostname])
            except IndexError:
                plugin_name = row[1].Name
                plugin_output = row[1]['Plugin Output']
                logger.warning(f'Failed to parse hostname. Plugin name: {plugin_name}, Plugin output: {plugin_output}')

        host_ip_df = pd.DataFrame(host_to_ip, columns=['Host', 'Hostname'])
        return host_ip_df.groupby('Host', as_index=False).agg({'Hostname': 'max'})

    def risk_score_to_category(self):
        return [NessusRisk(i).name for i in range(self.args.risk_score, len(NessusRisk.__members__) + 1)]

    def get_vulnerabilities(self):
        report = self._load_csv_report()
        if report is None or report.empty:
            return

        report.fillna('', inplace=True)
        ip_to_hostname = self._get_nessus_ip_to_hostname_dataframe(report)
        vulnerabilities_df = report[report['Risk'].isin(self.risk_score_to_category())].fillna('')
        vulnerabilities_df = vulnerabilities_df.merge(ip_to_hostname, on='Host', how='left')
        vulnerabilities_df['Hostname'].fillna(vulnerabilities_df['Host'], inplace=True)
        vulnerabilities_df.rename(columns={'Host': 'IP'}, inplace=True)
        return vulnerabilities_df[['Hostname', 'CVE', 'IP']]


class OpenVASParser(ReportParser):

    def get_vulnerabilities(self):
        report_df = self._load_csv_report()
        if report_df is None or report_df.empty:
            return

        relevant_vulnerabilities = report_df[report_df.CVSS >= (self.args.risk_score * 2) - 1]
        relevant_vulnerabilities['Hostname'].fillna(relevant_vulnerabilities['IP'], inplace=True)
        relevant_vulnerabilities.fillna('', inplace=True)
        relevant_vulnerabilities.CVEs = relevant_vulnerabilities.CVEs.map(lambda cves: cves.replace(',', ', '))

        relevant_vulnerabilities.rename(columns={'CVEs': 'CVE'}, inplace=True)
        return relevant_vulnerabilities[['Hostname', 'CVE', 'IP']]


class NmapParser(ReportParser):

    @staticmethod
    def _clean_line(output_line):
        return output_line.lstrip(' ').rstrip(':')

    def _get_cve(self, script_output):
        for line in script_output:
            if self._clean_line(line).startswith('IDs:'):
                return script_output[3].split('CVE:')[-1]

    @staticmethod
    def _get_hostname(host_tree):
        for hostname in host_tree.findall('hostnames'):
            for host in hostname.findall('hostname'):
                return host.attrib.get('name').upper()
        return ''

    @staticmethod
    def _get_host_ip(host_tree):
        for address in host_tree.findall('address'):
            if address.attrib.get('addrtype') == 'ipv4':
                return address.attrib.get('addr')
        return ''

    def get_vulnerabilities(self):
        nmap_vulnerabilities = []
        root = self._load_xml_report()
        for host in root.findall('host'):
            hostname = self._get_hostname(host)
            host_ip = self._get_host_ip(host)
            for hostscript in host.findall('hostscript'):
                for script in hostscript.findall('script'):
                    script_output = [line for line in script.get('output').split('\n') if line]
                    if self._clean_line(script_output[0]) == 'VULNERABLE':
                        nmap_vulnerabilities.append([hostname, self._get_cve(script_output), host_ip])

        return pd.DataFrame(nmap_vulnerabilities, columns=['Hostname', 'CVE', 'IP'])


def parse_all_vulnerabilities(args):
    logger.info('Parsing vulnerabilities from reports...')
    for child_class in ReportParser.__subclasses__():
        parser_class = child_class(args)
        parser_class.add_vulnerabilities()
    logger.debug(f'Vulnerable hosts parsed from the reports: {", ".join(vulnerabilities.Hostname.unique())}')
    return vulnerabilities.values.tolist()
