# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from graphene import relay
from niweb.schema import schema
from pprint import pformat
from apps.noclook.models import NodeHandle, NodeType
from apps.noclook.tests.stressload.data_generator import \
    CommunityFakeDataGenerator, NetworkFakeDataGenerator, \
    PhysicalDataRelationMaker
from . import Neo4jGraphQLNetworkTest

import logging
import norduniclient as nc


class GlobalSearchTest(Neo4jGraphQLNetworkTest):
    def get_expected_length(self, search):
        q = """
            MATCH (n:Node)
            WHERE any(prop in keys(n) WHERE n[prop] =~ "(?i).*{search}.*")
            RETURN count(n) as total
            """.format(search=search)

        res = nc.query_to_dict(nc.graphdb.manager, q, search=search)

        return res['total']

    def test_global_search(self):
        community_generator = CommunityFakeDataGenerator()
        network_generator = NetworkFakeDataGenerator()

        # create several entities
        organization1 = community_generator.create_organization(name="organization-01")
        organization2 = community_generator.create_organization(name="organization-02")

        port1 = network_generator.create_port(name="port-01")
        port2 = network_generator.create_port(name="port-02")

        # search common pattern
        query_t = '''
        {{
          search_generalsearch(filter:{{query: "{search}"}}){{
            edges{{
              node{{
                ninode{{
                  id
                  name
                  __typename
                }}
                match_txt
              }}
            }}
          }}
        }}
        '''

        search = '-0'
        query = query_t.format(search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        expected_num = self.get_expected_length(search)

        results = result.data['search_generalsearch']['edges']
        self.assertEqual(len(results), expected_num, \
            pformat(result.data, indent=1))

        # search first pattern
        search = '-01'
        query = query_t.format(search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        expected_num = self.get_expected_length(search)
        results = result.data['search_generalsearch']['edges']
        self.assertEqual(len(results), expected_num, \
            pformat(result.data, indent=1))

        # search second pattern
        search = '-02'
        query = query_t.format(search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        expected_num = self.get_expected_length(search)
        results = result.data['search_generalsearch']['edges']
        self.assertEqual(len(results), expected_num)


class SearchPortTest(Neo4jGraphQLNetworkTest):
    def setUp(self):
        super().setUp()

        data_generator = NetworkFakeDataGenerator()
        relation_maker = PhysicalDataRelationMaker()

        # get one of the ports
        self.common = 'test-0'
        self.rack = data_generator.create_rack()
        self.switch_with_ports = data_generator.create_switch()

        self.port1 = data_generator.create_port(name="{}1".format(self.common))
        self.port2 = data_generator.create_port(name="{}2".format(self.common))

        relation_maker.add_has(data_generator.user, self.switch_with_ports, self.port1)
        relation_maker.add_has(data_generator.user, self.switch_with_ports, self.port2)
        relation_maker.add_location(data_generator.user, self.switch_with_ports, self.rack)

    def check_port_search(self, query_name):
        # search common pattern
        search = self.common
        query = '''
        {{
          {query_name}(filter:{{ query: "{search}" }}){{
            edges{{
              node{{
                id
                name
                description
              }}
            }}
          }}
        }}
        '''.format(query_name=query_name, search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        results = result.data[query_name]['edges']
        self.assertEqual(len(results), 2)

        # search one port
        search = self.port1.node_name
        query = '''
        {{
          {query_name}(filter:{{ query: "{search}" }}){{
            edges{{
              node{{
                id
                name
                description
              }}
            }}
          }}
        }}
        '''.format(query_name=query_name, search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        results = result.data[query_name]['edges']
        self.assertEqual(len(results), 1)

    def test_search_port(self):
        # check searching port by name only
        self.check_port_search('search_port')

    def search_port(self, query_name, search):
        query = '''
        {{
          {query_name}(filter:{{ query: "{search}" }}){{
            edges{{
              node{{
                id
                name
                description
              }}
            }}
          }}
        }}
        '''.format(query_name=query_name, search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        return result.data[query_name]['edges']

    def test_cable_search_port(self):
        # check searching port by name
        query_name='search_cable_port'
        self.check_port_search(query_name)

        # search them by equipment name
        search = self.switch_with_ports.node_name

        # check length
        results = self.search_port(query_name, search)
        self.assertEqual(len(results), 2)

        # search them by location name
        search = self.rack.node_name

        # check length
        results = self.search_port(query_name, search)
        self.assertEqual(len(results), 2)
