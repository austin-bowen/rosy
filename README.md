# rosy

> It's not ROS... but it *is* ROS-y!

`rosy`, inspired by [ROS (Robot Operating System)](https://www.ros.org/), provides simple and fast inter-process message passing for distributed Python processes, or "nodes".

`rosy` allows sending messages between nodes in two different ways:
1. **Topics**: Unidirectional, "fire and forget" messages that are sent from a node to all nodes listening to that topic.
2. **Services**: Bidirectional, request-response messages that allow a node to get a response from any node hosting the service being called.

Messages can contain any Python data that is serializable by `pickle` (default), `json`, or `msgpack`. Alternatively, you can even provide your own custom codec.

Nodes can run on a single machine, or be distributed across multiple machines on a network. As long as they can talk to the coordinator node, they can figure out how to talk to each other. Nodes will automatically reconnect to the coordinator and other nodes if they lose connection.

`rosy` also has simple load balancing: if multiple nodes of the same name are listening to a topic, then messages will be sent to them in a round-robin fashion. (The load balancing strategy can be changed or disabled if desired.)

## Show me the code!

Here are some simplified examples. See the linked files for the full code.

### Example: Sending messages using Topics

[rosy/demo/**topic_sender.py**](src/rosy/demo/topic_sender.py):

```python
import rosy

async def main():
    node = await rosy.build_node(name='topic_sender')
    await node.send('some-topic', 'hello', name='world')
```

[rosy/demo/**topic_listener.py**](src/rosy/demo/topic_listener.py):

```python
import rosy

async def main():
    node = await rosy.build_node(name='topic_listener')
    await node.listen('some-topic', callback)
    await node.forever()

async def callback(topic, message, name=None):
    print(f'Received "{message} {name}" on topic={topic}')
```

**Terminal:**

```bash
# Terminal 1
$ rosy
Started rosy coordinator on :7679

# Terminal 2
$ python -m rosy.demo.topic_listener
Listening...

# Terminal 3
$ python -m rosy.demo.topic_sender

# Terminal 2
Received "hello world" on topic=some-topic
```

### Example: Calling Services

[rosy/demo/**service_caller.py**](src/rosy/demo/service_caller.py):

```python
import rosy

async def main():
    node = await rosy.build_node(name='service_caller')
    print('Calculating 2 * 2...')
    result = await node.call('multiply', 2, 2)
    print(f'Result: {result}')
```

[rosy/demo/**service_provider.py**](src/rosy/demo/service_provider.py):

```python
import rosy

async def main():
    node = await rosy.build_node(name='service_provider')
    await node.add_service('multiply', multiply)
    await node.forever()

async def multiply(service, a, b):
    return a * b
```

**Terminal:**

```bash
# Terminal 1
$ rosy
Started rosy coordinator on :7679

# Terminal 2
$ python -m rosy.demo.service_provider
Started service...

# Terminal 3
$ python -m rosy.demo.service_caller
Calculating 2 * 2...
Result: 4
```

## Installation

```bash
pip install rosy
```

## Commands

These commands mirror the [`ros2` ROS commands](https://docs.ros.org/en/rolling/Concepts/Basic/About-Command-Line-Tools.html). Use the `--help` flag on any command to see all options.

### `$ rosy` or `rosy coordinator`

Start the coordinator node. By default, it will listen on port `7679` on all interfaces.

### `$ rosy node list`

List all nodes in the mesh, what topics they are listening to, and what services they are providing.

### `$ rosy topic {list,echo,send}`

List all topics, echo messages from a topic, or send a message to a topic.

### `$ rosy service {list,call}`

List all services, or call a service.

### `$ rosy launch [config]`

Launch a coordinator and several nodes all at once. `config` defaults to `launch.yaml`. Check out the [template `launch.yaml`](launch.yaml) for all options, or the [demo `launch.yaml`](src/rosy/demo/launch.yaml) for a runnable example.

### `$ rosy bag {record,play,info}`

Tool for recording and playing back messages. The options are:

- `record <topics>`: Record messages on the given topic(s) to a file. By default, a file named `record_<datetime>.bag` will be created in the current directory.
- `play`: Play back messages from a bag file, with the same timing between messages as when they were recorded. By default, the most recent bag file in the current directory will be played back.
- `info`: Print information about a bag file. By default, the most recent bag file in the current directory will be used.

### `$ rosy speedtest {send,recv}`

Performs a speed test sending and receiving topic messages.

Some results:

| Hardware    | Message size | Messages/s | Latency (ms) | Bandwidth (MB/s) |
|-------------|--------------|------------|--------------|------------------|
| Laptop*     | 0            | 116000     | 0.023        | N/A              |
| Laptop*     | 1 kB         | 115000     | 0.028        | 115              |
| Laptop*     | 1 MB         | 1300       | 1.2          | 1300             |
| Orin Nano** | 0            | 29000      | 0.13         | N/A              |
| Orin Nano** | 1 kB         | 28000      | 0.15         | 28               |
| Orin Nano** | 1 MB         | 363        | 3.6          | 363              |

\* Dell XPS 17 9730 with an Intel Core i9-13900H CPU and 64 GB DDR5 RAM running Ubuntu 24.04 and Python 3.10.\
\** [NVIDIA Jetson Orin Nano](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/)
running Ubuntu 22.04 and Python 3.13.

## What is a mesh?

A mesh is a collection of "nodes" that can send messages to each other. A message can be any Python object. There is one node per Python process, with nodes potentially distributed across multiple machines. Each node listens to specific message "topics", and calls listener callbacks when messages are received on those topics. Each node can send messages to any topic, and the message will be sent to all listening nodes.

### How does it work?

A special "coordinator" node maintains the current mesh topology, and makes sure all nodes in the mesh know about each other. The mesh topology is a list of nodes in the mesh, their connection details, and topics they are listening to. When a new node is created, it registers itself with the coordinator, which then adds it to the mesh topology; when a node disconnects, it is removed from the mesh topology. When any change is made to the mesh topology, the coordinator node broadcasts the new mesh topology to all nodes on the mesh.

When a node needs to send a message, it uses the mesh topology to find all currently listening nodes, connects to them, and sends the message.

### Guarantees

`rosy` only guarantees that messages will be received in the order in which they were sent from a *single* node. It is possible for messages sent from different nodes to be received out of order.

It does **not** guarantee message delivery; there are no delivery confirmations, and if a message fails to be sent to a node (e.g. due to network failure), it will not be retried.

### Security

Security is not a primary concern of `rosy`. Messages are sent in plaintext (unencrypted) for speed, and by default, there is no authentication of nodes on the mesh.

There is optional authentication support to ensure all nodes on the mesh are allowed to be there. This is done using symmetric HMAC challenge-response. The coordinator will authenticate all nodes before adding them to the mesh, and all nodes will authenticate each other before connecting. This could come in handy when e.g. running multiple meshes on the same network, to avoid accidentally connecting a node to the wrong mesh.

Simply provide the `--authkey=...` argument when starting the coordinator, and ensure the `authkey=b'...'` argument is provided to `build_node(...)`, e.g.

```bash
$ rosy --authkey my-secret-key
```

```python
node = await rosy.build_node(name='my-node', authkey=b'my-secret-key')
```
