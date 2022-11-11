from jico_utils import JiCoUtils
import credentials
import xmltodict
import json
import pickle

jico = JiCoUtils(credentials.SERVER_URL['PROD'], 'test.log')

confluenge_page_w_confiforms_id = '831475599'
# confiforms overview here: https://devstack.vwgroup.com/confluence/confiforms/import.action?pageId=831475599
# mapping for team and art keys:
# https://devstack.vwgroup.com/confluence/display/PMTCS/Mapping+for+GUMC+Rollout

MDB_ID = 'id'
MEMBER_ID = 'Member'
CREATEDBY_ID = 'createdBy'
DEVSTACK_ID = 'devStack'
OWNEDBY_ID = 'ownedBy'
FULLNAME = 'fullName'
EMAIL = 'email'
SOLUTION = 'SolutionTrain'
ART = 'ART'
TEAM = 'Team'
ROLE = 'Role'
FIELDS = 'fields'

TEAM_KEY_PLACEHOLDER = '<team_key>'
ART_KEY_PLACEHOLDER = '<art_key>'
SOLUTION_KEY_PLACEHOLDER = '<solution_key>'


def convert_confiform_to_list(data_confiform):
    data_dict = json.loads(data_confiform)
    data_xml = data_dict['data']
    data_dict = xmltodict.parse(data_xml)
    data_list = data_dict['list']['entry']
    return data_list


def convert_confiform_to_dict(data_confiform, field_name):
    data_list = convert_confiform_to_list(data_confiform)
    data = dict()
    if type(data_list) is list:
        for d in data_list:
            data[d['id']] = d[FIELDS][field_name]
    elif type(data_list) is dict:
        # in this case it has only 1 entry
        data[data_list['id']] = data_list[FIELDS][field_name]
    return data


def get_affiliatesrs_dict(data_confiform, solutions_dict, arts_dict, teams_dict, roles_dict):

    data_dict = json.loads(data_confiform)
    # with open("data_dict.json", "w") as outfile:
    #     outfile.write(json.dumps(data_dict, indent=4))
    data_xml = data_dict['data']
    data_dict = xmltodict.parse(data_xml)
    data_list = data_dict['list']['entry']

    data = dict()

    for d in data_list:
        mdb_id = d[MDB_ID]
        member_id = d[FIELDS][MEMBER_ID]
        createdby_id = d.get(CREATEDBY_ID, '')
        devstack_id = d[FIELDS].get(DEVSTACK_ID, '')
        ownedby_id = d.get(OWNEDBY_ID, '')
        fullname = d[FIELDS][FULLNAME]
        email = d[FIELDS][EMAIL]
        solution = solutions_dict[d[FIELDS][SOLUTION]]
        art = arts_dict[d[FIELDS][ART]]
        team = teams_dict[d[FIELDS][TEAM]]

        role_ref = d[FIELDS].get(ROLE)
        if role_ref is None:
            role = ''
        else:
            role = roles_dict[role_ref]

        if ownedby_id is None or ownedby_id == 'None':
            ownedby_id = ''

        data[mdb_id] = {
            MEMBER_ID: member_id,
            CREATEDBY_ID: createdby_id,
            DEVSTACK_ID: devstack_id,
            OWNEDBY_ID: ownedby_id,
            FULLNAME: fullname,
            EMAIL: email,
            SOLUTION: solution,
            ART: art,
            TEAM: team,
            ROLE: role
        }

    return data


def save_dict_as_csv(file_name, res_dict):
    with open(file_name, 'w', encoding="utf-8") as f:
        f.write('Sep=;\n')
        f.write('ID;Member;createdBy;devStack_id;ownedBy_id;fullName;email;SolutionTrain;ART;Team;Role\n')
        for k, v in res_dict.items():
            f.write('{};{};{};{};{};{};{};{};{};{};{}\n'.format(k, v[MEMBER_ID], v[CREATEDBY_ID],  v[DEVSTACK_ID],
                                                                v[OWNEDBY_ID], v[FULLNAME], v[EMAIL], v[SOLUTION],
                                                                v[ART], v[TEAM], v[ROLE]))
        f.close()


def get_affiliations_dict(load_prev_result=False):
    pickle_name = 'pickle_affiliations.pickle'
    if load_prev_result:
        with open(pickle_name, 'rb') as handle:
            affiliations = pickle.load(handle)
            return affiliations

    arts = convert_confiform_to_dict(jico.get_confiform_data(confluenge_page_w_confiforms_id, 'ARTs'), 'nameShort')
    teams = convert_confiform_to_dict(jico.get_confiform_data(confluenge_page_w_confiforms_id, 'Teams'), 'name')
    roles = convert_confiform_to_dict(jico.get_confiform_data(confluenge_page_w_confiforms_id, 'Roles'), 'name')
    solutions = convert_confiform_to_dict(jico.get_confiform_data(confluenge_page_w_confiforms_id, 'SolutionTrains'),
                                          'name')

    affiliations = get_affiliatesrs_dict(jico.get_confiform_data(confluenge_page_w_confiforms_id, 'Affiliations'),
                                         solutions, arts, teams, roles)

    # save results
    with open(pickle_name, 'wb') as handle:
        pickle.dump(affiliations, handle, protocol=pickle.HIGHEST_PROTOCOL)
    save_dict_as_csv('80_affiliations.csv', affiliations)
    return affiliations


