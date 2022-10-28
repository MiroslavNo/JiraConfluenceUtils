from jico_utils import JiCoUtils
import credentials

def find_missing_approver_table():
    jico = JiCoUtils(credentials.SERVER_URL['PROD'], 'find_no_table.log')
    jico.logging.info('Start\n')

    #jql_query = 'type = "Access Request" AND project = "PMT X-Solution Support" and status in (Resolved, Closed) AND Organization = "PMT (PMT Solution)" AND "Support Level" in \
    #            ("PMT Tec Support") AND resolution not in (Canceled, Cancelled, Closed)'

    # ahmad ahmadi
    jql_query = 'type = "Access Request" AND project = "PMT X-Solution Support" and status in (Resolved, Closed) AND Organization = "PMT (PMT Solution)" AND "Support Level" in \
                ("PMT Tec Support") AND resolution not in (Canceled, Cancelled, Closed) AND cf[10202] != "Remove Access (ESSD)" AND updated > -210d AND assignee = v8vkkt2'

    all_ars = jico.search_jira_issues(jql_query, ["key"])
    print('query returned {} tickets'.format(len(all_ars)))

    key_list = [entry['key'] for entry in all_ars]

    for key in key_list:
        if not jico.is_tabelle_in_comments(key):
            if not jico.is_remove_access_ticket(key):
                print(key)
                jico.logging.info('Found {}'.format(key))

find_missing_approver_table()