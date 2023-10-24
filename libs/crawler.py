import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re
import ast


class IECrawler:
    def __init__(self):
        self.user_agent = UserAgent()
        self.base_url = 'http://nfe.sefaz.ba.gov.br/servicos/nfenc/Modulos/Geral/NFENC_consulta_cadastro_ccc.aspx'
        self.fields = ['cnpj', 'ie', 'razao_social', 'uf', 'situacao']
        self.pages = {
            'current': 0,
            'total': 0
        }
        self.payload = {}
        self.headers = {}
        self.__initialize()

    def __initialize(self):
        response = self.__get(self.base_url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch the page. Status code: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')
        self.__extract_payload(soup)
        self.__set_headers(response)

    def __get(self, url):
        headers = {'User-Agent': self.user_agent.random}
        return requests.get(url, headers=headers)

    def __extract_payload(self, soup):
        input_fields = ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']
        for field in input_fields:
            self.payload[field] = soup.find('input', {'name': field})['value']
        self.payload['__VIEWSTATEENCRYPTED'] = ''
        self.payload['__EVENTTARGET'] = ''
        self.payload['__EVENTARGUMENT'] = ''
        self.payload['txtCNPJ'] = ''
        self.payload['txtie'] = ''
        self.payload['CmdUF'] = ''
        self.payload['CmdSituacao'] = '99'
        self.payload['AplicarFiltro'] = 'Aplicar+Filtro'

    def __set_headers(self, response):
        self.headers = {
            'User-Agent': self.user_agent.random,
            'Cookie': '; '.join([f'{cookie.name}={cookie.value}' for cookie in response.cookies])
        }

    def __set_params(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        input_fields = ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']
        for field in input_fields:
            self.payload[field] = soup.find('input', {'name': field})['value']
        self.payload['__EVENTTARGET'] = 'Grid'
        self.payload['__EVENTARGUMENT'] = f'Page${int(self.pages["current"]) + 1}'
        self.payload.pop('AplicarFiltro', None)

    def get_ie(self, pie):
        self.payload['txtie'] = pie
        out = []
        while True:
            try:
                response = self.__post(self.base_url, data=self.payload, headers=self.headers)
                if response.status_code != 200:
                    raise Exception(f"Failed to fetch the page. Status code: {response.status_code}")

                out.extend(self.__parse(response.text))

                if int(self.pages['current']) >= int(self.pages['total']):
                    return out

                self.__set_params(response.text)
            except Exception as e:
                print(e)

    def __post(self, url, data, headers):
        return requests.post(url, data=data, headers=headers, timeout=60, allow_redirects=False)

    def __parse(self, text_html):
        ie_list = []
        soup = BeautifulSoup(text_html, "html.parser")

        if soup.find('span', {'id': 'lblConsultaVazia'}):
            return ie_list

        table = soup.find('table', {'id': 'Grid'})
        if table:
            rows = table.find_all('tr')[1:]
            for row in rows:
                ie_data = {}
                cols = row.find_all('td')
                if row.find_all('a'):
                    self.__read_page(row)
                else:
                    for field, col in zip(self.fields, cols):
                        ie_data[field] = col.text.strip()
                    ie_list.append(ie_data)
        return ie_list

    def __read_page(self, row):
        p = row.find_all('a')
        self.pages['current'] = row.find_all('span')[0].text.strip()
        self.pages['total'] = p[-1]['href'].split('Page$')[-1].rstrip("')")

    @staticmethod
    def __extract_numbers(input_string):
        return re.sub(r'\D', '', input_string)

    @staticmethod
    def __convert_to_boolean(value):
        try:
            return ast.literal_eval(value.title())
        except (ValueError, SyntaxError):
            return None
