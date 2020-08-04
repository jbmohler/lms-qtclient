import functools
import rtlib

class BasicWidgetsPlugin:
    def polish(self, attr, type_, meta):
        if 'widget_factory' not in meta:
            meta['widget_factory'] = widget_constructor(type_)

    def widget_map(self):
        import apputils.widgets as wid
        return {\
            'date': wid.date,
            'datetime': wid.datetimewid,
            'boolean': wid.checkbox,
            'integer': wid.integer,
            'numeric': wid.quantity,
            'percent': wid.percent,
            'currency_usd': functools.partial(wid.quantity, decimals=2),
            'multiline': wid.multiline,
            'html': wid.richtext,
            'richtext': wid.richtext,
            'search': wid.search,
            'options': wid.combo,
            'radio': wid.radio}

def widget_constructor(type_):
    map = {}
    for tplug in rtlib.TYPE_DEFINITION_PLUGINS:
        if hasattr(tplug, 'widget_map'):
            map.update(tplug.widget_map())
    # This logging is merely annoying.
    # if type_ not in [None, 'basic'] and type_ not in map:
    #     logger.warning('field type {} not supplied with a widget'.format(type_))
    import apputils.widgets as wid
    return map.get(type_, wid.basic)

def construct(type_, parent=None, **kwargs):
    return widget_constructor(type_)(parent, **kwargs)

LOCAL_STATIC_SETTINGS = []

def verify_settings_load(parent, client, widgets):
    global LOCAL_STATIC_SETTINGS
    needs_load = lambda w: getattr(w, 'STATIC_SETTINGS_NAME', None) not in [None]+LOCAL_STATIC_SETTINGS
    to_load_widgets = [w for w in widgets if needs_load(w)]

    client.session.ensure_static_settings(list(set([w.STATIC_SETTINGS_NAME for w in to_load_widgets])))

    for w in to_load_widgets:
        w.load_static_settings()
