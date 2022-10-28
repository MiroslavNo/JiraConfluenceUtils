from jico_utils import JiCoUtils
import credentials
from datetime import datetime

#jico = JiCoUtils(credentials.SERVER_URL['PROD'], '01_reminder_5plus2_days_after_PO_request.log')


#jico.do_transition('ESSD-30408', '191', 'Canceled')

#print(jico.get_transitions('ESSD-30408'))

groups_raw='abc({'
def clean_trailing_non_letters(input_str):
    while True:
        if not input_str[-1:].isalpha():
            input_str = input_str[:-1]
        else:
            break
    return input_str