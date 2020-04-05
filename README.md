# Notify Me
Python Bot to notify on Instacart Delivery Time availability.
## Ingredients
[Postman](https://postman.com), [Python](https://python.org), [Twilio](https://twilio.com) and [Mailgun](https://mailgun.com)

## How to Use this Program
Run this program periodically as a crob job. It will check and notify you via email or text if any local stores listed on Instacart (such as Costco, Safeway, Kroger, Bharat Bazar, CVS) have delivery time windows available so that you can submit orders.

- Provides ability to monitor multiple stores available on Instacart
- You have option to get notification via email or text or both
- Only one notification per delivery window availability

### Email Notifications
You will need a [Mailgun](https://www.mailgun.com/) domain to enable notifcation emails.
### Text Notifications
[Twilio](https://www.twilio.com/) account will be needed. 

For both of these services (Mailgun & Twilio), I'm replying on basic tier plan which is free and good enough for our minimum needs.

## Setup
- We will be using Python 3. It's recommended you use Python Virtual Environment along with [Pyenv](https://realpython.com/intro-to-pyenv/)
- Install all needed libraries `pip install -r requirements.txt`
- Configuration
  - Copy example.env as .env file into your home directory.
  - Update each parameter with correct values for your setup. To Find out your Session Cookie info, use [Postman](https://www.postman.com/) App along with Cookies Interceptor for [Chrome](https://support.getpostman.com/hc/en-us/articles/203779012-How-do-I-access-Chrome-s-cookies-in-Postman-s-Chrome-App-)
  - Update stores parameter with store names available in your local area. This may be case sensitivie, not sure. 
    - TODO: Future plan is get list of all stores available in your local area using zip code and only provide those as options.

## Running the program
```
# Get Help to know more about all available options (--store is mandatory. select from available options as mentioned in .env)
python instacart-delivery-time-alert.py --help

# Simple Command line execution
python instacart-delivery-time-alert.py

# Command line execution with email and text notification
python instacart-delivery-time-alert.py --email --text --store costco

# Cron job to run every 5 minutes
*/5 * * * * /usr/local/bin/python /Users/rkadam/work/pyfun/notify-me/instacart-delivery-time-alert.py --email --text --store total-wine-more 2>&1 >> /Users/rkadam/work/pyfun/instacart-run.log.total-wine-more
*/5 * * * * /usr/local/bin/python /Users/rkadam/work/pyfun/notify-me/instacart-delivery-time-alert.py --email --text --store costco 2>&1 >> /Users/rkadam/work/pyfun/instacart-run.log.costco
```
## Limitation
* You will need to delete lock file for given store (example notification-instacart.lock.costco) if you want to get notification again for your next order.
