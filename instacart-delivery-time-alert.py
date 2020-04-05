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

def send_simple_email(from_, to, subject, message_body):
    return requests.post(
        os.getenv('MAILGUN_DOMAIN'),
        auth=("api", os.getenv('MAILGUN_API_KEY')),
        data={"from": from_,
            "to": to,
            "subject": subject,
            "text": message_body})

def send_simple_text(from_number, to_number, message_body):
    client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
    client.messages.create(to=to_number, 
                    from_= from_number, 
                    body="-" + message_body )

def main():
    print(f"[{datetime.now()}]: --- Checking for Instacart Delivery Time Availability --") 

    load_dotenv(override=True)

    store_list = os.getenv('INSTACART_STORE_LIST').split(',')

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--email', type=bool, nargs='?', const=True, default=False,
                        help='Enable notification emails')
    parser.add_argument('-t', '--text', type=bool, nargs='?', const=True, default=False,
                        help='Enable notification texts')
    parser.add_argument('-s', '--store', required=True, choices=store_list)
    args = parser.parse_args()

    store = args.store

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

    conn.request("GET", f"/v3/containers/{store}/next_gen/retailer_information/content/delivery?source=web", payload, headers)
    res = conn.getresponse()
    if (res.status == 200):
        data = res.read()
        json_data = json.loads(data.decode("utf-8"))
        api_result = json_data["container"]["modules"][0]["types"][0]
        #print(api_result)

        # result_types = icon_info,error
        # 'error' means no delivery times are available!
        # 'icon_info' means delivery options are listed into second list available in "modules" section
        if api_result == 'error':
            # Do Nothing!
            print("No Delivery times are available! Let's check again in 5 minutes!")
            #pprint.pprint(json_data["container"]["modules"][0]['data']['title'])

        if api_result == 'icon_info':
            print('Delivery Time Windows available, Send Alert!')
            # We are in luck! Send Alert to Needy folks so that they can place their order right away!
            delivery_days_json = json_data["container"]["modules"][1]['data']['service_options']['service_options']['days']
            delivery_window_details = []
            for each_delivery_day in delivery_days_json:
                delivery_window_details.append(each_delivery_day["options"][0]["full_window"])

            #TODO - Send exact day and times available for Delivery Window - <Next Iteration>
            # Get all available dates from result and send them to end user        
            #delivery_window_messages = "\n".join(delivery_window_details)
            #message_body += delivery_window_messages
            if(args.email or args.text):
                if (args.email):
                    send_simple_email(os.getenv('MAILGUN_EMAIL_FROM'),
                                os.getenv('MAILGUN_EMAIL_TO'),
                                os.getenv('MAILGUN_EMAIL_SUBJECT_INSTACART_DELIVERY_ALERT'),
                                '\n' + os.getenv('MESSAGE_INSTACART_DELIVERY_ALERT_PART_1') + store + os.getenv('MESSAGE_INSTACART_DELIVERY_ALERT_PART_2') + f'\n\n Message Alert Date Time: {datetime.now()}')

                if (args.text):
                    send_simple_text(os.getenv('TWILIO_PHONE_FROM'),
                                os.getenv('TWILIO_PHONE_TO'),
                                '\n\n' + os.getenv('MESSAGE_INSTACART_DELIVERY_ALERT_PART_1') + store + os.getenv('MESSAGE_INSTACART_DELIVERY_ALERT_PART_2') + f'\n\n Message Alert Date Time: {datetime.now()}')
                    
                # create a lock file so that we don't spam ourselves with notification emails
                with open(os.getenv('INSTACART_NOTIFICATION_LOCK_FILE') + '.' + store, "w") as f:
                    f.write("")                
    else:
        print(f'Error Code: {res.status}')
        send_simple_email(os.getenv('MAILGUN_EMAIL_FROM'),
                        os.getenv('MAILGUN_EMAIL_TO'),
                        os.getenv('MAILGUN_ERROR_EMAIL_SUBJECT'),
                        '\n' + os.getenv('MESSAGE_ERROR') + f'\n Error Code: {res.status}')

        send_simple_text(os.getenv('TWILIO_PHONE_FROM'),
                        os.getenv('TWILIO_PHONE_TO'),
                        '\n' + os.getenv('MESSAGE_ERROR') + f'\n Error Code: {res.status}')

    print(f"[{datetime.now()}]: --- End of Checking on Instacart Delivery Time Availability --") 
    print()
    print()

# Reference Implementation: https://github.com/utkuufuk/ping-sm/blob/master/__main__.py
# https://utkuufuk.com/2020/03/28/grocery-scraping/
if __name__ == '__main__':
    main()