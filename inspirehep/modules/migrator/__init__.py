# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE.
# Copyright (C) 2014-2017 CERN.
#
# INSPIRE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INSPIRE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

"""INSPIRE migrator extension."""

from __future__ import absolute_import, division, print_function

from .cli import migrator


class INSPIREMigrator(object):
    """INSPIRE migrator extension."""

    def __init__(self, app=None, **kwargs):
        """Extension initialization."""
        if app:
            self.init_app(app, **kwargs)

    def init_app(self, app, **kwargs):
        """Initialize application object."""
        app.cli.add_command(migrator)
        self.init_config(app.config)
        # Save reference to self on object
        app.extensions['inspire-migrator'] = self

    def init_config(self, config):
        """Initialize configuration."""
        config.setdefault(
            'CFG_INSPIRE_LEGACY_BASEURL',
            'http://inspireheptest.cern.ch'
        )


__all__ = ('INSPIREMigrator',)
