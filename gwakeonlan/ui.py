##
#     Project: gWakeOnLAN
# Description: Wake up your machines using Wake on LAN
#      Author: Fabio Castelli (Muflone) <muflone@vbsimple.net>
#   Copyright: 2009-2014 Fabio Castelli
#     License: GPL-2+
#  This program is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by the Free
#  Software Foundation; either version 2 of the License, or (at your option)
#  any later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
##

from gi.repository import Gtk
from gi.repository import Gio
from gwakeonlan.constants import *
from gwakeonlan.functions import *
from gwakeonlan.settings import Settings
from gwakeonlan.model_machines import ModelMachines
from gwakeonlan.detail import DetailWindow
from gwakeonlan.arpcache import ARPCacheWindow
from gwakeonlan.about import AboutWindow

class MainWindow(object):
  def __init__(self, application, settings):
    self.application = application
    self.loadUI()
    self.settings = settings
    self.settings.load_hosts(self.model)
    # Restore the saved size and position
    if self.settings.get_value('width', 0) and self.settings.get_value('height', 0):
      self.winMain.set_default_size(
        self.settings.get_value('width', -1),
        self.settings.get_value('height', -1))
    if self.settings.get_value('left', 0) and self.settings.get_value('top', 0):
      self.winMain.move(
        self.settings.get_value('left', 0),
        self.settings.get_value('top', 0))
    # Load the others dialogs
    self.about = AboutWindow(self.winMain, False)
    self.detail = DetailWindow(self.winMain, False)
    self.detected_addresses = {}

  def run(self):
    "Show the UI"
    self.winMain.show_all()

  def loadUI(self):
    "Load the interface UI"
    builder = Gtk.Builder()
    builder.add_from_file(FILE_UI_MAIN)
    # Obtain widget references
    self.winMain = builder.get_object("winMain")
    self.model = ModelMachines(builder.get_object('storeMachines'))
    self.btnAdd = builder.get_object('btnAdd')
    self.btnEdit = builder.get_object('btnEdit')
    self.btnDelete = builder.get_object('btnDelete')
    self.tvwMachines = builder.get_object('tvwMachines')
    # Set various properties
    self.winMain.set_title(APP_NAME)
    self.winMain.set_icon_from_file(FILE_ICON)
    self.winMain.set_application(self.application)
    # Connect signals from the glade file to the functions with the same name
    builder.connect_signals(self)

  def on_winMain_delete_event(self, widget, event):
    "Close the application"
    self.about.destroy()
    self.detail.destroy()
    self.settings.set_sizes(self.winMain)
    self.settings.save()
    self.winMain.destroy()
    self.application.quit()

  def on_btnAbout_clicked(self, widget):
    "Show the about dialog"
    self.about.show()

  def on_cellMachinesSelected_toggled(self, renderer, treeIter, data=None):
    "Select or deselect an item"
    self.model.set_selected(treeIter,
      not self.model.get_selected(treeIter))

  def on_btnAdd_clicked(self, widget):
    "Add a new empty machine"
    self.detail.load_data('', '', 9, BROADCAST_ADDRESS)
    # Check if the OK button in the dialog was pressed
    if self.detail.show() == Gtk.ResponseType.OK:
      self.model.add_machine(
        False,
        self.detail.get_machine_name(),
        self.detail.get_mac_address(),
        self.detail.get_portnr(),
        self.detail.get_destination()
      )
      # Automatically select the last inserted item
      self.tvwMachines.set_cursor(self.model.count() - 1)

  def on_btnEdit_clicked(self, widget):
    "Edit the selected machine"
    selected = self.tvwMachines.get_selection().get_selected()[1]
    if selected:
      self.detail.load_data(
        self.model.get_machine_name(selected),
        self.model.get_mac_address(selected),
        self.model.get_portnr(selected),
        self.model.get_destination(selected)
      )
      if self.detail.show() == Gtk.ResponseType.OK:
        self.model.set_machine_name(selected, self.detail.get_machine_name())
        self.model.set_mac_address(selected, self.detail.get_mac_address())
        self.model.set_portnr(selected, self.detail.get_portnr())
        self.model.set_destination(selected, self.detail.get_destination())

  def on_menuitemARPCache_activate(self, widget):
    "Show the ARP cache picker dialog"
    dialog = ARPCacheWindow(self.settings, self.winMain, False)
    # Check if the OK button in the dialog was pressed
    if dialog.show() == Gtk.ResponseType.OK:
      # Check if a valid machine with MAC Address was selected
      if dialog.get_mac_address():
        # Add the machine to the model from the ARP cache
        self.model.add_machine(False, dialog.get_ip_address(),
          dialog.get_mac_address(), 9, BROADCAST_ADDRESS)
        # Select the last machine and edit its details
        self.tvwMachines.set_cursor(self.model.count() - 1)
        self.btnEdit.emit('clicked')

    # Destroy the dialog
    dialog.destroy()

  def on_tvwMachines_row_activated(self, widget, path, column):
    "The double click on a row acts as the Edit machine button"
    self.btnEdit.emit('clicked')

  def on_btnDelete_clicked(self, widget):
    "Delete the selected machine"
    selected_iter = self.tvwMachines.get_selection().get_selected()[1]
    if selected_iter:
      # Ask confirmation to delete the selected machine
      if show_message_dialog_yesno(
        self.winMain,
        _('Are you sure you want to remove the selected machine?'),
        _('Delete machine'),
        Gtk.ResponseType.NO
      ) == Gtk.ResponseType.YES:
        # The confirmation response was yes, delete the selected machine
        self.model.remove(selected_iter)

  def on_btnWake_clicked(self, widget):
    "Launch the Wake On LAN for all the selected machines"
    for machine in self.model:
      if self.model.get_selected(machine):
        # If a machine was selected then it will turned on
        wake_on_lan(
          self.model.get_mac_address(machine),
          self.model.get_portnr(machine),
          self.model.get_destination(machine),
          self.settings
        )
