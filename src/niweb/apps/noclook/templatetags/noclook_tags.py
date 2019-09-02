from apps.noclook.models import NodeType, NodeHandle
from apps.noclook.helpers import neo4j_data_age, neo4j_report_age, get_node_type
import norduniclient as nc
from datetime import datetime, timedelta
from django import template
import json
import re
from django.utils.html import escape, format_html
from dynamic_preferences.registries import global_preferences_registry
from django.utils import six


register = template.Library()


@register.inclusion_tag('type_menu.html')
def type_menu():
    """
    Returns a list with all wanted NodeType objects for easy menu
    handling.
    Just chain .exclude(type='name') to remove unwanted types.
    """
    types = NodeType.objects.exclude(hidden=True)
    return {'types': types}


@register.simple_tag(takes_context=True)
def noclook_node_to_url(context,handle_id):
    """G
    Takes a node id as a string and returns the absolute url for a node.
    """
    #handle fallback
    urls = context.get('urls')
    if urls and handle_id in urls:
      return urls.get(handle_id)
    else:
      return "/nodes/%s" % handle_id
   #else:
      #
      #try: 
      #  return get_node_url(handle_id)
      #except ObjectDoesNotExist:
      #  return ''


@register.simple_tag(takes_context=True)
def noclook_node_to_link(context, node):
    if "handle_id" in node:
        url = noclook_node_to_url(context, node.get("handle_id"))
        result = format_html(u'<a class="handle" href="{}" title="{}">{}</a>', url, node.get("name"), node.get("name"))
    else:
        result = None
    return result


@register.assignment_tag
def noclook_node_to_node_handle(node):
    """
    :param node: Neo4j node
    :return node_handle: Django NodeHandle or None
    """
    try:
        node_handle = NodeHandle.objects.get(handle_id = node.getProperty('handle_id', ''))
    except NodeHandle.DoesNotExist:
        return None
    return node_handle


@register.assignment_tag
def noclook_last_seen_to_dt(noclook_last_seen):
    """
    Returns noclook_last_seen property (ex. 2011-11-01T14:37:13.713434) as a
    datetime.datetime. If a datetime cant be made None is returned.
    """
    try:
        dt = datetime.strptime(noclook_last_seen, '%Y-%m-%dT%H:%M:%S.%f')
    except (ValueError, TypeError):
        dt = None
    return dt


@register.inclusion_tag('noclook/table_date_column.html')
def noclook_last_seen_as_td(date):
    """
    Returns noclook_last_seen property (ex. 2011-11-01T14:37:13.713434) as a
    table column.
    """
    if type(date) is datetime:
        last_seen = date    
    else:
        last_seen = noclook_last_seen_to_dt(date)
    return {'last_seen': last_seen}


@register.assignment_tag
def timestamp_to_td(seconds):
    """
    Converts a UNIX timestamp to a timedelta object.
    """
    try:
        td = timedelta(seconds=float(seconds))
    except (AttributeError, ValueError, TypeError):
        td = None
    return td


@register.assignment_tag
def noclook_has_expired(item):
    """
    Returns True if the item has a noclook_last_seen property and it has expired.
    """
    last_seen, expired = neo4j_data_age(item)
    return expired


@register.assignment_tag
def noclook_get_model(handle_id):
    """
    :param handle_id: unique id
    :return: Node model
    """
    try:
        return nc.get_node_model(nc.graphdb.manager, handle_id)
    except nc.exceptions.NodeNotFound:
        return ''


@register.assignment_tag(takes_context=True)
def noclook_get_type(context, handle_id):
    urls = context.get('urls')
    if urls and handle_id in urls:
        raw_type = urls[handle_id].split('/')[1]
        return raw_type.replace('-', ' ').title()
    else:
        try:
            return get_node_type(handle_id)
        except nc.exceptions.NodeNotFound:
            return ''


