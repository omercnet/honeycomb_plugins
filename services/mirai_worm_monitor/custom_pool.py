# -*- coding: utf-8 -*-
"""Mirai Worm Gevent Pool."""
from __future__ import unicode_literals
import gevent.pool


class CustomPool(gevent.pool.Pool):
    """An extension of the gevent pool.

    If this pool becomes full, it drops the oldest connections instead of waiting for them to end.
    """

    def __init__(self, logger, size=0, greenlet_class=None):
        self.open_connection = []  # FIFO for connection
        self.open_connection_dico_ip = {}  # 2-way dico
        self.open_connection_dico_green = {}  # 2-way dico
        self.logger = logger
        gevent.pool.Pool.__init__(self, size + 1, greenlet_class)  # +1 to avoid the semaphore

    def add(self, greenlet):
        """Add the greenlet to the pool."""
        source = greenlet.args[2][1][0] + ':' + str(greenlet.args[2][1][1])

        # With 1, we avoid the wait caused by the semaphore
        if self.free_count() < 2:
            # /!\ pool full, untracking oldest greenlet /!\
            oldest_source = self.open_connection[0]
            oldest_greenlet = self.open_connection_dico_ip[oldest_source]

            # kill the greenlet, this also closes its associated socket
            self.killone(oldest_greenlet, block=False)

        # Add the connection to the dicos
        self.open_connection.append(source)
        self.open_connection_dico_ip[source] = greenlet
        self.open_connection_dico_green[str(greenlet)] = source
        gevent.pool.Pool.add(self, greenlet)

    # discard the greenlet, free one slot of the pool
    def _discard(self, greenlet):
        to_del_greenlet = str(greenlet)
        to_del_source = self.open_connection_dico_green[to_del_greenlet]
        gevent.pool.Pool._discard(self, greenlet)

        # cleaning dicos
        del self.open_connection_dico_ip[to_del_source]
        del self.open_connection_dico_green[to_del_greenlet]
        self.open_connection.remove(to_del_source)

    def log_pool_info(self):
        """Debug log pool info."""
        self.logger.debug("pool_size: %d", self.free_count() - 1)

    def remove_connection(self, to_del_source):
        """Remove connection from pool."""
        to_del_greenlet = self.open_connection_dico_ip[to_del_source]
        self._discard(to_del_greenlet)
