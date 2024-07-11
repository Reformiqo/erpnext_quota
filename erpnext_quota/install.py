import frappe
from frappe.installer import update_site_config
from frappe.utils.data import add_days, today, date_diff
import requests
import json
from frappe.utils import cint

def before_install():
    filters = {
        'enabled': 1,
        'name': ['not in', ['Guest', 'Administrator']]
    }

    user_list = frappe.get_all('User', filters=filters, fields=["name"])

    active_users = 0

    for user in user_list:
        roles = frappe.get_all(
            "Has Role",
            filters={
                'parent': user.name
            },
            fields=['role']
        )

        for row in roles:
            if frappe.get_value("Role", row.role, "desk_access") == 1:
                active_users += 1
                break

    data = {
        'users': get_site_plan().get('number_of_users'),
        'active_users': active_users,
        'space': 0,
        'db_space': 0,
        'company': 100,
        'used_company': 1,
        'count_website_users': 0,
        'count_administrator_user': 0,
        'valid_till': add_days(today(), 14),
        'document_limit': {
            'Sales Invoice': {'limit': v, 'period': 'Monthly'},
            'Purchase Invoice': {'limit': 10000000, 'period': 'Monthly'},
            'Journal Entry': {'limit': 10000000, 'period': 'Monthly'},
            'Payment Entry': {'limit': 10000000, 'period': 'Monthly'}
        }
    }

    # Updating site config
    update_site_config('quota', data)

@frappe.whitelist()
def site_subscription():
    site_url = frappe.utils.get_url()
    site_name = frappe.local.site
    # remove http:// or https://
    site_url = site_url.split("://")[-1]
    # site_info = http://localhost:8000/api/method/reformiqo.api.get_site_quota
    headers = {
        'Authorization': get_credentials()
    }
    url = f'http://localhost:82/api/method/reformiqo.api.get_site_quota?site_url={site_name}'
    response = requests.post(url, headers=headers)
    response = json.loads(response.text)
    response = frappe._dict(response)
    return response.get('message').get('status')
   
@frappe.whitelist()
def get_credentials():
    # url = http://localhost:82/api/method/rsmb_auth.api.login?usr=administrator&pwd=Hey@you$know14
    headers = {
        'Content-Type': 'application/json'
    }
    url = 'http://localhost:82/api/method/rsmb_auth.api.login'
    data = {
        'usr': 'administrator',
        'pwd': 'Hey@you$know14'
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response = json.loads(response.text)
    response = frappe._dict(response)
    secret_key = response.get('message').get('api_secret')
    api_key = response.get('message').get('api_key')
    auth = f"token {api_key}:{secret_key}"
    return auth

#chdeck if subscription is active
@frappe.whitelist()
def check_subscription(doc, method):
    site_url = frappe.utils.get_url()
    site_name = frappe.local.site
    # remove http:// or https://
    site_url = site_url.split("://")[-1]
    return site_url
    headers = {
        'Authorization': get_credentials()
    }
    url = f'http://localhost:82/api/method/reformiqo.api.get_site_quota?site_url={site_name}'
    data = {
        'site_url': site_url
    }
    response = requests.post(url, headers=headers)
    response = json.loads(response.text)
    response = frappe._dict(response)
    response = response.get('message')
    if response.get('status') != 'Active' and response.get('status') != 'Trialing':
        frappe.throw("Your subscription has expired, please renew your subscription to continue using the system")

@frappe.whitelist()
def get_site_plan():
    site_url = frappe.local.site
    headers = {
        'Authorization': get_credentials()
    }
    url = f'http://localhost:82/api/method/reformiqo.api.get_plan_details?site_name={site_url}'
    
    response = requests.post(url, headers=headers)
    response = json.loads(response.text)
    response = frappe._dict(response)
    return response.get('message')

@frappe.whitelist()
def get_site_trial_days():
    site_url = frappe.local.site
    headers = {
        'Authorization': get_credentials()
    }
    url = f'http://localhost:82/api/method/reformiqo.api.get_site_trial_days?site_name={site_url}'
    
    response = requests.post(url, headers=headers)
    response = json.loads(response.text)
    response = frappe._dict(response)
    return response.get('message')
@frappe.whitelist()
def get_subscription():
    site_url = frappe.local.site
    headers = {
        'Authorization': get_credentials()
    }
    url = f'http://localhost:82/api/method/reformiqo.api.get_subscription?site_name={site_url}'
    
    response = requests.post(url, headers=headers)
    response = json.loads(response.text)
    response = frappe._dict(response)
    return response.get('message')
@frappe.whitelist()
def pop_trial_remianing_days(doc, method=None):
    site_url = frappe.local.site
    if cint(get_site_trial_days()) <= 0 and get_subscription().get('status') != 'Active':
        frappe.throw("Your trial period has expired, please renew your subscription to continue using the system")
    elif cint(get_site_trial_days()) <= 20 and get_subscription().get('status') != 'Active':
        frappe.msgprint(f"Your trial period will expire in  {get_site_trial_days()} days, please renew your subscription to continue using the system")