@register.assignment_tag
def noclook_get_ports(handle_id):
    """
    Return port nodes that are either dependencies or connected to item. Also returns the
    ports top parent.
    :param handle_id: unique id
    :return: list
    """
    return nc.get_node_model(nc.graphdb.manager, handle_id).get_ports()


@register.assignment_tag
def noclook_get_location(handle_id):
    return nc.get_node_model(nc.graphdb.manager, handle_id).get_location()


@register.assignment_tag
def noclook_report_age(item, old, very_old):
    """
    :param item: Neo4j node
    :return: String, current, old, very_old
    """
    try:
        return neo4j_report_age(item, old, very_old)
    except TypeError:
        return ''


@register.assignment_tag
def noclook_has_rogue_ports(handle_id):
    """
    :param handle_id: unique id
    :return: Boolean
    """
    q = """
        MATCH (host:Node {handle_id: {handle_id}})<-[r:Depends_on]-()
        RETURN count(r.rogue_port) as count
        """
    d = nc.query_to_dict(nc.graphdb.manager, q, handle_id=handle_id)
    if d['count']:
        return True
    return False


class BlockVar(template.Node):

    def __init__(self, nodelist, context_var):
        self.nodelist = nodelist
        self.context_var = context_var

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.context_var] = output
        return ''


@register.tag
def blockvar(parser, token):
    tagname, args= token.contents.split(None, 1)
    out_var = args.split(None,1)[0]
    nodelist = parser.parse("endblockvar",)
    parser.delete_first_token()
    return BlockVar(nodelist, out_var)


@register.inclusion_tag("noclook/table.html")
def table(th, tbody, *args, **kwargs):
    context = {'th': th, 'tbody': tbody}
    context.update(kwargs)
    return context


@register.inclusion_tag("noclook/table_search.html")
def table_search(target=None, field_id=None):
    return {"target": target, "field_id":field_id}


@register.filter
def as_json(value):
    return json.dumps(value, indent=4, sort_keys=True)


@register.simple_tag
def hardware_module(module, level=0):
    result = ""
    indent = " "*4*level
    keys = ["name", 
            "version", 
            "part_number", 
            "serial_number", 
            "description",
            "hardware_description", 
            "model_number",
            "clei_code"]
    if module:
        result += "\n".join([u"{0}{1}: {2}".format(indent,key,module[key]) for key in keys if key in module ])
        if module.get('modules') or module.get('sub_modules'):
            result += "\n{0}Modules:\n\n".format(indent)
            result += "\n".join([ hardware_module(mod, level+1) for mod in module.get('modules',[]) ])
            result += "\n".join([ hardware_module(mod, level+1) for mod in module.get('sub_modules',[]) ])
        result += "\n{0}{1}\n".format(indent,"-"*8)
    
    return result


@register.simple_tag
def scan_data(host_node):
    return escape(json.dumps({"target": host_node.data.get("hostnames", ["unknown"])[0], "ipv4s": host_node.data.get("ip_addresses",[])}))


@register.inclusion_tag("noclook/dynamic_ports.html", takes_context=True)
def dynamic_ports(context,bulk_ports, *args, **kwargs):
    port_names, port_types = [], []
    if context.request.POST:
        port_names = context.request.POST.getlist("port_name")
        port_types = context.request.POST.getlist("port_type")
    ports = zip(port_names, port_types)
    bulk_ports.auto_id = False
    
    export = {}
    export.update({"bulk_ports": bulk_ports, "ports": ports})
    export.update(kwargs)
    return export


@register.simple_tag
def more_info_url(name):
    global_preferences = global_preferences_registry.manager()
    base_url = global_preferences['general__more_info_link']
    return u'{}{}'.format(base_url, name)


@register.tag
def accordion(parser, token):
    tokens = token.split_contents()
    title = tokens[1]
    _id = tokens[2]
    try:
        parent_id = tokens[3]
    except IndexError:
        parent_id = None
    nodelist = parser.parse("endaccordion",)
    parser.delete_first_token()
    return AccordionNode(_id, title, nodelist, parent_id)


