#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2015 Thomas Voegtlin
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidgetItem, QMenu
from bitcoinx import Address

from electrumsv.i18n import _
from electrumsv.util import format_time, age
from electrumsv.paymentrequest import PR_UNKNOWN

from .util import MyTreeWidget, pr_tooltips, pr_icons, read_QIcon


class RequestList(MyTreeWidget):
    filter_columns = [0, 1, 2, 3, 4]  # Date, Account, Address, Description, Amount

    def __init__(self, parent):
        self.wallet = parent.parent_wallet.get_default_wallet()
        MyTreeWidget.__init__(self, parent, self.create_menu, [
            _('Date'), _('Address'), '', _('Description'), _('Amount'), _('Status')], 3)
        self.currentItemChanged.connect(self.item_changed)
        self.itemClicked.connect(self.item_changed)
        self.setSortingEnabled(True)
        self.setColumnWidth(0, 180)
        self.hideColumn(1)

    def item_changed(self, item):
        if item is None:
            return
        if not item.isSelected():
            return
        wallet_id, addr = item.data(0, Qt.UserRole)
        wallet = self.parent.parent_wallet.get_wallet_for_account(wallet_id)
        req = wallet.receive_requests[addr]
        expires = age(req['time'] + req['exp']) if req.get('exp') else _('Never')
        amount = req['amount']
        message = wallet.labels.get(addr.to_string(), '')
        self.parent.receive_address_e.setText(addr.to_string())
        self.parent.receive_message_e.setText(message)
        self.parent.receive_amount_e.setAmount(amount)
        self.parent.expires_combo.hide()
        self.parent.expires_label.show()
        self.parent.expires_label.setText(expires)
        self.parent.new_request_button.setEnabled(True)

    def on_update(self):
        # hide receive tab if no receive requests available
        b = len(self.wallet.receive_requests) > 0
        self.setVisible(b)
        self.parent.receive_requests_label.setVisible(b)
        if not b:
            self.parent.expires_label.hide()
            self.parent.expires_combo.show()

        # update the receive address if necessary
        current_address_string = self.parent.receive_address_e.text().strip()
        current_address = (Address.from_string(current_address_string)
                           if len(current_address_string) else None)
        domain = self.wallet.get_receiving_addresses()
        addr = self.wallet.get_unused_address()
        if not current_address in domain and addr:
            self.parent.set_receive_address(addr)
        self.parent.new_request_button.setEnabled(addr != current_address)

        wallet_id = self.wallet.get_id()

        # clear the list and fill it again
        self.clear()
        for req in self.wallet.get_sorted_requests(self.config):
            address = req['address']
            if address not in domain:
                continue
            timestamp = req.get('time', 0)
            amount = req.get('amount')
            expiration = req.get('exp', None)
            message = req.get('memo', '')
            date = format_time(timestamp, _("Unknown"))
            status = req.get('status')
            amount_str = self.parent.format_amount(amount) if amount else ""
            item = QTreeWidgetItem([date, address.to_string(), '', message,
                                    amount_str, pr_tooltips.get(status,'')])
            item.setData(0, Qt.UserRole, (wallet_id, address))
            if status is not PR_UNKNOWN:
                item.setIcon(6, read_QIcon(pr_icons.get(status)))
            self.addTopLevelItem(item)


    def create_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return
        addr = item.data(0, Qt.UserRole)
        req = self.wallet.receive_requests[addr]
        column = self.currentColumn()
        column_title = self.headerItem().text(column)
        column_data = item.text(column).strip()
        menu = QMenu(self)
        menu.addAction(_("Copy {}").format(column_title),
                       lambda: self.parent.app.clipboard().setText(column_data))
        menu.addAction(_("Copy URI"),
                       lambda: self.parent.view_and_paste(
                           'URI', '', self.parent.get_request_URI(addr)))
        menu.addAction(_("Save as BIP270 file"),
            lambda: self.parent.export_payment_request(addr))
        menu.addAction(_("Delete"),
            lambda: self.parent.delete_payment_request(addr))
        menu.exec_(self.viewport().mapToGlobal(position))
