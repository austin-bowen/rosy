from argparse import Namespace
from typing import Literal

from rosy import Node
from rosy.argparse import get_node_arg_parser
from rosy.authentication import Authenticator, optional_authkey_authenticator
from rosy.codec import (
    Codec,
    DictCodec,
    FixedLengthIntCodec,
    LengthPrefixedStringCodec,
    SequenceCodec,
    json_codec,
    msgpack_codec,
    pickle_codec,
)
from rosy.coordinator.client import build_coordinator_client
from rosy.coordinator.constants import DEFAULT_COORDINATOR_PORT
from rosy.network import get_lan_hostname
from rosy.node.clienthandler import ClientHandler
from rosy.node.codec import NodeMessageCodec
from rosy.node.loadbalancing import (
    GroupingTopicLoadBalancer,
    LeastRecentLoadBalancer,
    ServiceLoadBalancer,
    TopicLoadBalancer,
    node_name_group_key,
)
from rosy.node.peer import PeerConnectionBuilder, PeerConnectionManager, PeerSelector
from rosy.node.servers import TcpServerProvider, ServerProvider, ServersManager, TmpUnixServerProvider
from rosy.node.service.caller import ServiceCaller
from rosy.node.service.codec import ServiceRequestCodec, ServiceResponseCodec
from rosy.node.service.handlermanager import ServiceHandlerManager
from rosy.node.service.requesthandler import ServiceRequestHandler
from rosy.node.topic.codec import TopicMessageCodec
from rosy.node.topic.listenermanager import TopicListenerManager
from rosy.node.topic.messagehandler import TopicMessageHandler
from rosy.node.topic.sender import TopicSender
from rosy.node.topology import MeshTopologyManager
from rosy.specs import NodeId
from rosy.types import Data, Host, Port, ServerHost


async def build_node_from_args(
        default_node_name: str = None,
        args: Namespace = None,
        **kwargs,
) -> Node:
    """
    Builds a node from command line arguments.

    Args:
        default_node_name:
            Default node name. If not given, the argument is required.
            Ignored if `args` is given.
        args:
            Arguments from an argument parser. If not given, an argument parser
            is created using `get_node_arg_parser` and is used to parse args.
            This is useful if you create your own argument parser.
        kwargs:
            Additional keyword arguments to pass to `build_node`.
            These will override anything specified in `args`.
    """

    if args is None:
        args = get_node_arg_parser(default_node_name).parse_args()

    build_args = vars(args)

    if hasattr(args, 'coordinator'):
        build_args['coordinator_host'] = args.coordinator.host
        build_args['coordinator_port'] = args.coordinator.port

    build_args.update(kwargs)

    return await build_node(**build_args)