def get_members_list(load_prev_result=False):
    pickle_name = 'pickle_members.pickle'
    if load_prev_result:
        with open(pickle_name, 'rb') as handle:
            members = pickle.load(handle)
            return members
    members = convert_confiform_to_list(jico.get_confiform_data(confluenge_page_w_confiforms_id, 'Members'))
    with open('pickle_members.pickle', 'wb') as handle:
        pickle.dump(members, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return members


# ########################################      ANALYZE DATA      #############################################

def find_null_ids(afflis):
    counter = 0
    res = dict()
    for key, val in afflis.items():
        if val[DEVSTACK_ID] == '' or val[DEVSTACK_ID]:
            counter += 1
            res[key] = val

    print(counter)
    save_dict_as_csv('99_Gumc_null_ids.csv', res)


def find_dupl_in_members_table(members_list):
    devstack_ids = []
    devstack_duplicate_ids = []
    for member in members_list:
        devstack_id = member[FIELDS].get(DEVSTACK_ID)
        if devstack_id is None:
            continue
        if devstack_id in devstack_ids:
            devstack_duplicate_ids.append(devstack_id)
        else:
            devstack_ids.append(devstack_id)

    for member in members_list:
        devstack_id = member[FIELDS].get(DEVSTACK_ID)
        if devstack_id is None:
            continue
        if devstack_id in devstack_duplicate_ids:
            fullname = member[FIELDS].get(FULLNAME)
            entry_id = member['id']
            print(f'{entry_id};{devstack_id};{fullname}')


def find_unused_in_members_table(members_list, affils):
    member_ids_from_affils = []
    for key, val in affils.items():
        member_id = val[MEMBER_ID]
        member_ids_from_affils.append(member_id)

    for member in members_list:
        if member['id'] not in member_ids_from_affils:
            devstack_id = member[FIELDS].get(DEVSTACK_ID)
            if devstack_id is None:
                continue
            fullname = member[FIELDS].get(FULLNAME)
            entry_id = member['id']
            print(f'{entry_id};{devstack_id};{fullname}')


def verify_devstack_id_with_email(affils):
    for key, val in affils.items():
        devstack_id = val[DEVSTACK_ID]
        try:
            mdb_email = val['email']
            mdb_email = mdb_email.split('mailto:')[1]
            mdb_email = mdb_email.split('>')[0]
            jira_email = jico.get_user_email(devstack_id)
            if jira_email.lower() != mdb_email.lower():
                print(f'{devstack_id};{mdb_email};{jira_email}')
        except:
            print(f'ERR with the devstack ID {devstack_id}')


def add_role_groups(role_groups_dic, role, group):
    if role in role_groups_dic:
        role_groups = role_groups_dic[role]
        if group in role_groups:
            print('WARN: {} for role {} already in groups: {}'.format(group, role, role_groups))
        role_groups_dic[role] = '{};{}'.format(role_groups_dic[role], group)
    else:
        role_groups_dic[role] = group

    return role_groups_dic


def get_role_dedicated_groups():
    role_groups_dict = dict()
    # team level groups
    role_groups_dict = add_role_groups(role_groups_dict, 'Nexus Lead', f'cgm-{TEAM_KEY_PLACEHOLDER}-product-owner')
    role_groups_dict = add_role_groups(role_groups_dict, 'Product Owner', f'cgm-{TEAM_KEY_PLACEHOLDER}-product-owner')
    role_groups_dict = add_role_groups(role_groups_dict, 'Product Owner-ext', f'cgm-{TEAM_KEY_PLACEHOLDER}-product-owner-external')
    role_groups_dict = add_role_groups(role_groups_dict, 'Program Manager', f'cgm-{TEAM_KEY_PLACEHOLDER}-product-owner')
    role_groups_dict = add_role_groups(role_groups_dict, 'Proxy PO', f'cgm-{TEAM_KEY_PLACEHOLDER}-product-owner-external')
    role_groups_dict = add_role_groups(role_groups_dict, 'Scrum Master', f'cgm-{TEAM_KEY_PLACEHOLDER}-scrum-master')
    role_groups_dict = add_role_groups(role_groups_dict, 'Solution Architect', f'cgm-{TEAM_KEY_PLACEHOLDER}-developer')
    role_groups_dict = add_role_groups(role_groups_dict, 'System Architect', f'cgm-{TEAM_KEY_PLACEHOLDER}-developer')
    role_groups_dict = add_role_groups(role_groups_dict, 'Team Member', f'cgm-{TEAM_KEY_PLACEHOLDER}-developer')
    # art level groups
    role_groups_dict = add_role_groups(role_groups_dict, 'Release Train Engineer', f'cgm-{ART_KEY_PLACEHOLDER}-rte')
    role_groups_dict = add_role_groups(role_groups_dict, 'Product Owner', f'cgm-{ART_KEY_PLACEHOLDER}-product-owner')
    role_groups_dict = add_role_groups(role_groups_dict, 'Product Owner-ext', f'cgm-{ART_KEY_PLACEHOLDER}-product-owner-external')
    role_groups_dict = add_role_groups(role_groups_dict, 'Program Manager', f'cgm-{ART_KEY_PLACEHOLDER}-product-owner')
    role_groups_dict = add_role_groups(role_groups_dict, 'Proxy PO', f'cgm-{ART_KEY_PLACEHOLDER}-product-owner-external')
    role_groups_dict = add_role_groups(role_groups_dict, 'Scrum Master', f'cgm-{ART_KEY_PLACEHOLDER}-scrum-master')
    role_groups_dict = add_role_groups(role_groups_dict, 'Solution Architect', f'cgm-{ART_KEY_PLACEHOLDER}-developer')
    role_groups_dict = add_role_groups(role_groups_dict, 'System Architect', f'cgm-{ART_KEY_PLACEHOLDER}-developer')
    # solution level groups
    role_groups_dict = add_role_groups(role_groups_dict, 'Solution Management', 'cgm-pmt-solution-lead')
    role_groups_dict = add_role_groups(role_groups_dict, 'Domain Business Partner', f'cgm-{SOLUTION_KEY_PLACEHOLDER}-stakeholder')
    role_groups_dict = add_role_groups(role_groups_dict, 'Nexus Lead', 'cgm-pmt-product-owner')
    role_groups_dict = add_role_groups(role_groups_dict, 'Product Owner', 'cgm-pmt-product-owner')
    role_groups_dict = add_role_groups(role_groups_dict, 'Product Owner-ext', 'cgm-pmt-product-owner-external')
    role_groups_dict = add_role_groups(role_groups_dict, 'Program Manager', 'cgm-pmt-solution-lead')
    role_groups_dict = add_role_groups(role_groups_dict, 'Proxy PO', 'cgm-pmt-product-owner-external')
    role_groups_dict = add_role_groups(role_groups_dict, 'Release Train Engineer', 'cgm-pmt-rte-ste')
    role_groups_dict = add_role_groups(role_groups_dict, 'Scrum Master', 'cgm-pmt-scrum-master')
    role_groups_dict = add_role_groups(role_groups_dict, 'Solution Architect', 'cgm-pmt-solution-lead')
    role_groups_dict = add_role_groups(role_groups_dict, 'Solution Train Engineer', 'cgm-pmt-solution-lead')
    role_groups_dict = add_role_groups(role_groups_dict, 'Solution Train Engineer', 'cgm-pmt-rte-ste')
    role_groups_dict = add_role_groups(role_groups_dict, 'System Architect', 'cgm-pmt-solution-lead')

    return role_groups_dict


def get_compressed_groups_list_generic():
    role_groups = get_role_dedicated_groups()
    groups_list_all = list()
    for role, groups_srt in role_groups.items():
        groups_list = groups_srt.split(';')
        for group in groups_list:
            if group not in groups_list_all:
                groups_list_all.append(group)
    # print(len(groups_list_all))
    # print(groups_list_all)
    # ['cgm-{TEAM_KEY_PLACEHOLDER}-product-owner', 'cgm-pmt-product-owner', 'cgm-<art_key>-product-owner', 'cgm-<team_key>-product-owner-external',
    # 'cgm-<art_key>-product-owner-external', 'cgm-pmt-product-owner-external', 'cgm-pmt-solution-lead', 'cgm-<team_key>-scrum-master',
    # 'cgm-<art_key>-scrum-master', 'cgm-pmt-scrum-master', 'cgm-<team_key>-developer', 'cgm-<art_key>-developer', 'cgm-<art_key>-rte', 'cgm-pmt-rte-ste', 'cgm-<solution_key>-stakeholder']
    return groups_list_all

# get_compressed_groups_list_generic = get_compressed_generic_groups_list()


def find_unknown_roles(affiliations):
    role_groups = get_role_dedicated_groups()
    roles_unknown = dict()
    for key, val in affiliations.items():
        role = val[ROLE]
        if role not in role_groups:
            counter = roles_unknown.get(role, 0)
            counter += 1
            roles_unknown[role] = counter

    print(roles_unknown)
    # {'Business Owner': 7, 'Product Manager': 15, 'Portfolio Management': 1,
    # 'Other Role': 5, 'Cluster Lead': 3, '': 10}

# find_unknown_roles()


def find_unused_roles(affiliations):
    role_groups = get_role_dedicated_groups()
    for key, val in affiliations.items():
        role = val[ROLE]
        if role in role_groups:
            role_groups.pop(role)
    print(role_groups.keys())
    # dict_keys(['Nexus Lead', 'Program Manager'])

# find_unused_roles()


def get_team_mapping():
    # https://devstack.vwgroup.com/confluence/display/PMTCS/PMT+GROUP+KEYS
    # page with data last updated on 10.11.2022
    team_map = dict()
    team_map['ProSafe AI'] = 'airp'
    team_map['Architektur MGM (Cameo)'] = 'cameo'
    team_map['DEFMA'] = 'defma'
    team_map['Teststrategy & Test Methodolog'] = 'carts'
    team_map['CM (Configuration Management)'] = 'confima'
    # TODO 2 value for one team name - calrify which one should be taken
    #  team_map['Qhub Team 1 + 2'] = '"qhub1" and "qhub2"'
    team_map['Qhub Team 1 + 2'] = 'qhub1'
    team_map['VM (Variant Management)'] = 'vama'
    team_map['CI/CD Platform'] = 'cicd'
    team_map['CI/CD Runtime'] = 'cicd'
    team_map['Developer Workstation'] = 'dws'
    team_map['Prototypes'] = 'proto'
    team_map['Process Platform'] = 'prohub'
    team_map['VEF Architecture + Interfaces'] = 'vef'
    team_map['VEF ViSim-SCB'] = 'gxil'
    team_map['G-SIL Models'] = 'gxil'
    team_map['G-HIL.FASIS@HIL TB'] = 'gxil'
    team_map['G-SIL ADAS'] = 'gxil'
    team_map['G-SIL System'] = 'gxil'
    team_map['MBSD.SDK'] = 'PMTBSESDK'

    return team_map


def get_working_directories():
    role_dedicated_groups = get_role_dedicated_groups()
    affiliations = get_affiliations_dict(load_prev_result=False)
    team_mapping = get_team_mapping()

    result_group_members = dict()
    result_member_groups = dict()

    for affiliation in affiliations.values():
        devstack_id = affiliation[DEVSTACK_ID]
        role = affiliation[ROLE]
        team = affiliation[TEAM]
        art = affiliation[ART]
        solution = affiliation[SOLUTION]
        groups_for_this_role = role_dedicated_groups.get(role)
        if groups_for_this_role is None:
            # this means the role was not documented in the mapping -> is to be expected
            continue
        groups_for_this_role = groups_for_this_role.split(';')
        for group in groups_for_this_role:
            if TEAM_KEY_PLACEHOLDER in group:
                if team not in team_mapping:
                    # if group with TEAM_KEY_PLACEHOLDER, than the team of the user needs to be in the team_mapping
                    # -> otherwise skipping
                    continue
                else:
                    group = group.replace(TEAM_KEY_PLACEHOLDER, team_mapping[team])
            else:
                group = group.replace(ART_KEY_PLACEHOLDER, art).replace(SOLUTION_KEY_PLACEHOLDER, solution)

            curr_users = result_group_members.get(group)
            if curr_users is None:
                result_group_members[group] = [devstack_id]
            else:
                curr_users.append(devstack_id)
                result_group_members[group] = curr_users

            curr_groups = result_member_groups.get(devstack_id)
            if curr_groups is None:
                result_member_groups[devstack_id] = [group]
            else:
                curr_groups.append(group)
                result_member_groups[devstack_id] = curr_groups

    # TODO log result_member_groups, result_group_members
    # print(json.dumps(result_group_members, indent=4))
    # print(json.dumps(result_member_groups, indent=4))
    return result_group_members, result_member_groups


def set_group_members(group_members_dict):
    for group, added_users in group_members_dict.items():
        space_name = group.split('-')[1]
        # todo over ci tam nie su nejake obrovske pocty userov
        jico.add_users_to_group(space_name, group, added_users)


def check_results(group_members_dict):
    errors = dict()
    for group, added_users in group_members_dict.items():
        users_from_group = jico.get_users_ids_from_group(group)
        for added_user in added_users:
            if added_user not in users_from_group:
                error_users = errors.get(group, list())
                errors[group] = error_users.append(added_user)

    if errors:
        for err_group, err_users in errors:
            print('ERROR: In Group {} following users were not added: {}'.format(err_group, err_users))


        
# find_dupl_in_members_table(get_members_list(load_prev_result=True))

