# -*- coding: utf-8 -*-
from apps.noclook.tests.neo4j_base import NeoTestCase
from django.contrib.auth.models import User, Group
from apps.noclook.models import GroupContextAuthzAction, NodeHandleContext
import apps.noclook.vakt.utils as sriutils

class SRIVaktUtilsTest(NeoTestCase):
    def setUp(self):
        super(SRIVaktUtilsTest, self).setUp()

        # get contexts
        self.network_ctxt   = sriutils.get_network_context()
        self.community_ctxt = sriutils.get_community_context()
        self.contracts_ctxt = sriutils.get_contracts_context()

        # get auth actions
        self.get_read_authaction  = sriutils.get_read_authaction()
        self.get_write_authaction = sriutils.get_write_authaction()
        self.get_list_authaction = sriutils.get_list_authaction()
        self.get_admin_authaction = sriutils.get_admin_authaction()

        # create some nodes
        self.organization1 = self.create_node('organization1', 'organization', meta='Logical')
        self.organization2 = self.create_node('organization2', 'organization', meta='Logical')
        self.contact1 = self.create_node('contact1', 'contact', meta='Relation')
        self.contact2 = self.create_node('contact2', 'contact', meta='Relation')

        # add context to resources
        # organization1 belongs to the three modules
        NodeHandleContext(
            nodehandle=self.organization1,
            context = self.network_ctxt
        ).save()

        NodeHandleContext(
            nodehandle=self.organization1,
            context = self.community_ctxt
        ).save()

        NodeHandleContext(
            nodehandle=self.organization1,
            context = self.contracts_ctxt
        ).save()

        # organization2 belongs only to the network module
        NodeHandleContext(
            nodehandle=self.organization2,
            context = self.network_ctxt
        ).save()

        # the first contact belongs to the community module
        NodeHandleContext(
            nodehandle=self.contact1,
            context = self.community_ctxt
        ).save()

        # the second contact belongs to the contracts module
        NodeHandleContext(
            nodehandle=self.contact2,
            context = self.contracts_ctxt
        ).save()

        ### create users and groups and add permissions
        self.user1 = User(
            first_name="Kate", last_name="Svensson", email="ksvensson@sunet.se",
            is_staff=False, is_active=True, username="ksvensson",
        )
        self.user1.save()

        self.user2 = User(
            first_name="Jane", last_name="Atkins", email="jatkins@sunet.se",
            is_staff=False, is_active=True, username="jatkins",
        )
        self.user2.save()

        self.user3 = User(
            first_name="Sven", last_name="Svensson", email="ssvensson@sunet.se",
            is_staff=False, is_active=True, username="ssvensson",
        )
        self.user3.save()

        self.user4 = User(
            first_name="Pedro", last_name="Zutano", email="pzutano@sunet.se",
            is_staff=False, is_active=True, username="pzutano",
        )
        self.user4.save()

        # create groups
        self.group1 = Group( name="Group can read all contexts" )
        self.group2 = Group( name="Group can write community and contracts" )
        self.group3 = Group( name="Group can admin community module" )
        self.group4 = Group( name="Group can list community and contracts" )
        self.group5 = Group( name="Group can read community contracts" )

        self.group1.save()
        self.group2.save()
        self.group3.save()
        self.group4.save()
        self.group5.save()

        # add contexts and actions
        # first group
        contexts = [self.network_ctxt, self.community_ctxt, self.contracts_ctxt]

        for context in contexts:
            GroupContextAuthzAction(
                group = self.group1,
                authzprofile = self.get_read_authaction,
                context = context
            ).save()

        # second and fifth group
        contexts = [self.community_ctxt, self.contracts_ctxt]

        for context in contexts:
            GroupContextAuthzAction(
                group = self.group2,
                authzprofile = self.get_write_authaction,
                context = context
            ).save()

        for context in contexts:
            GroupContextAuthzAction(
                group = self.group5,
                authzprofile = self.get_read_authaction,
                context = context
            ).save()

        # third group
        GroupContextAuthzAction(
            group = self.group3,
            authzprofile = self.get_admin_authaction,
            context = self.community_ctxt
        ).save()

        for context in contexts:
            GroupContextAuthzAction(
                group = self.group4,
                authzprofile = self.get_list_authaction,
                context = context
            ).save()

        # add users to groups
        self.group1.user_set.add(self.user1)
        self.group1.user_set.add(self.user2)
        self.group1.user_set.add(self.user3)

        self.group2.user_set.add(self.user1)
        self.group2.user_set.add(self.user2)

        self.group3.user_set.add(self.user1)

        self.group4.user_set.add(self.user1)
        self.group4.user_set.add(self.user2)
        self.group4.user_set.add(self.user3)

        self.group5.user_set.add(self.user4)

    def test_ids_user_canread(self):
        readable_ids = sriutils.get_ids_user_canread(self.user4)
        expected_ids = [
            self.organization1.handle_id,
            self.contact1.handle_id,
            self.contact2.handle_id,
        ]

        self.assertEqual(readable_ids, expected_ids)

    def test_read_resource(self):
        # check the read permissions over the contexts for the users
        result_read_ucm1 = sriutils.authorize_read_module(self.user1, self.community_ctxt)
        result_read_ucm2 = sriutils.authorize_read_module(self.user1, self.community_ctxt)
        result_read_ucm3 = sriutils.authorize_read_module(self.user1, self.community_ctxt)

        result_read_unt1 = sriutils.authorize_read_module(self.user2, self.network_ctxt)
        result_read_unt2 = sriutils.authorize_read_module(self.user2, self.network_ctxt)
        result_read_unt3 = sriutils.authorize_read_module(self.user2, self.network_ctxt)

        result_read_uct1 = sriutils.authorize_read_module(self.user3, self.contracts_ctxt)
        result_read_uct2 = sriutils.authorize_read_module(self.user3, self.contracts_ctxt)
        result_read_uct3 = sriutils.authorize_read_module(self.user3, self.contracts_ctxt)

        self.assertTrue(result_read_ucm1)
        self.assertTrue(result_read_ucm2)
        self.assertTrue(result_read_ucm3)

        self.assertTrue(result_read_unt1)
        self.assertTrue(result_read_unt2)
        self.assertTrue(result_read_unt3)

        self.assertTrue(result_read_uct1)
        self.assertTrue(result_read_uct2)
        self.assertTrue(result_read_uct3)

        # check if the three users can read the organization1
        result_auth_u1 = sriutils.authorice_read_resource(self.user1, self.organization1.handle_id)
        result_auth_u2 = sriutils.authorice_read_resource(self.user2, self.organization1.handle_id)
        result_auth_u3 = sriutils.authorice_read_resource(self.user3, self.organization1.handle_id)

        self.assertTrue(result_auth_u1)
        self.assertTrue(result_auth_u2)
        self.assertTrue(result_auth_u3)

        # check if the three users can read the organization2
        result_auth_u1 = sriutils.authorice_read_resource(self.user1, self.organization2.handle_id)
        result_auth_u2 = sriutils.authorice_read_resource(self.user2, self.organization2.handle_id)
        result_auth_u3 = sriutils.authorice_read_resource(self.user3, self.organization2.handle_id)

        self.assertTrue(result_auth_u1)
        self.assertTrue(result_auth_u2)
        self.assertTrue(result_auth_u3)

        # check if the three users can read the contact1
        result_auth_u1 = sriutils.authorice_read_resource(self.user1, self.contact1.handle_id)
        result_auth_u2 = sriutils.authorice_read_resource(self.user2, self.contact1.handle_id)
        result_auth_u3 = sriutils.authorice_read_resource(self.user3, self.contact1.handle_id)

        self.assertTrue(result_auth_u1)
        self.assertTrue(result_auth_u2)
        self.assertTrue(result_auth_u3)

        # check if the three users can read the contact2
        result_auth_u1 = sriutils.authorice_read_resource(self.user1, self.contact2.handle_id)
        result_auth_u2 = sriutils.authorice_read_resource(self.user2, self.contact2.handle_id)
        result_auth_u3 = sriutils.authorice_read_resource(self.user3, self.contact2.handle_id)

        self.assertTrue(result_auth_u1)
        self.assertTrue(result_auth_u2)
        self.assertTrue(result_auth_u3)


    def test_write_resource(self):
        # check that only user1 and user2 (from the group2) can write for the resource
        result_auth_u1 = sriutils.authorice_write_resource(self.user1, self.organization1.handle_id)
        result_auth_u2 = sriutils.authorice_write_resource(self.user2, self.organization1.handle_id)
        result_auth_u3 = sriutils.authorice_write_resource(self.user3, self.organization1.handle_id)

        self.assertTrue(result_auth_u1)
        self.assertTrue(result_auth_u2)
        self.assertFalse(result_auth_u3)

        # check that nobody can write the resource since it's in the network module
        result_auth_u1 = sriutils.authorice_write_resource(self.user1, self.organization2.handle_id)
        result_auth_u2 = sriutils.authorice_write_resource(self.user2, self.organization2.handle_id)
        result_auth_u3 = sriutils.authorice_write_resource(self.user3, self.organization2.handle_id)

        self.assertFalse(result_auth_u1)
        self.assertFalse(result_auth_u2)
        self.assertFalse(result_auth_u3)

        # check that only user1 and user2 (from the group2) can write for the resource
        result_auth_u1 = sriutils.authorice_write_resource(self.user1, self.contact1.handle_id)
        result_auth_u2 = sriutils.authorice_write_resource(self.user2, self.contact1.handle_id)
        result_auth_u3 = sriutils.authorice_write_resource(self.user3, self.contact1.handle_id)

        self.assertTrue(result_auth_u1)
        self.assertTrue(result_auth_u2)
        self.assertFalse(result_auth_u3)

        # check that only user1 and user2 (from the group2) can write for the resource
        result_auth_u1 = sriutils.authorice_write_resource(self.user1, self.contact2.handle_id)
        result_auth_u2 = sriutils.authorice_write_resource(self.user2, self.contact2.handle_id)
        result_auth_u3 = sriutils.authorice_write_resource(self.user3, self.contact2.handle_id)

        self.assertTrue(result_auth_u1)
        self.assertTrue(result_auth_u2)
        self.assertFalse(result_auth_u3)


    def test_create_resource(self):
        # check that only user1 and user2 (from the group2) can create resources in the community module
        result_auth_u1 = sriutils.authorize_create_resource(self.user1, self.community_ctxt)
        result_auth_u2 = sriutils.authorize_create_resource(self.user2, self.community_ctxt)
        result_auth_u3 = sriutils.authorize_create_resource(self.user3, self.community_ctxt)

        self.assertTrue(result_auth_u1)
        self.assertTrue(result_auth_u2)
        self.assertFalse(result_auth_u3)

        # check that only user1 and user2 (from the group2) can create resources in the contracts modules
        result_auth_u1 = sriutils.authorize_create_resource(self.user1, self.contracts_ctxt)
        result_auth_u2 = sriutils.authorize_create_resource(self.user2, self.contracts_ctxt)
        result_auth_u3 = sriutils.authorize_create_resource(self.user3, self.contracts_ctxt)

        self.assertTrue(result_auth_u1)
        self.assertTrue(result_auth_u2)
        self.assertFalse(result_auth_u3)


        # check that none of them can create resources in the network module
        result_auth_u1 = sriutils.authorize_create_resource(self.user1, self.network_ctxt)
        result_auth_u2 = sriutils.authorize_create_resource(self.user2, self.network_ctxt)
        result_auth_u3 = sriutils.authorize_create_resource(self.user3, self.network_ctxt)

        self.assertFalse(result_auth_u1)
        self.assertFalse(result_auth_u2)
        self.assertFalse(result_auth_u3)


    def test_admin(self):
        # check that only user1 have admin rights over the community module
        result_auth_u1 = sriutils.authorize_admin_module(self.user1, self.community_ctxt)
        result_auth_u2 = sriutils.authorize_admin_module(self.user2, self.community_ctxt)
        result_auth_u3 = sriutils.authorize_admin_module(self.user3, self.community_ctxt)

        self.assertTrue(result_auth_u1)
        self.assertFalse(result_auth_u2)
        self.assertFalse(result_auth_u3)

        # check that nobody has admin rights over any other module
        result_auth_u1 = sriutils.authorize_admin_module(self.user1, self.network_ctxt)
        result_auth_u2 = sriutils.authorize_admin_module(self.user2, self.network_ctxt)
        result_auth_u3 = sriutils.authorize_admin_module(self.user3, self.network_ctxt)

        self.assertFalse(result_auth_u1)
        self.assertFalse(result_auth_u2)
        self.assertFalse(result_auth_u3)

        result_auth_u1 = sriutils.authorize_admin_module(self.user1, self.contracts_ctxt)
        result_auth_u2 = sriutils.authorize_admin_module(self.user2, self.contracts_ctxt)
        result_auth_u3 = sriutils.authorize_admin_module(self.user3, self.contracts_ctxt)

        self.assertFalse(result_auth_u1)
        self.assertFalse(result_auth_u2)
        self.assertFalse(result_auth_u3)


    def test_list(self):
        # check that the user1 can't list network context elements
        result_auth_u1 = sriutils.authorize_list_module(self.user1, self.network_ctxt)
        self.assertFalse(result_auth_u1)

        # check that the user1 can list community context elements
        result_auth_u2 = sriutils.authorize_list_module(self.user2, self.community_ctxt)
        self.assertTrue(result_auth_u2)

        # check that the user1 can list contracts context elements
        result_auth_u3 = sriutils.authorize_list_module(self.user3, self.contracts_ctxt)
        self.assertTrue(result_auth_u3)
