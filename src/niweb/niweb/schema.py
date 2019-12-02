import graphene
import graphql_jwt
from apps.noclook.schema import NOCSCHEMA_QUERIES, NOCSCHEMA_MUTATIONS,\
                                    NOCSCHEMA_TYPES
import logging
import pprint
import os

from django.conf import settings

logger = logging.getLogger(__name__)

ALL_TYPES = NOCSCHEMA_TYPES # + OTHER_APP_TYPES
ALL_QUERIES = NOCSCHEMA_QUERIES
ALL_MUTATIONS = NOCSCHEMA_MUTATIONS

class Query(*ALL_QUERIES, graphene.ObjectType):
    pass

class Mutation(*ALL_MUTATIONS, graphene.ObjectType):
    token_auth = graphql_jwt.relay.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.relay.Verify.Field()
    refresh_token = graphql_jwt.relay.Refresh.Field()
    #revoke_token = graphql_jwt.relay.Revoke.Field()

class LoggerMiddleware(object):
    def resolve(self, next, root, info, **args):
        with open(f'/app/log/graphql.log', 'w') as f:
            print('\n\n', file=f)
            print('==========', file=f)
            print(pprint.pformat(root, indent=1), file=f)
            print(pprint.pformat(info, indent=1), file=f)
            print(pprint.pformat(args, indent=1), file=f)
            print('\n\n', file=f)
        return next(root, info, **args)

class AuditSchema(graphene.Schema):
    def execute(self, *args, **kwargs):
        kwargs['middleware'] = [LoggerMiddleware()]
        return super().execute(*args, **kwargs)

schema = AuditSchema(
            query=Query,
            mutation=Mutation,
            auto_camelcase=False,
            types=ALL_TYPES
        )
