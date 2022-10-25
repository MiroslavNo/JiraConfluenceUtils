import credentials
import requests
import json
import time
import logging

class JiCoUtils:
    
    def __init__(self, server_base_url, log_file_name) -> None:
        self.SLEEP_SEC = 1.0
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

    def __get_user_ids_from_group(self, group_name, start=0, limit=200):
        self.logging.info('__get_user_ids_from_group(group_name={},start={},limit={})'.format(group_name, start, limit))
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

    def get_all_user_ids_from_group(self, group_name):
        self.logging.info('get_all_user_ids_from_group(group_name={})'.format(group_name))
        start = 0
        limit = 200
        step = limit
        r = list()

        size=step
        while size == step:
            r_sub, size = self.__get_user_ids_from_group(group_name, start=start, limit=limit)
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

    def search_jira_issues(self, jql, fields_list):
        url = '{self.server_base_url}/jira/rest/api/2/search'

        headers = {
           "accept": "application/json",
           "authorization": f"bearer " + self.__get_api_token(url),
        }

        params={
            "jql": jql,
            "startAt": 0,
            "maxResults": 15,
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

    def is_last_comment_canned_reminder_nr1(self, issue_key):
        comments = self.get_comments_from_jira_issue(issue_key)
        if len(comments) < 1:
            return False

        last_comment_body = comments[-1]['body']
        canned_reminder_1 = 'thank you for your request. The ticket is now in the approval status. To grant the access, we need the approval of an internal PO/PM or higher. If you know someone who can approve your request please share this issue with them and let them approve the request via a comment on the ticket.'
        
        if canned_reminder_1 in last_comment_body:
            return True
        return False

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




test = JiCoUtils(credentials.SERVER_URL['PROD'], 'tst.log')
print(test.reminder_before_closing_ticket('ESSD-30074', 'A62K7GX'))


# commit 1