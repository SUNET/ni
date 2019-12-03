# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from graphene_django.views import GraphQLView

from .core import *
from .types import *
from .query import *
from .mutations import *

NOCSCHEMA_TYPES = [
    User,
    Dropdown,
    Choice,
    Neo4jChoice,
    NodeHandler,
    Group,
    Contact,
    Procedure,
    Host,
    Address,
    Phone,
    Email,
]

NOCSCHEMA_QUERIES = [
    NOCRootQuery,
]

NOCSCHEMA_MUTATIONS = [
    NOCRootMutation,
]

import logging
import pprint
import os

@method_decorator(login_required, name='dispatch')
class AuthGraphQLView(GraphQLView):
    def dispatch(self, request, *args, **kwargs):
        with open(f'/app/log/graphql.log', 'w') as f:
            query_body = request.body.decode()
            print('\n', file=f)
            print(query_body, file=f)
            print('\n', file=f)

        return super().dispatch(request, *args, **kwargs)
