# easymesh

Guiding principles:
- Easy to use
- Easy to understand
- Simple -- no fancy bells and whistles
- Fast & efficient
- Async

## Installation

```bash
# TODO
```

## Quick example

```python
# TODO
```

## What is a mesh?

A mesh is a collection of "nodes" that can send messages to each other. A message can be any Python object. There is one node per Python process, with nodes potentially distributed across multiple machines. Each node listens to specific message "topics", and calls listener callbacks when messages are received on those topics. Each node can send messages to any topic, and the message will be sent to all listening nodes.

A special "coordinator" node makes sure all nodes in the mesh know about each other.

### How does it work?

The coordinator node maintains the mesh "topology" -- a list of all nodes in the mesh, with node connection details and topics that each node listens to. When a new node is created, it registers itself with the coordinator; when a node disconnects, it is removed from the mesh topology. When a change is made to the mesh topology, the coordinator node broadcasts the new mesh topology to all nodes on the mesh.

When a node needs to send a message, it uses the mesh topology to find all currently listening nodes, connects to them if necessary, and sends the message.

## Roadmap

- Load balancing
  - When multiple nodes with the same name are on the mesh, messages should be automatically distributed among them
