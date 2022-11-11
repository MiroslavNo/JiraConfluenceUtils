from jico_utils import JiCoUtils
import credentials
import webbrowser
from datetime import datetime, timedelta

def user_continue_question(msg=None):
    if msg is not None:
        input(msg + ' - Continue? [ENTER]')
    else:
        input('Continue? [ENTER]')

def get_date_string_n_days_ago(n_days):
    today = datetime.now()    
    n_days_ago = today - timedelta(days=n_days)
    return ('{:%Y/%m/%d}'.format(n_days_ago))

def reminder_after_PO_request(jico):
    # using 6d, because it is searching for LESS THAN, e.g. 7 and more (less and equal was not working properly)
    jql = 'assignee = currentUser() AND resolution = Unresolved AND updated < "{}"'.format(get_date_string_n_days_ago(6))
    all_ars = jico.search_jira_issues(jql, ["key"])
    key_list = [entry['key'] for entry in all_ars]

    positive_cases = list()
    # loop and check if last comment was the canned response
    for key in key_list:
        if jico.is_last_comment_canned_reminder_nr1(key):
            positive_cases.append(key)
            # get requester
            ticket_reporter = jico.get_ticket_reporter(key)
            canned_reminder = f'Hi [~{ticket_reporter}],\r\n\r\nthis is a friendly reminder that your ticket has been waiting for approval. In order to proceed we need an approval from an internal PO/PM or higher. Should we not receive any answer in the next 3 working days, we will close your ticket.\r\n\r\nBest regards\r\nMiroslav'
            print('Sending reminder on issue {}'.format(key))
            jico.create_comment(canned_reminder, key, internal_bool=False)

    return positive_cases

def close_3days_after_2nd_reminder(jico):
    # get day in the week. Nr. 3 is thursday and 4 is Friday
    dt = datetime.now()
    weekday = dt.weekday()
    if weekday in [3, 4]:
        n_days_ago = 2
    else: 
        n_days_ago = 4

    jql = 'assignee = currentUser() AND resolution = Unresolved AND updated < "{}"'.format(get_date_string_n_days_ago(n_days_ago))
    all_ars = jico.search_jira_issues(jql, ["key"])
    key_list = [entry['key'] for entry in all_ars]

    positive_cases = list()
    # loop and check if last comment was the canned response
    for key in key_list:
        if jico.is_last_comment_canned_reminder_nr2(key):
            positive_cases.append(key)
            # get data from issue
            ticket_object = jico.get_issue(key)
            ticket_status = jico.get_issue_status_from_issue_obj(ticket_object)
            ticket_reporter = jico.get_ticket_reporter_from_issue_obj(ticket_object)

            if ticket_status.lower() in ['wait for customer', 'requestor confirmation']:
                status_transition_id = '21'
            else:
                print('WARN: The issue {} should be closed, but it is the status {} -> SKIPPING, please check manually')
                continue

            canned_msg_close = f'Hi [~{ticket_reporter}],\r\n\r\nI will close the ticket for now. Please do not hesitate to reopen it if you need further support. This can be done by commenting on the ticket.\r\n\r\nBest regards\r\nMiroslav'
            print('Closing ticket {} - add comment'.format(key))
            jico.create_comment(canned_msg_close, key, internal_bool=False)
            print('Closing ticket {} - status transition'.format(key))
            jico.do_transition(key, status_transition_id, 'Closed')

    return positive_cases


def main():
    jico = JiCoUtils(credentials.SERVER_URL['PROD'], '01_morning_ticket_checks.log')
    jico.logging.info('Start\n')

    reminder_positive_cases = reminder_after_PO_request(jico)
    close_positive_cases = close_3days_after_2nd_reminder(jico)

    print('RESULT: {} tickets received the 1st reminder'.format(len(reminder_positive_cases)))
    print('RESULT: {} tickets were CLOSED'.format(len(close_positive_cases)))

    if len(close_positive_cases) > 0 or len(reminder_positive_cases) > 0:
        user_continue_question('Confirm to open tickets in browser')
        for key in reminder_positive_cases:
            webbrowser.open('https://devstack.vwgroup.com/jira/browse/{}'.format(key))
        for key in close_positive_cases:
            webbrowser.open('https://devstack.vwgroup.com/jira/browse/{}'.format(key))

main()