#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       noclook_consumer.py
#
#       Copyright 2010 Johan Lundberg <lundberg@nordu.net>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import sys
import os
from os.path import join
import json
import datetime
import ConfigParser
import argparse
import logging

## Need to change this path depending on where the Django project is
## located.
base_path = '../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "niweb.settings.prod")
import django
from django.conf import settings as django_settings
from apps.noclook.models import NodeType, NodeHandle
from apps.noclook import helpers  # Shortcircuit circular dependency
from apps.noclook import activitylog
from django_comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
import norduniclient as nc

#django cache hack
django_settings.CACHES['default']['LOCATION'] = '/tmp/django_cache_consumer'
logger = logging.getLogger('noclook_consumer')
django.setup()

import noclook_juniper_consumer
import noclook_nmap_consumer
import noclook_checkmk_consumer
import noclook_cfengine_consumer

# This script is used for adding the objects collected with the
# NERDS producers to the NOCLook database viewer.


def init_config(p):
    """
    Initializes the configuration file located in the path provided.
    """
    try:
        config = ConfigParser.SafeConfigParser()
        config.read(p)
        return config
    except IOError as (errno, strerror):
        logger.error("I/O error({0}): {1}".format(errno, strerror))


def normalize_whitespace(text):
    """
    Remove redundant whitespace from a string.
    """
    text = text.replace('"', '').replace("'", '')
    return ' '.join(text.split())


def load_json(json_dir, starts_with=''):
    """
    Thinks all files in the supplied dir are text files containing json.
    """
    logger.info('Loading data from {!s}.'.format(json_dir))
    try:
        for subdir, dirs, files in os.walk(json_dir):
            gen = (_file for _file in files if _file.startswith(starts_with))
            for a_file in gen:
                try:
                    f = open(join(json_dir, a_file), 'r')
                    yield json.load(f)
                except ValueError as e:
                    logger.error('Encountered a problem with {f}.'.format(f=a_file))
                    logger.error(e)
    except IOError as e:
        logger.error('Encountered a problem with {d}.'.format(d=json_dir))
        logger.error(e)


def generate_password(n):
    """
    Returns a psudo random string of lenght n.
    http://code.activestate.com/recipes/576722-pseudo-random-string/
    """
    import os
    import math
    from base64 import b64encode
    return b64encode(os.urandom(int(math.ceil(0.75*n))),'-_')[:n]


