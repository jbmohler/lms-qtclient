import xml.dom.minidom as xml
import client.qt as qt
import apputils

URL_BASE = 'api/roscoe'

"""
Twilio params:

    ('SmsSid', 'SMa9f871c6f183163a54199a5259bfb994')
    ('FromState', 'PA')
    ('MessageSid', 'SMa9f871c6f183163a54199a5259bfb994')
    ('ToZip', '19406')
    ('FromCity', 'NORRISTOWN')
    ('ToCity', 'NORRISTOWN')
    ('Body', 'Have a good day')
    ('ToState', 'PA')
    ('AccountSid', 'AC89a4ccde189dc41f0df85ac6fe74ecdf')
    ('ToCountry', 'US')
    ('FromZip', '19403')
    ('NumMedia', '0')
    ('To', '+14843334444')
    ('From', '+14845556666')
    ('SmsStatus', 'received')
    ('SmsMessageSid', 'SMa9f871c6f183163a54199a5259bfb994')
    ('FromCountry', 'US')
    ('MessagingServiceSid', 'MG7ff59c61b16993c055c73c185357f177')
    ('ApiVersion', '2010-04-01')
    ('NumSegments', '1')
"""

TEST_PHONES = [\
        '+11234567890',
        '+14843334444',
        '+14845556666']

class TwilioParams:
    def __init__(self):
        pass

    def get_data(self):
        return {'Body': self.Body, 'From': self.From}

def test_roscoe(session):
    dlg = qt.FormEntryDialog('PyHacc Journal')

    dlg.add_form_row('Body', 'Message', 'basic')
    dlg.add_form_row('From', 'Source phone', 'options', options=[(p, p) for p in TEST_PHONES])

    def apply(bound):
        nonlocal session, dlg
        client = session.raw_client()
        payload = client.post(URL_BASE, data=bound.get_data())
        root = xml.parseString(payload)
        xx = root.toprettyxml()
        apputils.information(dlg, 'TwiML:\n\n{}'.format(xx), richtext=False)

    obj = TwilioParams()
    obj.Body = ''
    obj.From = TEST_PHONES[1]

    dlg.bind(obj)
    dlg.applychanges = apply

    dlg.exec_()
