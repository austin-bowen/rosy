from argparse import Namespace
from typing import Literal

from rosy import Node
from rosy.argparse import get_node_arg_parser
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
from rosy.discovery.zeroconf import ZeroconfNodeDiscovery
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
from rosy.node.peer.connection import PeerConnectionBuilder, PeerConnectionManager
from rosy.node.peer.selector import PeerSelector
from rosy.node.servers import (
    ServerProvider,
    ServersManager,
    TcpServerProvider,
    TmpUnixServerProvider,
)
from rosy.node.service.caller import ServiceCaller
from rosy.node.service.codec import ServiceRequestCodec, ServiceResponseCodec
from rosy.node.service.handlermanager import ServiceHandlerManager
from rosy.node.service.requesthandler import ServiceRequestHandler
from rosy.node.topic.codec import TopicMessageCodec
from rosy.node.topic.listenermanager import TopicListenerManager
from rosy.node.topic.messagehandler import TopicMessageHandler
from rosy.node.topic.sender import TopicSender
from rosy.node.topology import MeshTopologyManager, TopologyChangedHandler
from rosy.specs import NodeId
from rosy.types import Data, DomainId, Host, ServerHost
from rosy.utils import get_domain_id

DataCodecArg = Codec[Data] | Literal["pickle", "json", "msgpack"]


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

    return await build_node(**vars(args))


async def build_node(
    name: str,
    domain_id: DomainId = None,
    allow_unix_connections: bool = True,
    allow_tcp_connections: bool = True,
    node_server_host: ServerHost = None,
    node_client_host: Host = None,
    data_codec: DataCodecArg = "pickle",
    topic_load_balancer: TopicLoadBalancer = None,
    service_load_balancer: ServiceLoadBalancer = None,
    start: bool = True,
    **kwargs,
) -> Node:
    """Builds a ROSY node.

    Args:
        name: Name of the node. Does not need to be unique; multiple nodes
            with the same name can be part of the same mesh. Topic messages
            will be sent to nodes of the same name in a round-robin fashion,
            by default, according to the value of `topic_load_balancer`.
            This makes horizontal scaling easy; just start the same node
            multiple times.
        domain_id: Domain ID of the node. Nodes must be in the same domain
            to connect to each other. If not given, defaults to the
            `ROSY_DOMAIN_ID` environment variable, or 'default' if not set.
        allow_unix_connections: Whether to allow connections to the node over
            Unix sockets. Defaults to True.
        allow_tcp_connections: Whether to allow connections to the node over
            TCP sockets. Defaults to True.
        node_server_host: Hostname to use for the node's server. If not given,
            the node will listen on all available network interfaces.
        node_client_host: Hostname that other nodes will use to connect to this
            node. If not given, defaults to the machine's mDNS hostname, e.g.
            "<hostname>.local".
        data_codec: A codec to use for serializing and deserializing data
            between nodes. Can be one of 'pickle', 'json', or 'msgpack';
            or, a custom Codec instance. Defaults to 'pickle'.
        topic_load_balancer: A load balancer to use for distributing topic
            messages. Defaults to a least-recently-used load balancer.
        service_load_balancer: A load balancer to use for distributing service
            requests. Defaults to a least-recently-used load balancer.
        start: Whether to start the node immediately. Defaults to True.
            If False, the user must call `await node.start()` before the node
            will be ready to use.
    """

    domain_id = domain_id or get_domain_id()
    discovery = ZeroconfNodeDiscovery(domain_id=domain_id)

    topic_listener_manager = TopicListenerManager()
    service_handler_manager = ServiceHandlerManager()

    request_id_bytes = 2
    node_message_codec = build_node_message_codec(request_id_bytes, data_codec)

    servers_manager = build_servers_manager(
        allow_unix_connections,
        allow_tcp_connections,
        node_server_host,
        node_client_host,
        topic_listener_manager,
        service_handler_manager,
        node_message_codec,
    )

    topology_manager = MeshTopologyManager()

    connection_manager = PeerConnectionManager(
        PeerConnectionBuilder(),
    )

    discovery.topology_changed_callback = TopologyChangedHandler(
        topology_manager,
        connection_manager,
    )

    peer_selector = build_peer_selector(
        topology_manager,
        topic_load_balancer,
        service_load_balancer,
    )

    topic_sender = TopicSender(peer_selector, connection_manager, node_message_codec)

    service_caller = ServiceCaller(
        peer_selector,
        connection_manager,
        node_message_codec,
        max_request_ids=2 ** (8 * request_id_bytes),
    )

    node = Node(
        id=NodeId(name),
        discovery=discovery,
        servers_manager=servers_manager,
        topology_manager=topology_manager,
        topic_sender=topic_sender,
        topic_listener_manager=topic_listener_manager,
        service_caller=service_caller,
        service_handler_manager=service_handler_manager,
    )

    if start:
        await node.start()

    return node


def build_node_message_codec(
    request_id_bytes: int,
    data_codec: DataCodecArg,
) -> NodeMessageCodec:
    data_codec = build_data_codec(data_codec)

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

    request_id_codec = FixedLengthIntCodec(length=request_id_bytes)

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
            ),
        ),
    )


def build_data_codec(data_codec: DataCodecArg) -> Codec[Data]:
    if data_codec == "pickle":
        return pickle_codec
    elif data_codec == "json":
        return json_codec
    elif data_codec == "msgpack":
        return msgpack_codec
    else:
        return data_codec


def build_servers_manager(
    allow_unix_connections: bool,
    allow_tcp_connections: bool,
    node_server_host: ServerHost,
    node_client_host: Host | None,
    topic_listener_manager: TopicListenerManager,
    service_handler_manager: ServiceHandlerManager,
    node_message_codec: NodeMessageCodec,
) -> ServersManager:
    topic_message_handler = TopicMessageHandler(topic_listener_manager)

    service_request_handler = ServiceRequestHandler(
        service_handler_manager,
        node_message_codec,
    )

    client_handler = ClientHandler(
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

    return ServersManager(server_providers, client_handler.handle_client)


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
        raise ValueError("Must allow at least one type of connection")

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