def get_user(username='noclook'):
    """
    Gets or creates a user that can be used to insert data.
    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        passwd = generate_password(30)
        user = User.objects.create_user(username, '', passwd)
    return user


def get_node_type(type_name):
    """
    Returns or creates and returns the NodeType object with the supplied
    name.
    """
    try:
        node_type = NodeType.objects.get(type=type_name)
    except NodeType.DoesNotExist:
        # The NodeType was not found, create one
        from django.template.defaultfilters import slugify
        node_type = NodeType(type=type_name, slug=slugify(type_name))
        node_type.save()
    return node_type


def get_unique_node(name, node_type, meta_type):
    """
    Gets or creates a NodeHandle with the provided name.
    Returns the NodeHandles node.
    """
    name = normalize_whitespace(name)
    node_handle = get_unique_node_handle(name, node_type, meta_type)
    node = node_handle.get_node()
    return node


def get_unique_node_handle(node_name, node_type_name, node_meta_type):
    """
    Takes the arguments needed to create a NodeHandle, if there already
    is a NodeHandle with the same name and type it will be considered
    the same one.
    Returns a NodeHandle object.
    """
    user = get_user()
    node_type = get_node_type(node_type_name)
    defaults = {
        'node_meta_type': node_meta_type,
        'creator': user,
        'modifier': user
    }
    node_handle, created = NodeHandle.objects.get_or_create(node_name=node_name, node_type=node_type, defaults=defaults)
    if created:
        activitylog.create_node(user, node_handle)
    return node_handle


def get_unique_node_handle_by_name(node_name, node_type_name, node_meta_type, allowed_node_types=None):
    """
    Takes the arguments needed to create a NodeHandle, if there already
    is a NodeHandle with the same name considered the same one.

    If the allowed_node_types is set the supplied node types will be used for filtering.

    Returns a NodeHandle object.
    """
    try:
        if not allowed_node_types:
            allowed_node_types = [node_type_name]
        return NodeHandle.objects.filter(node_type__type__in=allowed_node_types).get(node_name=node_name)
    except NodeHandle.DoesNotExist:
        return get_unique_node_handle(node_name, node_type_name, node_meta_type)
    except NodeHandle.MultipleObjectsReturned:
        logger.error("Assumed unique node not unique: {0}".format(node_name))
        return None


def create_node_handle(node_name, node_type_name, node_meta_type):
    """
    Takes the arguments needed to create a NodeHandle.
    Returns a NodeHandle object.
    """
    user = get_user()
    node_type = get_node_type(node_type_name)
    node_handle = NodeHandle.objects.create(node_name=node_name, node_type=node_type, node_meta_type=node_meta_type,
                                            creator=user, modifier=user)
    node_handle.save()
    activitylog.create_node(user, node_handle)
    return node_handle


def restore_node(handle_id, node_name, node_type_name, node_meta_type):
    """
    Tries to get a existing node handle from the SQL database before creating
    a new handle with an old handle id.
    
    When we are setting the handle_id explicitly we need to run django-admin.py
    sqlsequencereset noclook and paste that SQL statements in to the dbhell.
    """
    user = get_user()
    node_type = get_node_type(node_type_name)
    defaults = {
        'node_name': node_name,
        'node_type': node_type,
        'node_meta_type': node_meta_type,
        'creator': user,
        'modifier': user
    }
    node_handle, created = NodeHandle.objects.get_or_create(handle_id=handle_id, defaults=defaults)
    if not created:
        node_handle.node_meta_type = node_meta_type
    node_handle.save()  # Create a node if it does not already exist
    return node_handle


def set_comment(node_handle, comment):
    """
    Sets the comment string as a comment for the provided node_handle.
    """
    content_type = ContentType.objects.get_for_model(NodeHandle)
    object_pk = node_handle.pk
    user = get_user()
    site_id = django_settings.SITE_ID
    c = Comment(content_type=content_type, object_pk=object_pk, user=user, site_id=site_id, comment=comment)
    c.save()


def _consume_node(item):
    try:
        properties = item.get('properties')
        node_name = properties.get('name')
        handle_id = item.get('handle_id')
        node_type = item.get('node_type')
        meta_type = item.get('meta_type')
        # Get a node handle
        nh = restore_node(handle_id, node_name, node_type, meta_type)
        nc.set_node_properties(nc.neo4jdb, nh.handle_id, properties)
        logger.info('Added node {handle_id}.'.format(handle_id=handle_id))
    except Exception as e:
        ex_type = type(e).__name__
        logger.error('Could not add node {} (handle_id={}, node_type={}, meta_type={}) got {}: {})'.format(node_name, handle_id, node_type, meta_type, ex_type,  str(e)))


def consume_noclook(nodes, relationships):
    """
    Inserts the backup made with NOCLook producer.
    """
    tot_nodes = 0
    tot_rels = 0
    # Loop through all files starting with node
    for i in nodes:
        item = i['host']['noclook_producer']
        if i['host']['name'].startswith('node'):
            _consume_node(item)
            tot_nodes += 1
    print 'Added {!s} nodes.'.format(tot_nodes)

    # Loop through all files starting with relationship
    x = 0
    with nc.neo4jdb.write as w:
        for i in relationships:
            rel = i['host']['noclook_producer']
            properties = rel.get('properties')
            props = {'props': properties}
            q = """
                MATCH (start:Node { handle_id:{start_id} }),(end:Node {handle_id: {end_id} })
                CREATE UNIQUE (start)-[r:%s { props } ]->(end)
                """ % rel.get('type')

            w.execute(q, start_id=rel.get('start'), end_id=rel.get('end'), **props).fetchall()
            logger.info('{start}-[{rel_type}]->{end}'.format(start=rel.get('start'), rel_type=rel.get('type'),
                                                             end=rel.get('end')))
            x += 1
            if x >= 1000:
                w.connection.commit()
            x = 0
            tot_rels += 1
    print 'Added {!s} relationships.'.format(tot_rels)


def run_consume(config_file):
    """
    Function to start the consumer from another script.
    """
    config = init_config(config_file)
    # juniper_conf
    juniper_conf_data = config.get('data', 'juniper_conf')
    remove_expired_juniper_conf = config.getboolean('delete_data', 'juniper_conf')
    juniper_conf_data_age = config.get('data_age', 'juniper_conf')
    # nmap services
    nmap_services_py_data = config.get('data', 'nmap_services_py')
    # nagios checkmk
    nagios_checkmk_data = config.get('data', 'nagios_checkmk')
    # cfengine report
    cfengine_data = config.get('data', 'cfengine_report')
    # noclook
    noclook_data = config.get('data', 'noclook')
    # Consume data
    if juniper_conf_data:
        data = load_json(juniper_conf_data)
        noclook_juniper_consumer.consume_juniper_conf(data)
    if nmap_services_py_data:
        data = load_json(nmap_services_py_data)
        noclook_nmap_consumer.insert_nmap(data)
    if nagios_checkmk_data:
        data = load_json(nagios_checkmk_data)
        noclook_checkmk_consumer.insert(data)
    if cfengine_data:
        data = load_json(cfengine_data)
        noclook_cfengine_consumer.insert(data)
    if noclook_data:
        nodes = load_json(noclook_data, starts_with="node")
        relationships = load_json(noclook_data, starts_with="relationship")
        consume_noclook(nodes, relationships)
    # Clean up expired data
    if remove_expired_juniper_conf:
        noclook_juniper_consumer.remove_juniper_conf(juniper_conf_data_age)


def purge_db():
    for nh in NodeHandle.objects.all():
        nh.delete()


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('-P', action='store_true', help='Purge the database.')
    parser.add_argument('-I', action='store_true', help='Insert data in to the database.')
    parser.add_argument('-V', action='store_true', default=False)
    args = parser.parse_args()
    # Start time
    start = datetime.datetime.now()
    timestamp_start = datetime.datetime.strftime(start, '%b %d %H:%M:%S')
    print '%s noclook_consumer.py was started.' % timestamp_start
    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    # Purge DB if option -P was used
    if args.P:
        print 'Purging database...'
        purge_db()
    if args.V:
        logger.setLevel(logging.INFO)
    # Insert data from known data sources if option -I was used
    if args.I:
        print 'Inserting data...'
        run_consume(args.C)
    # end time
    end = datetime.datetime.now()
    timestamp_end = datetime.datetime.strftime(end, '%b %d %H:%M:%S')
    print '%s noclook_consumer.py ran successfully.' % timestamp_end
    timedelta = end - start
    print 'Total time: %s' % timedelta
    return 0

if __name__ == '__main__':
    logger.propagate = False
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
