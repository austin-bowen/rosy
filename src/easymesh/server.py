import asyncio
from asyncio import StreamReader, StreamWriter

from easymesh.objectstreamio import AnyObjectStreamIO

AUTHENTICATED_RESPONSE = b'OK'


class Handler:
    def __init__(
            self,
            reader: StreamReader,
            writer: StreamWriter,
            clients: set,
            auth_key: bytes = b'hellothere',
    ):
        print('connected')
        self.reader = reader
        self.writer = writer
        self.clients = clients
        self.auth_key = auth_key

        self.obj_io = AnyObjectStreamIO(reader, writer)

    async def run(self):
        await self._authenticate_client()
        self.clients.add(self.obj_io)

        await asyncio.gather(*(
            client.write_object(dict(len_clients=len(self.clients)))
            for client in self.clients
        ))

        try:
            await asyncio.gather(
                self._send_heartbeat(),
                self._receive_objects(),
            )
        except Exception as e:
            print('disconnected')
            print('error:', repr(e))
        finally:
            self.clients.remove(self.obj_io)

    async def _authenticate_client(self) -> None:
        client_auth_key = await self.obj_io.read_object()

        if client_auth_key == self.auth_key:
            await self.obj_io.write_object(AUTHENTICATED_RESPONSE)
        else:
            e = InvalidAuthKey(client_auth_key)
            await self.obj_io.write_object(e)
            raise e

    async def _send_heartbeat(self) -> None:
        while True:
            await self.obj_io.write_object(b'heartbeat')
            await asyncio.sleep(2.5)

    async def _receive_objects(self) -> None:
        while True:
            print('Received from client:', await self.obj_io.read_object())


class InvalidAuthKey(Exception):
    def __init__(self, auth_key: bytes):
        super().__init__(f'Received invalid auth key: {auth_key}')


async def main():
    clients = set()

    client_connected_cb = lambda r, w: Handler(r, w, clients).run()

    # server = await asyncio.start_server(
    #     client_connected_cb,
    #     host='localhost',
    #     port=8888,
    # )
    server = await asyncio.start_unix_server(
        client_connected_cb,
        path='./mesh.sock',
    )

    print(f'Serving on {server.sockets[0].getsockname()}')
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
