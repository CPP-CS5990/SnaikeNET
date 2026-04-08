# Multiplayer Snake Game

## Overview

This is a multiplayer snake game server implemented in Python

## Usage

- The preferred usage is to install `uv`
- Instructions to install `uv` can be found [here](https://docs.astral.sh/uv/getting-started/installation/).
- After installing `uv` you can run `uv sync` to install the dependencies and then `uv run server` to start the server.
- PyCharm also has support for `uv`


### Running server

```bash
uv run server
# run `uv run server --help` to see what options are available for the server (includes host and port options as well as grid size options and tick rate options)
```


### Running pygame client demo

```bash
uv run pygame_client_demo
# run `uv run pygame_client_demo --help` to see what options are available for the demo (includes server host and port options)
```

### Run pygame client demo as a spectator (useful for observing game without being an actual player)

```bash
uv run pygame_client_demo --spectator
```


## Module Structure

- `snaikenet_server` - Contains the server implementation for the multiplayer
snake game as well as the actual game implementation.
- `snaikenet_client` - Contains the client implementation for the multiplayer. Intended to have the
`SnaikenetClient` class be imported within the `snaikenet_demos` module to create demos of the client
(see pygame_client_demo.py for an example).
- `snaikenet_demos` - Contains demo implementations of the client. The `pygame_client_demo.py` is intended
to be a human interactable demo of the client using the `pygame` library.
- `snaikenet_protocol` - A sort of utility module that helps with implementing the server and client protocol. Most
of the utility of this module involves encoding and decoding messages to and from the server and client. The udp punch-hole
implementation is not specifically handled here, but the encoding and decoding of the messages that are sent during the punch-hole process is handled here.
- 

## Unit Tests

- The `tests` directory contains unit tests for the server and client implementations. These tests can be run using `uv run pytest`. It is encouraged to
add more tests whenever more functionality is added to the server and client implementations. Specifically when the protocol is expanded. This will ensure
that changes to the protocol can be made without as much worry about breaking existing functionality.


## Supported Python Versions

- Python=3.14
