# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from apps.noclook.models import NodeType
import apps.noclook.helpers as h
import norduniclient as nc


@login_required
def list_by_type(request, slug):
    node_type = get_object_or_404(NodeType, slug=slug)
    node_handle_list = node_type.nodehandle_set.all()
    return render_to_response('noclook/list/list_by_type.html',
                              {'node_handle_list': node_handle_list, 'node_type': node_type},
                              context_instance=RequestContext(request))


@login_required
def list_cables(request):
    q = """
        MATCH (cable:Cable)
        RETURN cable
        ORDER BY cable.name
        """
    cable_list = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/list/list_cables.html',
                              {'cable_list': cable_list},
                              context_instance=RequestContext(request))


@login_required
def list_hosts(request):
    q = """
        MATCH (host:Host)
        OPTIONAL MATCH (host)<-[:Owns|Uses]-(user)
        RETURN host, collect(user) as users
        ORDER BY host.name
        """
    with nc.neo4jdb.read as r:
        host_list = r.execute(q).fetchall()
    return render_to_response('noclook/list/list_hosts.html', {'host_list': host_list},
                              context_instance=RequestContext(request))


@login_required
def list_odfs(request):
    q = """
        MATCH (odf:ODF)
        OPTIONAL MATCH (odf)-[:Located_in]->location
        OPTIONAL MATCH location<-[:Has]-site
        RETURN odf, location, site
        ORDER BY site.name, location.name, odf.name
        """
    odf_list = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/list/list_odfs.html',
                              {'odf_list': odf_list},
                              context_instance=RequestContext(request))


@login_required
def list_optical_links(request):
    q = """
        MATCH (link:Optical_Link)
        RETURN collect(link.handle_id) as ids
        """
    result = nc.query_to_dict(nc.neo4jdb, q)
    optical_link_list = []
    for handle_id in result['ids']:
        optical_link_list.append(nc.get_node_model(nc.neo4jdb, handle_id))
    return render_to_response('noclook/list/list_optical_links.html',
                              {'optical_link_list': optical_link_list},
                              context_instance=RequestContext(request))


@login_required
def list_optical_multiplex_section(request):
    q = """
        MATCH (oms:Optical_Multiplex_Section)
        RETURN collect(oms.handle_id) as ids
        """
    result = nc.query_to_dict(nc.neo4jdb, q)
    optical_multiplex_section_list = []
    for handle_id in result['ids']:
        optical_multiplex_section_list.append(nc.get_node_model(nc.neo4jdb, handle_id))
    return render_to_response('noclook/list/list_optical_multiplex_section.html',
                              {'optical_multiplex_section_list': optical_multiplex_section_list},
                              context_instance=RequestContext(request))

@login_required
def list_optical_nodes(request):
    q = """
        MATCH (node:Optical_Node)
        RETURN node, node.type as type, node.link as link, node.ots as ots
        ORDER BY node.name
        """
    optical_node_list = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/list/list_optical_nodes.html',
                              {'optical_node_list': optical_node_list},
                              context_instance=RequestContext(request))


@login_required
def list_optical_paths(request):
    q = """
        MATCH (path:Optical_Path)
        RETURN path, path.framing as framing, path.capacity as capacity, path.enrs as enrs,
            path.description as description, path.operational_state as operational_state
        ORDER BY path.name
        """
    optical_path_list = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/list/list_optical_paths.html',
                              {'optical_path_list': optical_path_list},
                              context_instance=RequestContext(request))


@login_required
def list_peering_partners(request):
    q = """
        MATCH (peer:Peering_Partner)
        OPTIONAL MATCH peer-[:Uses]->peering_group
        WITH distinct peer, peering_group
        RETURN peer, collect(peering_group) as peering_groups
        ORDER BY peer.name
        """
    partner_list = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/list/list_peering_partners.html', {'partner_list': partner_list},
                              context_instance=RequestContext(request))


@login_required
def list_racks(request):
    q = """
        MATCH (rack:Rack)
        OPTIONAL MATCH rack<-[:Has]-site
        RETURN rack, site
        ORDER BY site.name, rack.name
        """
    rack_list = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/list/list_racks.html',
                              {'rack_list': rack_list},
                              context_instance=RequestContext(request))


@login_required
def list_routers(request):
    q = """
        MATCH (router:Router)
        RETURN router, router.model as model, router.version as version
        ORDER BY router.name
        """
    router_list = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/list/list_routers.html',
                              {'router_list': router_list},
                              context_instance=RequestContext(request))


@login_required
def list_services(request, service_class=None):
    where_statement = ''
    if service_class:
        where_statement = 'WHERE service.service_class = "%s"' % service_class
    q = """
        MATCH (service:Service)
        MATCH (service)<-[:Uses]-(customer:Customer)
        WITH service, COLLECT(customer) as customers
        MATCH (service)<-[:Uses]-(end_user:End_User)
        %s
        RETURN service, service.service_class as service_class,
            service.service_type as service_type, service.description as description,
            customers, COLLECT(end_user) as end_users
        ORDER BY service.name
        """ % where_statement
    service_list = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/list/list_services.html',
                              {'service_list': service_list, 'service_class': service_class},
                              context_instance=RequestContext(request))


@login_required
def list_sites(request):
    q = """
        MATCH (site:Site)
        RETURN site
        ORDER BY site.country_code, site.name
        """
    site_list = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/list/list_sites.html', {'site_list': site_list},
                              context_instance=RequestContext(request))








