from jico_utils import JiCoUtils
import credentials
import webbrowser

def find_collecteddata_comment(jico_obj, comments):
    return jico_obj.find_certain_comment(comments, '| *Username* |')

def find_usergroups_comment(jico_obj, comments):
    return jico_obj.find_certain_comment(comments, 'Type of permission')

def user_confirmation(msg):
    ans = input(msg + ' (y/n):')
    if ans.lower() != 'y':
        return False
    return True

def clean_trailing_non_letters(input_str):
    while True:
        if not input_str[-1:].isalpha():
            input_str = input_str[:-1]
        else:
            break
    return input_str

def user_continue_question(msg=None):
    if msg is not None:
        i = input(msg + ' - Continue? [ENTER]')
    else:
        i = input('Continue? [ENTER]')
    return i

def grant_access():
    jico = JiCoUtils(credentials.SERVER_URL['PROD'], '02_grant_access.log')
    jico.logging.info('Start\n')
    pmtc_read_confluence_page = False

    ticket_id = int(input("Enter ticket ID (w/o ESSD):"))
    if not isinstance(ticket_id, int):
        print('ERR - only interger characters allowed -> aborting')
        return
    ticket_id = 'ESSD-{}'.format(ticket_id)

    # open in browser?
    if user_confirmation('Open ticket in browser?'):
        webbrowser.open('https://devstack.vwgroup.com/jira/browse/{}'.format(ticket_id))

    # get status - accept only support investigated (1st version)
    ticket_object = jico.get_issue(ticket_id)
    ticket_status = jico.get_issue_status_from_issue_obj(ticket_object)
    if ticket_status.lower() != 'support investigating':
        print('ERR - status is {}, currently only Support Investigating supported -> aborting'.format(ticket_status))
        return

    ticket_comments = jico.get_comments_from_jira_issue(ticket_id)

    # read user IDs from comment from andreas
    user_ids_comment = find_collecteddata_comment(jico, ticket_comments)
    user_ids = ''.join(user_ids_comment.split(' |\n| *Full name* |')[:-1])
    user_ids = ''.join(user_ids.split('| *Username* | ')[1:])
    user_ids = user_ids.split(', ')

    # read groups from comment
    user_groups_comment = find_usergroups_comment(jico, ticket_comments)
    groups = 'cgm-pmt-users' + user_groups_comment.split('cgm-pmt-users')[1]
    groups = groups.split('*')[0]
    if groups[-1:] == ';':
        groups = groups[:-1]
    groups_raw = groups.replace(" ", "")
    
    # Group clean ups
    groups_raw = clean_trailing_non_letters(groups_raw)
    if 'cgm-pmt-consumers-read' in groups_raw:
        print('WARN: Removing cgm-pmt-consumers-read from groups - PLEASE ADD MANUALLY IN CONFLUENCE - opening..')
        groups_raw = groups_raw.replace("cgm-pmt-consumers-read;", "")
        groups_raw = groups_raw.replace(";cgm-pmt-consumers-read", "")
        pmtc_read_confluence_page = True
        webbrowser.open('https://devstack.vwgroup.com/confluence/display/PMTCS/PMT-consumer-read+Ticket+Approvals')
    if 'cgm-pmt-consumer-read' in groups_raw:
        print('WARN: Removing cgm-pmt-consumer-read from groups - PLEASE ADD MANUALLY IN CONFLUENCE - opening..')
        groups_raw = groups_raw.replace("cgm-pmt-consumer-read;", "")
        groups_raw = groups_raw.replace(";cgm-pmt-consumer-read", "")
        pmtc_read_confluence_page = True
        webbrowser.open('https://devstack.vwgroup.com/confluence/display/PMTCS/PMT-consumer-read+Ticket+Approvals')
    if 'cgm-pmtc-consumers-write' in groups_raw:
        groups_raw = groups_raw.replace("cgm-pmtc-consumers-write", "cgm-pmtc-consumer-write")
    
    groups = groups_raw.split(';')

    # ask user confirmation if IDs and groups are correct
    print('Following users ({}) were found: {}'.format(len(user_ids), user_ids))
    print('Following groups ({}) were found: {}'.format(len(groups), groups_raw))  

    # check if users in the groups already, if yes print warn and ask confirmation to continue
    skip_list = list()
    for group in groups:
        print('Reading users of the group {}'.format(group))
        group_members = jico.get_users_ids_from_group(group) 
        for user_id in user_ids:
            if user_id in group_members:
                skip_list.append('{}{}'.format(user_id, group))
                print('WARN: User {} is already a member of the group {}'.format(user_id, group))
    
    # add to groups
    for group in groups:
        # GROUP CHECKS AND EDITS
        if group in ['cgm-pmt-consumers-read', 'cgm-pmt-consumer-read']:
            print('WARN: For the group {} please add an entry/ies in Confluence'.format(group))
            continue
        if group in ['cgm-pmtc-consumers-write']:
            group = 'cgm-pmtc-consumer-write'

        # parse group to space and name - TODO ako je name gruppy, ci cele alebo len koniec
        for user_id in user_ids:
            if '{}{}'.format(user_id, group) not in skip_list:
                members_list = list()
                members_list.append(user_id)
                space_name = group.split('-')[1]
                user_continue_question('space_name={} / group={} / members_list={}'.format(space_name, group, members_list))
                jico.add_users_to_group(space_name, group, members_list)
            else:
                print('Skipping {} into {} because was already there'.format(user_id, group))
    
    # check if adding succesfull
    err = False
    for group in groups:
        group_members = jico.get_users_ids_from_group(group) 
        for user_id in user_ids:
            if '{}{}'.format(user_id, group) not in skip_list:
                if user_id not in group_members:
                    err = True
                    print('ERR: User {} was not added to the group {}'.format(user_id, group))
                else:
                    print('user {} was succesfuly added to {}'.format(user_id, group))
    if err:
        print('ERR - there was an error -> aborting')
        return
    
    print('Adding a comment')
    # reply to the ticket w canned response
    ticket_reporter = jico.get_ticket_reporter_from_issue_obj(ticket_object)
    canned_respone = f'Hi [~{ticket_reporter}],\r\n\r\nThe requested access rights were granted. Please check if everything works as expected.\r\nIf not, just add a comment to this ticket and we will take a look.\r\n\r\nBest regards\r\nMiroslav'
    jico.create_comment(canned_respone, ticket_id, False)

    # TODO change status of the ticket
    print('Changing status')
    jico.do_transition(ticket_id, '21', 'Done')
    print('done')

    if pmtc_read_confluence_page:
        print('DONT FORGET TO FILL THE CONFLUENCE PAGE !!!')
 
grant_access()