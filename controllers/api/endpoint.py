import tornado.web

from django.utils import simplejson as json

from wtforms import Form, BooleanField, TextField, validators, SelectField, SelectMultipleField, IntegerField
from wtforms.validators import Required

from lib.multidict import MultiDict

from models.endpoint import EndpointManager, Endpoint
from models.user import UserManager
from controllers.endpoint import EndpointForm

class EndpointAPIHandler(tornado.web.RequestHandler):
    # no easy way to pass errors to get_error_html()
    errors = None

    def get_error_html(self, status_code, **kwargs):
        self.set_header('Content-Type', 'application/json')
        return json.dumps(self.errors)

    def get(self, subdomain, action = None, endpoint_id = None):
        if action == 'retrieve':
            if endpoint_id:
                self.write(unicode(EndpointManager.get_endpoint(endpoint_id)))
            else:
                # a little convoluted, but we don't want lists of strings!
                self.write(json.dumps([json.loads(unicode(x)) for x in EndpointManager.get_all_endpoints()]))

    def post(self, subdomain, method = None, endpoint_id = None):
        form = EndpointForm(MultiDict(self))
        if not form.validate():
            self.errors = form.errors
            raise tornado.web.HTTPError(400)
            return
        user = UserManager.get_current_user()
        if method == 'create':
            endpoint = Endpoint()
        else:
            endpoint = EndpointManager.get_endpoint(endpoint_id)

        endpoint.email = user.email
        endpoint.subdomain = user.subdomain
        endpoint.provider = self.get_argument('provider')
        endpoint.description = self.get_argument('description', '')
        endpoint.service_key = self.get_argument('service_key')
        endpoint.alert_text = self.get_argument('alert_text', '')
        endpoint.put()
        self.redirect('/%s' % subdomain)
