# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
import apps.noclook.vakt.utils as sriutils

from apps.noclook import activitylog, helpers
from apps.noclook.forms import *
from apps.noclook.models import Role as RoleModel, \
    DEFAULT_ROLES, DEFAULT_ROLES, DEFAULT_ROLE_KEY
from apps.noclook.schema.types import *
from django.test import RequestFactory
from django_comments.forms import CommentForm
from django_comments.models import Comment
from graphene import Field
from graphene_django.forms.mutation import DjangoModelFormMutation, BaseDjangoFormMutation
from django.core.exceptions import ObjectDoesNotExist
from binascii import Error as BinasciiError

logger = logging.getLogger(__name__)

class NIGroupMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewGroupForm
        update_form    = EditGroupForm
        request_path   = '/'
        graphql_type   = Group

    class Meta:
        abstract = False


class NIProcedureMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewProcedureForm
        update_form    = EditProcedureForm
        request_path   = '/'
        graphql_type   = Procedure

    class Meta:
        abstract = False


def empty_processor(request, form, nodehandler, relation_name):
    pass


def process_works_for(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and 'role' in form.cleaned_data and \
        form.cleaned_data[relation_name] and form.cleaned_data['role']:

        organization_nh = NodeHandle.objects.get(pk=form.cleaned_data[relation_name])
        role_handle_id = form.cleaned_data['role']
        role = RoleModel.objects.get(handle_id=role_handle_id)
        helpers.set_works_for(request.user, nodehandler, organization_nh.handle_id, role.name)


def process_member_of(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        group_nh = NodeHandle.objects.get(pk=form.cleaned_data[relation_name])
        helpers.set_member_of(request.user, nodehandler, group_nh.handle_id)


def process_has_phone(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        contact_id = form.cleaned_data[relation_name]
        helpers.add_phone_contact(request.user, nodehandler, contact_id)


def process_has_email(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        contact_id = form.cleaned_data[relation_name]
        helpers.add_email_contact(request.user, nodehandler, contact_id)


def process_has_address(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        organization_id = form.cleaned_data[relation_name]
        helpers.add_address_organization(request.user, nodehandler, organization_id)


class NIPhoneMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form            = PhoneForm
        request_path    = '/'
        graphql_type    = Phone
        relations_processors = {
            'contact': process_has_phone,
        }
        property_update = ['name', 'type']

    class Meta:
        abstract = False


class NIEmailMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form            = EmailForm
        request_path    = '/'
        graphql_type    = Email

        relations_processors = {
            'contact': process_has_email,
        }
        property_update = ['name', 'type']

    class Meta:
        abstract = False


class NIAddressMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form            = AddressForm
        request_path    = '/'
        graphql_type    = Address

        relations_processors = {
            'organization': process_has_address,
        }
        property_update = ['name', 'phone', 'street', 'postal_code', 'postal_area']

    class Meta:
        abstract = False


def delete_outgoing_nodes(nodehandler, relation_name, user):
    node = nodehandler.get_node()
    relations = node.get_outgoing_relations()

    for relname, link_nodes in relations.items():
        if relname == relation_name:
            for link_node in link_nodes:
                link_node = link_node['node']
                helpers.delete_node(user, link_node.handle_id)


class NIContactMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form = MailPhoneContactForm
        request_path   = '/'
        graphql_type   = Contact
        relations_processors = {
            'relationship_works_for': process_works_for,
            'relationship_member_of': process_member_of,
        }

        subentity_processors = {
            'email': {
                'form': EmailForm,
                'type_slug': 'email',
                'meta_type': 'Logical',
                'fields': {
                    'id': 'email_id',
                    'name': 'email',
                    'type': 'email_type',
                },
                'link_method': 'add_email',
            },
            'phone': {
                'form': PhoneForm,
                'type_slug': 'phone',
                'meta_type': 'Logical',
                'fields': {
                    'id': 'phone_id',
                    'name': 'phone',
                    'type': 'phone_type',
                },
                'link_method': 'add_phone',
            },
        }

        delete_nodes = {
            'Has_email': delete_outgoing_nodes,
            'Has_phone': delete_outgoing_nodes,
        }

        property_update = [
            'first_name', 'last_name', 'contact_type', 'name', 'title',
            'pgp_fingerprint', 'notes'
        ]

        relay_extra_ids = ['role', ]

    class Meta:
        abstract = False


class CreateOrganization(CreateNIMutation):
    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()
        context_method = getattr(nimetatype, 'context_method')
        has_error      = False

        context = context_method()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(request.user, context)

        if not authorized:
            raise GraphQLAuthException()

        # Get needed data from node
        if request.POST:
            # replace relay ids for handle_id in contacts if present
            post_data = request.POST.copy()

            for field, roledict in DEFAULT_ROLES.items():
                if field in post_data:
                    handle_id = post_data.get(field)
                    handle_id = relay.Node.from_global_id(handle_id)[1]
                    post_data.pop(field)
                    post_data.update({field: handle_id})

            relay_extra_ids = ('relationship_parent_of', 'relationship_uses_a')
            for field in relay_extra_ids:
                handle_id = post_data.get(field)
                if handle_id:
                    try:
                        handle_id = relay.Node.from_global_id(handle_id)[1]
                        post_data.pop(field)
                        post_data.update({field: handle_id})
                    except BinasciiError:
                        pass # the id is already in handle_id format

            form = form_class(post_data)
            form.strict_validation = True

            if form.is_valid():
                try:
                    nh = helpers.form_to_generic_node_handle(request, form,
                            node_type, node_meta_type)
                except UniqueNodeError:
                    has_error = True
                    return has_error, [ErrorType(field="_", messages=["A {} with that name already exists.".format(node_type)])]

                # Generic node update
                # use property keys to avoid inserting contacts as a string property of the node
                property_keys = [
                    'name', 'description', 'organization_id', 'type', 'incident_management_info',
                    'affiliation_customer', 'affiliation_end_customer', 'affiliation_provider',
                    'affiliation_partner', 'affiliation_host_user', 'affiliation_site_owner',
                    'website', 'organization_number'
                ]
                helpers.form_update_node(request.user, nh.handle_id, form, property_keys)
                nh_reload, organization = helpers.get_nh_node(nh.handle_id)

                # add default context
                NodeHandleContext(nodehandle=nh, context=context).save()

                # specific role setting
                for field, roledict in DEFAULT_ROLES.items():
                    if field in form.cleaned_data:
                        contact_id = form.cleaned_data[field]

                        role = RoleModel.objects.get(slug=field)
                        set_contact = helpers.get_contact_for_orgrole(organization.handle_id, role)

                        if contact_id:
                            if set_contact:
                                if set_contact.handle_id != contact_id:
                                    helpers.unlink_contact_with_role_from_org(request.user, organization, role)
                                    helpers.link_contact_role_for_organization(request.user, organization, contact_id, role)
                            else:
                                helpers.link_contact_role_for_organization(request.user, organization, contact_id, role)
                        elif set_contact:
                            helpers.unlink_contact_and_role_from_org(request.user, organization, set_contact.handle_id, role)

                # Set child organizations
                if form.cleaned_data['relationship_parent_of']:
                    organization_nh = NodeHandle.objects.get(handle_id=form.cleaned_data['relationship_parent_of'])
                    helpers.set_parent_of(request.user, organization, organization_nh.handle_id)
                if form.cleaned_data['relationship_uses_a']:
                    procedure_nh = NodeHandle.objects.get(handle_id=form.cleaned_data['relationship_uses_a'])
                    helpers.set_uses_a(request.user, organization, procedure_nh.handle_id)

                return has_error, { graphql_type.__name__.lower(): nh }
            else:
                # get the errors and return them
                has_error = True
                errordict = cls.format_error_array(form.errors)
                return has_error, errordict
        else:
            # get the errors and return them
            has_error = True
            errordict = cls.format_error_array(form.errors)
            return has_error, errordict

    class NIMetaClass:
        django_form = EditOrganizationForm
        request_path   = '/'
        graphql_type   = Organization
        is_create = True

        relations_processors = {
            'relationship_parent_of': empty_processor,
            'relationship_uses_a': empty_processor,
        }



class UpdateOrganization(UpdateNIMutation):
    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()
        id      = request.POST.get('id')
        has_error      = False

        # check authorization
        handle_id = relay.Node.from_global_id(id)[1]
        authorized = sriutils.authorice_write_resource(request.user, handle_id)

        if not authorized:
            raise GraphQLAuthException()

        # Get needed data from node
        nh, organization = helpers.get_nh_node(handle_id)
        relations = organization.get_relations()
        out_relations = organization.get_outgoing_relations()

        if request.POST:
            # set handle_id into POST data and remove relay id
            post_data = request.POST.copy()
            post_data.pop('id')
            post_data.update({'handle_id': handle_id})

            # replace relay ids for handle_id in contacts if present
            for field, roledict in DEFAULT_ROLES.items():
                if field in post_data:
                    handle_id = post_data.get(field)
                    handle_id = relay.Node.from_global_id(handle_id)[1]
                    post_data.pop(field)
                    post_data.update({field: handle_id})

            relay_extra_ids = ('relationship_parent_of', 'relationship_uses_a')
            for field in relay_extra_ids:
                handle_id = post_data.get(field)
                if handle_id:
                    handle_id = relay.Node.from_global_id(handle_id)[1]
                    post_data.pop(field)
                    post_data.update({field: handle_id})

            form = form_class(post_data)
            form.strict_validation = True

            if form.is_valid():
                # Generic node update
                # use property keys to avoid inserting contacts as a string property of the node
                property_keys = [
                    'name', 'description', 'organization_id', 'type', 'incident_management_info',
                    'affiliation_customer', 'affiliation_end_customer', 'affiliation_provider',
                    'affiliation_partner', 'affiliation_host_user', 'affiliation_site_owner',
                    'website', 'organization_number'
                ]
                helpers.form_update_node(request.user, organization.handle_id, form, property_keys)

                # specific role setting
                for field, roledict in DEFAULT_ROLES.items():
                    if field in form.cleaned_data:
                        contact_id = form.cleaned_data[field]
                        role = RoleModel.objects.get(slug=field)
                        set_contact = helpers.get_contact_for_orgrole(organization.handle_id, role)

                        if contact_id:
                            if set_contact:
                                if set_contact.handle_id != contact_id:
                                    helpers.unlink_contact_with_role_from_org(request.user, organization, role)
                                    helpers.link_contact_role_for_organization(request.user, organization, contact_id, role)
                            else:
                                helpers.link_contact_role_for_organization(request.user, organization, contact_id, role)
                        elif set_contact:
                            helpers.unlink_contact_and_role_from_org(request.user, organization, set_contact.handle_id, role)

                # Set child organizations
                if form.cleaned_data['relationship_parent_of']:
                    organization_nh = NodeHandle.objects.get(handle_id=form.cleaned_data['relationship_parent_of'])
                    helpers.set_parent_of(request.user, organization, organization_nh.handle_id)
                if form.cleaned_data['relationship_uses_a']:
                    procedure_nh = NodeHandle.objects.get(handle_id=form.cleaned_data['relationship_uses_a'])
                    helpers.set_uses_a(request.user, organization, procedure_nh.handle_id)

                return has_error, { graphql_type.__name__.lower(): nh }
            else:
                # get the errors and return them
                has_error = True
                errordict = cls.format_error_array(form.errors)
                return has_error, errordict
        else:
            # get the errors and return them
            has_error = True
            errordict = cls.format_error_array(form.errors)
            return has_error, errordict

    class NIMetaClass:
        django_form = EditOrganizationForm
        request_path   = '/'
        graphql_type   = Organization


class NIOrganizationMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewOrganizationForm
        update_form    = EditOrganizationForm
        request_path   = '/'
        graphql_type   = Organization
        # create_include or create_exclude

        delete_nodes = {
            'Has_address': delete_outgoing_nodes,
        }

        manual_create = CreateOrganization
        manual_update = UpdateOrganization

    class Meta:
        abstract = False

## add the create and update manual mutations for Organization
## before its composite mutation is built, and after its factory is built
Organization.set_create_mutation(CreateOrganization)
Organization.set_update_mutation(UpdateOrganization)


class CreateRole(DjangoModelFormMutation):
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        context = sriutils.get_community_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(info.context.user, context)

        if not authorized:
            raise GraphQLAuthException()

        form = cls.get_form(root, info, **input)

        if form.is_valid():
            return cls.perform_mutate(form, info)
        else:
            errors = [
                ErrorType(field=key, messages=value)
                for key, value in form.errors.items()
            ]

            return cls(errors=errors)

    class Meta:
        form_class = NewRoleForm


class UpdateRole(DjangoModelFormMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    def get_form_kwargs(cls, root, info, **input):
        context = sriutils.get_community_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(info.context.user, context)

        if not authorized:
            raise GraphQLAuthException()

        kwargs = {"data": input}

        id = input.pop("id", None)
        handle_id = relay.Node.from_global_id(id)[1]
        if handle_id:
            instance = cls._meta.model._default_manager.get(pk=handle_id)
            kwargs["instance"] = instance

        return kwargs

    class Meta:
        form_class = EditRoleForm


class DeleteRole(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean(required=True)
    id = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        id = input.get("id", None)
        handle_id = relay.Node.from_global_id(id)[1]
        success = False

        context = sriutils.get_community_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(info.context.user, context)

        if not authorized:
            raise GraphQLAuthException()

        try:
            role = RoleModel.objects.get(handle_id=handle_id)
            role.delete()
            success = True
        except ObjectDoesNotExist:
            success = False

        return DeleteRole(success=success, id=id)


## Composite mutations
class CompositeGroupMutation(CompositeMutation):
    class Input:
        pass

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh):
        helpers.set_member_of(user, slave_nh.get_node(), master_nh.handle_id)

    class NIMetaClass:
        graphql_type = Group
        graphql_subtype = Contact
        main_mutation_f = NIGroupMutationFactory
        secondary_mutation_f = NIContactMutationFactory
        context = sriutils.get_community_context()


class CompositeOrganizationMutation(CompositeMutation):
    class Input:
        create_input = graphene.Field(CreateOrganization.Input)
        update_input = graphene.Field(UpdateOrganization.Input)

        create_subinputs = graphene.List(NIContactMutationFactory.get_create_mutation().Input)
        update_subinputs = graphene.List(NIContactMutationFactory.get_update_mutation().Input)
        delete_subinputs = graphene.List(NIContactMutationFactory.get_delete_mutation().Input)
        unlink_subinputs = graphene.List(DeleteRelationship.Input)

        create_address = graphene.List(NIAddressMutationFactory.get_create_mutation().Input)
        update_address = graphene.List(NIAddressMutationFactory.get_update_mutation().Input)
        delete_address = graphene.List(NIAddressMutationFactory.get_delete_mutation().Input)

    created = graphene.Field(CreateOrganization)
    updated = graphene.Field(UpdateOrganization)

    subcreated = graphene.List(NIContactMutationFactory.get_create_mutation())
    subupdated = graphene.List(NIContactMutationFactory.get_update_mutation())
    subdeleted = graphene.List(NIContactMutationFactory.get_delete_mutation())
    unlinked = graphene.List(DeleteRelationship)

    address_created = graphene.List(NIAddressMutationFactory.get_create_mutation())
    address_updated = graphene.List(NIAddressMutationFactory.get_update_mutation())
    address_deleted  = graphene.List(NIAddressMutationFactory.get_delete_mutation())

    @classmethod
    def get_link_kwargs(cls, master_input, slave_input):
        ret = {}
        role_id = slave_input.get('role_id', None)

        if role_id:
            ret['role_id'] = role_id

        return ret

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh, **kwargs):
        role_id = kwargs.get('role_id', None)
        role = None

        if role_id:
            role_handle_id = relay.Node.from_global_id(role_id)[1]
            role = RoleModel.objects.get(handle_id=role_handle_id)
        else:
            role = RoleModel.objects.get(slug=DEFAULT_ROLE_KEY)

        helpers.link_contact_role_for_organization(user, master_nh.get_node(), slave_nh.handle_id, role)

    @classmethod
    def link_address_to_organization(cls, user, master_nh, slave_nh, **kwargs):
        helpers.add_address_organization(user, slave_nh.get_node(), master_nh.handle_id)

    @classmethod
    def process_extra_subentities(cls, user, main_nh, root, info, input, context):
        extract_param = 'address'
        ret_subcreated = None
        ret_subupdated = None
        ret_subdeleted = None

        create_address = input.get("create_address")
        update_address = input.get("update_address")
        delete_address = input.get("delete_address")

        nimetaclass = getattr(cls, 'NIMetaClass')
        address_created = getattr(nimetaclass, 'address_created', None)
        address_updated = getattr(nimetaclass, 'address_updated', None)
        address_deleted = getattr(nimetaclass, 'address_deleted', None)

        main_handle_id = None

        if main_nh:
            main_handle_id = main_nh.handle_id

        if main_handle_id:
            if create_address:
                ret_subcreated = []

                for input in create_address:
                    input['context'] = context
                    ret = address_created.mutate_and_get_payload(root, info, **input)
                    ret_subcreated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_created = getattr(ret, extract_param, None)

                    if not sub_errors and sub_created:
                        helpers.add_address_organization(
                            user, sub_created.get_node(), main_handle_id)

            if update_address:
                ret_subupdated = []

                for input in update_address:
                    input['context'] = context
                    ret = address_updated.mutate_and_get_payload(root, info, **input)
                    ret_subupdated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_edited = getattr(ret, extract_param, None)

                    if not sub_errors and sub_edited:
                        helpers.add_address_organization(
                            user, sub_edited.get_node(), main_handle_id)

            if delete_address:
                ret_subdeleted = []

                for input in delete_address:
                    ret = address_deleted.mutate_and_get_payload(root, info, **input)
                    ret_subdeleted.append(ret)

        return dict(address_created=ret_subcreated,
                    address_updated=ret_subupdated,
                    address_deleted=ret_subdeleted)

    class NIMetaClass:
        create_mutation = CreateOrganization
        update_mutation = UpdateOrganization
        create_submutation = NIContactMutationFactory.get_create_mutation()
        update_submutation = NIContactMutationFactory.get_update_mutation()
        delete_submutation = NIContactMutationFactory.get_delete_mutation()
        unlink_submutation = DeleteRelationship
        address_created = NIAddressMutationFactory.get_create_mutation()
        address_updated = NIAddressMutationFactory.get_update_mutation()
        address_deleted  = NIAddressMutationFactory.get_delete_mutation()
        graphql_type = Organization
        graphql_subtype = Contact
        context = sriutils.get_community_context()


class RoleRelationMutation(relay.ClientIDMutation):
    class Input:
        role_id = graphene.ID()
        organization_id = graphene.ID(required=True)
        relation_id = graphene.Int()

    errors = graphene.List(ErrorType)
    rolerelation = Field(RoleRelation)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context or not info.context.user.is_authenticated:
            raise GraphQLAuthException()

        user = info.context.user

        errors = None
        rolerelation = None

        # get input
        contact_handle_id = input.get('contact_handle_id', None)
        organization_id = input.get('organization_id', None)
        role_id = input.get('role_id', None)
        relation_id = input.get('relation_id', None)

        if role_id:
            role_handle_id = relay.Node.from_global_id(role_id)[1]
        else:
            default_role = RoleModel.objects.get(slug=DEFAULT_ROLE_KEY)
            role_handle_id = default_role.handle_id

        organization_handle_id = relay.Node.from_global_id(organization_id)[1]

        # get entities and check permissions
        contact_nh = None
        organization_nh = None
        role_model = None

        add_error_contact = False
        add_error_organization = False
        add_error_role = False

        if sriutils.authorice_write_resource(user, contact_handle_id):
            try:
                contact_nh = NodeHandle.objects.get(handle_id=contact_handle_id)
            except:
                add_error_contact = True
        else:
            add_error_contact = True

        if add_error_contact:
            error = ErrorType(
                field="contact_handle_id",
                messages=["The selected contact doesn't exist"]
            )
            errors.append(error)


        if sriutils.authorice_write_resource(user, organization_handle_id):
            try:
                organization_nh = NodeHandle.objects.get(handle_id=organization_handle_id)
            except:
                add_error_organization = True
        else:
            add_error_organization = True

        if add_error_organization:
            error = ErrorType(
                field="organization_handle_id",
                messages=["The selected organization doesn't exist"]
            )
            errors.append(error)

        try:
            role_model = RoleModel.objects.get(handle_id=role_handle_id)
        except:
            add_error_role = True

        if add_error_role:
            error = ErrorType(
                field="role_handle_id",
                messages=["The selected role doesn't exist"]
            )
            errors.append(error)

        # link contact with organization
        if not errors:
            contact, rolerelation = helpers.link_contact_role_for_organization(
                user, organization_nh.get_node(), contact_nh.handle_id,
                role_model, relation_id
            )

        return cls(errors=errors, rolerelation=rolerelation)


class CompositeContactMutation(CompositeMutation):
    class Input:
        create_phones = graphene.List(NIPhoneMutationFactory.get_create_mutation().Input)
        update_phones = graphene.List(NIPhoneMutationFactory.get_update_mutation().Input)
        delete_phones = graphene.List(NIPhoneMutationFactory.get_delete_mutation().Input)

        link_rolerelations = graphene.List(RoleRelationMutation.Input)

    phones_created = graphene.List(NIPhoneMutationFactory.get_create_mutation())
    phones_updated = graphene.List(NIPhoneMutationFactory.get_update_mutation())
    phones_deleted = graphene.List(NIPhoneMutationFactory.get_delete_mutation())
    rolerelations = graphene.List(RoleRelationMutation)

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh):
        helpers.add_email_contact(user, slave_nh.get_node(), master_nh.handle_id)

    @classmethod
    def process_extra_subentities(cls, user, main_nh, root, info, input, context):
        extract_param = 'phone'
        ret_subcreated = None
        ret_subupdated = None
        ret_subdeleted = None
        ret_rolerelations = None

        create_phones = input.get("create_phones")
        update_phones = input.get("update_phones")
        delete_phones = input.get("delete_phones")
        link_rolerelations = input.get("link_rolerelations")

        nimetaclass = getattr(cls, 'NIMetaClass')
        phones_created = getattr(nimetaclass, 'phones_created', None)
        phones_updated = getattr(nimetaclass, 'phones_updated', None)
        phones_deleted = getattr(nimetaclass, 'phones_deleted', None)
        rolerelation_mutation = getattr(nimetaclass, 'rolerelation_mutation', None)

        main_handle_id = None

        if main_nh:
            main_handle_id = main_nh.handle_id

        if main_handle_id:
            if create_phones:
                ret_subcreated = []

                for input in create_phones:
                    input['context'] = context
                    ret = phones_created.mutate_and_get_payload(root, info, **input)
                    ret_subcreated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_created = getattr(ret, extract_param, None)

                    if not sub_errors and sub_created:
                        helpers.add_phone_contact(
                            user, sub_created.get_node(), main_handle_id)

            if update_phones:
                ret_subupdated = []

                for input in update_phones:
                    input['context'] = context
                    ret = phones_updated.mutate_and_get_payload(root, info, **input)
                    ret_subupdated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_edited = getattr(ret, extract_param, None)

                    if not sub_errors and sub_edited:
                        helpers.add_phone_contact(
                            user, sub_edited.get_node(), main_handle_id)

            if delete_phones:
                ret_subdeleted = []

                for input in delete_phones:
                    ret = phones_deleted.mutate_and_get_payload(root, info, **input)
                    ret_subdeleted.append(ret)

            if link_rolerelations:
                ret_rolerelations = []

                for input in link_rolerelations:
                    input['contact_handle_id'] = main_handle_id
                    ret = rolerelation_mutation.mutate_and_get_payload(root, info, **input)
                    ret_rolerelations.append(ret)

        return dict(phones_created=ret_subcreated,
                    phones_updated=ret_subupdated,
                    phones_deleted=ret_subdeleted,
                    rolerelations=ret_rolerelations)

    class NIMetaClass:
        phones_created = NIPhoneMutationFactory.get_create_mutation()
        phones_updated = NIPhoneMutationFactory.get_update_mutation()
        phones_deleted = NIPhoneMutationFactory.get_delete_mutation()
        rolerelation_mutation = RoleRelationMutation
        graphql_type = Contact
        graphql_subtype = Email
        main_mutation_f = NIContactMutationFactory
        secondary_mutation_f = NIEmailMutationFactory
        context = sriutils.get_community_context()
