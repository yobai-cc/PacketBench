from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.services.logging_service import system_log_service
from app.services.packet_logger import packet_logger
from app.utils.codec import parse_payload


@dataclass(slots=True)
class UDPServerConfig:
    bind_ip: str = "0.0.0.0"
    bind_port: int = 9000
    custom_reply_data: str = ""
    hex_mode: bool = False


@dataclass(slots=True)
class UDPPeerState:
    host: str
    port: int
    first_seen: datetime
    last_seen: datetime
    rx_packets: int = 0
    tx_packets: int = 0
    rx_bytes: int = 0
    tx_bytes: int = 0


class UDPServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, service: "UDPServerService") -> None:
        self.service = service

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.service.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        asyncio.create_task(self.service.handle_datagram(data, addr))

    def error_received(self, exc: Exception) -> None:
        self.service.emit_system_log("error", "network", "UDP transport error", str(exc))

    def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            self.service.emit_system_log("error", "network", "UDP transport closed unexpectedly", str(exc))


class UDPServerService:
    """Async UDP service that replies fixed configured payloads to devices."""

    def __init__(self, db_factory: Callable[[], Session] = SessionLocal) -> None:
        self.db_factory = db_factory
        self.config = UDPServerConfig()
        self.transport: asyncio.DatagramTransport | None = None
        self.protocol: UDPServerProtocol | None = None
        self.running = False
        self.tx_count = 0
        self.rx_count = 0
        self.last_client_addr: tuple[str, int] | None = None
        self.current_target_addr: tuple[str, int] | None = None
        self.peers: dict[str, UDPPeerState] = {}

    def update_config(self, config: UDPServerConfig) -> None:
        self.config = config

    def record_client_addr(self, addr: tuple[str, int]) -> None:
        now = datetime.now(timezone.utc)
        peer = self._get_or_create_peer(addr, now)
        peer.last_seen = now
        peer.rx_packets += 1
        self.last_client_addr = addr
        if self.current_target_addr is None:
            self.current_target_addr = addr

    def _peer_key(self, addr: tuple[str, int]) -> str:
        return f"{addr[0]}:{addr[1]}"

    def _get_or_create_peer(self, addr: tuple[str, int], now: datetime | None = None) -> UDPPeerState:
        timestamp = now or datetime.now(timezone.utc)
        key = self._peer_key(addr)
        peer = self.peers.get(key)
        if peer is None:
            peer = UDPPeerState(host=addr[0], port=addr[1], first_seen=timestamp, last_seen=timestamp)
            self.peers[key] = peer
        return peer

    def select_target(self, addr: tuple[str, int]) -> None:
        self.current_target_addr = addr
        self.last_client_addr = addr
        self._get_or_create_peer(addr)

    def select_target_from_label(self, peer_addr: str) -> None:
        host, port = peer_addr.rsplit(":", 1)
        self.select_target((host, int(port)))

    def remove_peer(self, peer_addr: str) -> None:
        peer = self.peers.pop(peer_addr, None)
        if not peer:
            return
        addr = (peer.host, peer.port)
        if self.current_target_addr == addr:
            self.current_target_addr = None
        if self.last_client_addr == addr:
            self.last_client_addr = None

    def peer_snapshots(self) -> list[dict[str, object]]:
        snapshots: list[dict[str, object]] = []
        for peer in sorted(self.peers.values(), key=lambda item: item.last_seen, reverse=True):
            addr = (peer.host, peer.port)
            snapshots.append(
                {
                    "peer_addr": self._peer_key(addr),
                    "first_seen": peer.first_seen.isoformat(),
                    "last_seen": peer.last_seen.isoformat(),
                    "rx_packets": peer.rx_packets,
                    "tx_packets": peer.tx_packets,
                    "rx_bytes": peer.rx_bytes,
                    "tx_bytes": peer.tx_bytes,
                    "status": "active" if self.last_client_addr == addr else "idle",
                    "is_current_target": self.current_target_addr == addr,
                }
            )
        return snapshots

    async def start(self) -> None:
        if self.running:
            return
        loop = asyncio.get_running_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: UDPServerProtocol(self),
            local_addr=(self.config.bind_ip, self.config.bind_port),
        )
        self.running = True
        self.emit_system_log("info", "service", f"UDP server started on {self.config.bind_ip}:{self.config.bind_port}")

    async def stop(self) -> None:
        if self.transport:
            self.transport.close()
            self.transport = None
        self.running = False
        self.emit_system_log("info", "service", "UDP server stopped")

    async def send_manual(self, payload_text: str, target_addr: tuple[str, int] | None = None) -> None:
        payload = parse_payload(payload_text, self.config.hex_mode)
        target = target_addr or self.current_target_addr or self.last_client_addr
        if not target:
            raise RuntimeError("no device address available")
        self.select_target(target)
        await self._send_payload(payload, target, "manual")

    async def handle_datagram(self, data: bytes, addr: tuple[str, int]) -> None:
        self.rx_count += len(data)
        self.record_client_addr(addr)
        self._get_or_create_peer(addr).rx_bytes += len(data)
        self.emit_system_log("info", "rule", f"device -> server {addr[0]}:{addr[1]}")
        self._persist_packet("device -> server", addr, (self.config.bind_ip, self.config.bind_port), data)

        if not self.config.custom_reply_data.strip():
            self.emit_system_log("warning", "rule", "UDP packet received but custom reply payload is empty")
            return

        reply_payload = parse_payload(self.config.custom_reply_data, self.config.hex_mode)
        await self._send_payload(reply_payload, addr, "server -> device", source=addr)

    async def _send_payload(
        self,
        payload: bytes,
        target: tuple[str, int],
        direction: str,
        source: tuple[str, int] | None = None,
    ) -> None:
        if not self.transport:
            raise RuntimeError("UDP server is not running")

        self.transport.sendto(payload, target)
        self.tx_count += len(payload)
        peer = self._get_or_create_peer(target)
        peer.last_seen = datetime.now(timezone.utc)
        peer.tx_packets += 1
        peer.tx_bytes += len(payload)
        src = source or (self.config.bind_ip, self.config.bind_port)
        self.emit_system_log("info", "network", f"{direction} {src[0]}:{src[1]} -> {target[0]}:{target[1]}")
        self._persist_packet(direction, src, target, payload)

    def _persist_packet(self, direction: str, src: tuple[str, int], dst: tuple[str, int], payload: bytes) -> None:
        db = self.db_factory()
        try:
            packet_logger.log_packet(
                db=db,
                service_type="udp_server",
                protocol="UDP",
                direction=direction,
                src_ip=src[0],
                src_port=src[1],
                dst_ip=dst[0],
                dst_port=dst[1],
                payload=payload,
            )
        finally:
            db.close()

    def emit_system_log(self, level: str, category: str, message: str, detail: str = "") -> None:
        db = self.db_factory()
        try:
            system_log_service.log_to_db(level, category, message, detail, db=db)
        finally:
            db.close()
