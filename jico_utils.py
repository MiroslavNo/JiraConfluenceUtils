import credentials
import requests
import json
import time
import logging

class JiCoUtils:
    
    def __init__(self, server_base_url, log_file_name) -> None:
        self.SLEEP_SEC = 0.0
        self.server_base_url = server_base_url
        self.logging = logging
        logging.basicConfig(filename=log_file_name, 
                            encoding='utf-8', format='%(asctime)s - %(levelname)s - %(message)s', 
                            level=logging.DEBUG)

    def __get_api_token(self, url):
        if '/confluence/' in url:
            return credentials.API_CREDS['token_confluence']
        if '/jira/' in url:
            return credentials.API_CREDS['token_jira']

    def __get_users_ids_from_group(self, group_name, start=0, limit=200):
        self.logging.info('__get_users_ids_from_group(group_name={},start={},limit={})'.format(group_name, start, limit))
        url = f"{self.server_base_url}/confluence/rest/api/group/{group_name}/member"

        headers = {
           "accept": "application/json",
           "authorization": f"bearer " + self.__get_api_token(url),
        }

        params={
           "start": start,
           "limit": limit,
        }
    
        response = requests.request(
           "GET",
           url,
           headers=headers,
           params=params,
        )
        time.sleep(self.SLEEP_SEC)
        return self.__process_get_user_ids_response(response, group_name)

    def __process_get_user_ids_response(self, response, group_name):
        if response.status_code != 200:
            self.logging.error ('Error: {} when trying to GET the users from the group {}'.format(response.status_code, group_name))

        r_dict = json.loads(response.text)
        size = r_dict.get("size", 0)

        r_list = r_dict.get("results")
        r_list = [user_entry['username'] for user_entry in r_list]

        return r_list, size

    def get_users_ids_from_group(self, group_name):
        self.logging.info('get_users_ids_from_group(group_name={})'.format(group_name))
        start = 0
        limit = 200
        step = limit
        r = list()

        size=step
        while size == step:
            r_sub, size = self.__get_users_ids_from_group(group_name, start=start, limit=limit)
            start += step
            r.extend(r_sub)

        return r

    def add_users_to_group(self, space_name, group_name, members_list):
        self.logging.info('set_users_from_group(group_name={},group_name={},group_name={})'.format(space_name, group_name, members_list))
        url = "https://devstack.vwgroup.com/confluence/rest/csum/latest/public/group/addusers"

        headers = {
           "accept": "application/json",
           "authorization": f"bearer " + self.__get_api_token(url),
        }

        params={
            "spaceKey": space_name,
            "spaceGroups": group_name,
            "spaceUsers": ','.join(members_list),
        }

        response = requests.request(
           "PUT",
           url,
           headers=headers,
           params=params
        )
        time.sleep(self.SLEEP_SEC)

        if response.status_code != 200:
            self.logging.error ('Error: {} when trying to SET the users for the group {}'.format(response.status_code, group_name))
            return False
        return True

    def __search_jira_issues_limit_results(self, jql, fields_list, start=0, limit=1000):
        url = f'{self.server_base_url}/jira/rest/api/2/search'

        headers = {
           "accept": "application/json",
           "authorization": f"bearer " + self.__get_api_token(url),
        }

        params={
            "jql": jql,
            "startAt": start,
            "maxResults": limit,     # maxResults default hodnota je 50, max com mi vracalo bolo 1000
            "fields": fields_list
        }

        response = requests.request(
           "GET",
           url,
           headers=headers,
           params=params,
        )

        time.sleep(self.SLEEP_SEC)
        return json.loads(response.text)['issues']

    def search_jira_issues(self, jql, fields_list):
        # TODO tst
        start = 0
        limit = 1000
        step = limit
        r = list()

        size=step
        while size == step:
            r_sub = self.__search_jira_issues_limit_results(jql, fields_list, start=start, limit=limit)
            size = len(r_sub)
            start += step
            r.extend(r_sub)

        return r

    def get_ars_grt_5_days(self):
        jql = 'assignee = currentUser() AND resolution = Unresolved AND updated <= -3d ORDER BY updated ASC'
        fields_list = [
                "key"
            ]
        r_list = self.search_jira_issues(jql, fields_list)
        return [entry['key'] for entry in r_list]

    def get_comments_from_jira_issue(self, issue_key):
        url = f"{self.server_base_url}/jira/rest/api/2/issue/{issue_key}/comment"

        headers = {
           "accept": "application/json",
           "authorization": f"bearer " + self.__get_api_token(url),
        }

        params={
            "maxResults": 50,
            "orderBy": "created"
        }

        response = requests.request(
           "GET",
           url,
           headers=headers,
           params=params,
        )

        time.sleep(self.SLEEP_SEC)
        return json.loads(response.text)['comments']

    def __check_last_comment(self, issue_key, tag):
        comments = self.get_comments_from_jira_issue(issue_key)
        if len(comments) < 1:
            return False

        last_comment_body = comments[-1]['body']
        canned_reminder_1 = 'thank you for your request. The ticket is now in the approval status. To grant the access, we need the approval of an internal PO/PM or higher. If you know someone who can approve your request please share this issue with them and let them approve the request via a comment on the ticket.'
        
        if tag in last_comment_body:
            return True
        return False

    def is_last_comment_canned_reminder_nr1(self, issue_key):
        canned_reminder_1 = 'thank you for your request. The ticket is now in the approval status. To grant the access, we need the approval of an internal PO/PM or higher. If you know someone who can approve your request please share this issue with them and let them approve the request via a comment on the ticket.'
        return self.__check_last_comment(issue_key, canned_reminder_1)

    def is_last_comment_canned_reminder_nr2(self, issue_key):
        canned_reminder_2 = 'this is a friendly reminder that your ticket has been waiting for approval. In order to proceed we need an approval from an internal PO/PM or higher. Should we not receive any answer in the next 3 working days, we will close your ticket'
        return self.__check_last_comment(issue_key, canned_reminder_2)

    def create_comment(self, comment_str, issue_key, internal_bool):
        url = f"{self.server_base_url}/jira/rest/api/2/issue/{issue_key}/comment"

        headers = {
           "accept": "application/json",
           "content-type": "application/json",
           "authorization": f"bearer " + self.__get_api_token(url),
        }

        params=json.dumps({
           "body": comment_str,
           "properties": [
             {
               "key": "sd.public.comment",
               "value": {
                  "internal": internal_bool
               }
             }
           ]
        })

        response = requests.request(
           "POST",
           url,
           headers=headers,
           data=params,
        )

        if response.status_code != 201:
            self.logging.error ('Error: "{}" when trying to POST a comment on the issue {}'.format(response.status_code, issue_key))
            return False
        return True

    def reminder_before_closing_ticket(self, issue_key, reporter_id):
        body_reminder_before_closing = f'Hello [~{reporter_id}] ,\n\nthis is a friendly reminder that your ticket is still waiting for approval. \
                                        In order to proceed we need an approval from an internal PO/PM or higher. Should we not receive any answer in the next 3 days, \
                                        we will close your ticket.\n\nBest regards,\nMiroslav'
        return self.create_comment(body_reminder_before_closing, issue_key, True)

    def find_certain_comment(self, comments, searched_tags):
        # todo prerob searched_tags na *args
        for comment in comments:
            if searched_tags in comment['body']:
                return comment['body']
        return None


    def is_tabelle_in_comments(self, key):
        tag = 'Type of permission'
        tag2 = 'cgm-'
        comments = self.get_comments_from_jira_issue(key)

        for comment in comments:
            if tag in comment['body']:
                return True
            if tag2 in comment['body']:
                return True
        return False

    def get_issue(self, issue_key):
        url = f"{self.server_base_url}/jira/rest/api/2/issue/{issue_key}"

        headers = {
           "accept": "application/json",
           "authorization": f"bearer " + self.__get_api_token(url),
        }

        #params={
        #    "fields": "customfield_10202"
        #}

        # TODO nejak dorob parameter fields, momentalne nefunguje dobre, ked tam dam array tak nevrati ziadne fields info

        response = requests.request(
           "GET",
           url,
           headers=headers,

        )

        time.sleep(self.SLEEP_SEC)
        return json.loads(response.text)

    def get_issue_status_from_issue_obj(self, issue_obj):
        return(issue_obj['fields']['customfield_10202']['currentStatus']['status'])

    def get_issue_status(self, key):
        # TODO inefective, fetching all fields
        issue_obj = self.get_issue(key)
        return self.get_issue_status_from_issue_obj(issue_obj)

    def get_ticket_reporter_from_issue_obj(self, issue_obj):
        return(issue_obj['fields']['reporter']['name'])

    def get_ticket_reporter(self, key):
        issue_obj = self.get_issue(key)
        return self.get_ticket_reporter_from_issue_obj(issue_obj)

    def is_remove_access_ticket(self, issue_key):
        request_type = self.get_issue(issue_key)['fields']['customfield_10202']['requestType']['name']
        if request_type.lower() == 'remove access':
            return True
        return False

    def get_transitions(self, issueID):
        '''
        you can read here about all possible transitions from the current state
        '''
        url = f"{self.server_base_url}/jira/rest/api/2/issue/{issueID}/transitions"

        headers = {
           "accept": "application/json",
           "authorization": f"bearer " + self.__get_api_token(url),
        }
   
        response = requests.request(
           "GET",
           url,
           headers=headers,
        )

        return response.text

    def do_transition(self, issueID, transition_id, resolution):
        url = f"{self.server_base_url}/jira/rest/api/2/issue/{issueID}/transitions"

        headers = {
           "accept": "application/json",
           "content-type": "application/json",
           "authorization": f"bearer " + self.__get_api_token(url),
        }

        params=json.dumps({
            "transition": {
                "id": str(transition_id)
            },
            "fields": {
                "resolution": {
                    "name": resolution
                }
            }
        })
   
        response = requests.request(
           "POST",
           url,
           headers=headers,
           data=params,
        )

        return response.text


        

        

        


