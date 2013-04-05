import logging

from google.appengine.api import mail
from google.appengine.api import users as google_users
from google.appengine.api import xmpp
from google.appengine.api.app_identity import get_application_id
from google.appengine.ext import db

from django.utils import simplejson as json

from pagerduty import PagerDuty

PROVIDERS = [('pd', 'PagerDuty'),
             ('xmpp', 'GTalk/Email')]

class EndpointManager():
    @staticmethod
    def get_endpoint(endpoint_id, email = None):
        if not email:
            email = google_users.get_current_user().nickname()
        return db.GqlQuery('SELECT * FROM Endpoint WHERE email = :1 AND __key__ = :2 LIMIT 1',
            email, db.Key(endpoint_id))[0]

    @staticmethod
    def get_all_endpoints(email = None):
        if not email:
            email = google_users.get_current_user().nickname()
        return db.GqlQuery('SELECT * FROM Endpoint WHERE email = :1', email)

class Endpoint(db.Model):
    email = db.StringProperty()
    subdomain = db.StringProperty()
    provider = db.StringProperty()
    description = db.StringProperty()
    service_key = db.StringProperty()
    alert_text = db.StringProperty()

    def __str__(self):
        return unicode(self).encode('utf-8')

    def saving(self):
        if self.provider == 'xmpp':
            # Send xmpp invites on save
            for jid in self.service_key.split(','):
                xmpp.send_invite(jid.strip())

    def xmpp_send(self, type):
        if self.provider == 'xmpp':
            body = u"[{0}] {1}".format(type, self.alert_text)
            jids = map(lambda i: i.strip(), self.service_key.split(','))
            try:
                xmpp.send_message(jids, body)
            except Exception, ex:
                logging.error({'module': 'models.endpoing', 'message': 'xmpp.send_message error: %s' % ex})

            #And send emails too
            subject = u"[{0}] AlertBirds".format(type)
            sender = "sender@{0}.appspotmail.com".format(get_application_id())
            try:
                mail.send_mail(sender, self.service_key, subject, body)
            except Exception, ex:
                logging.error({'module': 'models.endpoing', 'message': 'mail.send_mail error: %s' % ex})


    def trigger(self, alert):
        if self.provider == 'pd':
            pagerduty = PagerDuty(self.service_key)
            pagerduty.trigger(self.alert_text, unicode(alert.key()), alert.description)
        elif self.provider == 'xmpp':
            self.xmpp_send('TRIGGER')

    def resolve(self, alert):
        if self.provider == 'pd':
            pagerduty = PagerDuty(self.service_key)
            pagerduty.resolve(unicode(alert.key()))
        elif self.provider == 'xmpp':
            self.xmpp_send('RESOLVE')

    def __unicode__(self):
        return json.dumps({'id': unicode(self.key()),
                           'email': self.email,
                           'subdomain': self.subdomain,
                           'provider': self.provider,
                           'description': self.description,
                           'service_key': self.service_key,
                           'alert_text': self.alert_text})
