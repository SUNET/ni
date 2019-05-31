# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from . import Neo4jGraphQLTest
from niweb.schema import schema

class QueryTest(Neo4jGraphQLTest):
    def test_get_contacts(self):
        # test contacts
        query = '''
        query getLastTenContacts {
          contacts(first: 2, orderBy: handle_id_DESC) {
            edges {
              node {
                handle_id
                name
                first_name
                last_name
                is_roles {
                  name
                }
                member_of_groups {
                  name
                }
              }
            }
          }
        }
        '''

        expected =  OrderedDict([('contacts',
                      OrderedDict([('edges',
                        [
                         OrderedDict([('node',
                           OrderedDict([('handle_id', '29'),
                                ('name', 'John Smith'),
                                ('first_name', 'John'),
                                ('last_name', 'Smith'),
                                ('is_roles',
                                 [OrderedDict([('name',
                                    'role2')])]),
                                ('member_of_groups',
                                 [OrderedDict([('name',
                                    'group2')])])]))]),
                        OrderedDict([('node',
                           OrderedDict([('handle_id', '28'),
                                ('name', 'Jane Doe'),
                                ('first_name', 'Jane'),
                                ('last_name', 'Doe'),
                                ('is_roles',
                                 [OrderedDict([('name',
                                    'role1')])]),
                                ('member_of_groups',
                                 [OrderedDict([('name',
                                    'group1')])])]))]),
                        ])]))])


        result = schema.execute(query, context=self.context)

        assert not result.errors, result.errors
        assert result.data == expected

        # getNodeById
        query = '''
        query {
          getNodeById(handle_id: 28){
            handle_id
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors

        # filter tests
        query = '''
        {
          groups(first: 10, filter:{
            AND:[{
              name: "group1", name_not: "group2",
              name_not_in: ["group2"]
            }]
          }, orderBy: handle_id_ASC){
            edges{
              node{
                handle_id
                name
              }
            }
          }
        }
        '''
        expected = OrderedDict([('groups',
                        OrderedDict([('edges',
                            [OrderedDict([('node',
                                   OrderedDict([('handle_id', '32'),
                                        ('name',
                                         'group1')]
                                    ))])]
                            )]))
                    ])


        result = schema.execute(query, context=self.context)

        assert not result.errors, result.errors
        assert result.data == expected

        query = '''
        {
          groups(first: 10, filter:{
            OR:[{
              name: "group1",
              name_in: ["group1", "group2"]
            },{
              name: "group2",
            }]
          }, orderBy: handle_id_ASC){
            edges{
              node{
                handle_id
                name
              }
            }
          }
        }
        '''
        expected = OrderedDict([('groups',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('handle_id', '32'),
                            ('name', 'group1')]))]),
                         OrderedDict([('node',
                           OrderedDict([('handle_id', '33'),
                                ('name',
                                 'group2')]))])])]))])

        result = schema.execute(query, context=self.context)

        assert not result.errors, result.errors
        assert result.data == expected

    def test_getnodebyhandle_id(self):
        query = '''
        query {
          getNodeById(handle_id: 1){
            handle_id
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        #assert not result.errors, result.errors

    def test_dropdown(self):
        query = '''
        query{
          getChoicesForDropdown(name:"contact_type"){
            id
            dropdown{
              id
              name
              choice_set{
                id
                dropdown {
                  id
                }
                name
                value
              }
            }
            name
            value
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
