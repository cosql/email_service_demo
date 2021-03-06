# email_service_demo
Email Service Demo - for the Uber coding challenge

This is a demo for [Uber coding challenge] (https://github.com/uber/coding-challenge-tools/blob/master/coding_challenge.md#email-service).

###The requirements:
Create a service that accepts the necessary information and sends emails.
* It should provide an abstraction between two different email service providers.
* If one of the services goes down, your service can quickly fail over to a different provider without affecting your customers.


###The solution:
Implemented a mail service to let user send/save/view/delete all their emails.
A service running on google engine implemented using webapp2 framework.
The service uses mailgun as default mailing service provider and mandrill as
secondary backup.

**EmailRequest** class in **email_request.py** encapsulates required email information such as
recipient, email subject, etc.

A wrapper class **EmailClient** in **email_request.py** delivers emails, which tries to use
mailgun (implemented in **mailgun_client.py**) first and falls back to mandrill (implemented in **mandrill_client.py**) upon failures.

**main.py** contains all the http handlers including MainHandler, ComposeHandler, OutboxHandler and DeleteHandler.

* Users have to first log in using email address, (gmail can be used as
login credential).
* The most recent emails (up to 10) are shown on the homepage after
login, memcache is used as a lookaside cache to cache these recent
emails for each user.
* Users can search emails by their subjects. (only exact match is
supported due to the limitation of appengine ndb api)
* Users can click 'compose' to write a new email to send or save for
later use.
* And users can use 'outbox' link to retrieve all the historical
emails, and are able to delete a selected email at a time.
* Finally, users can also use 'drafts' link to see all the unsent emails
and then edit/send one of them.

[demo site] (http://emailservicedemo.appspot.com)

##How to Deploy
* Clone this repository
* Apply for mailgun and mandrill api keys and put them in config.py
* Launch the project using GoogleAppEngineLauncher with a preferred
project name.

##Development
### Design
I focused on backend side.
Different actions (compose, view all message, view drafts) are handled by corresponding handlers, these
handlers are inherited from webapp2.RequestHandler class.
Cookies are used when users want to edit an existing email.

###Implement Details
####Front-end
  * All the templates in template directory are manually generated.
  * Some javascript code in templates and js folder is used to do ajax request and change page view dynamically.
  * Some style setting for table row focus, button effect, etc. in static folder.

####Back-end

  * Python. I have used python for different purposes, and it is
    really convient to write web apps in python.

  * Webapp2. It is a recommended web framework for google app engine.

  * memcache. It is used to speed up home page render.

  * ndb. It is used as persistent storage for all the emails.

### Further Improvements
  * Due the upper limitation for mailgun and mandrill free accounts,
  users may be only allowed to send a certain amount of emails per day.
  * Add more features that people normally use, such as attachment,
  cc, bcc, and calendar request.
  * Implement full text search for emails.
  * More user-friendly UI.

## Run Tests
   * python unit_test.py
