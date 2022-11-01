from jico_utils import JiCoUtils
import credentials
from datetime import datetime, timedelta

N_DAYS_AGO = 25


def get_date_string_n_days_ago(n_days):
    today = datetime.now()    
    n_days_ago = today - timedelta(days=n_days)
    return ('{:%Y/%m/%d}'.format(n_days_ago))

print(get_date_string_n_days_ago(3))