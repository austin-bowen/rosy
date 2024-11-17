# easymesh

Simple, fast inter-process message passing for distributed Python processes.

`easymesh` is inspired by [ROS (Robot Operating System)](https://www.ros.org/); it allows nodes to send messages on a "topic" to any other nodes listening to that topic. Messages can contain any Python data that is serializable by `pickle`, or whatever serde implementation you choose.

Nodes can run on a single machine, or be distributed across multiple machines on a network. As long as they can talk to the coordinator node, they can figure out how to talk to each other.

`easymesh` also has simple load balancing: if multiple nodes of the same name are listening to a topic, then messages will be sent to them in a round-robin fashion. (The load balancing strategy can be changed or disabled if desired.)

## Show me the code!

[easymesh/demo/**sender.py**](src/easymesh/demo/sender.py):
```python
import easymesh

async def main():
    node = await easymesh.build_mesh_node(name='sender')
    await node.wait_for_listener('some-topic')
    await node.send('some-topic', {'hello': 'world!'})

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

[easymesh/demo/**receiver.py**](src/easymesh/demo/receiver.py):

```python
import easymesh
from easymesh.asyncio import forever

async def callback(topic, data):
    print(f'receiver got: topic={topic}; data={data}')

async def main():
    node = await easymesh.build_mesh_node(name='receiver')
    await node.listen('some-topic', callback)
    await forever()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

**Terminal:**

```bash
$ python -m easymesh.coordinator &
$ python -m easymesh.demo.receiver &
$ python -m easymesh.demo.sender
receiver got: topic=some-topic; data={'hello': 'world!'}
```

## Installation

```bash
pip install git+https://github.com/austin-bowen/easymesh.git
```

## What is a mesh?

A mesh is a collection of "nodes" that can send messages to each other. A message can be any Python object. There is one node per Python process, with nodes potentially distributed across multiple machines. Each node listens to specific message "topics", and calls listener callbacks when messages are received on those topics. Each node can send messages to any topic, and the message will be sent to all listening nodes.

### How does it work?

A special "coordinator" node maintains the current mesh topology, and makes sure all nodes in the mesh know about each other. The mesh topology is a list of nodes in the mesh, their connection details, and topics they are listening to. When a new node is created, it registers itself with the coordinator, which then adds it to the mesh topology; when a node disconnects, it is removed from the mesh topology. When any change is made to the mesh topology, the coordinator node broadcasts the new mesh topology to all nodes on the mesh.

When a node needs to send a message, it uses the mesh topology to find all currently listening nodes, connects to them, and sends the message.

### Guarantees

`easymesh` only guarantees that messages will be received in the order in which they were sent from a *single* node. It is possible for messages sent from different nodes to be received out of order.

It does **not** guarantee message delivery; there are no delivery confirmations, and if a message fails to be sent to a node (e.g. due to network failure), it will not be retried.

### Security

Security is not a primary concern of `easymesh`. Messages are sent in plaintext (unencrypted) for speed, and by default, there is no authentication of nodes on the mesh.

There is optional authentication support to ensure all nodes on the mesh are allowed to be there. This is done using symmetric HMAC challenge-response. The coordinator will authenticate all nodes before adding them to the mesh, and all nodes will authenticate each other before connecting. This could come in handy when e.g. running multiple meshes on the same network, to avoid accidentally connecting a node to the wrong mesh.

Simply provide the `--authkey=...` argument when starting the coordinator, and ensure the `authkey=b'...'` argument is provided to `build_mesh_node(...)`, e.g.

```bash
$ python -m easymesh.coordinator --authkey my-secret-key
```

```python
node = await easymesh.build_mesh_node(name='my-node', authkey=b'my-secret-key')
```


## Roadmap

- Robustness to failure
  - Nodes should automatically reconnect to coordinator if they lose connection
- Logging
- Coordinator commands
  - Kill one or all nodes
