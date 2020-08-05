# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.schema.core import *
from apps.noclook.models import SwitchType as SwitchTypeModel
from .community import Group

## Organizations
class Customer(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Customer'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class EndUser(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'End User'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class Provider(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Provider'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class SiteOwner(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Site Owner'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class HostUser(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Host User'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


## Cables and Equipment
class Port(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    port_type = NIChoiceField(dropdown_name="port_types")
    description = NIStringField()
    connected_to = NIListField(type_args=(lambda: Physical,), rel_name='Connected_to', rel_method='_incoming')

    class NIMetaType:
        ni_type = 'Port'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class Cable(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    cable_type = NIChoiceField(dropdown_name="cable_types")
    description = NIStringField()
    provider = NISingleRelationField(field_type=(lambda: Provider), rel_name="Provides", rel_method="_incoming")
    ports = NIListField(type_args=(lambda: Port,), rel_name='Connected_to', rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Cable'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


allowed_types_converthost = ['firewall', 'switch', 'pdu', 'router']


class Host(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    host_type = graphene.String()
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': True })
    ip_addresses = NIIPAddrField()
    responsible_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Takes_responsibility", rel_method="_incoming",
        check_permissions=False)
    support_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Supports", rel_method="_incoming", check_permissions=False)
    managed_by = NIChoiceField(dropdown_name="host_management_sw")
    backup = NIStringField()
    os = NIStringField()
    os_version = NIStringField()
    contract_number = NIStringField()
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    host_owner = NISingleRelationField(field_type=(lambda: Relation), rel_name="Owns", rel_method="_incoming")
    host_services = NIStringField()

    def resolve_ip_addresses(self, info, **kwargs):
        '''Manual resolver for the ip field'''
        return self.get_node().data.get('ip_addresses', None)

    def resolve_host_type(self, info, **kwargs):
        '''Manual resolver for host type string'''
        return self.get_node().meta_type

    class NIMetaType:
        ni_type = 'Host'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context


class Router(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': True })
    model = NIStringField()
    version = NIStringField()
    rack_units = NIIntField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has', rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Router'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class SwitchType(DjangoObjectType):
    '''
    This class represents a SwitchType for switch's mutations
    '''
    class Meta:
        #only_fields = ('id', 'name')
        model = SwitchTypeModel
        interfaces = (graphene.relay.Node, )


def resolve_getSwitchTypes(self, info, **kwargs):
    if info.context and info.context.user.is_authenticated:
        return SwitchTypeModel.objects.all()
    else:
        raise GraphQLAuthException()


class Switch(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIStringField(type_kwargs={ 'required': True })
    ip_addresses = NIIPAddrField()
    responsible_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Takes_responsibility", rel_method="_incoming",
        check_permissions=False)
    support_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Supports", rel_method="_incoming", check_permissions=False)
    managed_by = NIChoiceField(dropdown_name="host_management_sw")
    backup = NIStringField()
    os = NIStringField()
    os_version = NIStringField()
    contract_number = NIStringField()
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    provider = NISingleRelationField(field_type=(lambda: Provider),
        rel_name="Provides", rel_method="_incoming")
    max_number_of_ports = NIIntField()

    class NIMetaType:
        ni_type = 'Switch'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class Firewall(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIStringField(type_kwargs={ 'required': True })
    ip_addresses = NIIPAddrField()
    responsible_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Takes_responsibility", rel_method="_incoming",
        check_permissions=False)
    support_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Supports", rel_method="_incoming", check_permissions=False)
    managed_by = NIChoiceField(dropdown_name="host_management_sw")
    managed_by = NIChoiceField(dropdown_name="host_management_sw")
    backup = NIStringField()
    security_class = NIChoiceField(dropdown_name="security_classes")
    security_comment = NIStringField()
    os = NIStringField()
    os_version = NIStringField()
    model = NIStringField()
    vendor = NIStringField()
    service_tag = NIStringField()
    end_support = NIStringField()
    contract_number = NIStringField()
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    max_number_of_ports = NIIntField()

    class NIMetaType:
        ni_type = 'Firewall'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class ExternalEquipment(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has', rel_method='_outgoing')
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()

    class NIMetaType:
        ni_type = 'External Equipment'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


## Peering
class PeeringPartner(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    as_number = NIStringField()

    class NIMetaType:
        ni_type = 'Peering Partner'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class PeeringGroup(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })

    class NIMetaType:
        ni_type = 'Peering Group'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context


network_type_resolver = {
    'Customer': Customer,
    'End User': EndUser,
    'Peering Partner': PeeringPartner,
    'Peering Group': PeeringGroup,
    'Provider': Provider,
    'Site Owner': SiteOwner,
    'Port': Port,
    'Cable': Cable,
    'Host': Host,
    'Host User': HostUser,
    'Switch': Switch,
    'Firewall': Firewall,
    'External Equipment': ExternalEquipment,
}
