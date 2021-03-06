# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from apps.userprofile.models import UserProfile
from collections import OrderedDict
from django.contrib.auth.models import User
from niweb.schema import schema
from pprint import pformat

from . import BasicAdminTest

import apps.noclook.vakt.utils as sriutils
import graphene

class AdminMutationsTest(BasicAdminTest):
    def test_user_profile(self):
        if not hasattr(self, 'test_type'):
            return

        # edit user profile for the first time
        # check that the user profile object doesn't exist yet
        up_exists = UserProfile.objects.filter(user=self.another_user).exists()
        self.assertFalse(up_exists)

        # the data
        user_id = self.another_user.id
        display_name = "Another User"
        email = "anotheruser@sunet.se"
        is_staff = False
        is_active = False

        view_network = False
        view_services = False
        view_community = False

        # do the mutation
        query_t = """
        mutation{{
          edit_user_profile(input:{{
            user_id: {user_id}
            display_name: "{display_name}"
            email: "{email}"
            is_staff: {is_staff}
            is_active: {is_active}
            view_network: {view_network}
            view_services: {view_services}
            view_community: {view_community}
          }}){{
            success
            errors{{
              field
              messages
            }}
            userprofile{{
              id
              user{{
                id
                email
                is_staff
                is_active
              }}
              display_name
              email
              landing_page
              view_network
              view_services
              view_community
            }}
          }}
        }}
        """

        query = query_t.format(user_id=user_id, display_name=display_name,
                    email=email, is_staff=str(is_staff).lower(),
                    is_active=str(is_staff).lower(),
                    view_network=str(view_network).lower(),
                    view_services=str(view_services).lower(),
                    view_community=str(view_community).lower())

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check that the user profile now exists
        up_exists = UserProfile.objects.filter(user=self.another_user).exists()
        self.assertTrue(up_exists)

        # check data
        self.another_user = User.objects.get(id=self.another_user.id)
        uprofile = UserProfile.objects.get(user=self.another_user)

        self.assertEquals(uprofile.display_name, display_name)
        self.assertEquals(uprofile.email, email)
        self.assertEquals(self.another_user.email, email)
        self.assertEquals(self.another_user.is_staff, is_staff)
        self.assertEquals(self.another_user.is_active, is_active)
        self.assertEquals(uprofile.view_network, view_network)
        self.assertEquals(uprofile.view_services, view_services)
        self.assertEquals(uprofile.view_community, view_community)

        # check query result
        up_data = result.data['edit_user_profile']['userprofile']

        self.assertEquals(up_data["display_name"], display_name)
        self.assertEquals(up_data["email"], email)
        self.assertEquals(up_data["user"]["email"], email)
        self.assertEquals(up_data["user"]["is_staff"], is_staff)
        self.assertEquals(up_data["user"]["is_active"], is_active)
        self.assertEquals(up_data["landing_page"], "COMMUNITY")
        self.assertEquals(up_data["view_network"], view_network)
        self.assertEquals(up_data["view_services"], view_services)
        self.assertEquals(up_data["view_community"], view_community)

    def test_set_node_contexts(self):
        # only run mutations if we have set this value
        if not hasattr(self, 'test_type'):
            return

        query_t = """
        mutation{{
          set_nodes_context(input:{{
            contexts: [ {contexts_name} ]
            nodes:[ {nodes_ids} ]
          }}){{
            success
            errors{{
              field
              messages
            }}
            nodes{{
              __typename
              id
              name
            }}
          }}
        }}
        """

        # test fully successful mutation:
        contexts_name = '"{}"'.format(self.network_ctxt.name)
        nodes_ids = []

        for nh in [self.organization, self.host]:
            nodes_ids.append( graphene.relay.Node.to_global_id(
                str(nh.node_type), str(nh.handle_id)) )

        nodes_ids_str = ", ".join([ '"{}"'.format(x) for x in nodes_ids])

        query = query_t.format(
            contexts_name=contexts_name, nodes_ids=nodes_ids_str)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = OrderedDict([('set_nodes_context',
                      {'errors': [],
                       'nodes': [{'__typename': 'Organization',
                                  'id': nodes_ids[0],
                                  'name': 'organization1'},
                                 {'__typename': 'Host',
                                  'id': nodes_ids[1],
                                  'name': 'host1'}],
                       'success': True})])

        self.assert_correct(result, expected)

        # admin test: Has network admin rights and write rights network and
        # contacts so it must be able to do it
        # superadmin: Since the user has every right no problem it should do it
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # test partial successful mutation:
        nodes_ids = []

        for nh in [self.organization, self.host, self.address]:
            nodes_ids.append( graphene.relay.Node.to_global_id(
                str(nh.node_type), str(nh.handle_id)) )

        nodes_ids_str = ", ".join([ '"{}"'.format(x) for x in nodes_ids])

        query = query_t.format(
            contexts_name=contexts_name, nodes_ids=nodes_ids_str)

        if self.test_type == "admin":
            # admin test: It should be able to change only the contexts of
            # the organization and the host, but not the address
            expected = OrderedDict([('set_nodes_context',
              {'errors': [{'field': nodes_ids[2],
                           'messages': ["You don't have write rights for node "
                                        'id {}'.format(nodes_ids[2])]}],
               'nodes': [{'__typename': 'Organization',
                          'id': nodes_ids[0],
                          'name': 'organization1'},
                         {'__typename': 'Host',
                          'id': nodes_ids[1],
                          'name': 'host1'}],
               'success': True})])
        elif self.test_type == "superadmin":
            # superadmin: Since the user has every right no problem it should
            # do it
            expected = OrderedDict([('set_nodes_context',
              {'errors': [],
               'nodes': [{'__typename': 'Organization',
                          'id': nodes_ids[0],
                          'name': 'organization1'},
                         {'__typename': 'Host',
                          'id': nodes_ids[1],
                          'name': 'host1'},
                         {'__typename': 'Address',
                          'id': nodes_ids[2],
                          'name': 'address1'}],
               'success': True})])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        self.assert_correct(result, expected)


    def test_grant_user_permissions(self):
        # only run mutations if we have set this value
        if not hasattr(self, 'test_type'):
            return

        another_user_id = self.another_user.id
        other_user_id = self.other_user.id

        for user in [self.another_user, self.other_user]:
            # first query another_user permissions
            user_id = user.id

            query = """
            {{
              getUserById(ID: {user_id}){{
                id
                username
                user_permissions{{
                  community{{
                    read
                    list
                    write
                    admin
                  }}
                  network{{
                    read
                    list
                    write
                    admin
                  }}
                  contracts{{
                    read
                    list
                    write
                    admin
                  }}
                }}
              }}
            }}
            """.format(user_id=user_id)
            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            expected = {
                        'getUserById':
                            {
                                'id': str(user_id),
                                'user_permissions':
                                {
                                    'community': {
                                        'admin': False,
                                        'list': False,
                                        'read': False,
                                        'write': False
                                    },
                                    'contracts': {
                                        'admin': False,
                                        'list': False,
                                        'read': False,
                                        'write': False
                                    },
                                    'network': {
                                        'admin': False,
                                        'list': False,
                                        'read': False,
                                        'write': False
                                    }
                                },
                                'username': user.username
                            }
                        }


            # they must be blank as we didn't set anything yet
            self.assert_correct(result, expected)

        # add read, list and write permissions over our module
        query_t = """
        mutation{{
          grant_users_permissions(input:{{
            users_ids:[ {users_ids} ]
            context: "{context_name}"
            read: {read}
            list: {list}
            write: {write}
            {admin}
          }}){{
            results{{
              success
              errors{{
                field
                messages
              }}
    		  user{{
                id
                username
                user_permissions{{
                  network{{
                    read
                    list
                    write
                    admin
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        # check the user permissions query
        net_ctxt = sriutils.get_network_context()
        context_name = net_ctxt.name
        read = str(True).lower()
        list = str(True).lower()
        write = str(True).lower()
        users_ids = ", ".join(['"{}"'.format(x) \
            for x in [other_user_id, another_user_id]])

        query = query_t.format(
            users_ids=users_ids,
            context_name=context_name,
            read=read, list=list, write=write, admin=""
        )

        # test vakt functions before
        for user in [self.other_user, self.another_user]:
            can_read = sriutils.authorize_read_module(user, net_ctxt)
            can_list = sriutils.authorize_list_module(user, net_ctxt)
            can_write = sriutils.authorize_create_resource(user, net_ctxt)

            self.assertFalse(can_read)
            self.assertFalse(can_list)
            self.assertFalse(can_write)

        # run mutation and check response
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = OrderedDict([('grant_users_permissions',
              {'results': [{'errors': None,
                            'success': True,
                            'user': {'id': str(other_user_id),
                                     'user_permissions':
                                     {'network': {'admin': False,
                                                  'list': True,
                                                  'read': True,
                                                  'write': True}},
                                     'username': self.other_user.username}},
                           {'errors': None,
                            'success': True,
                            'user': {'id': str(another_user_id),
                                     'user_permissions':
                                     {'network': {'admin': False,
                                                  'list': True,
                                                  'read': True,
                                                  'write': True}},
                                     'username': self.another_user.username}}
        ]})])

        self.assert_correct(result, expected)

        # after
        for user in [self.other_user, self.another_user]:
            can_read = sriutils.authorize_read_module(user, net_ctxt)
            can_list = sriutils.authorize_list_module(user, net_ctxt)
            can_write = sriutils.authorize_create_resource(user, net_ctxt)

            self.assertTrue(can_read)
            self.assertTrue(can_list)
            self.assertTrue(can_write)

        # revoke write permission
        write = str(False).lower()

        query = query_t.format(
            users_ids=users_ids,
            context_name=context_name,
            read=read, list=list, write=write, admin=""
        )
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = OrderedDict([('grant_users_permissions',
              {'results': [{'errors': None,
                            'success': True,
                            'user': {'id': str(other_user_id),
                                     'user_permissions':
                                     {'network': {'admin': False,
                                                  'list': True,
                                                  'read': True,
                                                  'write': False}},
                                     'username': self.other_user.username}},
                           {'errors': None,
                            'success': True,
                            'user': {'id': str(another_user_id),
                                     'user_permissions':
                                     {'network': {'admin': False,
                                                  'list': True,
                                                  'read': True,
                                                  'write': False}},
                                     'username': self.another_user.username}}
        ]})])

        # check the user permissions query
        self.assert_correct(result, expected)

        # test vakt functions
        for user in [self.other_user, self.another_user]:
            can_write = sriutils.authorize_create_resource(user, net_ctxt)
            self.assertFalse(can_write)

        # grand admin rights
        admin = "admin: true"
        query = query_t.format(
            users_ids=users_ids,
            context_name=context_name,
            read=read, list=list, write=write, admin=admin
        )

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        expected = None

        if self.test_type == "admin":
            # if it's not check the error
            expected = OrderedDict([('grant_users_permissions',
              {'results': [{'errors': [{'field': '_',
                                        'messages': ['Only superadmins can '
                                                     'grant admin rights']}],
                            'success': False,
                            'user': {'id': str(other_user_id),
                                     'user_permissions': {'network':
                                        {'admin': False,
                                          'list': True,
                                          'read': True,
                                          'write': False}},
                                     'username': self.other_user.username}},
                           {'errors': [{'field': '_',
                                        'messages': ['Only superadmins can '
                                                     'grant admin rights']}],
                            'success': False,
                            'user': {'id': str(another_user_id),
                                     'user_permissions': {'network':
                                        {'admin': False,
                                          'list': True,
                                          'read': True,
                                          'write': False}},
                                     'username': self.another_user.username}}
                        ]})])
        elif self.test_type == "superadmin":
            # if it's superadmin test it should be possible
            expected = OrderedDict([('grant_users_permissions',
              {'results': [{'errors': None,
                            'success': True,
                            'user': {'id': str(other_user_id),
                                     'user_permissions': {'network': {
                                        'admin': True,
                                        'list': True,
                                        'read': True,
                                        'write': False}},
                                     'username': self.other_user.username}},
                           {'errors': None,
                            'success': True,
                            'user': {'id': str(another_user_id),
                                     'user_permissions': {'network': {
                                         'admin': True,
                                         'list': True,
                                         'read': True,
                                         'write': False}},
                                     'username':  self.another_user.username}}
            ]})])

        self.assert_correct(result, expected)



class AdminAdminMutationsTest(AdminMutationsTest):
    def setUp(self, group_dict=None):
        group_dict = {
            'community': {
                'admin': False,
                'read': True,
                'list': True,
                'write': True,
            },
            'network': {
                'admin': True,
                'read': True,
                'list': True,
                'write': True,
            },
            'contracts': {
                'admin': False,
                'read': True,
                'list': True,
                'write': False,
            },
        }

        self.test_type = "admin"

        super().setUp(group_dict=group_dict)


class SuperAdminAdminMutationsTest(AdminMutationsTest):
    def setUp(self, group_dict=None):
        group_dict = {
            'community': {
                'admin': True,
                'read': True,
                'list': True,
                'write': True,
            },
            'network': {
                'admin': True,
                'read': True,
                'list': True,
                'write': True,
            },
            'contracts': {
                'admin': True,
                'read': True,
                'list': True,
                'write': True,
            },
        }

        self.test_type = "superadmin"

        super().setUp(group_dict=group_dict)