def is_quoted(what):
    return re.match(r'^[\'"].*[\'"]$', what)


def resolve_arg(arg, context):
    if not arg:
        result = arg
    elif is_quoted(arg):
        result = arg[1:-1]
    else:
        result = template.Variable(arg).resolve(context)
    return result


class AccordionNode(template.Node):
    def __init__(self, _id, title, nodelist, parent_id=None, template='noclook/tags/accordion_tag.html'):
        self.nodelist = nodelist
        self.id = _id
        self.title = title
        self.template = template
        self.parent_id = parent_id

    def render(self, context):
        t = context.render_context.get(self)
        if t is None:
            t = context.template.engine.get_template(self.template)
            context.render_context[self] = t
        new_context = context.new({
            'accordion_id': resolve_arg(self.id, context),
            'accordion_parent_id': resolve_arg(self.parent_id, context),
            'accordion_title': resolve_arg(self.title, context),
            'csrf_token': context.get('csrf_token'),
            'body': self.nodelist.render(context)})
        return t.render(new_context)


@register.inclusion_tag('noclook/tags/json_combo.html')
def json_combo(form_field, urls, initial=None, skip_field=False):
    urls = [url.strip() for url in urls.split(",")]
    first_url = None

    if initial:
        if isinstance(initial, six.text_type) or isinstance(initial, str):
            initial = initial.split(',')
        choices = [u"['{}',' {}']".format(val, val.title().replace("-", " ")) for val in initial]
        initial = u",\n".join(choices)
    else:
        first_url = urls[0]
        if len(urls) > 1:
            urls = urls[1:]
        else:
            urls = []
    return {
        'first_url': first_url,
        'initial': initial,
        'urls': urls,
        'field': form_field,
        'skip_field': skip_field,
    }


@register.inclusion_tag('noclook/tags/typeahead.html')
def typeahead(form_field, url, placeholder=None, has_parent=False, min_length=3, node_types=None):

    return {
        'url': url,
        'placeholder': placeholder,
        'field': form_field,
        'has_parent': has_parent,
        'min_length': min_length,
        'node_types': node_types,
    }


def _equipment_spacer(units):
    return {'units': units, 'spacer': True, 'height': "{}px".format(units * 18)}


def _rack_sort(item):
    pos = item.get('node').data.get('rack_position', -1)
    size = item.get('node').data.get('rack_units', 0) * -1

    return (pos, size)

RACK_SIZE_PX=20

def _equipment(item):
    data = item.get('node').data
    units = data.get('rack_units', 1)
    return {
        'units': units,
        'position': data.get('rack_position'),
        'position_end': units + data.get('rack_position', 1) - 1,
        'height': "{}px".format(units * RACK_SIZE_PX),
        'sub_equipment': [],
        'data': data,
    }


@register.inclusion_tag('noclook/tags/rack.html')
def noclook_rack(rack, equipment):
    racked_equipment = []
    unracked_equipment = []

    if equipment:
        equipment.sort(key=_rack_sort)
    idx = 1
    last_eq = None
    for item in equipment:
        view_data = _equipment(item)
        ridx = view_data.get('position')
        if ridx and ridx > 0:
            spacing = ridx - idx
            if spacing < 0:
                # Equipment overlaps with previous
                last_eq['sub_equipment'].append(view_data)
            else:
                if spacing > 0:
                    racked_equipment.append(_equipment_spacer(spacing))
                racked_equipment.append(view_data)

                idx = ridx + view_data['units']
                last_eq = view_data
        else:
            unracked_equipment.append(item)
    return {
        'rack_size': rack.data.get('rack_units', 42) * RACK_SIZE_PX,
        'racked_equipment': racked_equipment,
        'unracked_equipment': unracked_equipment,
    }


@register.filter
def rack_sort(equipment):
    if equipment:
        equipment.sort(key=_rack_sort, reverse=True)
    return equipment
