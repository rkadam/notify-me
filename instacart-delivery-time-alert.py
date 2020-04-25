from twilio.rest import Client

import http.client
import argparse
import pprint
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
import os
import sys
import logging

# https://documentation.mailgun.com/en/latest/quickstart-sending.html
def send_simple_email(from_email, to_emails, subject, message_body):
    return requests.post(
        os.getenv('MAILGUN_DOMAIN'),
        auth=("api", os.getenv('MAILGUN_API_KEY')),
        data={"from": from_email,
            "to": to_emails,
            "subject": subject,
            "text": message_body})

def send_simple_text(from_number, to_numbers, message_body):
    to_numbers_list = [x.strip() for x in to_numbers.split(',') ]
    for to_number in to_numbers_list:
        client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
        client.messages.create( to=to_number, 
                                from_= from_number, 
                                body="-" + message_body )

def main():
    print(f"[{datetime.now()}]: --- Checking for Instacart Time Availability --") 

    load_dotenv(override=True)
    store_list = os.getenv('INSTACART_STORE_LIST').split(',')

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--email', type=bool, nargs='?', const=True, default=False,
                        help='Enable notification emails')
    parser.add_argument('-t', '--text', type=bool, nargs='?', const=True, default=False,
                        help='Enable notification texts')
    parser.add_argument('-m', '--method', required=True, choices=['pickup', 'delivery'],
                        help='pickup or delivery')
    parser.add_argument('-s', '--store', required=True, choices=store_list)
    args = parser.parse_args()

    store = args.store
    shopping_method = args.method
    
    # abort if an opening was found previously
    if (args.email or args.text):
        try:
            with open(os.getenv('INSTACART_NOTIFICATION_LOCK_FILE') + '.' + store):
                print(f"[{datetime.now()}]: Lock file exists, aborting...")
            sys.exit(0)
        except IOError:
            pass
        
    conn = http.client.HTTPSConnection(os.getenv('INSTACART_BASE_URL'))
    payload = ''
    headers = {
      'Cookie': os.getenv('INSTACART_COOKIE_CONTENT')
    }

    # https://www.pylenin.com/blogs/python-logging-guide/
    log_format = '%(asctime)s - %(name)s - %(levelname)s - line %(lineno)d - %(message)s'
    logger = logging.getLogger(__name__)
    logger.setLevel(os.getenv('INSTACART_LOG_LEVEL'))
    file_handler = logging.FileHandler(os.getenv('INSTACART_LOG_FILE') + '.' + store)
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


    #ensure you are going to the correct store
    if ( os.getenv(store + "_LOC_ID") and  os.getenv(store + "_ID") ):
        #TODO: either make the location id a cmd line flag or loop through multi values
        #      so that you can check multiple locations of the same store
        payload_loc = {'current_zip_code': os.getenv('MY_ZIP'),
                       'warehouse_location_id': os.getenv(store + "_LOC_ID"),
                       'current_retailer_id': os.getenv(store + "_ID")
        }
        json_payload_loc = json.dumps(payload_loc)
        headers_loc = {
            'Cookie':  os.getenv('INSTACART_COOKIE_CONTENT') + ";",
            'content-type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        }
        logger.debug(json_payload_loc)
        logger.info('Setting store location')
        conn.request("PUT", f"/v3/bundle?source=web", json_payload_loc, headers_loc)
        res_loc = conn.getresponse()
        loc_data = res_loc.read()
        logger.debug(f'Status Code: {res_loc.status}')
        
    conn.request("GET", f"/v3/containers/{store}/next_gen/retailer_information/content/{shopping_method}?source=web", payload, headers)
    res = conn.getresponse()
    if (res.status == 200):
        data = res.read()
        json_data = json.loads(data.decode("utf-8"))
        api_result = json_data["container"]["modules"][0]["types"][0]

        # Two possible values for api_result = icon_info or error
        # 'error' means no times are available!
        # 'icon_info' means options are listed into second list available in "modules" section
        if api_result == 'error':
            # Do Nothing!
            logger.debug(pprint.pformat(json_data["container"]["modules"][0]['data']['title']))
            logger.error("No " + shopping_method + " times are available! Let's check again in 5 minutes!")

        if api_result == 'icon_info':
            logger.info(shopping_method + ' time windows available, Send Alert!')
            # We are in luck! Send Alert to Needy folks so that they can place their order right away!
            days_json = json_data["container"]["modules"][1]['data']['service_options']['service_options']['days']
            window_details = []
            for each_day in days_json:
                window_details.append(each_day["options"][0]["full_window"])
            window_messages = "\n".join(window_details)
            msg_body = '\n' + os.getenv('MESSAGE_INSTACART_ALERT_PART_1') + store + os.getenv('MESSAGE_INSTACART_ALERT_PART_2') + '\n\n' + window_messages + f'\n\n Message Alert Date Time: {datetime.now()}'
            logger.info(msg_body)
            
            if(args.email or args.text):
                if (args.email):
                    for email in os.getenv('MAILGUN_EMAIL_TO').split(','):
                        send_simple_email(os.getenv('MAILGUN_EMAIL_FROM'),
                                          email,
                                          os.getenv('MAILGUN_EMAIL_SUBJECT_INSTACART_ALERT'),
                                          msg_body)

                if (args.text):
                    for phone_number in os.getenv('TWILIO_PHONE_TO').split(','):
                        send_simple_text(os.getenv('TWILIO_PHONE_FROM'),
                                         phone_number,
                                         msg_body)
                    
                # create a lock file so that we don't spam ourselves with notification emails
                with open(os.getenv('INSTACART_NOTIFICATION_LOCK_FILE') + '.' + store, "w") as f:
                    f.write("")                
    else:
        print(f'Error Code: {res.status}')

        if(args.email or args.text):
            if (args.email):
                for email in os.getenv('MAILGUN_EMAIL_TO').split(','):                
                    send_simple_email(os.getenv('MAILGUN_EMAIL_FROM'),
                                      email
                                      os.getenv('MAILGUN_ERROR_EMAIL_SUBJECT'),
                                      '\n' + os.getenv('MESSAGE_ERROR') + f'\n Error Code: {res.status}')

        if (args.text):
            for phone_number in os.getenv('TWILIO_PHONE_TO').split(','):        
                send_simple_text(os.getenv('TWILIO_PHONE_FROM'),
                                 phone_number,
                                 '\n' + os.getenv('MESSAGE_ERROR') + f'\n Error Code: {res.status}')
                
    logger.info("-- End of Checking on Instacart Time Availability --") 
    logger.info("")
    logger.info("")

# Reference Implementation: https://github.com/utkuufuk/ping-sm/blob/master/__main__.py
# https://utkuufuk.com/2020/03/28/grocery-scraping/
if __name__ == '__main__':
    main()
