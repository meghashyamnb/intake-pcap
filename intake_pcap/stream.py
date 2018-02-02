from collections import OrderedDict

import pandas as pd

import pcapy

from .packet import IPPacket


class PacketStream(object):
    def __init__(self, reader, protocol, payload):
        self._reader = reader
        self._payload = payload
        self.to_bpf(protocol)

    @property
    def dtype(self):
        items = [
            ('time', 'datetime64[ns]'),
            ('src_host', 'object'),
            ('src_port', 'object'),
            ('dst_host', 'object'),
            ('dst_port', 'object'),
            ('protocol', 'object')]

        if self._payload:
            items.append(('payload', 'object'))

        return OrderedDict(items)

    def to_bpf(self, protocol):
        if protocol:
            self._bpf = "ip proto \{}".format(protocol)
        else:
            self._bpf = "ip"

    def to_dataframe(self, n=-1):
        packets = []

        def decode_ip_packet(header, data):
            seconds, fractional = header.getts()
            ts = pd.to_datetime(10**6 * seconds + fractional, unit='us')

            packet = IPPacket(data)

            items = [
                ('time', ts),
                ('src_host', packet.source_ip_address),
                ('src_port', packet.source_ip_port),
                ('dst_host', packet.destination_ip_address),
                ('dst_port', packet.destination_ip_port),
                ('protocol', packet.ip_protocol)]

            if self._payload:
                items.append(('payload', packet.payload))

            return dict(items)

        def decoder(header, data):
            packets.append(decode_ip_packet(header, data))

        self._reader.setfilter(self._bpf)
        self._reader.loop(n, decoder)

        df = pd.DataFrame(packets, columns=self.dtype.keys())
        return df.astype(dtype=self.dtype)


class LiveStream(PacketStream):
    def __init__(self, interface, protocol=None, payload=False, max_packet=2**16, timeout=1000):
        """
        Parameters:
            interface : str
                Network interface from which to capture packets.
            protocol : str
                Exclude all other IP traffic except packets matching this
                protocol. If None, all traffic is shown.
            payload : bool
                Toggle whether to include packet data.
            max_packet : int
                Maximum allowed packet size.
            timeout: int
                Maximum time to wait for packets from interface.
        """
        reader = pcapy.open_live(interface, max_packet, 1, timeout)
        super(LiveStream, self).__init__(reader, protocol, payload)


class OfflineStream(PacketStream):
    def __init__(self, path, protocol=None, payload=False):
        """
        Parameters:
            path : str
                Absolute path to source file.
            protocol : str
                Exclude all other IP traffic except packets matching this
                protocol. If None, all traffic is shown.
            payload : bool
                Toggle whether to include packet data.
        """
        reader = pcapy.open_offline(path)
        super(OfflineStream, self).__init__(reader, protocol, payload)