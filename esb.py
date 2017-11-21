# -*- coding: utf-8 -*-

import datetime
import itertools
import requests
from errbot import BotPlugin, botcmd, arg_botcmd, utils


class ESBPlugin(BotPlugin):

    CONFIG_TEMPLATE = {
        'PROTOCOL': 'http',
        'HOST': 'esb-test.utb.coop',
        'TIAMP_PORT': '8091',
        'TIAMP_PATH': 'api/system/tiamp',
        'PROJECT_URL_TEMPLATE': '{PROTOCOL}://{HOST}:{TIAMP_PORT}/{TIAMP_PATH}/project/{project_id}?client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}',
        'EMPLOYEE_URL_TEMPLATE': '{PROTOCOL}://{HOST}:{TIAMP_PORT}/{TIAMP_PATH}/employee/{employee_id}?client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}',
        'CLIENT_ID': '',
        'CLIENT_SECRET': '',
        'HTTP_PROXY': '',
        'HTTPS_PROXY': '',
    }

    def get_configuration_template(self):
        return self.CONFIG_TEMPLATE

    def check_configuration(self, configuration=None):
        if not configuration:
            configuration = dict()
        invalid_keys = list()
        invalid_values = dict()
        for key, value in configuration.items():
            if key in self.CONFIG_TEMPLATE:
                validator = getattr(self, 'check_{}'.format(key.lower()))
                try:
                    validator(value)
                except ValueError as e:
                    invalid_values[key] = str(e)
            else:
                invalid_keys.append(key)
        invalid_keys.sort()
        if invalid_keys or invalid_values:
            error_msg = ''
            if invalid_keys:
                error_msg += 'invalid keys: ' + ', '.join(invalid_keys)
                if invalid_values:
                    error_msg += '; '
            if invalid_values:
                error_msg += '; '.join('invalid value for key "{}": {}'.format(key, value) for key, value in invalid_values.items())
            raise utils.ValidationException(error_msg)

    def configure(self, configuration=None):
        if not configuration:
            configuration = dict()
        config = dict(itertools.chain(self.CONFIG_TEMPLATE.items(), configuration.items()))
        super(ESBPlugin, self).configure(config)

    def get_project_url(self, project_id):
        return self.config['PROJECT_URL_TEMPLATE'].format(project_id=project_id, **self.config)

    def get_employee_url(self, employee_id):
        return self.config['EMPLOYEE_URL_TEMPLATE'].format(employee_id=employee_id, **self.config)

    def to_short_date(self, isoformat):
        if not isoformat:
            return ''
        return datetime.datetime.strptime(isoformat, '%Y-%m-%dT%H:%M:%SZ').strftime('%d/%m/%Y')
    
    # Passing split_args_with=None will cause arguments to be split on any kind
    # of whitespace, just like Python's split() does
    @botcmd(split_args_with=None)
    def esb(self, message, args):
        proxies = dict(http=self.config['HTTP_PROXY'], https=self.config['HTTPS_PROXY'])
        PROJECT_VALID_VALUES = ('p', 'project', 'imputation')
        EMPLOYEE_VALID_VALUES = ('e', 'employee', 'salarie', 'salarié')
        VALID_VALUES = PROJECT_VALID_VALUES + EMPLOYEE_VALID_VALUES
        if len(args) < 1:
            return 'Erreur : veuillez renseigner un type d\'entité (imputation ou salarié)'
        type_ = args[0]
        if type_ not in VALID_VALUES:
            return 'Erreur : veuillez renseigner un type d\'entité valide (imputation ou salarié)'
        if type_ in PROJECT_VALID_VALUES:
            if len(args) != 2:
                return 'Erreur : veuillez fournir un code d\'imputation'
            project_id = args[1]
            url = self.get_project_url(project_id)
            response = requests.get(url, proxies=proxies)
            if 200 <= response.status_code < 300:
                d = response.json()
                for k in d:
                    if d[k] is None:
                        d[k] = ''
                d['start_date'] = self.to_short_date(d['start_date'])
                d['invoice_date'] = self.to_short_date(d['invoice_date'])
                result = '''Imputation {id}
{label}
Affaire : {business_id}
Marché : {market_id}
Centre de gestion : {department_id}
Identifiant du client : {customer_id}
Matricule du responsable : {employee_responsible_id}
Date de début : {start_date}
Date de facturation : {invoice_date}'''.format(**d)
                return result
            else:
                return 'Erreur : {message}'.format(**response.json())
        elif type_ in EMPLOYEE_VALID_VALUES:
            if len(args) != 2:
                return 'Erreur : veuillez fournir un matricule'
            employee_id = args[1]
            url = self.get_employee_url(employee_id)
            response = requests.get(url, proxies=proxies)
            if 200 <= response.status_code < 300:
                d = response.json()
                for k in d:
                    if d[k] is None:
                        d[k] = ''
                d['contract_start_date'] = self.to_short_date(d['contract_start_date'])
                result = '''Salarié {id}
{first_name} {last_name}
Login : {login}
Centre de gestion : {department_id}
Adresse e-mail : {work_email}
Date du début du contrat : {contract_start_date}'''.format(**d)
                return result
            else:
                return 'Erreur : {message}'.format(**response.json())
        return response