async def build_node(
        name: str,
        coordinator_host: Host = 'localhost',
        coordinator_port: Port = DEFAULT_COORDINATOR_PORT,
        coordinator_reconnect_timeout: float | None = 5.0,
        allow_unix_connections: bool = True,
        allow_tcp_connections: bool = True,
        node_server_host: ServerHost = None,
        node_client_host: Host = None,
        data_codec: Codec[Data] | Literal['pickle', 'json', 'msgpack'] = 'pickle',
        authkey: bytes = None,
        authenticator: Authenticator = None,
        topic_load_balancer: TopicLoadBalancer = None,
        service_load_balancer: ServiceLoadBalancer = None,
        start: bool = True,
        **kwargs,
) -> Node:
    authenticator = authenticator or optional_authkey_authenticator(authkey)

    coordinator_client = await build_coordinator_client(
        coordinator_host,
        coordinator_port,
        authenticator,
        reconnect_timeout=coordinator_reconnect_timeout,
    )

    topology_manager = MeshTopologyManager()

    peer_selector = build_peer_selector(
        topology_manager,
        topic_load_balancer,
        service_load_balancer,
    )

    connection_manager = PeerConnectionManager(
        PeerConnectionBuilder(authenticator),
    )

    if data_codec == 'pickle':
        data_codec = pickle_codec
    elif data_codec == 'json':
        data_codec = json_codec
    elif data_codec == 'msgpack':
        data_codec = msgpack_codec

    node_message_codec = build_node_message_codec(data_codec)

    topic_sender = TopicSender(peer_selector, connection_manager, node_message_codec)

    topic_listener_manager = TopicListenerManager()
    topic_message_handler = TopicMessageHandler(topic_listener_manager)

    service_handler_manager = ServiceHandlerManager()
    service_request_handler = ServiceRequestHandler(
        service_handler_manager,
        node_message_codec,
    )

    client_handler = ClientHandler(
        authenticator,
        node_message_codec,
        topic_message_handler,
        service_request_handler,
    )

    server_providers = build_server_providers(
        allow_unix_connections,
        allow_tcp_connections,
        node_server_host,
        node_client_host,
    )
    servers_manager = ServersManager(server_providers, client_handler.handle_client)

    request_id_bytes = 2  # Codec uses 2 bytes for request ID
    service_caller = ServiceCaller(
        peer_selector,
        connection_manager,
        node_message_codec,
        max_request_ids=2 ** (8 * request_id_bytes),
    )

    node = Node(
        id=NodeId(name),
        coordinator_client=coordinator_client,
        servers_manager=servers_manager,
        topology_manager=topology_manager,
        connection_manager=connection_manager,
        topic_sender=topic_sender,
        topic_listener_manager=topic_listener_manager,
        service_caller=service_caller,
        service_handler_manager=service_handler_manager,
    )

    if start:
        await node.start()

    return node


def build_server_providers(
        allow_unix_connections: bool,
        allow_tcp_connections: bool,
        node_server_host: ServerHost | None,
        node_client_host: Host | None,
) -> list[ServerProvider]:
    server_providers = []

    if allow_unix_connections:
        server_providers.append(TmpUnixServerProvider())

    if allow_tcp_connections:
        if not node_client_host:
            node_client_host = get_lan_hostname()

        provider = TcpServerProvider(node_server_host, node_client_host)
        server_providers.append(provider)

    if not server_providers:
        raise ValueError('Must allow at least one type of connection')

    return server_providers


def build_peer_selector(
        topology_manager: MeshTopologyManager,
        topic_load_balancer: TopicLoadBalancer | None,
        service_load_balancer: ServiceLoadBalancer | None,
) -> PeerSelector:
    least_recent_load_balancer = LeastRecentLoadBalancer()

    default_topic_load_balancer = GroupingTopicLoadBalancer(
        group_key=node_name_group_key,
        load_balancer=least_recent_load_balancer,
    )

    return PeerSelector(
        topology_manager,
        topic_load_balancer=topic_load_balancer or default_topic_load_balancer,
        service_load_balancer=service_load_balancer or least_recent_load_balancer,
    )


def build_node_message_codec(
        data_codec: Codec[Data],
) -> NodeMessageCodec:
    short_string_codec = LengthPrefixedStringCodec(
        len_prefix_codec=FixedLengthIntCodec(length=1)
    )

    short_int_codec = FixedLengthIntCodec(length=1)

    args_codec: SequenceCodec[Data] = SequenceCodec(
        len_header_codec=short_int_codec,
        item_codec=data_codec,
    )

    kwargs_codec: DictCodec[str, Data] = DictCodec(
        len_header_codec=short_int_codec,
        key_codec=short_string_codec,
        value_codec=data_codec,
    )

    request_id_codec = FixedLengthIntCodec(length=2)

    return NodeMessageCodec(
        topic_message_codec=TopicMessageCodec(
            topic_codec=short_string_codec,
            args_codec=args_codec,
            kwargs_codec=kwargs_codec,
        ),
        service_request_codec=ServiceRequestCodec(
            request_id_codec,
            service_codec=short_string_codec,
            args_codec=args_codec,
            kwargs_codec=kwargs_codec,
        ),
        service_response_codec=ServiceResponseCodec(
            request_id_codec,
            data_codec=data_codec,
            error_codec=LengthPrefixedStringCodec(
                len_prefix_codec=FixedLengthIntCodec(length=2),
            )
        ),
    )
